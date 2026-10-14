# 已有接口定义 → 接口用例 AI Prompt 模板（Agent 侧流程）

适用场景：MeterSphere v2 项目里**已存在接口定义**（手工建或导入过），要为它们批量生成接口用例。
字段级契约（id/priority/request/tags）见 `ai-v2-api-case-prompt.md`，本模板只讲编排与提示词，不重复字段树。

## 使用方式（Agent 编排）

1. **拉全接口定义**：`./skills/scripts/v2/ms.sh api list '{"projectId":"<projectId>"}'`
   （v2 起自动分页循环合并，输出 `{"success":true,"data":[全部定义]}`；双前缀 `/api/api/...` 全量视图）
2. **找缺口**（还没有用例的定义）：分别 `api list` 与 `api-case list`（同样自动分页合并），按 `apiDefinitionId` 求差集：
   `python3 -c` 读两份输出，`case_ids = {c["apiDefinitionId"] for c in cases}`，`gap = [d for d in defs if d["id"] not in case_ids]`
   ⚠️ 单前缀 `related` 类接口只返回当前用户是成员的项目，空列表 ≠ 项目不存在。
3. **读取定义详情**：对每个缺口定义 `./skills/scripts/v2/ms.sh api get <apiId>`（拿 method/path/参数/响应结构，以及要复用的 `request` 对象）。
4. **生成用例**，二选一：
   - **标准覆盖（推荐，一步到位）**：`./skills/scripts/v2/ms.sh api-case generate-create [--tags <标签>] <projectId> <definitionId>...`
     每个定义自动生成 3 个变体：`*成功场景`（断言 200，P1）/ `*必填缺失`（首个必填参数置空，断言 400，仅当存在必填参数）/ `*边界场景`（首个字符串参数 128 个 'x'，断言 200，仅当存在字符串参数）。不传 definitionId = 项目内全部 HTTP 定义。
   - **自定义设计**：把定义 JSON 贴给 AI + 下面的 Prompt，AI 返回用例创建体数组，逐条 `./skills/scripts/v2/ms.sh api-case create '<json>'` 写入。
5. **复核**：重跑 `api-case list`，确认每个缺口定义至少有 1 条用例（差集清零）。

## Prompt（自定义设计用；输入 = 一条接口定义 JSON）

你现在是资深接口测试工程师。请根据我提供的 MeterSphere v2 接口定义，为它设计并生成接口用例创建体。

要求：

1. 输出必须是 **JSON 数组**（多条用例），每条字段语义对齐 v2 `/api/testcase/create`：
   - 必填：`name`、`projectId`、`apiDefinitionId`、`priority`（`P0`/`P1`/`P2`/`P3`）、`id`（uuid4，服务端不生成）、`request`（完整 HTTPSamplerProxy 对象）
   - 可选：`description`、`tags`（必须是 JSON 编码的字符串，如 `"[\"T-123\"]"`；不打标签就省略该键）
2. `request` 以我提供的定义里的 `request` 为基础补用例侧字段：sampler 内 `id` 填**接口定义 ID**（不是用例 ID）、`name` 填定义名、`refType: "CASE"`、`hashTree` 至少含一条 `Assertions` 断言。不要从零手写，不要输出空壳 `request`（会被拒绝且 GUI 无法编辑）。
3. 场景覆盖优先级：成功场景（200）→ 必填参数缺失 → 非法类型/非法取值 → 超长/边界值 → 资源不存在 → 权限不足（仅当接口语义明显涉及权限）。没有必填/字符串参数的定义可以只有成功场景，不要硬造。
4. 用例名称用中文，风格 `<定义名>-<场景>`，如 `获取用户详情-必填参数缺失`。
5. 不要输出服务端写入的字段：`num`、`createTime`、`createUser`；`caseStatus` 可省略。
6. 输出原始 JSON（无 markdown 围栏、无解释文字），确保 `python3 -m json.tool` 可解析。

## 已知边界（如实告知，不要臆造）

- v2 的 `api-case` **没有批量创建命令**：自定义设计的多条用例需逐条 `api-case create`（标准 3 变体走 `generate-create` 一次写入）。
- `tags` 裸数组会丢标签（v2.10 实体是 String 字段）。
- `api-module create` 不受支持（需工作空间权限）：目标模块必须已存在，或把定义建在已有模块/根下。
