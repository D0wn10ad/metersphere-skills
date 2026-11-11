# metersphere-skill Runtime-Decision Review

- **Branch:** `review/metersphere-skill-runtime-review`
- **Scope:** documentation-only review of the `metersphere` Agent Skill. No `skills/` code is changed; every recommendation below is a proposal, not an implementation.
- **Evidence:** SKILL.md / README / v2 `ms.sh` line citations + two real agent-run transcripts of the EXCEL TEMPLATE IMPORT workflow (`/mnt/c/Users/T14/Downloads/session-ses_e3c9.md`, `/mnt/c/Users/T14/Downloads/session-ses_e407_noversion.md`).
- **Status of forks:** all forks are DECIDED; see `## Recommendations` for the applied resolutions.

---

## TL;DR

The skill is functionally capable, but it pushes many **deterministic decisions onto the agent at run time**: version routing, definition-vs-case gap analysis, template routing, acceptance checks, excel normalization, cross-skill stitching, version-id resolution, header normalization, shell-loop fragility, folder-vs-file ambiguity, and import case-id reporting. Each one is a place where two runs can diverge and where tokens are burned re-deriving the same answer. The fix is a single principle: move those decisions from **runtime** to **skill-build time** (scripts + reference docs), leaving only irreducible parameters in the prompt.

---

## FIX PRINCIPLE

**Shift decisions from runtime to skill-build time.** Anything the agent computes deterministically on every run should be a script. The prompt should carry only the irreducible parameters: **project, file, ticket id.** If a decision has a single correct answer derivable from the repo or the server, the skill must encode it once (in a script or a reference file), not re-derive it in prose on each invocation.

Corollaries:
- A script owns the decision and its exit code; prose only explains how to call it.
- A reference file owns a data contract (schema, mapping, locale set); the prompt does not re-negotiate it.
- If the agent can only answer by trial-and-error against the server (path guessing, header probing), that trial-and-error belongs in a script.

---

## Findings

### Findings A–F (structural hotspots)

**A. Version routing is agent-decided.**
`skills/SKILL.md:26` tells the agent "MeterSphere v2 users: use `./scripts/v2/ms.sh` (auto-detect version, or set `METERSPHERE_VERSION=v2` to force)". The routing decision between the root (v3.x) and `v2/` script trees is left to the agent's reading of the prompt. Grounding: the two script trees are independent files (`skills/scripts/ms.sh` vs `skills/scripts/v2/ms.sh`), and `skills/scripts/v2/ms.sh:23` reads `METERSPHERE_VERSION="${METERSPHERE_VERSION:-}"` while `detect_version` (`skills/scripts/v2/ms.sh:93-115`) only resolves after the correct tree is already chosen. → R2.

**B. Gap analysis (definition-vs-case difference set) is agent-computed — the biggest hotspot.**
There is no `gap` command anywhere in `skills/scripts/v2/ms.sh` (grep `gap` = 0 matches). The building blocks exist: `skills/scripts/v2/ms.sh:304-307` maps `api`→`METERSPHERE_API_DEFINITION_LIST_PATH` and `api-case`→`METERSPHERE_API_CASE_LIST_PATH`; the `list` action is wired at `skills/scripts/v2/ms.sh:552` (`list) [[ -n "$list_path" ]] || die "资源 $resource 不支持 list"`); and both list endpoints auto-paginate into a merged `{"success":true,"data":[all]}` (`skills/SKILL.md:403`). The agent still hand-computes two paginated fetches + a set-diff + group on every run. → R1/R3.

**C. Template routing is re-resolved each run.**
`skills/SKILL.md:406-409` maps "user intent → reference template": e.g. "read existing APIs and generate API cases / fill APIs without cases" → `references/ai-existing-api-to-cases-prompt.md`; "generate from Swagger/OpenAPI 3 JSON" → `references/ai-swagger-to-api-cases-prompt.md`. This is a judgment the agent repeats every run instead of a command lookup. → R5.

**D. Acceptance logic is prompt-injected; the only self-check (`ms doctor`) is unwired.**
`ms doctor` exists (`skills/scripts/v2/ms.sh:479-513`) but only checks binaries (`python3`/`openssl`/`curl`), env vars (`BASE_URL`/`ACCESS_KEY`/`SECRET_KEY`), version metadata + git short SHA, and a connectivity probe. It does NOT check workflow acceptance criteria such as "difference set = 0" or "request is not an empty shell". Those criteria are re-injected into every prompt. → R3.

**E. Excel schema + normalization is prompt-negotiated.**
The 11-column schema (Name, Module, Tag, Prerequisite, Step description, Step result, Edit Model, Remark, Case status, Maintainer, Priority), the merged step-blocks, the `[Finished, Running, Prepare]` status whitelist, and the "责任人 required" rule live in no reference file: grep `Finished|Running|Prepare|Step description|Edit Model` across `skills/references/` = 0 matches. `README.md:434` documents `--fix-status` / `--default-maintainer` (normalize a temp copy, never the original; needs openpyxl; merged cells write anchor row only), but `skills/SKILL.md` contains ZERO `fix-status` matches. → R4/R8.

**F. Cross-skill composition is 3 manual hops.**
`doc-based-testcase-generator` does not emit a metersphere-v2 excel-ready xlsx (grep `xlsx|excel|metersphere` in that skill's SKILL.md = 0 matches). The chain PRD → generator → xlsx → `functional-case import` requires hand-stitching the format. → R6 (deferred).

### Findings G–L (from the two real EXCEL TEMPLATE IMPORT transcripts)

Both runs succeeded, but with heavy runtime friction. Transcript citations below are phrased as **"content present within the cited range"** — the referenced content sits inside that range, not necessarily on the exact single line.

**G. Version-id resolution is a major hotspot.**
Both transcripts show the agent spending ~10–15+ turns path-guessing the version endpoint before finding the version id. Content present within `ses_e3c9.md:1535` ("the important step: version v1.0.0 … I need the version ID … let me check how versions are queried") through `ses_e3c9.md:2648` ("The versionId for v1.0.0 is `48f13177-fe4c-424c-b119-871960f7ea76`"), and `ses_e407_noversion.md:1932` ("First, I need the version id for v1.0.0. Let me query the version list") through `ses_e407_noversion.md:2158` ("versionId for v1.0.0: `48f13177-…`"). The agent tried `/track/project/version/getVersions`, `/track/project/version/list`, `/track/test/case/version/getVersions`, `/track/test/case/version/list/{id}`, `/track/test/case/version/{id}/all`, `/project/version/init`, POST variants (all 404/405/401) before discovering the id by reading an existing functional case's list (`versionId` + `versionName:"v1.0.0"`). There is NO version list command in `ms.sh` (grep `version list|getVersions|project/version` = 0 matches) and NO version endpoint in `skills/references/ms-api.md` (grep `version` = 0 matches). A deterministic lookup should be scripted. → R7/R7a.

**H. Header-language normalization is prompt-negotiated; the rule is all-or-nothing for the HEADER ROW only, across THREE locales.**
Server rule (`README.md:434`): the v2 import server selects the single acceptable header set per request locale (`LocaleContextHolder`) and rejects a header row that matches none with `case_import_table_header_missing`. There are **three** supported locales — en-US / zh-CN / zh-TW — not two. The import path already auto-detects the first-row header and sends the matching `Accept-Language`, and `--lang en|zh|tw` forces it. Header language and cell-value allowed sets are SEPARATE concerns: 编辑模式/Edit Model ∈ {`STEP`,`TEXT`}; 用例状态/Case status ∈ a few allowed statuses (e.g. `未评审`/`已评审`, or the `[Finished, Running, Prepare]` whitelist); 责任人/Maintainer must be an existing project user; 用例等级/Priority ∈ the template's allowed fields. **Observed defect:** the transcript xlsx used Chinese headers and the first import failed with `缺少名称表头` (missing Name header, HTTP 500; content present within `ses_e407_noversion.md:2769`). Because the server rule is per-locale with auto-negotiation, this is NOT explained by a blanket "server requires English"; the open question is why auto-detect failed (mixed-language header row / wrong `Accept-Language` / inconsistent locale tag). The ambiguity is itself the defect, so the agent hand-writes an openpyxl rename script every run (rename script content present within `ses_e3c9.md:3554-3571`). → R8.

**I. Shell-loop fragility.**
Content present within `ses_e3c9.md:3161-3399`: the picture-upload loop broke because the agent `cd /opt/testcaseimport/pictures` then used relative `./scripts/v2/ms.sh`, which no longer resolved → confusing errors (a mangled `python3 -c`, `'/opt/testcaseimport/pictures/-c' FileNotFoundError`; the JSON decode trace at `ses_e3c9.md:3399`). The agent redid it with the absolute path `$HOME/.agents/skills/metersphere/scripts/v2/ms.sh` (content present within `ses_e3c9.md:3420-3438`). Also a bash gotcha: `UID` is readonly — content present within `ses_e407_noversion.md:2518` (`/bin/bash: line 2: UID: readonly variable`); the agent had to rename to `MYUID`. → R9.

**J. "这两个文件" folder-vs-file ambiguity.**
The task said "把这两个文件关联到全部新生成的用例" (associate these TWO files), but `pictures` is a folder of 5 PNGs. The agent agonized over the interpretation (content present within `ses_e3c9.md:2704-2730` and `3107-3129`) and finally uploaded 6 files (xlsx + 5 PNGs) and related all 6 to each case. This is a prompt/reference clarity issue. → R10.

**K. Import reports delta count but NOT new case IDs.**
After `functional-case import` succeeded ("import 完成: 新增 12 条"), the agent had to re-list ALL cases and match by name to identify the 12 new case IDs before it could `attachment relate` (content present within `ses_e3c9.md:3691-3743`; `ses_e407_noversion.md:3185-3235`). Import should return the new case IDs. → R11.

**L. `attachment relate` success shape.**
`attachment relate` returns `{"success":true,"data":null}`, which the agent had to know is the expected success response (documented at `skills/SKILL.md:479`). The agent initially worried it was a failure. Minor — already documented; no build-time shift recommended.

### New Finding M (from v2.10 LTS source, not a runner transcript)

**M. Inline rich-text images require pre-serving via `/md/upload` before the markdown link can be placed in a WYSIWYG cell; the returned storage key is `<id>+<ext>`, not the original filename.** This is DISTINCT from case-level attachment (`file create` + `attachment relate`, `belongType:testcase`), which attaches pictures as case attachments but does not place them inline. Source audit: `ResourceController.java:19-21` (`POST /md/upload`), `ResourceService.java:43-51` (`getMdImage`), commit `b2d3d1d09ac119d6c03d7b767e33fd449665ced5` (v2.10.26-lts). → R12.

---

## Recommendations

Each recommendation is grounded in the actual mechanism with line citations. Fork resolutions below are DECIDED and not open for re-litigation.

**R1. Scripted gap analysis — add `api-case gap <projectId>` to the v2 script tree (biggest win).**
The command fetches API definitions and API cases (both auto-paginate into merged `{"success":true,"data":[all]}`, `skills/SKILL.md:403`), computes the difference set by `apiDefinitionId`, and exits 0 when the gap is zero. The agent stops hand-computing two paginated fetches + set-diff + group. Grounding: dispatch map at `skills/scripts/v2/ms.sh:304-307`, `list` action at `skills/scripts/v2/ms.sh:552`, no `gap` action exists (grep = 0 matches).

**R2. Cascading version resolution — script-level, in `skills/scripts/v2/ms.sh detect_version`.**
Decided cascade order:
1. `.env` `METERSPHERE_VERSION` (`skills/scripts/v2/ms.sh:23`).
2. Discovery probe `GET /system/version/current`.
3. **IF the probe is ambiguous** → prompt the user `'v2 还是 v3?'`.
4. Default to **v2** if the user gives no answer.

**"Ambiguous" is defined explicitly as:** the curl to `/system/version/current` returns a **non-200 status** OR a **connection error/timeout** — i.e. the probe cannot definitively determine the version. Grounding: `detect_version` (`skills/scripts/v2/ms.sh:93-115`) currently returns on env or probe only; the prompt tier is the missing middle link and must be shell logic (it must decide before any prompt is composed). Note: v3 has `/system/version/current`; v2 does not, which is why a non-200 currently infers v2 — but a timeout/connection error is different from a clean non-200 and must be treated as ambiguous, not silently as v2.

**R3. Merge acceptance checks into the command contracts (ONE output schema per command).**
`api-case gap <projectId>` exits 0 when the difference set is empty, exit 1 when non-empty. `verify-request <definitionId>` exits 0 when the request body is non-empty ("非空壳" = has a method, a path, and at least one non-empty request body / parameter block), exit 1 otherwise. Decided output schemas:
- **`api-case gap` prints a list of `apiDefinitionId` + `name` lines** (one per missing case).
- **`verify-request` prints a plain status line.**

Both are machine-readable so a wrapper can branch on exit code without scraping prose. `functional-case import` already owns its own 3-way check (HTTP 200 + `success:true` + 落库增量, `README.md:505`); trust it instead of re-deriving it in prose. `ms doctor` (`skills/scripts/v2/ms.sh:479-513`) stays a binary/env/connectivity self-check and does not own workflow acceptance.

**R4. Move the excel schema + normalization into `skills/references/excel-import-schema.md` (new file).**
Do NOT fold it into `ai-v2-functional-case-prompt.md`; the schema is a shared data contract referenced by both the v2 functional-case flow and the future cross-skill seam (R6). Content: the 11-column schema, merged step-blocks, the `[Finished, Running, Prepare]` whitelist, "责任人 required", and the normalization flags (`--fix-status` / `--default-maintainer`). Grounding: `README.md:434`; SKILL.md surfaces `fix-status` 0 times.

**R5. Add a SKILL.md "工作流速查表" decision table (task keyword → exact command, not template).**
e.g. "补齐无用例的接口" → `api-case gap <projectId>`; "从 Swagger/OpenAPI 3 JSON 生成" → `api import-create <projectId> <spec>`. Grounding: no decision table exists (grep `工作流速查表|决策表|decision table` in SKILL.md = 0 matches); current routing is the template map at `skills/SKILL.md:406-409`.

**R6. Cross-skill seam — make `doc-based-testcase-generator` emit a metersphere-v2 excel-ready xlsx (DEFERRED).**
Deferred, out of scope for this single deliverable. Chain would become PRD → generator → xlsx → `functional-case import` with zero runtime format stitching. Grounding: no such emitter exists today.

**R7. Scripted version-id resolution — `skills/scripts/v2/ms.sh functional-case version <projectId>` (primary).**
Returns the project's version list (id + name) so the agent stops path-guessing. Resolve against a functional-case module tree, so it belongs on the `functional-case` resource. Edge cases: zero versions → empty list + exit 2 with a clear "no versions" message; multiple versions → return all (id + name), default to the first if no preference is given. The new command must REPLACE the hardcoded mapping at `skills/SKILL.md:304` (`1163437937827840 → versionId 1163437937827887`); that fallback stays only behind `METERSPHERE_DEFAULT_VERSION_ID`, never as the primary path. Grounding: no version command exists (grep = 0 matches); transcript path-guessing (Finding G).

**R7a. Document the version endpoint in `skills/references/ms-api.md` (secondary).**
`ms-api.md` currently has ZERO `version` matches; document the endpoint so R7's implementation has a source-of-truth reference.

**R8. Scripted header-language normalization — add `--fix-headers` to `functional-case import`, orthogonal to `--fix-status` / `--default-maintainer`.**
`--fix-headers` normalizes the header row to ONE of THREE locale sets, selected by `--lang en|zh|tw` (default auto-detect), **never a mix**:
- **EN:** `Name / Module / Tag / Prerequisite / Step description / Step result / Edit Model / Remark / Case status / Maintainer / Priority`
- **zh-CN:** `用例名称 / 所属模块 / 标签 / 前置条件 / 步骤描述 / 预期结果 / 编辑模式 / 备注 / 用例状态 / 责任人 / 用例等级`
- **zh-TW:** `用例名稱 / 所屬模組 / 標籤 / 前置條件 / 步驟描述 / 預期結果 / 編輯模式 / 備註 / 用例狀態 / 責任人 / 用例等級`

Run on a temp copy (never the original). Cell values follow their own per-column allowed sets regardless of header language (编辑模式/Edit Model ∈ {`STEP`,`TEXT`}; 用例状态/Case status ∈ allowed statuses; 责任人/Maintainer ∈ existing project users; 用例等级/Priority ∈ allowed fields). Grounding: `--fix-status`/`--default-maintainer` parsing at `skills/scripts/v2/ms.sh:2183-2198` rewrites cell values only, not headers; both transcripts show the agent hand-writing an openpyxl rename script after `缺少名称表头` (`ses_e407_noversion.md:2769`).

**R9. Skill guidance for shell-loop robustness — target `skills/SKILL.md`, new subsection under the v2 section (e.g. `## v2 脚本健壮性`).**
Instruct: use absolute script paths, and do not `cd` away from the skill dir when looping over files; avoid the readonly `UID` bash variable. Grounding: `ses_e3c9.md:3161-3399`, `ses_e407_noversion.md:2518`.

**R10. Clarify folder-vs-file semantics — target `skills/references/ai-v2-functional-case-prompt.md`.**
Add a folder-vs-file clarification to the file-library upload/relate steps: state explicitly whether a path is a single file or a folder, and if a folder, whether to upload each member file. Grounding: `ses_e3c9.md:2704-2730`, `3107-3129`.

**R11. `functional-case import` ITSELF returns the new case IDs (not a separate helper).**
The import command's own output must include the new case IDs (in addition to the delta count), so the agent does not re-list all cases and match by name before `attachment relate`. Grounding: both transcripts re-list all cases and match by name after import reported only "新增 12 条" (`ses_e3c9.md:3691-3743`; `ses_e407_noversion.md:3185-3235`).

**R12. Scripted inline-image pre-serving — add a new `md upload` action.**
Do NOT fall back to documenting a hand-written `raw POST /md/upload` (a raw POST re-introduces per-request signature construction, which the skill exists to avoid). `md upload` pre-serves a picture at the `/resource/md/get` path and returns the storage key so the agent can place the markdown link in a rich-text cell before import. Grounding: Finding M (v2.10.26-lts `ResourceController.java:19-21`, `ResourceService.java:43-51`, commit `b2d3d1d09ac119d6c03d7b767e33fd449665ced5`). Critical caveat: the stored fileName is server-generated `<id>+<extension>`, NOT the original filename — the markdown link must use the RETURNED storage key.

---

## Finding ↔ Recommendation Mapping

| Finding | Recommendation | Hotspot |
| --- | --- | --- |
| A | R2 | version routing |
| B | R1 | gap analysis |
| C | R5 | template routing |
| D | R3 | acceptance checks |
| E | R4 | excel schema |
| F | R6 | cross-skill seam |
| G | R7 / R7a | version-id resolution |
| H | R8 | header normalization |
| I | R9 | shell-loop fragility |
| J | R10 | folder-vs-file ambiguity |
| K | R11 | import case-id reporting |
| L | none-documented | attachment relate success shape (already in `skills/SKILL.md:479`) |
| M | R12 | inline rich-text image pre-serving |

---

## Runner prompts (evidence)

Three real runner prompts were exercised in the original session.

### Prompt (1) — EXCEL TEMPLATE IMPORT

Reconstructed from the transcripts (the task message is present within `session-ses_e3c9.md:505-515`, mirrored at `session-ses_e407_noversion.md:508-515`). Reproduced verbatim as recovered; the skill-instruction preamble above it is the standard SKILL.md block, not the task.

> 把 \opt\testcaseimport\new\Meetily-测试用例_CN.xlsx 批量写入 Project: igus项目 的功能用例。
>
> 1. 导入方式：使用 `functional-case import`（服务端 excel 导入，该 xlsx 是 v2 导入模板格式）。不要用 split+batch-create。
> 2. 项目：igus 若不存在先创建或询问，不要反复轮询。
> 3. 文件库：把原 xlsx 和 \\wsl.localhost\Ubuntu-26.04\opt\testcaseimport\pictures 上传到文件库「测试附件」文件夹（file-module，与 functional-module 是两套体系；不存在则先 file-module create）。
> 4. 关联：把这两个文件关联到全部新生成的用例（attachment relate）。
> 5. 数据规范化：xlsx 可能非导入就绪（Case status="Pass"、Maintainer 空）。若校验失败，复制到 /tmp 修正（Pass→Finished，Maintainer→admin）后导入副本；绝不改原文件。
> 6. 验证标准：① 用例数与xlsx一致；② 两文件均在「测试附件」；③ 抽查 ≥2 个用例 attachment list 确认均已关联。
> 7. 版本：默认版本 v1.0.0。

### Prompt (2) — EXISTING APIS → API CASES

**Session-DB-only, not recoverable on disk — titles only.** Only the title is available in this environment; no transcript for this run exists on disk. Per the repository's verification discipline, no prompt text is fabricated here. The intended workflow is documented at `skills/SKILL.md:406-409` (→ `references/ai-existing-api-to-cases-prompt.md`) and the corresponding recommendation is R1/R3 (`api-case gap`) / R5.

### Prompt (3) — SWAGGER/OPENAPI 3 JSON → API CASES

**Session-DB-only, not recoverable on disk — titles only.** Only the title is available; no transcript for this run exists on disk. No prompt text is fabricated. The intended workflow is documented at `skills/SKILL.md:406-409` (→ `references/ai-swagger-to-api-cases-prompt.md`), with the command path `api import-create <projectId> <spec>` (R5).

---

## Verification provenance

Raw command output captured for every claim below (AGENTS.md verification discipline — no conclusion without reproducible output).

**Transcript citations — "content present within the cited range" semantics (not "line X = exact content"):**
- `ses_e3c9.md:3554` is a `**Tool: bash**` marker immediately followed by the openpyxl rename script — the content is in the range `3554-3571`, not on the exact line.
- `ses_e3c9.md:1535`/`:2648`, `ses_e407_noversion.md:1932`/`:2158`: version-id resolution content present within those ranges (Finding G).
- `ses_e407_noversion.md:2769`: `{"success":false,"message":"缺少名称表头","data":null}` (Finding H).
- `ses_e3c9.md:3161`/`:3399`/`:3420`, `ses_e407_noversion.md:2518`: shell-loop fragility content present within those ranges (Finding I).
- `ses_e3c9.md:2704`/`:3107-3129`: folder-vs-file ambiguity content present within those ranges (Finding J).
- `ses_e3c9.md:3691`/`ses_e407_noversion.md:3185`: import case-id re-listing content present within those ranges (Finding K).

**R12 / Finding M source audit (v2.10.26-lts, commit `b2d3d1d09ac119d6c03d7b767e33fd449665ced5`):**
- `ResourceController.java:19-21` — `POST /md/upload`.
- `ResourceService.java:43-51` — `getMdImage` (serves from `MD_IMAGE_DIR` / `MD_IMAGE_TEMP_DIR`).

**Citation-anchor audit (skills/ + README anchors) — each resolves to a real line containing the claimed token:**
- `skills/scripts/v2/ms.sh:23` (METERSPHERE_VERSION), `:93-115` (detect_version), `:304-307` (dispatch map), `:479-513` (ms doctor), `:552` (list action), `:2183-2198` (--fix-status/--default-maintainer).
- `skills/SKILL.md:304` (hardcoded versionId mapping), `:403` (pagination merge), `:406-409` (§3.0b template map), `:479` (attachment relate success shape).
- `README.md:434` (§8.6 header-language rule), `:505` (§8.6 3-way check).

**Refreshed git status (MAIN repo, `/home/tango/repo/metersphere-skills`):**
```
$ git status --short
?? session-ses_e3c7.md
```
The main worktree is NOT empty (an untracked transcript export is present). This corrects the earlier provenance claim of "(empty, exit 0)".

**Scope guardrail:** this deliverable changes no `skills/` file; only `docs/reviews/metersphere-skill-runtime-review.md` is added on `review/metersphere-skill-runtime-review`.
