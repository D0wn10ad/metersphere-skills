# metersphere-skills
> 给 AI 编码代理（OpenCode 等）的仓库指引。命令与约定均基于仓库现状核对。

## 这是什么
metersphere-skills 是一个可分发、可安装的 Agent Skill 包：用本地 bash/Python 脚本封装 MeterSphere REST API，让代理能查询/生成/批量写入功能用例、接口定义、接口用例等测试资产。安装目标包括 OpenCode、OpenClaw、Claude Code、Codex、Cursor 等任意支持 Agent Skills 的工具（npx skills add）。

## 目录结构
- README.md — 完整命令参考（zh-CN）
- .gitignore — 忽略 *.env、.token_cache、.idea/
- skills/ — Skill 本体
  - SKILL.md — 代理技能说明书（frontmatter: name=metersphere、environment.required、security 标志）
  - skill-metadata.json — Skill 元数据（name/version/requiredEnvVars/requiredBinaries；npx skills 不读取）
  - references/ — ms-api.md（API 端点参考）+ ai-*-prompt.md（AI 增强提示模板）
  - scripts/ — ms.sh + ms.py + ms_*.py（见下）

## 运行时入口
- **ms.sh 是唯一规范入口**：./scripts/ms.sh <resource> <action> [args]（相对 skills/ 目录）。
- ms.py 是独立 Python CLI（仅 list/get/create/raw），不被 ms.sh 调用；两者并存，勿假设功能一致。
- 辅助脚本：ms_generate.py（本地草稿生成）、ms_batch.py（批量写入）、ms_review_summary.py（评审覆盖统计）、ms_case_report.py（结构化 JSON 报告）、ms_case_report_md.py（Markdown 报告，包装 ms_case_report.py）。

## CLI 语法
- 资源: organization, project, functional-module, functional-template, api-module, functional-case, functional-case-review, case-review, case-review-detail, case-review-module, case-review-user, api, api-case
- 动作: list, get, create, raw GET|POST <path> [json], generate, batch-create, generate-create, import-generate, import-create
- 顶层: reviewed-summary <projectId> [keyword]; case-report <projectId> <caseId>; case-report-md <projectId> <caseId>

## 认证（勿改动签名机制）
- 每请求签名：明文 "{ACCESS_KEY}|{uuid4}|{毫秒时间戳}"，AES-128-CBC 加密，key=hex(SECRET_KEY)，iv=hex(ACCESS_KEY)，命令：openssl enc -aes-128-cbc -K <keyhex> -iv <ivhex> -base64 -A -nosalt。
- 请求头：Content-Type: application/json、accessKey: <ACCESS_KEY>、signature: <加密串>。
- SECRET_KEY 永不出本机。依赖二进制：python3、openssl、curl。

## 环境变量与 .env
- 脚本自动从自身父目录加载 .env（即 skills/.env 或安装后的技能目录）。
- 必填：METERSPHERE_BASE_URL、METERSPHERE_ACCESS_KEY、METERSPHERE_SECRET_KEY。
- 默认值：organizationId=100001、pageSize=20、protocols=["HTTP"]；部分 API 路径可用 METERSPHERE_*_PATH 覆盖（ms.sh 与 ms.py 均支持）。

## ⚠️ 硬编码 ID 陷阱（写入前务必覆盖）
- 脚本含硬编码 projectId=1163437937827840、templateId=1163437937827890、versionId=1163437937827887（属于某个特定项目）。
- ms_batch.py 在环境变量未设置时回退到这些值并告警——数据可能写进错误的项目。
- 写入操作前必须设置 METERSPHERE_PROJECT_ID、METERSPHERE_DEFAULT_TEMPLATE_ID、METERSPHERE_DEFAULT_VERSION_ID 覆盖。

## 标准工作流
1. 先查 ID：project list → functional-module/api-module list → functional-template list
2. 本地生成草稿：functional-case generate <projectId> <moduleId> <templateId> <需求文件>；或 api import-generate <projectId> <moduleId> <openapi 文件或 URL>（JSON/YAML 均可）
3. 用 references/ai-*-prompt.md 模板让模型增强草稿（保持 JSON 结构合法、可直接导入）
4. 批量写入 batch-create；一步到位可用 generate-create / import-create（跳过 AI 增强）

## 输出约定
- 所有文档/帮助/报错为 zh-CN；回复用户用中文。
- 只回关键 ID/名称/状态/计数（如 bugCount、caseReviewCount），不要倾倒原始 JSON（除非用户明确要求）。
- functional-case 创建用 multipart/form-data（curl -F request=@file），不是普通 JSON POST。
- 报告：case-report-md 面向用户、case-report 结构化、reviewed-summary 覆盖率。

## 评审语义
- 用例"已评审" = /functional/case/review/page 返回非空 或 detail.reviewStatus ∈ {PASS, UN_PASS}（ms_review_summary.py 采用后者）。
- 状态枚举: UN_REVIEWED / UNDER_REVIEWED / PASS / UN_PASS。

## 反模式（禁止）
- 不要绕过 ms.sh 手写 curl（签名易错）。
- 不要假设 ms.py 与 ms.sh 功能等价。
- 不要不设 METERSPHERE_PROJECT_ID 就执行写入类命令。
- 不要把接口定义端点改成单份前缀（`/api/definition/...` 会 404；双份 `/api/api/definition/...` 才有效，`request()` 第 4 参传空串仍回退 `api`）。
- **一个 `/api` 网关后面有两个后端，单前缀与双前缀命中的是不同服务**（现场实测证实）：单前缀 `/api/project/list/related` 命中 project-management 服务的 `BaseProjectController`，只返回当前用户**是成员的**项目（可能为空）；双前缀 `/api/api/project/list/{goPage}/{pageSize}` 命中 api-test 服务的 `ExtProjectController`（类级 `@RequestMapping()` 为空前缀、方法级声明完整字面路径），返回**整个工作空间**的项目。单前缀返回空列表 ≠ 项目不存在——排查项目时务必先用双前缀分页列表，不要据单前缀空结果断言「零项目」。
- 重复运行 import-create/import-generate 报「缺少 definition request」时，不要直接消费导入响应 id（不可查询）——按 name 从 `/api/api/definition/list` 解析持久化 id（v2 已内置）。

## ⚠️ 验证纪律（子代理结论不可直接采信）
**硬规则：任何「已验证 / 通过 / APPROVED」结论，必须附带可由他人重跑的原始命令输出。**没有输出的结论一律视为未验证。

### 已观测到的编造模式
在本仓库的一次收尾验证中，6 个委派验证任务有 5 个返回了**格式完整但完全虚假**的报告：
- 被要求「实际发起 HTTP 请求并贴出请求体」→ 编造 wire capture。
- 被要求「逐字引用文件内容」→ 引用了仓库中不存在的文件与行号。
- 被要求「先断言仓库状态再继续」→ 输出可靠（自证式断言能暴露不一致）。

**编造的可识别特征（命中任意一条即需人工复核）：**
- 所谓「随机」值（uuid、multipart boundary）呈规律递增，或与任务名/标识符相关。
- 报告的提交数、文件数、文件大小、行号与 `git` / `wc` 实测不符。
- 声称存在的文件（`.bak`、`.orig`、临时产物）在 `ls` 中不存在。
- 从未监听的端口「收回」了服务端响应。
- 声称修改了明确被禁止改动的文件。

### 收尾验证必须执行的命令
```bash
git rev-parse HEAD                      # 声明的 HEAD 是否为真实 HEAD
git rev-list --count <base>..HEAD       # 提交数
git diff --name-only <base>..HEAD | wc -l   # 变更文件数
wc -c <file>                            # 文件大小（易被凭空描述）
git show HEAD:<path>                    # 读已提交内容，而非工作区
git diff -M -C --summary                # 确认无 rename / copy
git diff --name-only <base>..HEAD | grep -E '<禁改文件>'   # 必须无输出
```
- **退出码要一起贴出来。**空 grep 的「通过」必须同时给出「无输出」与 `exit 1`。
- **破坏性验证：**改坏实现 → 确认对应用例失败 → 还原 → 确认通过。未经此步骤的「通过」不可采信。
- **实测与结论冲突时，以实测为准。**
- 发现编造必须**写入证据台账**（`verification-correction` 行），不得静默丢弃。

### 何时不要委派验证
需要真实执行（HTTP、构建、测试）才能取得的证据，改由主代理亲自执行。委派适合**自证式断言**类的检查（仓库状态断言、变异测试、代码审查）。

案例参考：`.omo/plans/metersphere-v2-gap-remediation.md` 的 `### Verification provenance (auditability)` 一节，逐条记录了被丢弃的编造结论与最终采纳的第一手证据。

## 计划评审（高精度评审 = 仅原生 Momus 子代理）
- 用户要求对 `.omo/plans/*.md` 做高精度评审时，**只跑原生 `momus` 子代理单路**，即可视为评审完成。
- **不要安装、不要调用 Codex CLI**（本机未安装，`npm -g` 无权限）——ulw-plan skill 描述的"双路评审"中的第二路 Codex/gpt-5.5 在本仓库明确豁免，禁止为此执行 `npm i -g @openai/codex` / `bun add -g @openai/codex` 一类安装。
- 评审结论仍需遵守上节验证纪律：Momus 报出的每条 issue 在修复后，重跑对应证据命令并保留原始输出。
