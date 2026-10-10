# MeterSphere Skills

面向多 Agent 平台（OpenCode、OpenClaw、Claude Code、Codex、Cursor 等）的 MeterSphere 能力封装。

本项目将 **MeterSphere REST API** 与本地脚本能力整合为一套可复用的 Skills，使 Agent 能够以更稳定、更可控的方式完成以下工作：

- 查询组织、项目、模块、模板、功能用例、接口定义、接口用例
- 根据需求生成并写入 **功能用例**
- 根据 Swagger / OpenAPI 生成并写入 **接口定义 + 接口用例**
- 查询 **用例评审**、评审详情、评审状态、评审人
- 回答“哪些功能用例被评审过”“某条用例关联了多少个缺陷”
- 输出单条功能用例的 **详情 + 缺陷 + 评审记录**

---

## 1. 项目定位

MeterSphere 本身提供完整的测试资产管理能力，但在日常使用中，以下场景往往仍存在较多重复劳动：

- 手工整理需求并编写测试用例
- 反复从 Swagger / OpenAPI 提取接口并录入系统
- 查询单条用例的缺陷、评审、测试计划等关联信息
- 统计“哪些用例被评审过”“哪些用例缺陷更多”
- 在 Agent 场景下临时拼装请求、反复摸索 API 参数

本项目的目标，是把这些高频动作沉淀为：

1. **可触发的 Skill 能力**
2. **可复用的 CLI 命令**
3. **可直接用于用户回复的输出格式**

这样 Agent 不必每次从零构造请求，也不必把大段原始 JSON 直接抛给用户。

---

## 2. 核心能力

### 2.1 查询能力

支持查询：

- 组织 / 项目
- 功能模块 / 功能模板
- API 模块
- 功能用例 / 接口定义 / 接口用例
- 评审单 / 评审详情 / 评审模块 / 评审人
- 单条功能用例的详情、缺陷、评审记录

### 2.2 生成功能用例

支持根据一句需求或需求文档生成：

- 主流程
- 异常场景
- 边界场景
- 基础优先级
- 基础标签

并支持批量写入 MeterSphere。

### 2.3 导入接口定义与接口用例

支持基于 Swagger / OpenAPI 自动生成：

- 接口定义
- 成功场景用例
- 必填缺失场景用例
- 边界场景用例

并支持批量写入 MeterSphere。

### 2.4 用例评审与关联分析

支持回答以下典型问题：

- 哪些功能用例被评审过
- 某条功能用例参与过哪些评审
- 某个评审单下有哪些功能用例
- 某条功能用例关联了多少个缺陷
- 某条功能用例的详情、缺陷、评审记录是什么

---

## 3. 推荐设计原则

本项目采用 **“本地生成 + AI 增强 + 系统写入”** 的混合模式：

- **本地脚本**：负责稳定生成结构、调用真实 API、控制输出格式
- **AI 增强**：负责补场景、润色命名、优化描述与断言
- **系统写入**：负责把最终结果落到 MeterSphere

这样做的好处是：

- 比纯自然语言直写更稳定
- 比纯脚本静态模板更灵活
- 比每次重新摸索接口更高效

---

## 4. 项目结构

```text
metersphere-skills/
├── README.md
└── skills/
    ├── SKILL.md
    ├── .env.example
    ├── references/
    │   ├── ms-api.md
    │   ├── ai-functional-case-prompt.md
    │   ├── ai-api-bundle-prompt.md
    │   ├── ai-v2-functional-case-prompt.md
    │   └── ai-v2-api-case-prompt.md
    └── scripts/
        ├── ms.sh
        ├── ms.py
        ├── ms_generate.py
        ├── ms_batch.py
        ├── ms_review_summary.py
        ├── ms_case_report.py
        ├── ms_case_report_md.py
        └── v2/
            ├── ms.sh
            ├── ms_generate.py
            ├── ms_generate_case.py
            ├── ms_import_helper.py
            ├── ms_chat_log.py
            ├── ms_case_report.py
            ├── ms_review_summary.py
            └── ms_case_report_md.py
```

### 目录说明

- `skills/SKILL.md`：Skill 元信息与 Agent 执行指南
- `skills/references/ms-api.md`：MeterSphere API 参考与能力边界说明
- `skills/references/ai-functional-case-prompt.md`：功能用例增强提示词
- `skills/references/ai-api-bundle-prompt.md`：接口定义 / 接口用例增强提示词
- `skills/scripts/ms.sh`：统一 Shell 入口
- `skills/scripts/ms.py`：基础 Python CLI
- `skills/scripts/ms_generate.py`：本地生成草稿 JSON
- `skills/scripts/ms_batch.py`：批量写入 MeterSphere
- `skills/scripts/ms_review_summary.py`：用例评审汇总脚本
- `skills/scripts/ms_case_report.py`：单用例结构化报告
- `skills/scripts/ms_case_report_md.py`：单用例 Markdown 报告
- `skills/scripts/v2/`：MeterSphere v2.10 LTS 专用脚本（ms.sh / ms_generate.py / ms_generate_case.py / ms_import_helper.py / ms_chat_log.py / ms_case_report.py / ms_review_summary.py / ms_case_report_md.py，自动嗅探版本，或设 `METERSPHERE_VERSION=v2`）。目标版本详见 §16。

---

## 5. 安装方式（npx skills）

本技能通过 [vercel-labs/skills](https://github.com/vercel-labs/skills) CLI 分发和安装到多种 AI Agent 工具。下文中 `<owner>` 指本仓库的 GitHub 拥有者（组织或个人）。

### 5.1 预览可安装的技能

```bash
npx skills add <owner>/metersphere-skills --list
```

### 5.2 安装到 OpenCode（全局）

```bash
npx skills add <owner>/metersphere-skills -s metersphere -a opencode -g
```

### 5.3 安装到所有已检测到的 Agent

```bash
npx skills add <owner>/metersphere-skills --all
```

### 5.4 不安装直接使用（试用）

> **注意**：当前 `npx skills use` 仅支持 claude-code、codex、sarvam-code 等部分 Agent，暂不支持 opencode。

```bash
npx skills use <owner>/metersphere-skills --skill metersphere --agent opencode
```

### 5.5 卸载

```bash
npx skills remove metersphere --agent opencode -g
```

### 5.6 本地路径安装

除 GitHub 仓库地址外，也可直接指定本地路径：

```bash
npx skills add /path/to/metersphere-skills -s metersphere -a opencode -g
```

### 5.7 关闭 CLI 遥测

如需关闭 `npx skills` 的遥测上报，可在执行前设置环境变量：

```bash
DISABLE_TELEMETRY=1 npx skills add <owner>/metersphere-skills --all
# 或
DO_NOT_TRACK=1 npx skills add <owner>/metersphere-skills --all
```

### 5.8 更新已安装的技能

`npx skills add` 会**完整递归复制**技能目录（含 `scripts/`、`references/` 及 `scripts/v2/` 子目录；仅排除 `.git`、`__pycache__`、`metadata.json`），无需手动复制文件。但安装是**副本而非实时链接**，仓库更新后需重新安装：

```bash
npx skills add <owner>/metersphere-skills --all
```

> **⚠️ 重装前备份 `.env`**：安装器会先清空规范副本目录再复制，技能根目录下的 `.env`（含真实密钥）会被删除。重装前备份、重装后恢复：
>
> ```bash
> cp ~/.agents/skills/metersphere/.env /tmp/env.backup
> npx skills add <owner>/metersphere-skills --all
> cp /tmp/env.backup ~/.agents/skills/metersphere/.env
> ```

---

## 6. 环境配置

脚本按 `SKILL_DIR/.env` 解析环境变量，即编辑技能安装目录下的 `.env` 文件。不同安装方式对应的编辑位置：

- **默认符号链接安装（OpenCode 等）**：编辑 `~/.agents/skills/metersphere/.env`（该目录是规范副本，各 Agent 通过符号链接共用）
- **OpenClaw 经 npx 安装**：编辑 `~/.openclaw/skills/metersphere/.env`
- **`--copy` 方式安装**：分别编辑每个 Agent 各自副本目录下的 `.env`

模板随技能包附送：仓库内为 `skills/.env.example`，经 npx 安装后位于技能根目录，名为 `.env.example`。首次使用前复制为 `.env` 并填写：

```bash
cp .env.example .env
```

最小配置如下：

```bash
METERSPHERE_BASE_URL=https://your-metersphere.example.com
METERSPHERE_ACCESS_KEY=your_access_key
METERSPHERE_SECRET_KEY=your_secret_key
```

### 参数说明

- `METERSPHERE_BASE_URL`：MeterSphere 服务地址
- `METERSPHERE_ACCESS_KEY`：AK
- `METERSPHERE_SECRET_KEY`：SK

---

## 7. 安装后验证

```bash
cd ~/.agents/skills/metersphere

./scripts/ms.sh --help
./scripts/ms.sh organization list
./scripts/ms.sh project list
```

以 OpenCode 全局安装为例；OpenClaw 用户使用 `cd ~/.openclaw/skills/metersphere`。

如果以上命令可以返回真实数据，说明基础鉴权与接口访问正常。

---

以下所有命令均假设已进入技能目录。首次使用前请先复制模板并填写环境变量（见 §6）。

> **MeterSphere v2 用户**：使用 `./scripts/v2/ms.sh`（自动嗅探版本，或设 `METERSPHERE_VERSION=v2` 强制指定）。v2 无组织概念，用工作空间（workspace）。

## 8. 常用命令

### 8.1 基础查询

```bash
./scripts/ms.sh organization list
./scripts/ms.sh project list
./scripts/ms.sh functional-module list <projectId>
./scripts/ms.sh functional-template list <projectId>
./scripts/ms.sh api-module list <projectId>
./scripts/ms.sh functional-case list '<JSON>'
./scripts/ms.sh api list '<JSON>'
./scripts/ms.sh api-case list '<JSON>'
```

### 8.2 用例评审查询

```bash
./scripts/ms.sh functional-case-review list '{"caseId":"<功能用例ID>"}'
./scripts/ms.sh case-review list '{"projectId":"<项目ID>"}'
./scripts/ms.sh case-review get <reviewId>
./scripts/ms.sh case-review-detail list '{"projectId":"<项目ID>","reviewId":"<评审ID>","viewStatusFlag":false}'
./scripts/ms.sh case-review-module list <projectId>
./scripts/ms.sh case-review-user list <projectId>
```

### 8.3 功能用例生成与写入

```bash
./scripts/ms.sh functional-case generate <projectId> <moduleId> <templateId> <requirement-file>
./scripts/ms.sh functional-case batch-create <json-file>
./scripts/ms.sh functional-case generate-create <projectId> <moduleId> <templateId> <requirement-file>
```

### 8.4 接口定义 / 接口用例生成与写入

```bash
./scripts/ms.sh api import-generate <projectId> <moduleId> <openapi-file-or-url>
./scripts/ms.sh api batch-create <json-file>
./scripts/ms.sh api import-create <projectId> <moduleId> <openapi-file-or-url>
```

### 8.5 高层聚合查询

#### 查询哪些用例被评审过

```bash
./scripts/ms.sh reviewed-summary <projectId>
./scripts/ms.sh reviewed-summary <projectId> 登录
```

#### 查询单条功能用例完整画像（JSON）

```bash
./scripts/ms.sh case-report <projectId> <caseId>
```

返回内容包含：

- `summary`
- `detail`
- `bugs`
- `reviews`

#### 查询单条功能用例完整画像（Markdown）

```bash
./scripts/ms.sh case-report-md <projectId> <caseId>
```

该命令更适合直接回复用户，输出结构为：

1. 用例摘要
2. 前置条件
3. 备注
4. 步骤
5. 缺陷
6. 评审记录

### 8.6 v2 AI 命令（comment / attachment / 生成写入）

> 本节命令仅存在于 `./scripts/v2/ms.sh`（v2 分支）。v2 无组织概念，用工作空间（workspace）。

#### 用例评论（comment）

```bash
./scripts/v2/ms.sh comment save <caseId> <description> [type] [belongId]
./scripts/v2/ms.sh comment list <caseId> [type [belongId]]
./scripts/v2/ms.sh comment delete <commentId>
./scripts/v2/ms.sh comment edit <commentId> <caseId> <description> [type] [belongId]
```

- `comment save` 默认 `type=CASE`、`belongId=""`；也接受自定义类型（如 `AI_CHAT`）。
- `comment list` 可按 `type` / `belongId` 过滤。
- `comment delete` 为 GET 请求；`comment edit` 必须携带 `caseId`（服务端 CheckOwner 校验需要）。
- 评论作者由服务端根据 AK 用户解析，客户端不传 author。

#### 用例附件（attachment）

```bash
./scripts/v2/ms.sh attachment upload <caseId> <file>
./scripts/v2/ms.sh attachment list <caseId>
./scripts/v2/ms.sh attachment relate <caseId> <fileId> [<fileId>...]
./scripts/v2/ms.sh attachment unrelated <caseId> <metadataRefId> [<metadataRefId>...]
./scripts/v2/ms.sh attachment download <attachmentId> <isLocal> <outfile>
./scripts/v2/ms.sh attachment delete <attachmentId>
```

- `attachment upload` 为 multipart 上传（`sourceId` 参数即 caseId）；`attachment delete` 为 GET 请求。
- `attachment list` 返回附件元数据（id / name / size / isLocal / creator 等）。
- `attachment relate` 把**库文件元数据 id** 关联为用例附件（body `{belongId, belongType:"testcase", metadataRefIds:[...]}`）；**只接受库文件 id**——传库 id 成功返回 `{"success":true,"data":null}`，误传「另一条用例的用例内附件行 id」会得 HTTP 500（服务端用法边界）。
- `attachment unrelated` 为 relate 的配对操作（取消关联，body 同形状；`metadataRefId` 为库文件引用 id）。
- `attachment download` 需指定 `isLocal`（普通上传的附件为 `true`）。

#### 项目文件库（file）与用例附件共享

v2 的「项目文件库」文件可被多条用例共享（同一份 MinIO 对象，零拷贝）。`file` 资源暴露四个动作（list/get/create/exists）：

```bash
./scripts/v2/ms.sh file create '{"id":"<uuid4>","projectId":"<projectId>","storage":"MINIO","name":"a.txt"}' <local-file>
./scripts/v2/ms.sh file exists <fileId> [<fileId>...]
./scripts/v2/ms.sh file list <projectId> [goPage] [pageSize]
./scripts/v2/ms.sh file get <fileId> [outfile]
./scripts/v2/ms.sh file-module list <projectId>
./scripts/v2/ms.sh functional-case batch-create <json-array-file> --file-id <fileMetadataId>
```

- `file create`：multipart 上传，返回文件元数据 id；服务端**按 name 去重**（同名时英文报 `The file already exists`）；body 加 `moduleId` 可指定**文件夹**（`file-module list` 解析，缺省省略该键 = 根目录）。
- `file exists`：`POST /file/metadata/exists`，载荷为 id 数组；服务端仅回显存在的 id，任一缺失即 zh-CN 报错退出。
- `file list`：`POST /file/metadata/project/{projectId}/{goPage}/{pageSize}`（body `{}`，默认分页 1/20）。
- `file get`：`GET /file/metadata/info/{id}`——**返回文件字节流**（非元数据 JSON）；省略 outfile 时输出到 stdout。
- `file-module list`：`GET /file/module/list/{projectId}`——项目文件库**文件夹树**（body 里的 `moduleId` 即此处的文件夹 id；与功能用例模块 `functional-module` 是两个不同体系，勿混用）。
- `attachment relate` 或 `batch-create --file-id` 均接受该库文件元数据 id；后者在写入前把库文件注入每条用例的 `relateFileMetaIds`，**N 条用例共享同一份 MinIO 对象**（attachment list 中 filePath 相同、createTime 相同）。
- **用例内上传（`attachment upload`）不可共享**：它产生绑定到该用例 sourceId 的行，无法挂到另一条用例（实测 HTTP 500）；跨用例共享只能走 `file create`。
- **反模式（禁止）**：不要调用 `file` 资源的**按名称过滤**的查询端点——实测损坏且不暴露；分页列表走 `file list`（v2.10 实测有效）。
- 清理：删除用例会级联删除其附件关联（删除后 `attachment list` 为 `[]`）；库文件元数据删除可能返回 HTTP 500 却已删除——务必重新查询确认（list / exists 为空）。

#### 未规划用例模块（module 省略）

- 生成 / 写入时省略 module（传 `-` 或空）→ v2 生成器以 `default-module` 占位；`batch-create` 在写入前**按项目实时查询**模块树（`GET /track/case/node/list/{projectId}`），解析出该项目的「未规划用例」节点，并同时填好 `nodeId` 与 `nodePath`。
- 实测：两个项目分别把全部用例落进各自的「未规划用例」节点（对同一模块树端点做 oracle，nodeId 匹配率 100%）。

#### 需求 → 功能用例（生成写入）

```bash
./scripts/v2/ms.sh functional-case generate <projectId> <moduleId> <templateId> <requirement-file>
./scripts/v2/ms.sh functional-case batch-create <json-array-file>
./scripts/v2/ms.sh functional-case batch-create <json-array-file> --file-id <fileMetadataId>
./scripts/v2/ms.sh functional-case generate-create <projectId> <moduleId> <templateId> <requirement-file>
./scripts/v2/ms.sh functional-case template <projectId> [importType] [outfile]
./scripts/v2/ms.sh functional-case import <projectId> <excelFile> [--import-type Create|Update] [--version-id <id>]
./scripts/v2/ms.sh functional-case relate-demand <projectId> <demandId> <caseId> [<caseId>...] [--demand-name <name>]
./scripts/v2/ms.sh functional-case split-create <projectId> <file> [moduleId] [--link-mode same-call|separate]
./scripts/v2/ms.sh functional-case delete <caseId>
```

- `generate` 本地生成 v2 草稿（`skills/scripts/v2/ms_generate.py`），不写入；`batch-create` 批量写入（JSON 数组文件）；`generate-create` 生成后直接批量写入，一步到位。
- `batch-create --file-id <fileMetadataId>` 把项目文件库文件注入每条用例的 `relateFileMetaIds`（库文件零拷贝，详见下方「项目文件库」）。
- `template` 下载 excel 导入模板（二进制 xlsx；`importType` 仅 `Create|Update`，默认 `Create`；省略 outfile 时输出到 stdout）。
- `import` excel/xmind 导入（multipart 双 part `request`+`file`；`.xmind` 同端点，服务端按扩展名分发到 XmindCaseParser；request 体仅需 `{projectId, importType, ignore:false[, versionId]}`，userId 由服务端自行填充）。
- `relate-demand` 批量关联需求（需求管理为第三方平台集成，Phabricator 配置后可列出；body `{ids:[...], demandId, demandName}`；`demandId` 为 `other` 时必须提供 `--demand-name`）。
- `split-create` 一键拆分写入（见下方「测试用例文件拆分写入」）。
- `delete` 删除指定功能用例（POST /test/case/delete/{id}，服务端需 PROJECT_TRACK_CASE_READ_DELETE 权限）；用于清理误写入的用例。
- 草稿增强可参考 `references/ai-v2-functional-case-prompt.md`；Phabricator 工单 + excel 模板双输入可参考 `references/ai-phabricator-functional-case-prompt.md`；excel 模板 + 原文件共享关联（含文件夹选择）可参考 `references/ai-excel-template-shared-attachment-prompt.md`。

#### 测试用例文件拆分写入（split-create）

把测试用例文件（docx/pdf/xlsx/xmind）一键拆分为多条用例并关联原文件：

```bash
python3 skills/scripts/v2/ms_split_cases.py <file> [--format auto|docx|pdf|xlsx|xmind] [-o out.json] [--project-id <id>]
./scripts/v2/ms.sh functional-case split-create <projectId> <file> [moduleId] [--link-mode same-call|separate]

# 例：拆分 xmind 并写入，原文件关联到全部拆出的用例
./scripts/v2/ms.sh functional-case split-create <projectId> /path/to/cases.xmind
# 例：显式指定目标模块 + separate 降级关联
./scripts/v2/ms.sh functional-case split-create <projectId> /path/to/cases.docx <moduleId> --link-mode separate
```

- `ms_split_cases.py`：本地拆分器（无网络）。xlsx 按 MeterSphere 导入模板列序解析（需 openpyxl）；docx 按标题层级+表格（需 python-docx）；pdf 按行式启发（需 pdfplumber）；xmind 按 v2.10 XmindCaseParser 语义（`tc:`/`tc-P1:` 用例节点、`pc:`/`rc:`/`tag:` 子节点，stdlib 解析无富依赖）。缺富依赖时报错含 `pip install` 安装提示。输出 v2 字段契约 JSON 数组草稿（缺关键列的行跳过并告警计数）。
- `split-create` 编排（5 步，中途失败即停并报告已完成步骤，可重跑幂等）：① 拆分 → ② moduleId 解析注入 nodeId（缺省时查模块树按 nodePath 匹配，0 或多匹配告警不自动选并退出）→ ③ 按 name 查重（已存在同名跳过并计数；全部已存在则幂等跳过，不上传不写入）→ ④ 上传原文件到项目文件库一次（复用 `file create`）→ ⑤ `batch-create --file-id` 写入并同调用关联（每条用例 `relateFileMetaIds` 注入原文件 id）。
- `--link-mode separate` 降级：若目标实例的 `relateFileMetaIds` 同调用关联不生效，改对每个新 caseId 调 `attachment relate`（同一 fileId）。

#### API 定义 → 接口用例（case factory）

```bash
./scripts/v2/ms.sh api-case generate-create [--tags <标签[,标签...]>] <projectId> [<definitionId>...]

# 例：给用户故事 T-story-123 与技术工单 T-tech-456 打标签，批量生成并写入
./scripts/v2/ms.sh api-case generate-create --tags T-story-123,T-tech-456 <projectId> <definitionId1> <definitionId2>
```

- 为**已存在**的 API 定义批量生成带断言的接口用例（每端点 3 个变体：`*成功场景`（断言 200，P1）/ `*必填缺失`（首个必填 query / rest / arguments 参数置空，断言 400，P1，仅当存在必填参数）/ `*边界场景`（首个字符串参数 = 128 个 'x'，断言 200，P2，仅当存在字符串参数）），填补 v2 导入只建定义不建用例（`caseTotal='0'`）的缺口。
- 不传 definitionId = 项目内全部 HTTP 定义（自动分页拉取）；变体生成由 `skills/scripts/v2/ms_generate_case.py` 完成（纯本地，无网络）。
- **服务端实测要求**（缺一即创建失败）：每条用例必须显式携带 `id`（uuid4，服务端不自动生成）、显式 `priority`、`request` 为嵌套对象（JSON 字符串会被 400 拒绝）——脚本已自动处理。
- `--tags <标签[,标签...]>`（**可选，可重复**）：给每条生成的用例写入 `tags` 标签（典型用途是 Phabricator 工单号），值内可用逗号或空格分隔多个标签，脚本归一化去重后序列化成 **JSON 编码的字符串**（v2.10 的 `tags` 是 String 字段而非数组，裸数组会丢标签）；等价的重复写法 `--tags T-story-123 --tags T-tech-456`。**缺省时载荷里完全不含 `tags` 键**（连 `"[]"` 都不发）。必须在位置参数之前或之后皆可——脚本先剥离 `--tags` 再解析位置参数。
- **不创建定义**（定义由导入或插件负责）；不执行用例；不添加 JSONPath 断言（仅状态码断言）。
- 覆盖说明：v2 将 query 参数存储在 `arguments` 字段（非 `query`），`skills/scripts/v2/ms_generate_case.py` 的变体扫描按 `query` > `rest` > `arguments` 的优先级依次覆盖三组参数（`PARAM_GROUPS = ('query', 'rest', 'arguments')`，`arguments` 条目与 `query` 同构故一并扫描）。因此**只有 body、三个参数组都没有必填或字符串参数**的定义才会只生成 `*成功场景`，缺少必填缺失与边界覆盖，这类定义需交给 AI 增强步骤补偿。
- 参数组命名对照（易混淆点）：`v1` 指 `skills/scripts/`（对接 MeterSphere v3.x），`v2` 指 `skills/scripts/v2/`（对接 MeterSphere v2.10 LTS），并非 MeterSphere 产品版本号。详见 §16。
- 失败不中断：单条创建失败继续其余，汇总报告；仅当 0 条创建成功时退出非零。

#### AI 对话记录（chat-history flow）

```bash
python3 skills/scripts/v2/ms_chat_log.py <conversation-json-file> [--creator <label>] [--title <title>] [--out <file>]
./scripts/v2/ms.sh attachment upload <caseId> conversation-log.md
```

- 输入 JSON 结构：`{"title": "...", "exchanges": [{"user": "...", "assistant": "..."}]}`。
- `ms_chat_log.py` 纯本地格式化（无网络），默认输出 `conversation-log.md`、默认 creator 为 `agent`。
- 输出 Markdown 含标题 / 创建者 / 时间头 + 每轮 `[USER]` / `[ASSISTANT]` 段落，再通过 `attachment upload` 挂到目标用例，之后用 `attachment list` / `attachment download` 取回。

#### 查看控制与写入安全

- **查看控制（诚实说明）**：v2 的评论与附件**没有逐条 / 逐用户的访问控制**——访问仅受项目级权限约束（能否查看用例由用例所属项目的 ACL 决定，而非评论 / 附件本身）。任何能查看该用例的人都能看到其全部评论与附件；`type` / `belongId` 只是内容过滤条件，不是可见性控制。
- **写入安全**：`functional-case batch-create` / `generate-create` / `import` / `relate-demand` / `split-create` / `delete` / `api-case generate-create` / 通用 `create` / `attachment upload` / `attachment relate` / `attachment unrelated` / `file create` 要求显式设置 `METERSPHERE_PROJECT_ID`，未设置时拒绝执行并退出（exit 1），不会回退到硬编码项目 ID。v2 守卫消息为 `错误: 未设置 METERSPHERE_PROJECT_ID，拒绝写入（防止误写硬编码项目）`；v3 为 `错误: 写入操作需要设置 METERSPHERE_PROJECT_ID`（v3 未验证 (source-only)）。
- **`ms_batch.py` 已移除硬编码回退**：不再回退到硬编码 projectId / templateId / versionId；缺元素级 `projectId` / `templateId`（且未设 `METERSPHERE_DEFAULT_TEMPLATE_ID`）时抛 zh-CN 错误拒绝。

#### 报告命令（reviewed-summary / case-report）

```bash
./scripts/v2/ms.sh reviewed-summary <projectId> [keyword]
./scripts/v2/ms.sh case-report <projectId> <caseId>
./scripts/v2/ms.sh case-report-md <projectId> <caseId>
```

- 与主包同名命令（§8.5）语义一致，但走 v2 路径；`case-report-md` 输出面向用户的 Markdown 报告（摘要/前置条件/备注/步骤/缺陷/评审记录）。

---

## 9. 典型使用场景

### 场景 1：根据需求生成功能用例

```bash
./scripts/ms.sh project list
./scripts/ms.sh functional-module list <projectId>
./scripts/ms.sh functional-template list <projectId>
./scripts/ms.sh functional-case generate <projectId> <moduleId> <templateId> ./requirement.txt
```

如果需要更高质量内容：

1. 先生成 JSON 草稿
2. 再用 `references/ai-functional-case-prompt.md` 增强
3. 最后 `batch-create` 写入

### 场景 2：根据 OpenAPI 导入接口测试资产

```bash
./scripts/ms.sh project list
./scripts/ms.sh api-module list <projectId>
./scripts/ms.sh api import-generate <projectId> <moduleId> ./openapi.json
```

如需增强：

1. 先生成 bundle
2. 再用 `references/ai-api-bundle-prompt.md` 增强
3. 最后 `api batch-create`

### 场景 3：判断哪些用例被评审过

```bash
./scripts/ms.sh reviewed-summary <projectId>
```

可直接得到：

- 总用例数
- 已评审用例数
- 未评审用例数
- 每条用例的评审情况

### 场景 4：查看某条功能用例的完整情况

```bash
./scripts/ms.sh case-report-md <projectId> <caseId>
```

适合在聊天场景中直接回答：

- 用例详情
- 关联缺陷
- 评审记录

---

## 10. 推荐工作流

### 10.1 功能用例工作流

1. `project list`
2. `functional-module list <projectId>`
3. `functional-template list <projectId>`
4. `functional-case generate`
5. 按 `references/ai-functional-case-prompt.md` 增强
6. `functional-case batch-create`

### 10.1.1 测试用例文件拆分工作流（docx/pdf/xlsx/xmind）

1. `functional-case template <projectId>` 下载 excel 模板（可选，对照列序）
2. `functional-case split-create <projectId> <file>` 一键拆分写入并关联原文件
   - 或分步：`ms_split_cases.py` 拆分 → 按 `references/ai-phabricator-functional-case-prompt.md` 增强 → `batch-create --file-id <fileId>`
3. Phabricator 工单驱动时按 `references/ai-phabricator-functional-case-prompt.md`（epic→story→tech 工单读取 + 双输入映射）

### 10.2 接口定义 / 接口用例工作流

1. `project list`
2. `api-module list <projectId>`
3. `api import-generate`
4. 按 `references/ai-api-bundle-prompt.md` 增强
5. `api batch-create`

### 10.3 单用例查询工作流

1. 已知 `caseId` 时，优先 `case-report-md`
2. 需要结构化数据时，再用 `case-report`
3. 只关心评审覆盖时，用 `reviewed-summary`

---

## 11. 输出策略

本项目区分两类输出：

### 11.1 结构化输出

适用于：

- Agent 继续加工
- 脚本联动
- 二次分析

推荐命令：

```bash
./scripts/ms.sh case-report <projectId> <caseId>
./scripts/ms.sh reviewed-summary <projectId> [keyword]
```

### 11.2 面向用户的可读输出

适用于：

- 聊天回复
- 汇总说明
- 单用例说明

推荐命令：

```bash
./scripts/ms.sh case-report-md <projectId> <caseId>
```

---

## 12. 已确认能力边界

当前已验证并可稳定使用的能力包括：

- 组织 / 项目 / 模块 / 模板查询
- 功能用例详情查询
- 功能用例评审查询
- 功能用例关联缺陷查询
- 单用例详情 + 缺陷 + 评审记录聚合
- 功能用例草稿生成与批量写入
- OpenAPI 导入草稿生成与批量写入
- 用例评论（comment）与附件（attachment）管理（v2）
- 项目文件库（file）与用例附件共享（v2，`file create` + `attachment relate` / `batch-create --file-id`，库文件零拷贝）
- 未规划用例模块（省略 module 时按项目实时解析「未规划用例」节点）（v2）
- AI 对话记录格式化并挂载为用例附件（v2）
- 功能用例删除（v2，含写入安全守卫）
- API 路径按版本/部署覆盖（`METERSPHERE_*_PATH`，ms.sh / ms.py / 报告脚本均支持）
- v3 的 file / attachment 资源与 `batch-create --file-id`（**未验证 (source-only)**，本环境无 v3 服务器可连）

当前项目定位仍以：

- **稳定查询**
- **稳定生成草稿**
- **稳定写入系统**

为优先目标。

---

## 13. 已知问题与踩坑（现场实测证实）

> 适用于 `api import-generate` / `api import-create`（v2）。详细说明见 `skills/references/ms-api.md` §10。

- **接口定义端点必须双份前缀** `{BASE}/api/api/definition/...`：单份 `{BASE}/api/definition/...` 得 Spring 404（无 `success` 键）——是路径错，不是数据不存在。
- **重复导入报「缺少 definition request」**：fullCoverage 按 path 去重不落新行，但导入响应 `data.data[]` 返回解析阶段新生成的不可查询 id（GET 得 `data:null`）。v2 `import-create`/`import-generate` 已内置按 name 从定义列表解析持久化 id 的修复——重复运行同一 spec 会干净跳过（EXIT 0），不再失败。
- **勿消费导入响应内联 request**：`apiDefinitionId` 必须来自持久化 id 的 detail，否则用例归属错误。
- **spec 端点 name 变更再导入**：会更新既有定义 name（id 不变），旧变体名不匹配 → 生成新变体用例（重跑跳过，幂等成立）。

### 13.1 文件库 / 附件 / 未规划模块（v2，现场实测证实）

- **包装响应形状**：成功统一 `{"success":true,"data":...}`；`attachment relate` 成功时 `data` 为 `null`。
- **`attachment relate` 只接受库文件元数据 id**：传库 id → `{"success":true,"data":null}`；误传用例内附件行 id（另一用例 attachment list 里的 id）→ HTTP 500 `{"status":500,"error":"Internal Server Error","path":"/attachment/testcase/metadata/relate"}`——服务端用法边界。
- **用例内上传不可共享**：`attachment upload` 的行绑定该用例 sourceId；跨用例共享必须走 `file create` + relate / `--file-id`。
- **库文件零拷贝**：`batch-create --file-id` 让 N 条用例共享同一份 MinIO 对象（filePath 相同、createTime 相同）。
- **库文件按 name 去重**：同名创建失败，英文消息 `The file already exists`。
- **库文件删除可能 500 却已删除**：务必重新查询确认（list / exists 为空）。
- **附件关联随用例级联删除**：删除用例后其 `attachment list` 为 `[]`。
- **`POST /track/test/case/list/{n}/{size}` 要求请求体内带 `projectId`**，否则不能按项目过滤。
- **`batch-create` 逐元素非原子**：中途失败先前的元素已落库、不回滚；失败体含 `"success":false` 时以 zh-CN 报错退出（exit 1），否则原样打印未包裹 zh-CN 的原始服务端错误后继续，末尾打印 `batch-create 完成: 共 N 个元素，成功创建 M 个用例`（exit 0，裸错误属已知 cosmetic gap）。
- **反模式（禁止）**：`file` 资源的按名称过滤的分页 / 列表查询端点实测损坏，脚本刻意不暴露 `file list` / `file get`。

### 13.2 v3 file / attachment（未验证 (source-only)）

> 本环境无 v3 服务器可连，v3-only 路径返回 404。以下路径来源 v3.x 源码，**全部为 `未验证 (source-only)`**。

- `file upload` / `file page` / `file delete` 分别走 `POST /project/file/upload` / `POST /project/file/page` / `POST /project/file/delete`——`未验证 (source-only)`。
- `attachment upload` / `attachment page` / `attachment delete` 分别走 `POST /attachment/upload/file` / `POST /attachment/page` / `POST /attachment/delete/file`——`未验证 (source-only)`。
- `attachment relate` 复用 `attachment upload` 端点并携带 `{projectId, caseId, fileIds}`——`未验证 (source-only)`。
- v3 省略 module → 字面量 `root`——`未验证 (source-only)`。

---

## 14. 参考文件

如需查看更细的接口与提示词说明，请参考：

- `skills/SKILL.md`
- `skills/references/ms-api.md`
- `skills/references/ai-functional-case-prompt.md`
- `skills/references/ai-api-bundle-prompt.md`
- `skills/references/ai-v2-functional-case-prompt.md`
- `skills/references/ai-v2-api-case-prompt.md`
- `skills/references/ai-module-api-case-prompt.md`
- `skills/references/ai-phabricator-api-case-prompt.md`

---

## 15. 总结

如果你希望 Agent 能够在 MeterSphere 中：

- 更稳地查询测试资产
- 更快地生成测试资产
- 更清楚地回答评审与缺陷问题
- 更自然地输出单用例完整报告

那么这套 Skills 的价值就在于：

> 用统一命令与统一输出格式，把零散的 MeterSphere API 操作，收敛为可复用、可触发、可直接交付的 Agent 能力。

---

## 16. 两套脚本的版本对应关系（v1 / v2 命名的真实含义）

本仓库有两套脚本入口，目录名 `v1` / `v2` 指的是**脚本的版本**，而**不是** MeterSphere 的产品版本。这一点极易误解，下表为源码实测结论。

| 脚本位置 | 通常被称作 | 实际对接的 MeterSphere 版本 |
| --- | --- | --- |
| `skills/scripts/` | v1 | **MeterSphere v3.x** |
| `skills/scripts/v2/` | v2 | **MeterSphere v2.10 LTS** |

### 16.1 `skills/scripts/`（俗称 v1）→ MeterSphere v3.x

依据（均可在 MeterSphere 源码树核对）：

- 校验点：本地 MeterSphere 检出 `cf7a649a71` 与 `origin/v3.x`、tag `v3.6.9-lts` 指向同一提交。
- v1 使用的路径在该树上均存在：`/api/case/add`、`/functional/case/add`、`/system/version/current`。
- `ApiTestCaseService.addCase()` 内 `testCase.setId(IDGenerator.nextStr())`——**由 v3.x 服务端自行生成用例 ID**，因此 v1 写入时无需客户端指定 ID。
- v1 新增的 `file` / `attachment` 资源（`file upload|page|delete`、`attachment upload|relate|page|delete`）路径来自 v3.x 源码 `FileManagementController` / `FunctionalCaseAttachmentController`（`/project/file/*`、`/attachment/*`），但**本环境无 v3 服务器可连，全部 `未验证 (source-only)`**（`skills/scripts/ms.sh` 内 `未验证` 计数 19）。

### 16.2 `skills/scripts/v2/` → MeterSphere v2.10 LTS

依据：

- 校验点：真实 tag `v2.10.26-lts`（提交 `b2d3d1d09ac119d6c03d7b767e33fd449665ced5`）的 `ApiTestCaseController.java:36` 为 `@RequestMapping(value = "/api/testcase")`，`:120` 为 `@PostMapping(value = "/create", consumes = {"multipart/form-data"})`。
- 该路径与 `skills/scripts/v2/ms.sh:49` 的 `METERSPHERE_API_CASE_CREATE_PATH='/api/testcase/create'` 完全一致。
- 服务端**不生成**用例 ID，故 v2 侧每条用例必须显式携带 `id`（uuid4）——这是 v2 与 v1 最容易踩的差异之一。
- v2 的 query 参数存放在 `arguments` 字段而非 `query`（参数组扫描差异见 §8.6 覆盖说明）。

### 16.3 两条产品线源码布局不同

定位问题时可直接用目录结构区分：

- **v2.10 LTS**：`api-test/backend/src/main/java/io/metersphere/...`
- **v3.x**：`backend/services/api-test/src/main/java/io/metersphere/api/...`

### 16.4 排查同名脚本时的注意事项

`skills/scripts/ms.sh` 与 `skills/scripts/v2/ms.sh` 是**两个独立文件**，各自可能存在同名内部函数（例如 `normalize_json_with_defaults`）。它们服务于不同产品版本、互不共享实现。定位问题时务必确认当前路径属于哪一套，**不要**把两者的函数实现当作同一份代码来推断行为。

> 校验 tag 时注意：若本地存在与 tag 同名的分支（例如 `v2.10.26-lts` 分支会遮蔽同名 tag），`git rev-parse v2.10.26-lts` 会解析到分支上。必须使用 `git rev-parse v2.10.26-lts^{commit}` 显式解析到 tag 对应的提交。