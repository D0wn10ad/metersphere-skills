# Swagger / OpenAPI 3 JSON → 接口用例 AI Prompt 模板（Agent 侧流程）

适用场景：手里有一份 **Swagger / OpenAPI 3 JSON**（文件或 URL），要在 MeterSphere v2 里落成接口定义 + 接口用例。
两条路线：**A. 脚本一步到位**（推荐，幂等）；**B. 脚本生成草稿 + AI 增强**（需要定制场景/命名时）。

## 使用方式（Agent 编排）

### 路线 A：一步到位（幂等，推荐）

```bash
./skills/scripts/v2/ms.sh api import-create <projectId> [moduleId] <spec.json-or-url>
```

- 导入定义 → 按定义生成用例（成功/必填缺失/边界变体）→ 已存在同名变体自动跳过（重跑安全）
- `moduleId` 可空 = 建在根下；**`api-module create` 不受支持**（需工作空间权限），目标模块必须已存在，否则省略 moduleId
- 完成后用 `api list` / `api-case list`（自动分页合并）复核数量

### 路线 B：草稿 + AI 增强

1. `./skills/scripts/v2/ms.sh api import-generate <projectId> [moduleId] <spec.json-or-url>` —— 生成定义+用例**草稿**，不写入
2. 把草稿 JSON 贴给 AI + 下面的 Prompt，让 AI 增强场景取舍/命名/断言（保持 JSON 结构合法）
3. `./skills/scripts/v2/ms.sh api batch-create <json-file>` 写入

## 已验证的坑（务必遵守）

- **双前缀**：定义端点是 `{BASE}/api/api/definition/...`；单前缀 `/api/definition/...` 得 Spring 404（无 `success` 键）——是路径错，不是数据不存在。脚本已内置，不要手写 curl 绕过。
- **导入响应里的 id 不可查询**：fullCoverage 按 path 去重不落新行时，响应 `data.data[]` 返回解析阶段新生成的 id，GET 得 `data:null`。要拿持久化 id，**按 name 从 `api list` 解析**（`import-create`/`import-generate` 已内置此修复，重复运行同一 spec 会干净跳过）。
- **勿消费导入响应内联 request**：`apiDefinitionId` 必须来自持久化定义的 detail，否则用例归属错误。
- **spec 变更再导入**：name 变更会更新既有定义（id 不变），旧变体名不匹配 → 生成新变体用例（重跑幂等成立）。
- **OpenAPI 版本**：3.0.x 实测可用；3.1 未验证（v2.10 解析器以 3.0 为目标），3.1 spec 建议先降级转换。
- **tags**：要打标签时值必须是 JSON 编码的字符串 `"[\"T-123\"]"`，裸数组会丢标签。

## Prompt（路线 B 的 AI 增强用；输入 = import-generate 草稿 JSON + 原 spec 摘要）

你现在是资深接口测试工程师。我提供了 MeterSphere v2 的接口定义/用例草稿（由 Swagger/OpenAPI 自动生成）和原始 spec 摘要。请审阅并增强这份草稿。

要求：

1. **保持 JSON 结构合法**：字段名与层级不得改动（`name`/`projectId`/`apiDefinitionId`/`priority`/`id`/`request`/`tags` 语义见 `ai-v2-api-case-prompt.md`），只做内容增强；输出仍是可直接 `batch-create` 的 JSON。
2. **场景取舍**：在脚本生成的成功/必填缺失/边界变体之外，依据 spec 语义补充：状态码分支（404/401/403）、组合参数（可选参数组合）、分页/过滤参数边界。每个定义的用例数控制在 3-8 条，避免爆炸。
3. **命名**：中文，`<接口名>-<场景>`，与既有变体名不冲突（重名会被幂等跳过）。
4. **断言**：每条用例 `request.hashTree` 至少一条 `Assertions`（状态码断言为准；不要臆造响应体 JSONPath，除非 spec 里明确给出响应结构）。
5. **不臆造**：spec 里没有的参数/字段不要发明；`projectId`/`apiDefinitionId`/`id` 沿用草稿值（`id` 是 uuid4，草稿已给）。
6. 输出原始 JSON（无 markdown 围栏、无解释文字）。

## 复核

写入后：`api list` 与 `api-case list`（自动分页合并）按 `apiDefinitionId` 求差集，确认每个新定义都有用例；抽查一条 `api-case get <caseId>` 确认 `request` 非空壳（GUI 可编辑）。
