# v2 Excel 模板用例批量写入 + 原文件共享关联 Prompt 模板（MeterSphere v2）

用于 v2 分支的功能用例（functional-case）生成。工作流：把一份符合 MeterSphere v2 excel 导入模板格式的用例文件批量写入功能用例，并把**该文件本身**上传到项目文件库（可选指定文件夹）后关联到全部新生成的用例（零拷贝共享）。

## 使用方式

1. 解析项目 ID：`./skills/scripts/v2/ms.sh project list`（按 `name` 字段匹配项目名，0 个或多个匹配时告警，不自动选）
2. 解析用例模块（可选）：`./skills/scripts/v2/ms.sh functional-module list '<projectId>'`（按 `name` 匹配目标功能子模块名，0 个或多个匹配时告警，不自动选）
3. 解析文件库文件夹（可选）：`./skills/scripts/v2/ms.sh file-module list '<projectId>'`（按 `name` 匹配目标文件夹名，得到 `moduleId` 即文件夹 id；0 个或多个匹配时告警，不自动选）
4. 拆分草稿（本地，无网络）：`python3 skills/scripts/v2/ms_split_cases.py <excelFile> --project-id <projectId> -o drafts.json`
5. 上传原文件到指定文件夹：`./skills/scripts/v2/ms.sh file create '<json>' <excelFile>`（JSON body 加 `moduleId` 选文件夹，缺省省略该键 = 根目录）
6. 写入并同调用关联：`./skills/scripts/v2/ms.sh functional-case batch-create drafts.json --file-id <fileMetadataId>`
7. 输出计数清单（zh-CN，不倾倒原始 JSON）：拆分数 / 跳过数 / 写入数 / fileId / caseId 列表

### 占位符契约（调用方须知）

- `<excelFile>`：excel 用例文件路径（模板列序见下文「Excel 导入模板列契约」）
- `<projectId>`：目标项目 id（或由代理按项目名解析）
- `<folderId>`（可选）：项目文件库目标文件夹 id（`file-module list` 解析；缺省上传到根目录）
- `<moduleId>`（可选）：用例目标功能模块 id（`functional-module list` 解析；缺省按每行「所属模块」nodePath 匹配）

## Prompt

你现在是资深功能测试工程师。请按以下流程，把 excel 导入模板格式的用例文件批量写入 MeterSphere v2 功能用例，并把原文件共享关联到全部新生成的用例。

**阶段 1：解析 ID**

1. 用 `./skills/scripts/v2/ms.sh project list` 列出项目，按 `name` 匹配目标项目名，得到 `projectId`。0 个匹配说明项目名写错或环境变量不对；多个匹配说明项目名不唯一，需人工确认，不要擅自选一个。
2. 用 `./skills/scripts/v2/ms.sh functional-module list '<projectId>'` 列出功能模块树，按 `name` 匹配目标子模块，得到 `moduleId` 与 `nodePath`。0 个或多个匹配 → 告警，不自动选。
3. 用 `./skills/scripts/v2/ms.sh file-module list '<projectId>'` 列出项目文件库文件夹树，按 `name` 匹配目标文件夹，得到文件夹 `moduleId`。0 个或多个匹配 → 告警，不自动选；调用方未指定文件夹时跳过本步（上传到根目录）。

**阶段 2：拆分草稿（本地，无网络）**

`python3 skills/scripts/v2/ms_split_cases.py <excelFile> --project-id <projectId> -o drafts.json`

- 按模板列序解析；多行步骤自动合并；缺关键列（用例名称/所属模块）的行跳过并告警——不要编造。
- 标签列须为 JSON 数组字符串（普通逗号文本会被服务端静默丢弃为空，见下文契约）。

**阶段 3：上传原文件到项目文件库（可选指定文件夹）**

`./skills/scripts/v2/ms.sh file create '{"id":"<uuid4>","projectId":"<projectId>","storage":"MINIO","name":"<文件名>","moduleId":"<folderId>"}' <excelFile>`

- body 里的 `moduleId` 即项目 > 文件 的**文件夹 id**（v2.10 `FileMetadata.moduleId`，实测）；缺省省略该键 = 根目录。
- 服务端按 name 去重：同名文件已存在时改用 `./skills/scripts/v2/ms.sh file list '<projectId>'` 查已有文件 id，不要重复上传。
- 得到 `fileMetadataId`。

**阶段 4：写入并同调用关联**

`./skills/scripts/v2/ms.sh functional-case batch-create drafts.json --file-id <fileMetadataId>`

- 每条用例自动注入 `relateFileMetaIds:[<fileMetadataId>]`——N 条用例共享同一份 MinIO 对象（零拷贝）。
- 全部用例已存在（查重全跳过）时幂等跳过：不上传不写入，直接报告。
- 中途失败即停并报告已完成步骤（可重跑，幂等）。

**阶段 5：输出计数清单**

zh-CN 输出：拆分数 / 跳过数 / 写入数 / fileId / caseId 列表。不倾倒原始 JSON。

## Excel 导入模板列契约（TestCaseImportFiled.java 列序即列序）

ID(可选) → 用例名称(name, 必填 ≤255) → 所属模块(nodePath, 必填, 正则禁 `//`) → 标签(tags, 可选, **JSON 数组字符串** `["a","b"]`) → 前置条件 → 步骤描述 → 预期结果 → 编辑模式(可选 TEXT|STEP) → 备注 → 用例状态 → 责任人 → 用例等级(P0-P3) + 自定义字段列。

- `importType` 仅 `Create | Update`（v2.10 ExcelImportType 枚举）。
- `.xmind` 同端点（POST /test/case/import，服务端按扩展名分发到 XmindCaseParser）。

## 字段契约（v2，禁 v3-only 字段）

- 必填：`name`、`projectId`、`nodeId`、`nodePath`、`priority`(P0-P3)、`steps`([{num,desc,result}])、`caseEditType`("STEP")
- 可选仅在有值时：`precondition`、`remark`、`tags`（**JSON 编码字符串** `"[\"a\",\"b\"]"`，不是裸数组）
- ⚠️ 两个 moduleId 勿混用：草稿里的 `nodeId` 是**功能用例模块** id（functional-module 树）；上传文件 body 里的 `moduleId` 是**文件库文件夹** id（file-module 树）——两个不同体系。

## 安全规则

- 写入前必须已设 `METERSPHERE_PROJECT_ID`（脚本守卫，防误写硬编码项目）。
- 全部已存在时幂等跳过（不上传不写入）；重跑安全。
- 不绕过 ms.sh 手写 curl（签名易错）；拆分阶段不调用网络。
- 不实现 xmind 导出（仅导入/拆分；导入走既有端点，服务端按扩展名分发）。
