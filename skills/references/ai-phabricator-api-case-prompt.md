# v2 工单驱动接口用例生成 Prompt 模板（Phabricator 工单 → 接口用例）

用于 v2 分支的接口用例（api-case）生成。工作流：通过 Phabricator MCP 读取技术工单与用户故事，解析目标子模块的 ID，把工单需求映射到模块内已有 HTTP 接口定义，再按标准用例构建流程生成用例。

## 使用方式

1. 通过 Phabricator MCP 读取技术工单 `<techTaskId>` 与用户故事 `<storyTaskId>`（按任务 ID 列出 / 获取），提取需求、验收标准、受影响接口、数据约束
2. 解析项目 ID：`./skills/scripts/v2/ms.sh project list '<workspaceId>'`（按 name 字段匹配项目名，0 个或多个匹配时告警）
3. 解析模块 ID：`./skills/scripts/v2/ms.sh api-module list '<projectId>'`（按 name 匹配目标子模块名，0 个或多个匹配时告警）
4. 枚举模块内接口定义：`./skills/scripts/v2/ms.sh api list '{"projectId":"<projectId>","protocols":["HTTP"]}'`
5. 确定性批量生成：`./skills/scripts/v2/ms.sh api-case generate-create --tags <标签[,标签...]> '<projectId>' <definitionId>...`（显式列出全部 definitionId）
6. 对覆盖不足的定义，把 `./skills/scripts/v2/ms.sh api get <definitionId>` 的 JSON 贴给 AI，附上下面提示词，生成增强用例
7. 将 AI 返回的 JSON 用 `./skills/scripts/v2/ms.sh api-case create '<json>'` 写入，一次一条

### 占位符与工单标签契约（调用方须知）

- **两个工单占位符**：技术工单 `<techTaskId>`、用户故事 `<storyTaskId>`。⚠️ 调用方契约变更：旧版模板这两处复用同一个占位符（一个值被填两次），现在**必须分别提供两个工单号**；只提供一个值无法区分技术工单与用户故事。
- **故事 + 技术两个工单号必须同时打上**，两条写入路径都要满足，只是传入机制不同：
  - 确定性路径：`./skills/scripts/v2/ms.sh api-case generate-create --tags <storyTaskId>,<techTaskId> '<projectId>' <definitionId>...`——标签经 `--tags` 传入（可选、可重复），由脚本序列化后写进每条生成的用例。
  - AI 路径：`./skills/scripts/v2/ms.sh api-case create '<json>'`——标签写在模型输出的 JSON 的 `tags` 字段里，由调用方逐条提交。
- `tags` 本身是**可选**的：整体省略该键合法，写 `"[]"` 也合法（服务端归一化为空串）。是否打标签由调用方决定，一旦打标签就要包含故事 + 技术两个工单号。

## Prompt

你现在是资深接口测试工程师。请按以下流程，根据 Phabricator 工单为目标子模块的已有 HTTP 接口生成接口用例。

**阶段 1：读取 Phabricator 工单**

通过 Phabricator MCP 获取技术工单 `<techTaskId>` 与用户故事 `<storyTaskId>`（按任务 ID 列出 / 获取任务详情）。从工单中提取：

- 需求（本次要做什么）
- 验收标准（可验证的完成条件）
- 受影响接口（工单中提到的接口 / 模块）
- 数据约束（字段规则、取值范围、必填项）

如果当前环境的 Phabricator MCP 不具备按任务 ID 获取工单的 affordance，停止并报告，不要自行编造工具或数据。

**阶段 2：解析目标子模块的 ID**

1. 用 `./skills/scripts/v2/ms.sh project list '<workspaceId>'` 列出项目，按 `name` 字段匹配目标项目名，得到 `projectId`。0 个匹配说明项目名写错或 workspaceId 不对；多个匹配说明项目名不唯一，需人工确认，不要擅自选一个。
2. 用 `./skills/scripts/v2/ms.sh api-module list '<projectId>'` 列出模块树，遍历 JSON 按 `name` 匹配目标子模块名，得到 `moduleId`。0 个匹配说明模块名写错；多个匹配说明模块名不唯一，需人工确认。

**阶段 3：把工单需求映射到目标子模块的已有接口定义**

用 `./skills/scripts/v2/ms.sh api list '{"projectId":"<projectId>","protocols":["HTTP"]}'` 列出项目内全部 HTTP 接口定义，按模块过滤出目标子模块的定义。对每个候选定义执行 `./skills/scripts/v2/ms.sh api get <definitionId>` 读取详情，结合工单的受影响接口与验收标准，确定哪些定义需要用例：

- 工单明确改动 / 影响的接口：必须覆盖。
- 与验收标准直接相关的接口：必须覆盖。
- 其余接口：按标准 3 变体基础覆盖。

**阶段 4：判定接口受众并应用网关前缀**

根据工单内容判断每个受影响接口的受众，并据此确定端点路径前缀（网关主机前缀）：

- 工单明确接口面向**管理员**（管理端 / admin）使用：该接口端点路径带 `/iapi/` 前缀（IAPI 网关主机如 `iapi.dev.igus.cn`，路径常含 `managed` 段）。
- 工单明确接口面向**普通用户**（用户端 / 前台）使用：该接口端点路径带 `/eapi/` 前缀（EAPI 网关主机如 `eapi.dev.igus.cn`）。
- 同一逻辑接口可能同时被两类用户使用，经不同 API 网关暴露为两个不同端点（如 `iapi...` 与 `eapi...` 两套网关各一个实例）：二者都要覆盖——在阶段 3 的候选定义中，将这两个端点对应的定义都纳入用例生成范围。
- 分组与模块命名按网关区分，形如 `<微服务名>_iapi` / `<微服务名>_eapi`：`XXX` 为微服务名**占位符**（如 `XXX_iapi`、`XXX_eapi`），使用时须替换为具体微服务名、不可字面使用——微服务 `Admin`、`order-service` 分别对应 `Admin-iapi`、`order-service_eapi`（实测另有 `iapi_` 前缀形式）。实测分组示例（`TS_costService`、`TS_ecom_costOuer_APIs`、`TS_edge_OA_APIs`、`TS_admin_iapi_APIs`、`E2E_cost`）：分组常带 `TS_` 前缀，模块（folder）常以 `API::` 开头（`API::configurations`、`API::article-cost/{article_code}`、`API::costcoefficient`、`API::workshop-infos`），用例常见 `流: <场景>`（如 `流: 计算材料成本`）与 `TC## - <描述>`（如 `TC01 - 委外采购件 不计算工时，总成本=材料成本×数量×成本系数`）两种形态。阶段 2 匹配目标子模块名、阶段 3 过滤定义时按受众选择对应网关的模块——同名模块在两个网关下会各有一个变体，不要选错。
- 工单未明确受众：不臆断前缀，按定义中的原始路径处理，并在报告中注明需人工确认。

在阶段 3 读取定义详情（`./skills/scripts/v2/ms.sh api get <definitionId>` 得到 method / path）时，结合本阶段判定核对 path 前缀：若工单受众是管理员而所选定义的 path 不带 `/iapi/`（如主机不含 `iapi`），优先怀疑选错了定义（可能还存在同名 `/iapi/` 变体），继续在 `./skills/scripts/v2/ms.sh api list` 结果中查找；**不要修改定义本身的 path**。

**工单标签（两条写入路径都适用）**

在本流程下（工单驱动，两个工单号总是已知），每条生成的用例都要带 `tags`，且必须**同时包含用户故事工单号与技术工单号两个元素**（如 `["<storyTaskId>","<techTaskId>"]`），便于按 ticket 双向追溯。（`tags` 字段在载荷里本身是可选的，见下一条。）

- `tags` 必须是 **JSON 编码的字符串**，不是 JSON 数组。正确载荷是 `"tags": "[\"T-story-123\",\"T-tech-456\"]"`——一个字符串，其内容本身是 JSON 数组。写成裸数组 `"tags": ["T-story-123","T-tech-456"]` 会丢失工单信息。原因（MeterSphere v2.10 源码）：`SaveApiTestCaseRequest extends ApiTestCase`，实体字段是 `private String tags`；`ApiTestCaseService.createTest()` 以 `StringUtils.equals("[]", request.getTags())` 判断后原样存入。
- `tags` 是**可选**字段：整体省略该键合法；写 `"[]"` 也合法，服务端会把它归一化为空串（落库为空值）。
- 单个标签元素不超过 64 字符（仓库约定：v2.10 的 `api_test_case.tags` 列为 `VARCHAR(1000)`，整串 JSON 存放且服务端不校验逐元素长度；限制元素长度是为了避免整串溢出并保持按 ticket 前缀可检索）。工单号远小于该上限。
- **机制分流**：`api-case generate-create` 是确定性路径，标签经 `--tags` 传入并由脚本按上述字符串形态写入；`api-case create` 是 AI 路径，标签由模型在输出的 JSON 中给出。故事 + 技术两个工单号的要求对**两条路径同样成立**。

然后进入下面的用例构建流程。该流程与 `skills/references/ai-module-api-case-prompt.md` 中的 `## 用例构建流程（复用）` 一节完全一致，本文件直接复用同一段内容。

## 用例构建流程（复用）

**确定性基础用例（批量生成写入）**

对已枚举出的每个接口定义，执行：

`./skills/scripts/v2/ms.sh api-case generate-create --tags <storyTaskId>,<techTaskId> '<projectId>' <definitionId1> <definitionId2> ...`

- 必须把目标模块的**全部 definitionId 显式列出**，不要省略。省略 definitionId 会对整个项目生成用例，超出目标模块范围。
- `--tags` 可选、可重复，用于给生成的每条用例打上故事 + 技术两个工单号；缺省时载荷里不含 `tags` 键。
- 每个定义生成 3 个变体：
  - `*成功场景`：断言 200，优先级 P1
  - `*必填缺失`：首个必填 query / rest / arguments 参数置空，断言 400，优先级 P1（仅当存在必填参数）
  - `*边界场景`：首个字符串参数 = 128 个 'x'，断言 200，优先级 P2（仅当存在字符串参数）
- 覆盖说明：v2 将 query 参数存储在 `arguments` 字段（非 `query`）；`skills/scripts/v2/ms_generate_case.py` 的变体扫描按 `query` > `rest` > `arguments` 的优先级依次覆盖三组参数（`PARAM_GROUPS = ('query', 'rest', 'arguments')`，`arguments` 条目与 `query` 同构故一并扫描）。因此**只有 body、三个参数组都没有必填或字符串参数**的定义才会只生成 `*成功场景`，缺少必填缺失与边界覆盖，这类定义必须交给下面的 AI 增强步骤补偿。

**AI 增强变体（逐条创建）**

对确定性步骤中覆盖不足的定义（只有 `*成功场景`，或需求 / 工单要求更多场景），执行：

1. 读取定义详情：`./skills/scripts/v2/ms.sh api get <definitionId>`，拿到 method / path / 请求参数 / 响应结构。
2. 把定义 JSON 贴给 AI，附上 `skills/references/ai-v2-api-case-prompt.md` 的字段契约（本模板的字段契约以本文件「输出规则」一节为准），生成增强用例，覆盖：
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
- 创建体字段集合：
  - **必填**：`name` / `projectId` / `apiDefinitionId` / `priority` / `id`。
  - **可选**：`description` / `tags`（见上面「工单标签」一节）/ `versionId`（仅当已知时提供）。
  - `id` 必须由客户端提供（uuid4）。MeterSphere v2.10 的 `ApiTestCaseService.createTest()` 只做 `test.setId(request.getId())`，文件内没有任何 `IDGenerator` 调用，服务端不会替你生成；缺 `id` 会落库失败（实测报 `Column 'id' cannot be null`）。`priority` 同理（`test.setPriority(request.getPriority())`，缺省会报 `Column 'priority' cannot be null`）。
  - 不要输出由服务端写入的字段：`num`（`getNextNum(...)` 生成）、`createTime` / `createUser`（`SessionUtils.getUser()` 取当前用户 + 当前时间）；`caseStatus` 可省略，服务端缺省填 `Underway`。
  - **版本差异**：MeterSphere v3.x 的 `ApiTestCaseService.addCase()` 在服务端 `testCase.setId(IDGenerator.nextStr())` 生成 ID，所以 v3.x（`./skills/scripts/`）写入时可以不传 `id`；本模板面向 v2.10（`./skills/scripts/v2/`），必须传。

## 参考：真实 api-case 字段树（来自 `ms.sh api-case get` 实测响应，仅作字段参考，创建体只需 name/id/projectId/apiDefinitionId/priority）

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
  "id": "<uuid4>",
  "name": "获取用户详情-200",
  "projectId": "<projectId>",
  "apiDefinitionId": "<apiDefinitionId>",
  "priority": "P1",
  "tags": "[\"<storyTaskId>\",\"<techTaskId>\"]",
  "description": "验证使用有效用户 ID 获取用户详情的成功场景"
}
```

- `id` 是必填的客户端生成 uuid4（v2.10 服务端不生成，见「输出规则」）。
- `tags` 是 JSON 编码的字符串：值的最外层是引号包裹的字符串，内部引号用 `\"` 转义，解码后为 `["<storyTaskId>","<techTaskId>"]`。要打标签就同时给出故事与技术两个工单号；不打标签可整体省略该键，或写 `"tags": "[]"`。