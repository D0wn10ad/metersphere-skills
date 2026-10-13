---
name: metersphere
description: MeterSphere REST API 的可复用 Skills 封装——支持测试资产查询、功能用例生成、接口定义导入与写入，适配多种 AI Agent 平台。
environment:
  required:
    - METERSPHERE_BASE_URL
    - METERSPHERE_ACCESS_KEY
    - METERSPHERE_SECRET_KEY
  optional: []
security:
  requiresSecrets: true
  sensitiveEnvironment: true
  externalNetworkAccess: true
  notes: 此技能需要访问 MeterSphere API，使用 ACCESS_KEY 和 SECRET_KEY 进行身份验证。请确保只向可信的 METERSPHERE_BASE_URL 发送请求。

---

# MeterSphere Skills

优先用本 skill 自带脚本,不要临时手写 curl。

> **执行前提**:下文所有 `./scripts/ms.sh` 均为相对本技能目录的相对路径。执行前必须先进入技能安装目录(或改用绝对路径):
> - npx skills 安装(OpenCode 等): `cd ~/.agents/skills/metersphere`
> - OpenClaw 安装: `cd ~/.openclaw/skills/metersphere`
>
> **MeterSphere v2 用户**:使用 `./scripts/v2/ms.sh`(自动嗅探版本,或设 `METERSPHERE_VERSION=v2` 强制指定)。v2 无组织概念,用工作空间(workspace)。

## 选择工作流

按任务类型选最短路径:

### 1. 查询类

用于:

- 查组织 / 项目 / 模块 / 模板
- 查功能用例 / 接口定义 / 接口用例
- 查评审单 / 评审详情 / 评审人 / 评审模块
- 回答"哪些用例被评审过"
- 回答"这条用例关联了多少个缺陷 / 哪些用例缺陷最多"
- 当用户查询某个功能用例时,返回:用例详情 + 缺陷 + 评审记录

优先命令:

```bash
./scripts/ms.sh organization list
./scripts/ms.sh project list
./scripts/ms.sh functional-module list <projectId>
./scripts/ms.sh functional-template list <projectId>
./scripts/ms.sh api-module list <projectId>
./scripts/ms.sh functional-case list '<JSON>'
./scripts/ms.sh api list '<JSON>'
./scripts/ms.sh api-case list '<JSON>'
./scripts/ms.sh functional-case-review list '{"caseId":"<功能用例ID>"}'
./scripts/ms.sh case-review list '{"projectId":"<项目ID>"}'
./scripts/ms.sh case-review get <reviewId>
./scripts/ms.sh case-review-detail list '{"projectId":"<项目ID>","reviewId":"<评审ID>","viewStatusFlag":false}'
./scripts/ms.sh case-review-module list <projectId>
./scripts/ms.sh case-review-user list <projectId>
./scripts/ms.sh reviewed-summary <projectId> [keyword]
./scripts/ms.sh case-report <projectId> <caseId>
./scripts/ms.sh case-report-md <projectId> <caseId>
```

### 2. 需求 → 功能用例

用于:

- 根据一句需求生成测试用例
- 根据需求文档批量生成功能用例
- 先出草稿,再让 AI 补场景
- 最终写入 MeterSphere

默认流程:

```bash
./scripts/ms.sh functional-case generate <projectId> <moduleId> <templateId> <requirement-file>
./scripts/ms.sh functional-case batch-create <json-file>
```

需要一步直写时:

```bash
./scripts/ms.sh functional-case generate-create <projectId> <moduleId> <templateId> <requirement-file>
```

### 3. Swagger / OpenAPI → 接口定义 + 接口用例

用于:

- 根据 Swagger / OpenAPI 导入接口定义
- 自动生成成功 / 必填缺失 / 边界场景接口用例
- 先本地生成,再批量写入

默认流程:

```bash
./scripts/ms.sh api import-generate <projectId> <moduleId> <openapi-file-or-url>
./scripts/ms.sh api batch-create <json-file>
```

需要一步直写时:

```bash
./scripts/ms.sh api import-create <projectId> <moduleId> <openapi-file-or-url>
```

## 处理"哪些用例被评审过"

优先用:

```bash
./scripts/ms.sh reviewed-summary <projectId> [keyword]
```

这是最高层入口,直接输出:

- 项目内总用例数
- 已被评审的用例数
- 未被评审的用例数
- 项目内总缺陷关联数 `totalBugLinks`
- 每条功能用例的 `reviewed: true/false`
- 每条功能用例参与过哪些评审单
- 每条功能用例关联了多少个缺陷 `bugCount`

如果用户直接问某条功能用例,优先用:

```bash
./scripts/ms.sh case-report-md <projectId> <caseId>
```

如果需要结构化 JSON 再用:

```bash
./scripts/ms.sh case-report <projectId> <caseId>
```

其中 Markdown 版更适合直接回复用户;JSON 版更适合继续加工。

`case-report` 返回四块:

- `summary`:用例基础信息、缺陷数、评审数、测试计划数、需求数
- `detail`:前置条件、备注、步骤、标签、附件
- `bugs`:已关联缺陷列表
- `reviews`:评审记录列表

如果用户追问某条用例的评审来源,再补:

```bash
./scripts/ms.sh functional-case-review list '{"caseId":"<功能用例ID>"}'
```

如果用户要看某个评审单里的全部用例状态,再补:

```bash
./scripts/ms.sh case-review-detail list '{"projectId":"<项目ID>","reviewId":"<评审ID>","viewStatusFlag":false}'
```

判断口径:

- `functional-case-review list` 返回非空:该功能用例可视为**被评审过**
- `case-review-detail list` 中每条记录的 `status` 代表该用例在该评审单中的当前状态,如:`UN_REVIEWED` / `UNDER_REVIEWED` / `PASS` / `UN_PASS`
- `functional/case/detail/{id}` 中的 `bugCount` 代表该用例当前关联缺陷数

## 默认执行顺序

### 查询项目或模块前

先确认:

1. `project list`
2. 需要时再查 `functional-module list` / `api-module list`

### 生成功能用例前

先确认:

1. 项目 ID
2. 功能模块 ID
3. 模板 ID

命令顺序:

```bash
./scripts/ms.sh project list
./scripts/ms.sh functional-module list <projectId>
./scripts/ms.sh functional-template list <projectId>
```

### 生成功能用例后

如需提质,再读:

- `references/ai-functional-case-prompt.md`

### 导入 OpenAPI 后

如需补断言、补异常场景、补命名,再读:

- `references/ai-api-bundle-prompt.md`

### 需要确认接口字段 / 路径 / 评审 API 时

再读:

- `references/ms-api.md`

## 本地生成能力边界

### 功能用例草稿

默认能稳定生成:

- 主流程
- 异常场景
- 边界场景
- 基础优先级
- 基础标签

### 接口定义 / 接口用例草稿

默认能稳定生成:

- 1 条接口定义
- 3 条接口用例:成功 / 必填缺失 / 边界
- 基于 example/schema 自动带值
- 基础状态码断言

### 评审与关联查询

默认能稳定回答:

- 有哪些评审单
- 某条功能用例是否参与过评审
- 某个评审单下有哪些功能用例
- 当前评审状态统计
- 哪些用例已评审 / 未评审
- 某条功能用例关联了多少个缺陷
- 某个功能用例的详情、缺陷、评审记录
- 哪些功能用例的缺陷关联数更多

## 环境变量

### 必需环境变量
```bash
METERSPHERE_BASE_URL=          # MeterSphere 实例地址(如:http://172.16.200.18:8081)
METERSPHERE_ACCESS_KEY=        # API 访问密钥
METERSPHERE_SECRET_KEY=        # API 密钥(用于本地签名,不传输)
```

### 可选环境变量
```bash
METERSPHERE_PROJECT_ID=        # 默认项目 ID
METERSPHERE_ORGANIZATION_ID=100001  # 默认组织 ID
METERSPHERE_HEADERS_JSON=      # 额外的 HTTP 头(JSON 格式,谨慎使用)
METERSPHERE_PROTOCOLS_JSON='["HTTP"]'  # 支持的协议
METERSPHERE_DEFAULT_TEMPLATE_ID= # 默认模板 ID (避免使用硬编码值)
METERSPHERE_DEFAULT_VERSION_ID=  # 默认版本 ID (避免使用硬编码值)
```

### 依赖要求
- `python3`:运行辅助脚本和数据处理
- `openssl`:本地生成请求签名(不传输密钥)
- `curl`:发送 HTTP 请求到 MeterSphere API

## 输出要求

回答 MeterSphere 查询结果时，优先输出：

- 关键 ID
- 名称
- 状态
- 计数信息（如 `bugCount` / `caseReviewCount`）
- 下一步可执行命令

如果是"单条功能用例查询"，优先按这个顺序整理：

1. 用例摘要
2. 前置条件 / 描述 / 步骤
3. 缺陷列表
4. 评审记录

不要把大段原始 JSON 一股脑全贴给用户，除非用户明确要原始返回。

## 安全注意事项

### 1. 凭证范围
- 仅提供具有最小必要权限的 MeterSphere 测试账户凭证
- 建议使用只读 API 密钥进行查询操作
- 为创建操作使用单独的、有限权限的密钥

### 2. 环境变量安全
- `.env` 文件应仅包含必要的环境变量
- 避免在 `.env` 中存放额外敏感信息
- `METERSPHERE_HEADERS_JSON` 可注入任意 HTTP 头，请谨慎使用

### 3. 外部二进制文件
- 脚本会调用 `openssl`、`curl` 和 `python3`
- 确保这些二进制文件来自受信任的来源
- 签名逻辑在本地使用 `SECRET_KEY`，不传输密钥

### 4. 硬编码 ID 警告（部分已移除）
- **`ms_batch.py`（批量写入）已移除硬编码回退**：不再回退到硬编码 projectId / templateId / versionId。写入前必须提供元素级 `projectId` 与 `templateId`（或设置 `METERSPHERE_DEFAULT_TEMPLATE_ID`），否则以 zh-CN 抛错拒绝（`元素 N 缺少 projectId` / `元素 N 缺少 templateId，且未设置 METERSPHERE_DEFAULT_TEMPLATE_ID`）。
- **`ms_generate.py`（草稿生成）仍保留一处硬编码版本映射**：项目 `1163437937827840` → versionId `1163437937827887`，命中时打印 zh-CN 警告；未命中且未设 `METERSPHERE_DEFAULT_VERSION_ID` 时返回空串（可能导致创建失败）。
- 为避免数据被错误归属到错误项目，写入前务必显式设置：
  - `METERSPHERE_PROJECT_ID`（写入安全守卫，见下节第 6 条）
  - `METERSPHERE_DEFAULT_TEMPLATE_ID`
  - `METERSPHERE_DEFAULT_VERSION_ID`

### 5. 已知陷阱（接口定义导入，现场实测证实）

- **双份前缀必须**：接口定义端点走 `{BASE}/api/api/definition/...`（v2 网关剥离首段后服务 context 为 `/api`）；单份 `{BASE}/api/definition/...` 得 Spring 404（无 `success` 键）——是路径错，不是数据不存在。
- **重复导入报「缺少 definition request」时**：fullCoverage 按 path 去重不落新行，但导入响应 `data.data[]` 返回解析阶段新生成的**不可查询 id**（GET 得 `data:null`）。不要直接消费响应 id——按 name 从 `/api/api/definition/list` 解析持久化 id 再做 detail GET（v2 `import-create`/`import-generate` 已内置此解析）。
- **勿消费导入响应内联 request**：`apiDefinitionId` 必须来自持久化 id 的 detail，否则用例归属错误。
- **同名定义多个**：按 name 解析取首个并输出中文警告；spec 端点 name 变更再导入会更新既有定义 name（id 不变），旧变体名不匹配 → 生成新变体（幂等：重跑跳过）。

### 6. 首次使用建议
1. 复制 `.env.example` 为 `.env` 并填写实际值
2. 在非生产环境或沙箱中测试
3. 使用最小权限的凭证
4. 检查网络流量，确认只连接到预期的 `BASE_URL`
5. 写入前设置 `METERSPHERE_PROJECT_ID`（写入操作在缺失时直接拒绝执行）
6. 设置 `METERSPHERE_DEFAULT_TEMPLATE_ID` 和 `METERSPHERE_DEFAULT_VERSION_ID`（`ms_batch.py` 已移除硬编码回退）
7. 注意脚本中的警告信息，确保数据被正确归属到目标项目

## v2 AI 工作流（comment / attachment / 生成写入）

> 本节命令仅存在于 `./scripts/v2/ms.sh`（v2 分支）。v2 无组织概念，用工作空间（workspace）。

### 1. 用例评论（comment）

在功能用例上保存 / 查询 / 删除 / 编辑评论（如 AI 生成的说明、评审意见等）：

```bash
./scripts/v2/ms.sh comment save <caseId> <description> [type] [belongId]
./scripts/v2/ms.sh comment list <caseId> [type [belongId]]
./scripts/v2/ms.sh comment delete <commentId>
./scripts/v2/ms.sh comment edit <commentId> <caseId> <description> [type] [belongId]
```

- `comment save` 默认 `type=CASE`、`belongId=""`；也接受自定义类型（如 `AI_CHAT`）。
- `comment list` 可按 `type` / `belongId` 过滤。
- `comment delete` 为 GET 请求（v2 接口如此定义）。
- `comment edit` 必须携带 `caseId`（服务端 CheckOwner 校验需要）。
- 评论作者由服务端根据 AK 用户解析，客户端不传 author。

### 2. 用例附件（attachment）

在功能用例上上传 / 查询 / 下载 / 删除附件（如 AI 对话记录、需求文档等）：

```bash
./scripts/v2/ms.sh attachment upload <caseId> <file>
./scripts/v2/ms.sh attachment list <caseId>
./scripts/v2/ms.sh attachment relate <caseId> <fileId> [<fileId>...]
./scripts/v2/ms.sh attachment unrelated <caseId> <metadataRefId> [<metadataRefId>...]
./scripts/v2/ms.sh attachment download <attachmentId> <isLocal> <outfile>
./scripts/v2/ms.sh attachment delete <attachmentId>
```

- `attachment upload` 为 multipart 上传（`sourceId` 参数即 caseId）。
- `attachment list` 返回附件元数据（id / name / size / isLocal / creator 等）。
- `attachment relate` 把库文件元数据 id 关联为用例附件（body `{belongId, belongType:"testcase", metadataRefIds:[...]}`）。
- `attachment unrelated` 为 relate 的配对操作（取消关联，body 同形状；`metadataRefId` 为库文件引用 id）。
- `attachment download` 需指定 `isLocal`（普通上传的附件为 `true`）。
- `attachment delete` 为 GET 请求（v2 接口如此定义）。

### 3. 需求 → 功能用例（生成写入）

```bash
./scripts/v2/ms.sh functional-case generate <projectId> <moduleId> <templateId> <requirement-file>
./scripts/v2/ms.sh functional-case batch-create <json-array-file>
./scripts/v2/ms.sh functional-case generate-create <projectId> <moduleId> <templateId> <requirement-file>
./scripts/v2/ms.sh functional-case template <projectId> [importType] [outfile]
./scripts/v2/ms.sh functional-case import <projectId> <excelFile> [--import-type Create|Update] [--version-id <id>]
./scripts/v2/ms.sh functional-case relate-demand <projectId> <demandId> <caseId> [<caseId>...] [--demand-name <name>]
./scripts/v2/ms.sh functional-case split-create <projectId> <file> [moduleId] [--link-mode same-call|separate]
./scripts/v2/ms.sh functional-case delete <caseId>
```

- `generate`：本地生成 v2 草稿 JSON（`skills/scripts/v2/ms_generate.py`），不写入。
- `batch-create`：批量写入（JSON 数组文件，逐条 POST /track/test/case/add）。
- `generate-create`：生成后直接批量写入，一步到位。
- `template`：下载 excel 导入模板（二进制 xlsx；`importType` 仅 `Create|Update`，默认 `Create`；省略 outfile 时输出到 stdout）。
- `import`：excel/xmind 导入（multipart 双 part `request`+`file`；`.xmind` 同端点，服务端按扩展名分发到 XmindCaseParser；request 体仅需 `{projectId, importType, ignore:false[, versionId]}`，userId 由服务端自行填充）。
- `relate-demand`：批量关联需求（需求管理为第三方平台集成，Phabricator 配置后可列出；body `{ids:[...], demandId, demandName}`；`demandId` 为 `other` 时必须提供 `--demand-name`）。
- `split-create`：一键拆分写入（见下节）。
- `delete`：删除指定功能用例（POST /test/case/delete/{id}，服务端需 PROJECT_TRACK_CASE_READ_DELETE 权限）；用于清理误写入的用例。
- 草稿增强可参考 `references/ai-v2-functional-case-prompt.md`；Phabricator 工单 + excel 模板双输入可参考 `references/ai-phabricator-functional-case-prompt.md`；excel 模板 + 原文件共享关联（含文件夹选择）可参考 `references/ai-excel-template-shared-attachment-prompt.md`。

### 3.1 测试用例文件拆分写入（split-create，v2）

把测试用例文件（docx/pdf/xlsx/xmind）一键拆分为多条用例并关联原文件：

```bash
python3 skills/scripts/v2/ms_split_cases.py <file> [--format auto|docx|pdf|xlsx|xmind] [-o out.json] [--project-id <id>]
./scripts/v2/ms.sh functional-case split-create <projectId> <file> [moduleId] [--link-mode same-call|separate]
```

- `ms_split_cases.py`：本地拆分器（无网络）。xlsx 按 MeterSphere 导入模板列序解析（需 openpyxl）；docx 按标题层级+表格（需 python-docx）；pdf 按行式启发（需 pdfplumber）；xmind 按 v2.10 XmindCaseParser 语义（`tc:`/`tc-P1:` 用例节点、`pc:`/`rc:`/`tag:` 子节点，stdlib 解析无富依赖）。缺富依赖时报错含 `pip install` 安装提示。输出 v2 字段契约 JSON 数组草稿（缺关键列的行跳过并告警计数）。
- `split-create` 编排（5 步，中途失败即停并报告已完成步骤，可重跑幂等）：① 拆分 → ② moduleId 解析注入 nodeId（缺省时查模块树按 nodePath 匹配，0 或多匹配告警不自动选并退出）→ ③ 按 name 查重（已存在同名跳过并计数；全部已存在则幂等跳过，不上传不写入）→ ④ 上传原文件到项目文件库一次（复用 `file create`）→ ⑤ `batch-create --file-id` 写入并同调用关联（每条用例 `relateFileMetaIds` 注入原文件 id）。
- `--link-mode separate` 降级：若目标实例的 `relateFileMetaIds` 同调用关联不生效，改对每个新 caseId 调 `attachment relate`（同一 fileId）。

### 4. AI 对话记录（chat-history flow）

把一次 AI 交互的完整对话保存为 Markdown 附件挂到用例上：

```bash
python3 skills/scripts/v2/ms_chat_log.py <conversation-json-file> [--creator <label>] [--title <title>] [--out <file>]
./scripts/v2/ms.sh attachment upload <caseId> conversation-log.md
```

- 输入 JSON 结构：`{"title": "...", "exchanges": [{"user": "...", "assistant": "..."}]}`。
- `ms_chat_log.py` 纯本地格式化（无网络），默认输出 `conversation-log.md`、默认 creator 为 `agent`。
- 输出 Markdown 含标题 / 创建者 / 时间头 + 每轮 `[USER]` / `[ASSISTANT]` 段落。
- 再通过 `attachment upload` 挂到目标用例，之后用 `attachment list` / `attachment download` 取回。

### 5. 查看控制（诚实说明）

v2 的评论与附件**没有逐条 / 逐用户的访问控制**——访问仅受项目级权限约束（能否查看用例由用例所属项目的 ACL 决定，而非评论 / 附件本身）。任何能查看该用例的人都能看到其全部评论与附件。`type` / `belongId` 只是内容过滤条件，不是可见性控制。如需隔离，只能通过独立的用例 / 模块实现粗粒度隔离，无法做到真正的逐条 ACL。

### 6. 写入安全

`functional-case batch-create` / `generate-create` / `template` 以外的 `import` / `relate-demand` / `split-create` / `delete` / 通用 `create` / `attachment upload` / `attachment relate` / `attachment unrelated` / `file create`（v2）/ `file upload`、`file delete`（v3，未验证）等写入操作要求显式设置 `METERSPHERE_PROJECT_ID` 环境变量；未设置时脚本拒绝执行并退出（exit 1），不会回退到硬编码项目 ID。

- v2（`./scripts/v2/ms.sh`）守卫消息：`错误: 未设置 METERSPHERE_PROJECT_ID，拒绝写入（防止误写硬编码项目）`。
- v3（`./scripts/ms.sh`）守卫消息：`错误: 写入操作需要设置 METERSPHERE_PROJECT_ID`（`未验证 (source-only)`）。
- 另需设置 `METERSPHERE_BASE_URL` / `METERSPHERE_ACCESS_KEY` / `METERSPHERE_SECRET_KEY`，缺失时分别报 `未设置 METERSPHERE_BASE_URL` / `未设置 METERSPHERE_ACCESS_KEY` / `未设置 METERSPHERE_SECRET_KEY`。
- `ms_batch.py` 自身也做元素级校验：缺 `projectId` / 缺 `templateId`（且无 `METERSPHERE_DEFAULT_TEMPLATE_ID`）时抛错。

### 7. 报告命令（reviewed-summary / case-report）

```bash
./scripts/v2/ms.sh reviewed-summary <projectId> [keyword]
./scripts/v2/ms.sh case-report <projectId> <caseId>
./scripts/v2/ms.sh case-report-md <projectId> <caseId>
```

- 与主包同名命令语义一致，但走 v2 路径；`case-report-md` 输出面向用户的 Markdown 报告（摘要/前置条件/备注/步骤/缺陷/评审记录）。

### 8. 项目文件库（file 资源）与用例附件共享（v2 实测）

v2 的「项目文件库」文件可被多个用例共享（同一份 MinIO 对象，零拷贝）。`file` 资源暴露四个动作（list/get/create/exists）：

```bash
./scripts/v2/ms.sh file create '{"id":"<uuid4>","projectId":"<projectId>","storage":"MINIO","name":"a.txt"}' <local-file>
./scripts/v2/ms.sh file exists <fileId> [<fileId>...]
./scripts/v2/ms.sh file list <projectId> [goPage] [pageSize]
./scripts/v2/ms.sh file get <fileId> [outfile]
./scripts/v2/ms.sh file-module list <projectId>
```

- `file create`：multipart 上传（`request=FileMetadataCreateRequest` 字段 + `file=@` 文件字段），返回文件元数据 id；服务端**按 name 去重**（已存在同名文件时英文报 `The file already exists`）；body 加 `moduleId` 可指定**文件夹**（`file-module list` 解析，缺省省略该键 = 根目录）。
- `file exists`：`POST /file/metadata/exists`，载荷为 id 数组；服务端仅回显存在的 id，全部存在返回 0，任一缺失以 zh-CN 报错退出。
- `file list`：`POST /file/metadata/project/{projectId}/{goPage}/{pageSize}`（body `{}`，默认分页 1/20）。
- `file get`：`GET /file/metadata/info/{id}`——**返回文件字节流**（非元数据 JSON）；省略 outfile 时输出到 stdout。
- `file-module list`：`GET /file/module/list/{projectId}`——项目文件库**文件夹树**（body 里的 `moduleId` 即此处的文件夹 id；与功能用例模块 `functional-module` 是两个不同体系，勿混用）。
- 库文件挂到**已创建**的用例：`./scripts/v2/ms.sh attachment relate <caseId> <fileId> [<fileId>...]`（body `{belongId, belongType:"testcase", metadataRefIds:[...]}`）。
- **`attachment relate` 只接受库文件元数据 id**：传库 id 返回 `{"success":true,"data":null}`；若误传「另一条用例的用例内附件行 id」（取自该用例 attachment list）会得到 HTTP 500（`/attachment/testcase/metadata/relate`）——服务端用法边界，不是客户端缺陷。
- 批量创建时一次性注入：`./scripts/v2/ms.sh functional-case batch-create <json-array-file> --file-id <fileMetadataId>`，把库文件写入每条用例的 `relateFileMetaIds`。v3 入口 `./scripts/ms.sh functional-case batch-create <json-file> --file-id <fileMetadataId>` 则透传给 `ms_batch.py --attach-file-id <id>`（`未验证 (source-only)`）。
- **共享语义**：N 条用例共享同一份 MinIO 对象（attachment list 中 filePath 相同、createTime 相同）——库文件路径零拷贝。
- **为何用例内上传不可共享**：`attachment upload` 产生绑定到该用例 sourceId 的行；relate 端点绑定的是库文件元数据行，故用例内附件行无法挂到另一条用例（实测 HTTP 500）。要共享必须走 `file create`。
- 清理：删除用例会**级联删除**其附件关联（删除后 `attachment list` 为 `[]`）；库文件元数据删除可能返回 HTTP 500 却已删除——务必重新查询确认（list / exists 为空）。
- **反模式（禁止）**：不要去调用 `file` 资源**按名称过滤**的查询端点——实测已损坏且不暴露；分页列表走 `file list`（`POST /file/metadata/project/{projectId}/{goPage}/{pageSize}`，v2.10 实测有效）。

### 9. 未规划用例模块处理（module 省略，v2 实测）

- 生成 / 写入时省略 module（传 `-` 或空）→ v2 生成器以 `default-module` 占位；`batch-create` 在写入前**按项目实时查询**模块树（`GET /track/case/node/list/{projectId}`，即 `METERSPHERE_FUNCTIONAL_MODULE_TREE_PATH`），解析出该项目的「未规划用例」节点，并同时填好该项目的 `nodeId` 与 `nodePath`。
- 实测：两个项目分别把全部用例落进各自的「未规划用例」节点（对同一模块树端点做 oracle，nodeId 匹配率 100%）。
- 解析失败（nodePath 无效或无匹配节点）时逐元素硬失败：`batch-create 第 N 个用例解析失败: nodePath 无效或未能解析模块`。

## v3 file / attachment（source-only，未验证）

> 以下命令存在于 `./scripts/ms.sh`（v3.x，README §16.1 俗称 v1）。**本环境无 v3 服务器可连**，v3-only 路径返回 404，故**全部为 `未验证 (source-only)`**，不得当作已验证行为。

```bash
./scripts/ms.sh file upload <json> <local-file>       # 未验证 (source-only)
./scripts/ms.sh file page <json>                      # 未验证 (source-only)
./scripts/ms.sh file delete <json>                    # 未验证 (source-only)
./scripts/ms.sh attachment upload <caseId|json> <file> # 未验证 (source-only)
./scripts/ms.sh attachment relate <caseId> <fileId>... # 未验证 (source-only)
./scripts/ms.sh attachment page <json>                 # 未验证 (source-only)
./scripts/ms.sh attachment delete <json>               # 未验证 (source-only)
```

- `file` 资源动作：`upload`、`page`、`delete`（均以 JSON body 承载参数；`upload` 额外带 `<local-file>`）——全部 `未验证 (source-only)`。
- `attachment` 资源动作：`upload`、`relate`、`page`、`delete`——全部 `未验证 (source-only)`。
- `file list` / `file get` 在 v3 同样被拒绝（`file 资源不支持 list/get`），`attachment list` / `attachment get` 被拒绝（`attachment 资源不支持 list/get（请使用 attachment page）`）——均 `未验证 (source-only)`。
- v3 省略 module（空或 `-`）会被替换为字面量 `root`（`未验证 (source-only)`），与 v2 的实时节点解析不同。
- v3 路径来源：v3.x 源码 `FileManagementController` / `FunctionalCaseAttachmentController`（`/project/file/*`、`/attachment/*`）。