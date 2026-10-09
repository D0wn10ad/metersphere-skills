# MeterSphere API 参考（混合模式版）

## 1. 推荐策略

推荐采用三段式：

1. **本地生成 JSON 草稿**
2. **AI 模型增强草稿**
3. **批量写入 MeterSphere**

## 2. 真实鉴权

请求头：

```http
accessKey: <AK>
signature: <动态签名>
```

## 3. 功能用例混合流程

### 生成草稿

```bash
./scripts/ms.sh functional-case generate <projectId> <moduleId> <templateId> <requirement-file>
```

### AI 增强模板

```text
references/ai-functional-case-prompt.md
```

### 批量写入

```bash
./scripts/ms.sh functional-case batch-create <json-file>
```

## 4. 接口定义 / 接口用例混合流程

### 生成草稿 bundle

```bash
./scripts/ms.sh api import-generate <projectId> <moduleId> <openapi-file-or-url>
```

### AI 增强模板

```text
references/ai-api-bundle-prompt.md
```

### 批量写入

```bash
./scripts/ms.sh api batch-create <json-file>
```

## 5. 当前本地生成能力

### 功能用例
- 主流程
- 异常场景
- 边界场景
- 基础优先级 / 标签

### 接口用例
- 成功场景（200）
- 必填缺失（400）
- 边界场景（200）
- example/schema 自动带值
- 基础状态码断言自动挂载

## 6. 查询辅助接口

- `POST /system/organization/list`
- `GET /project/list/options/{organizationId}`
- `GET /functional/case/module/tree/{projectId}`
- `GET /functional/case/default/template/field/{projectId}`
- `POST /api/definition/module/tree`

## 7. 功能用例评审相关接口

已确认可用的 case-management 评审相关接口包括：

- `POST /functional/case/review/page`
  - 从**功能用例视角**查询它参与过哪些评审
  - 适合回答：某条用例有没有被评审过
- `POST /case/review/page`
  - 查询项目下评审单列表
  - 返回 `reviewedCount / unReviewCount / underReviewedCount / passCount / unPassCount`
- `GET /case/review/detail/{id}`
  - 查询单个评审单详情
- `POST /case/review/detail/page`
  - 查询某评审单下已关联的功能用例列表
  - 每条记录包含 `status / myStatus / reviewers / reviewNames`
- `GET /case/review/module/tree/{projectId}`
  - 查询评审模块树
- `GET /case/review/user-option/{projectId}`
  - 查询具备评审权限的用户列表
- `GET /case/review/detail/reviewer/status/{reviewId}/{caseId}`
- `GET /case/review/detail/reviewer/status/total/{reviewId}/{caseId}`
  - 查询单条用例在评审中的人和状态汇总
- `GET /review/functional/case/get/list/{reviewId}/{caseId}`
  - 查询单条用例在某次评审中的评审历史

## 8. 如何判断“哪些用例被评审过”

推荐两种口径：

### 口径 A：功能用例维度（最适合用户问答）

对项目下每条功能用例调用：

- `POST /functional/case/review/page`
- `GET /functional/case/detail/{id}`

其中：

- `functional/case/review/page` 用于判断该用例是否参与过评审
- `functional/case/detail/{id}` 返回详情字段，可直接读取：
  - `bugCount`：该用例关联的缺陷数量
  - `caseReviewCount`：该用例关联的评审数量
  - `testPlanCount`：该用例关联的测试计划数量

若 `functional/case/review/page` 返回列表非空，则该用例**被评审过**；否则可视为**未被评审过**。

### 口径 B：评审单维度

先查：

- `POST /case/review/page`

再对每个评审单查：

- `POST /case/review/detail/page`

可以得到“某个评审单里有哪些用例、每条用例当前评审状态”。

## 9. 当前限制

- 更细粒度 JSONPath 断言仍建议由 AI 增强阶段补充
- 当前本地生成仍以稳定、可落库为优先

## 10. 接口定义导入（fullCoverage）幂等语义与陷阱

> 以下均为现场实测证实的事实（v2.10.26-lts），适用于 `api import-generate` / `api import-create`。

### 双份前缀是正确且必需的

- 接口定义相关端点必须走**双份前缀** `{BASE}/api/api/definition/...`（v2 网关 `/{serviceId}/**` 剥离首段后，服务自身 context 为 `/api`）。
- **单份前缀** `{BASE}/api/definition/get/{id}` 会得到 Spring 404（`{"status":404,"error":"Not Found"}`，无 `success` 键）——不是数据不存在，是路径打错。
- `ms.sh` 的 `request()` 第 4 参默认 `api`，传空串 `""` 仍回退为 `api`（`${4:-api}`）——不要试图"改单份"。

### fullCoverage 重复导入的幂等语义

- fullCoverage 模式**按 path 去重**：重复导入同一 spec 不会落新定义行，但导入响应 `data.data[]` 返回的是**解析阶段新生成的不可查询 id**（GET 该 id 得 `{"success":true,"data":null}`），不是持久化 id。
- 因此**不能直接消费导入响应里的 id** 去 detail GET / 关联用例——首次导入成功仅因响应 id 恰为持久化 id，重复导入必失败。
- **正确做法（v2 已内置）**：按 name 从 `POST /api/api/definition/list/{goPage}/{pageSize}`（body `{"projectId":...,"protocols":[...]}`）解析持久化 id，再用持久化 id 做 detail GET 与已存在用例预检。同名定义多个时取首个并输出中文警告。
- **勿消费导入响应内联 request**：`apiDefinitionId` 必须来自持久化 id 的 detail，否则用例归属错误。

### name 漂移语义

- spec 中端点 name 变更（path 不变）再导入：fullCoverage 按 path 去重不落新行，但会**更新既有定义的 name**（id/createTime 不变）。
- 此时按 name 解析仍能命中（改名后的定义在列表中），旧用例变体名不匹配新变体名 → 生成新变体用例（EXIT 0）→ 重跑跳过，幂等成立。
- 若 name 在定义列表中完全不存在（如跨项目、列表拉取失败），回退响应 id → detail GET 得 `data:null` → 输出中文诊断并跳过该定义。

## 11. 项目文件库 / 用例附件 / 未规划模块（现场实测 + source-only）

> 以下除明确标注 `未验证 (source-only)` 者外，均为现场实测证实的事实（v2.10.26-lts）。v3 章节无服务器可连，**全部为推测来源，不得当作已验证**。

### 11.1 包装响应形状

所有 track / file 端点的成功响应统一为：

```json
{ "success": true, "data": ... }
```

- 失败时 `success:false`（或 HTTP 4xx/5xx）。脚本以子串匹配 `"success":false` 判失败。
- 部分写操作 `data` 为 `null`（如 `attachment relate` 成功返回 `{"success":true,"data":null}`）。

### 11.2 项目文件库 file 资源（v2）

- **暴露动作仅**：`file create '<JSON>' <local-file>`（`POST /file/metadata/create`，multipart：`request=FileMetadataCreateRequest` + `file=@`）与 `file exists <fileId>...`（`POST /file/metadata/exists`，载荷为 id 数组）。
- 服务端**按 name 去重**：已存在同名文件时创建失败，英文消息 `The file already exists`。
- `file exists` 仅回显存在的 id；脚本据「请求 id 集合 − 回显集合」判缺失，任一缺失即 zh-CN 报错退出。
- **反模式（禁止）**：`file` 资源的**按名称过滤的分页 / 列表查询**端点实测已损坏，脚本刻意不暴露 `list` / `get`（调用即 `file 资源不支持 list/get`）。发布路径只有 create + exists。
- 库文件元数据删除可能返回 HTTP 500 却已删除——**必须重新查询确认**（list / exists 为空）。

### 11.3 用例附件与库文件关联（v2）

用例内上传与库文件关联是两条不同路径：

- `attachment upload <caseId> <file>`：multipart（`sourceId=caseId` + `file=@`），产生**绑定到该用例 sourceId 的附件行**。
- `attachment list <caseId>`：`POST /attachment/metadata/list`，body `{belongId, belongType:"testcase"}`，返回该用例附件元数据（id / name / size / isLocal / creator…）。
- `attachment relate <caseId> <fileId>...`：`POST /attachment/testcase/metadata/relate`，body `{belongId, belongType:"testcase", metadataRefIds:[...]}`。
- **relate 只接受库文件元数据 id**：
  - 传库 id（来自 `file create`）→ `{"success":true,"data":null}`。
  - 传「另一条用例的用例内附件行 id」（取自该用例 attachment list）→ **HTTP 500** `{"status":500,"error":"Internal Server Error","path":"/attachment/testcase/metadata/relate"}`。这是服务端用法边界，不是客户端缺陷。
- **级联删除**：删除用例会级联删除其附件关联；删除后该用例 `attachment list` 返回 `[]`。

### 11.4 batch-create --file-id 的共享语义（v2）

- `functional-case batch-create <json-array-file> --file-id <fileMetadataId>` 在写入前把该库文件 id 注入每条用例的 `relateFileMetaIds`（`ms.sh` 与 `ms_batch.py --attach-file-id` 均做去重注入）。
- 服务端**零拷贝**：N 条用例共享同一份 MinIO 对象（attachment list 中 filePath 相同、createTime 相同）——库文件语义，而非每用例复制。
- 因用例内附件行绑定到各自 sourceId，无法借 `attachment relate` 挂到另一条用例（见 11.3），故跨用例共享只能走 `file create` + relate / `--file-id`。

### 11.5 未规划用例模块解析（v2）

- 省略 module（`-` 或空）时，生成器输出 `default-module` 占位（`nodePath` 恒为 `/` + nodeId）。
- `batch-create` 检测到占位后，**按项目实时查询** `GET /track/case/node/list/{projectId}`，取 `name == '未规划用例'` 且 `parentId is None` 且 `level == 1` 的节点，把该项目的 `nodeId` 与 `nodePath`（`/未规划用例`）一并写入载荷。
- 实测：两个项目分别把全部用例落进各自的「未规划用例」节点（对同一模块树端点做 oracle，nodeId 匹配率 100%）。
- 解析失败（nodePath 为空、以 `/default-module` 开头、或仍等于 `/<nodeId>`）→ 逐元素硬失败 `batch-create 第 N 个用例解析失败: nodePath 无效或未能解析模块`。

### 11.6 其他服务端怪癖（v2 实测）

- `POST /track/test/case/list/{n}/{size}` **要求请求体内带 `projectId`**，否则不能按项目过滤。
- 库文件创建**按 name 去重**（英文 `The file already exists`）；库文件删除**可能 500 却已删除**（见 11.2）。
- `batch-create` **逐元素非原子**：中途失败时先前的元素已落库、不会回滚。若失败响应体含 `"success":false`，脚本以 zh-CN 报错并退出（exit 1）；若失败体不含该键（如其他 HTTP 错误体），则原样打印该元素的**未包裹 zh-CN 的原始服务端错误**后继续处理，最后打印 `batch-create 完成: 共 N 个元素，成功创建 M 个用例`（exit 0）——此裸错误输出是已知的 cosmetic gap。
- 附件关联随用例**级联删除**（见 11.3）。

### 11.7 v3 file / attachment（未验证 (source-only)）

> 本环境无 v3 服务器可连，v3-only 路径返回 404。以下路径来源 v3.x 源码，**全部为 `未验证 (source-only)`**。

- `file upload`：`POST /project/file/upload`（multipart，JSON body + 文件）——`未验证 (source-only)`。
- `file page`：`POST /project/file/page`——`未验证 (source-only)`。
- `file delete`：`POST /project/file/delete`——`未验证 (source-only)`。
- `attachment upload`：`POST /attachment/upload/file`——`未验证 (source-only)`。
- `attachment page`：`POST /attachment/page`——`未验证 (source-only)`。
- `attachment delete`：`POST /attachment/delete/file`——`未验证 (source-only)`。
- `attachment relate`：v3 复用 `attachment upload` 端点并携带 `{projectId, caseId, fileIds}`——`未验证 (source-only)`。
- `file list/get` 与 `attachment list/get` 在 v3 均被拒绝（改用 `page`）——`未验证 (source-only)`。
- v3 省略 module → 字面量 `root`——`未验证 (source-only)`。
