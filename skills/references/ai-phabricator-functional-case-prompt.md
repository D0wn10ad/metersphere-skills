# v2 工单驱动功能用例生成 Prompt 模板（Phabricator 工单 / Excel 模板 → 功能用例）

用于 v2 分支的功能用例（functional-case）生成。工作流：通过 Phabricator MCP 读取史诗、用户故事与技术工单，解析目标功能模块的 ID，把工单需求或 excel 导入模板格式的用例文件映射为 v2 字段契约的 JSON 草稿，再按标准用例构建流程批量写入；支持把原始用例文件上传到项目文件管理并关联到全部拆分出的用例。

## 使用方式

1. 通过 Phabricator MCP 读取史诗 `<epicTaskId>`（可选）→ 用户故事 `<storyTaskId>` → 技术工单 `<techTaskId>`（按任务 ID 列出 / 获取），提取需求、验收标准、数据约束
2. 解析项目 ID：`./skills/scripts/v2/ms.sh project list`（按 `name` 字段匹配项目名，0 个或多个匹配时告警，不自动选）
3. 解析模块 ID：`./skills/scripts/v2/ms.sh functional-module list '<projectId>'`（按 `name` 匹配目标功能子模块名，0 个或多个匹配时告警，不自动选）
4. 构建用例草稿（双输入，二选一或并用）：
   - **输入 A（Phabricator 工单驱动）**：把工单需求、验收标准、数据约束与下面 Prompt 一起贴给 AI，生成 v2 字段契约 JSON 草稿
   - **输入 B（excel 导入模板格式的用例文件）**：`./skills/scripts/v2/ms.sh functional-case generate <projectId> [moduleId] <templateId> <需求文件>` 得到草稿（moduleId 现可省略，省略时脚本解析为真实「未规划用例」节点）；或直接 `./skills/scripts/v2/ms.sh functional-case import '<projectId>' <excelFile>` 走服务端导入（.xmind 同端点）
   - **输入 C（docx / pdf / xlsx / xmind 用例文件）**：`./skills/scripts/v2/ms.sh functional-case split-create '<projectId>' '<moduleId>' <用例文件>` 一键拆分并写入；或先 `ms_split_cases.py` 拆分得到草稿再 batch-create
5. 确定性批量写入：`./skills/scripts/v2/ms.sh functional-case batch-create '<json-file>'`；需把原始用例文件关联到全部拆分出的用例时，先 `./skills/scripts/v2/ms.sh file create '<json>' <本地文件>` 上传到项目文件管理，再 `batch-create --file-id <fileMetadataId>`
6. 关联与核对：separate 通道用 `./skills/scripts/v2/ms.sh attachment relate '<caseId>' <fileId>...` 逐条关联；批量关联需求（可选，需 MeterSphere 已配置 Phabricator 第三方平台集成）用 `./skills/scripts/v2/ms.sh functional-case relate-demand '<projectId>' <demandId> <caseId>...`

### 占位符与工单标签契约（调用方须知）

- **三个工单占位符**：史诗 `<epicTaskId>`（可选）、用户故事 `<storyTaskId>`、技术工单 `<techTaskId>`。⚠️ 调用方契约：用户故事与技术工单**必须分别提供两个工单号**（沿袭 ai-phabricator-api-case-prompt.md 契约），史诗占位符为本次扩展新增——只在工单层级包含 epic 时提供，用于按 epic 溯源。
- **打标签时必须同时包含用户故事 + 技术两个工单号**（史诗可选追加），两条写入路径都要满足：
  - 确定性路径：`functional-case batch-create '<json-file>'`——标签写在草稿 JSON 数组每个元素的 `tags` 字段里。
  - AI 路径：同上，标签由模型在输出的 JSON 中给出，由调用方逐条提交。
- `tags` 本身是**可选**的：整体省略该键合法。是否打标签由调用方决定，一旦打标签就要包含故事 + 技术两个工单号。

## Prompt

你现在是资深功能测试分析师。请按以下流程，根据 Phabricator 工单或 excel 导入模板格式的用例文件，生成 MeterSphere v2 功能用例。

**阶段 1：读取 Phabricator 工单**

通过 Phabricator MCP 获取工单内容。工单层级遍历：先用 `phabricator_phabricator_task_search` 按 ID 获取技术工单 `<techTaskId>` 与用户故事 `<storyTaskId>`；若提供史诗 `<epicTaskId>`，用 `task_search` 的 `subtaskIDs` / `parentIDs` 过滤器沿 epic → story → tech 链遍历，或用 `phabricator_phabricator_phid_lookup` 解析 `T123` / `@用户名` 形式的引用。从工单中提取：

- 需求（本次要做什么）
- 验收标准（可验证的完成条件）
- 数据约束（字段规则、取值范围、必填项）
- 受影响的功能模块（工单中提到的页面 / 功能）

如果当前环境的 Phabricator MCP 不具备按任务 ID 获取工单的 affordance，停止并报告，不要自行编造工具或数据。

**阶段 2：解析项目与功能模块的 ID**

1. 用 `./skills/scripts/v2/ms.sh project list` 列出项目，按 `name` 字段匹配目标项目名，得到 `projectId`。0 个匹配说明项目名写错或环境变量不对；多个匹配说明项目名不唯一，需人工确认，不要擅自选一个。
2. 用 `./skills/scripts/v2/ms.sh functional-module list '<projectId>'` 列出功能模块树，遍历 JSON 按 `name` 匹配目标子模块名，得到 `moduleId` 与模块路径 `nodePath`。0 个匹配说明模块名写错；多个匹配说明模块名不唯一，需人工确认。注意这是 `functional-module` 资源，不是接口的 `api-module`。

**阶段 3：双输入映射为用例草稿**

- **输入 A（工单驱动）**：把工单的需求与验收标准逐条映射为功能用例。每条验收标准至少一条用例；补充主流程、异常流程、边界值、权限校验、空值 / 非法值场景。
- **输入 B（excel 导入模板格式行）**：若调用方提供了符合 excel 导入模板列契约（见下文「Excel 导入模板列契约」）的用例文件，把每行数据映射为一条用例草稿：用例名称 → `name`，所属模块 → `nodePath`，标签 → `tags`，前置条件 → `precondition`，步骤描述 / 预期结果 → `steps`，编辑模式 → `caseEditType`，备注 → `remark`，用例等级 → `priority`。关键列（用例名称、所属模块）缺失的行跳过并告警，不要编造。
- 两种输入并用时，先按输入 B 拆出确定性用例，再用输入 A 补充工单要求但 excel 未覆盖的场景，最后合并去重。

**阶段 4：输出 v2 字段契约 JSON**

按下面「输出规则」一节的字段契约输出 JSON 数组。`tags` 契约见下文「工单标签」一节：必须是 JSON 编码的字符串。

**工单标签（两条写入路径都适用）**

在本流程下（工单驱动，工单号总是已知），每条生成的用例都可带 `tags`，且必须**同时包含用户故事工单号与技术工单号两个元素**（如 `["<storyTaskId>","<techTaskId>"]`），史诗工单号可选追加为第三个元素，便于按 ticket 双向溯源。

- `tags` 必须是 **JSON 编码的字符串**，不是 JSON 数组。正确载荷是 `"tags": "[\"T-story-123\",\"T-tech-456\"]"`——一个字符串，其内容本身是 JSON 数组。写成裸数组 `"tags": ["T-story-123","T-tech-456"]` 会丢失工单信息。原因（MeterSphere v2.10 源码）：v2 功能用例创建走 `EditTestCaseRequest extends TestCaseWithBLOBs`，实体字段是 `private String tags`；excel 导入的标签列同样走 JSON 数组解析（见「Excel 导入模板列契约」），普通逗号文本会被静默丢弃。
- `tags` 是**可选**字段：整体省略该键合法。
- 单个标签元素不超过 64 字符（仓库约定：保持按 ticket 前缀可检索，避免整串溢出）。工单号远小于该上限。

然后进入下面的用例构建流程。

## 用例构建流程（复用）

**确定性批量写入（batch-create）**

把 AI 返回的 JSON 数组保存为文件，执行：

`./skills/scripts/v2/ms.sh functional-case batch-create '<json-file>'`

- 文件内是 JSON 数组，每个元素一个功能用例对象，字段见「输出规则」。
- 需要把原始用例文件（excel / docx / pdf / xmind）关联到全部拆分出的用例时：
  1. 先上传到项目文件管理：`./skills/scripts/v2/ms.sh file create '<json>' <本地文件>`（JSON body 指定项目与文件名），得到 `fileMetadataId`。
  2. 再写入并同调用关联：`./skills/scripts/v2/ms.sh functional-case batch-create '<json-file>' --file-id <fileMetadataId>`——脚本对每条用例注入 `relateFileMetaIds`（去重追加），一次调用完成「创建 + 关联」，无需单独 relate 调用。
  3. 备用通道（separate 模式）：先 `batch-create` 写入，再对每条新用例执行 `./skills/scripts/v2/ms.sh attachment relate '<caseId>' <fileId>...`（服务端校验 `belongType == "testcase"`；脚本先经文件存在性预校验）。

**关联文件管理引用的说明**

`relateFileMetaIds` 是 v2.10 `EditTestCaseRequest` 的字段（关联文件管理引用 ID，新增操作）：上传文件到项目文件管理后，引用其 `fileMetadataId` 即可让用例与文件建立关联，文件本体不复制。下载已关联文件时走附件下载通道。

**需求关联（可选）**

MeterSphere 已配置 Phabricator 第三方平台集成时，可把用例批量关联到需求：

`./skills/scripts/v2/ms.sh functional-case relate-demand '<projectId>' <demandId> <caseId>...`

- `demandId` 来自 MeterSphere 需求管理（第三方平台需求列表）；`demandId == "other"` 时必须加 `--demand-name <名称>` 参数。
- 服务端走 `POST /batch/relate/demand`（载荷 `{ids:[...], demandId, demandName}`）。

**去重与重跑**

- 写入前先查：`./skills/scripts/v2/ms.sh functional-case list '{"projectId":"<projectId>"}'`。
- 若目标用例名已存在，跳过不重复创建；重跑同一流程时同样先查后写，保证幂等。

**写入安全**

- 所有写入命令必须显式传 `<projectId>`，或确保环境变量 `METERSPHERE_PROJECT_ID` 已导出。
- 未设置时脚本会拒绝执行并退出（exit 1），不要绕过。

**输出规则**

- 输出必须是**原始 JSON 数组**，不要 markdown 代码块围栏（不要 json 围栏），不要解释性文字，确保可直接被 `python3 -m json.tool` 解析。
- 用例名称用中文，风格为测试人员写法（如 `用户登录-主流程`）。
- 创建体字段集合（与 v2 草稿一致）：
  - **必填**：`name` / `projectId` / `nodeId` / `nodePath` / `priority` / `steps` / `caseEditType`。
  - `priority` 取值只能是 `P0` / `P1` / `P2` / `P3`。
  - `steps` 是 JSON 数组，每项为 `{"num": 序号, "desc": 步骤描述, "result": 预期结果}`。
  - `caseEditType` 固定为 `"STEP"`。
  - **可选**：`description` / `precondition` / `remark` / `tags`（见上面「工单标签」一节）/ `templateId` / `versionId`（仅当已知时提供，不要自行编造）。
  - 不要输出 v3 专属字段（如 `moduleId`、`customNum`、`maintainer`、`customFields`、`aiCreate` 等）——v2 使用 `nodeId` / `nodePath`（模块树），不使用模板化字段。

## Excel 导入模板列契约（v2.10 源码 TestCaseImportFiled.java 列序）

服务端 excel 导入（POST `/test/case/import`，multipart 双 part：`request` + `file`）按以下列序解析，模板列从左到右：

1. **ID**（可选——仅 Update 模式且启用自定义 ID 时有效）
2. **用例名称**（必填，≤255 字符）
3. **所属模块**（必填，≤1000 字符，模块树路径，禁止连续斜杠 `//`）
4. **标签**（可选，≤1000 字符；⚠️ **JSON 数组字符串** `["a","b"]`——服务端按 JSON 数组解析后落库，普通逗号分隔文本解析失败会被静默丢弃为空）
5. **前置条件**
6. **步骤描述**
7. **预期结果**
8. **编辑模式**（可选，取值 `TEXT` 或 `STEP`；建议 `STEP`）
9. **备注**
10. **用例状态**（可选）
11. **责任人**（可选）
12. **用例等级**（取值 `P0` / `P1` / `P2` / `P3`）
13. 自定义字段列（模板尾部追加，按项目模板定义）

- `importType` 枚举仅 `Create` | `Update`（默认 `Create`）。
- `.xmind` 文件走同一端点：服务端按扩展名分发到脑图解析器，节点前缀语义 `tc:`（用例）、`tc-P1:`（用例 + 优先级）、`pc:`（前置条件）、`rc:`（备注）、`tag:`（标签）、`id:`（自定义 ID，仅 Update）；非 `tc` 节点累积为模块路径。
- 调用方提供 excel / xmind 文件时，可直接 `functional-case import` 走服务端导入（不生成 JSON 草稿）；或按本契约拆分为 JSON 草稿再 batch-create（需要把文件关联到拆分出的用例时走后者）。

## 示例（创建体，字段与 v2 草稿一致）

```json
{
  "name": "用户登录-主流程",
  "projectId": "<projectId>",
  "nodeId": "<moduleId>",
  "nodePath": "/默认模块/登录",
  "priority": "P0",
  "steps": [
    {"num": 0, "desc": "准备测试环境，确认系统正常运行", "result": "环境准备就绪"},
    {"num": 1, "desc": "输入正确的用户名和密码，点击登录", "result": "登录成功，跳转至首页"},
    {"num": 2, "desc": "验证登录状态与页面展示", "result": "页面展示正确，会话已建立"}
  ],
  "caseEditType": "STEP",
  "tags": "[\"<storyTaskId>\",\"<techTaskId>\"]",
  "description": "验证用户使用正确凭据登录的主流程",
  "precondition": "用户已注册账号且系统正常运行"
}
```

- `tags` 是 JSON 编码的字符串：值的最外层是引号包裹的字符串，内部引号用 `\"` 转义，解码后为 `["<storyTaskId>","<techTaskId>"]`。要打标签就同时给出故事与技术两个工单号（史诗可选追加）；不打标签可整体省略该键。
- 需要关联原始用例文件时，调用方走 `batch-create --file-id <fileMetadataId>`（同调用注入 `relateFileMetaIds`），创建体本身无需携带该字段。
