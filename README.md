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
- `skills/scripts/v2/`：MeterSphere v2 分支兼容脚本（ms.sh / ms_generate.py / ms_chat_log.py / ms_case_report.py / ms_review_summary.py / ms_case_report_md.py，自动嗅探版本，或设 `METERSPHERE_VERSION=v2`）

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
./scripts/v2/ms.sh attachment download <attachmentId> <isLocal> <outfile>
./scripts/v2/ms.sh attachment delete <attachmentId>
```

- `attachment upload` 为 multipart 上传（`sourceId` 参数即 caseId）；`attachment delete` 为 GET 请求。
- `attachment list` 返回附件元数据（id / name / size / isLocal / creator 等）。
- `attachment download` 需指定 `isLocal`（普通上传的附件为 `true`）。

#### 需求 → 功能用例（生成写入）

```bash
./scripts/v2/ms.sh functional-case generate <projectId> <moduleId> <templateId> <requirement-file>
./scripts/v2/ms.sh functional-case batch-create <json-array-file>
./scripts/v2/ms.sh functional-case generate-create <projectId> <moduleId> <templateId> <requirement-file>
./scripts/v2/ms.sh functional-case delete <caseId>
```

- `generate` 本地生成 v2 草稿（`skills/scripts/v2/ms_generate.py`），不写入；`batch-create` 批量写入（JSON 数组文件）；`generate-create` 生成后直接批量写入，一步到位。
- `delete` 删除指定功能用例（POST /test/case/delete/{id}，服务端需 PROJECT_TRACK_CASE_READ_DELETE 权限）；用于清理误写入的用例。
- 草稿增强可参考 `references/ai-v2-functional-case-prompt.md`。

#### API 定义 → 接口用例（case factory）

```bash
./scripts/v2/ms.sh api-case generate-create <projectId> [<definitionId>...]
```

- 为**已存在**的 API 定义批量生成带断言的接口用例（每端点 3 个变体：`*成功场景`（断言 200，P1）/ `*必填缺失`（首个必填 query/rest 参数置空，断言 400，P1，仅当存在必填参数）/ `*边界场景`（首个字符串参数 = 128 个 'x'，断言 200，P2，仅当存在字符串参数）），填补 v2 导入只建定义不建用例（`caseTotal='0'`）的缺口。
- 不传 definitionId = 项目内全部 HTTP 定义（自动分页拉取）；变体生成由 `skills/scripts/v2/ms_generate_case.py` 完成（纯本地，无网络）。
- **服务端实测要求**（缺一即创建失败）：每条用例必须显式携带 `id`（uuid4，服务端不自动生成）、显式 `priority`、`request` 为嵌套对象（JSON 字符串会被 400 拒绝）——脚本已自动处理。
- **不创建定义**（定义由导入或插件负责）；不执行用例；不添加 JSONPath 断言（仅状态码断言）。
- 覆盖说明：v2 将 query 参数存储在 `arguments` 字段（非 `query`），当前变体扫描 `query`/`rest`——参数存于 `arguments` 或仅 body 必填的定义只会生成 `*成功场景`（后续版本扩展）。
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
- **写入安全**：`functional-case batch-create` / `generate-create` / `delete` / `api-case generate-create` / 通用 `create` / `attachment upload` 要求显式设置 `METERSPHERE_PROJECT_ID`，未设置时拒绝执行并退出（exit 1），不会回退到硬编码项目 ID。

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
- AI 对话记录格式化并挂载为用例附件（v2）
- 功能用例删除（v2，含写入安全守卫）
- API 路径按版本/部署覆盖（`METERSPHERE_*_PATH`，ms.sh / ms.py / 报告脚本均支持）

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

---

## 14. 参考文件

如需查看更细的接口与提示词说明，请参考：

- `skills/SKILL.md`
- `skills/references/ms-api.md`
- `skills/references/ai-functional-case-prompt.md`
- `skills/references/ai-api-bundle-prompt.md`
- `skills/references/ai-v2-functional-case-prompt.md`
- `skills/references/ai-v2-api-case-prompt.md`

---

## 15. 总结

如果你希望 Agent 能够在 MeterSphere 中：

- 更稳地查询测试资产
- 更快地生成测试资产
- 更清楚地回答评审与缺陷问题
- 更自然地输出单用例完整报告

那么这套 Skills 的价值就在于：

> 用统一命令与统一输出格式，把零散的 MeterSphere API 操作，收敛为可复用、可触发、可直接交付的 Agent 能力。