# v2 工单驱动接口用例生成 Prompt 模板（Phabricator 工单 → 接口用例）

用于 v2 分支的接口用例（api-case）生成。工作流：通过 Phabricator MCP 读取技术工单与用户故事，解析模块 YYYYY 的 ID，把工单需求映射到模块内已有 HTTP 接口定义，再按标准用例构建流程生成用例。

## 使用方式

1. 通过 Phabricator MCP 读取技术工单 TXXXX 与用户故事 TXXXX（按任务 ID 列出 / 获取），提取需求、验收标准、受影响接口、数据约束
2. 解析项目 ID：`./skills/scripts/v2/ms.sh project list '<workspaceId>'`（按 name 字段匹配项目名，0 个或多个匹配时告警）
3. 解析模块 ID：`./skills/scripts/v2/ms.sh api-module list '<projectId>'`（按 name 匹配模块 YYYYY，0 个或多个匹配时告警）
4. 枚举模块内接口定义：`./skills/scripts/v2/ms.sh api list '{"projectId":"<projectId>","protocols":["HTTP"]}'`
5. 确定性批量生成：`./skills/scripts/v2/ms.sh api-case generate-create '<projectId>' <definitionId>...`（显式列出全部 definitionId）
6. 对覆盖不足的定义，把 `./skills/scripts/v2/ms.sh api get <definitionId>` 的 JSON 贴给 AI，附上下面提示词，生成增强用例
7. 将 AI 返回的 JSON 用 `./skills/scripts/v2/ms.sh api-case create '<json>'` 写入，一次一条

## Prompt

你现在是资深接口测试工程师。请按以下流程，根据 Phabricator 工单为模块 YYYYY 的已有 HTTP 接口生成接口用例。

**阶段 1：读取 Phabricator 工单**

通过 Phabricator MCP 获取技术工单 TXXXX 与用户故事 TXXXX（按任务 ID 列出 / 获取任务详情）。从工单中提取：

- 需求（本次要做什么）
- 验收标准（可验证的完成条件）
- 受影响接口（工单中提到的接口 / 模块）
- 数据约束（字段规则、取值范围、必填项）

如果当前环境的 Phabricator MCP 不具备按任务 ID 获取工单的 affordance，停止并报告，不要自行编造工具或数据。

**阶段 2：解析模块 YYYYY 的 ID**

1. 用 `./skills/scripts/v2/ms.sh project list '<workspaceId>'` 列出项目，按 `name` 字段匹配目标项目名，得到 `projectId`。0 个匹配说明项目名写错或 workspaceId 不对；多个匹配说明项目名不唯一，需人工确认，不要擅自选一个。
2. 用 `./skills/scripts/v2/ms.sh api-module list '<projectId>'` 列出模块树，遍历 JSON 按 `name` 匹配模块 YYYYY，得到 `moduleId`。0 个匹配说明模块名写错；多个匹配说明模块名不唯一，需人工确认。

**阶段 3：把工单需求映射到模块 YYYYY 的已有接口定义**

用 `./skills/scripts/v2/ms.sh api list '{"projectId":"<projectId>","protocols":["HTTP"]}'` 列出项目内全部 HTTP 接口定义，按模块过滤出模块 YYYYY 的定义。对每个候选定义执行 `./skills/scripts/v2/ms.sh api get <definitionId>` 读取详情，结合工单的受影响接口与验收标准，确定哪些定义需要用例：

- 工单明确改动 / 影响的接口：必须覆盖。
- 与验收标准直接相关的接口：必须覆盖。
- 其余接口：按标准 3 变体基础覆盖。

然后进入下面的用例构建流程。该流程与 `skills/references/ai-module-api-case-prompt.md` 中的 `## 用例构建流程（复用）` 一节完全一致，本文件直接复用同一段内容。

## 用例构建流程（复用）

**确定性基础用例（批量生成写入）**

对已枚举出的每个接口定义，执行：

`./skills/scripts/v2/ms.sh api-case generate-create '<projectId>' <definitionId1> <definitionId2> ...`

- 必须把目标模块的**全部 definitionId 显式列出**，不要省略。省略 definitionId 会对整个项目生成用例，超出目标模块范围。
- 每个定义生成 3 个变体：
  - `*成功场景`：断言 200，优先级 P1
  - `*必填缺失`：首个必填 query/rest 参数置空，断言 400，优先级 P1（仅当存在必填参数）
  - `*边界场景`：首个字符串参数 = 128 个 'x'，断言 200，优先级 P2（仅当存在字符串参数）
- 覆盖说明：v2 将 query 参数存储在 `arguments` 字段（非 `query`），变体扫描 `query` / `rest`。因此参数存于 `arguments` 或仅 body 必填的定义只会生成 `*成功场景`，缺少必填缺失与边界覆盖，这类定义必须交给下面的 AI 增强步骤补偿。

**AI 增强变体（逐条创建）**

对确定性步骤中覆盖不足的定义（只有 `*成功场景`，或需求 / 工单要求更多场景），执行：

1. 读取定义详情：`./skills/scripts/v2/ms.sh api get <definitionId>`，拿到 method / path / 请求参数 / 响应结构。
2. 把定义 JSON 贴给 AI，附上 `skills/references/ai-v2-api-case-prompt.md` 的字段契约，生成增强用例，覆盖：
   - 非法类型（如字符串字段传数字）
   - 非法取值（如枚举外取值）
   - 资源不存在（如不存在的 ID）
   - 权限不足（仅当接口语义明显涉及权限）
3. 每条用例用 `./skills/scripts/v2/ms.sh api-case create '<json>'` 写入，一次一条。

**去重与重跑**

- 写入前先查：`./skills/scripts/v2/ms.sh api-case list '{"projectId":"<projectId>","apiDefinitionId":"<definitionId>"}'`。
- 若目标用例名已存在，跳过不重复创建；重跑同一流程时同样先查后写，保证幂等。

**写入安全**

- 所有写入命令必须显式传 `<projectId>`，或确保环境变量 `METERSPHERE_PROJECT_ID` 已导出。
- 未设置时脚本会拒绝执行并退出（exit 1），不要绕过。

**输出规则**

- 输出必须是**原始 JSON**，不要 markdown 代码块围栏（不要 json 围栏），不要解释性文字，确保可直接被 `python3 -m json.tool` 解析。
- 用例名称用中文，风格为测试人员写法（如 `获取用户详情-200`）。
- 创建体只包含 `name` / `projectId` / `apiDefinitionId` / `priority`（可选 `description` / `tags` / `versionId`），不要输出服务端自动生成的字段（`id`、`num`、`createTime`、`createUser`、`caseStatus` 等）。

## 参考：真实 api-case 字段树（来自 `ms.sh api-case get` 实测响应，仅作字段参考，创建体只需 name/projectId/apiDefinitionId/priority）

```json
{
  "id": "308ded46-6225-4516-8bcd-4b972b37261d",
  "projectId": "184896ef-073c-11f1-9f0a-0242ac1e0a08",
  "name": "v2-apicase-qa-1789790932089",
  "priority": "P0",
  "apiDefinitionId": "4b89bc21-214d-4c11-9acf-0bfc127e7b99",
  "createUserId": "admin",
  "updateUserId": "admin",
  "createTime": 1789790932378,
  "updateTime": 1789790932378,
  "num": 100003001,
  "tags": null,
  "caseStatus": "Underway",
  "versionId": "3b493bd1-073c-11f1-9f0a-0242ac1e0a08",
  "description": null,
  "request": "null",
  "createUser": "Administrator",
  "updateUser": "Administrator",
  "apiMethod": "GET",
  "active": false,
  "responseActive": false
}
```

## 示例（创建体）

```json
{
  "name": "获取用户详情-200",
  "projectId": "<projectId>",
  "apiDefinitionId": "<apiDefinitionId>",
  "priority": "P1",
  "description": "验证使用有效用户 ID 获取用户详情的成功场景"
}
```