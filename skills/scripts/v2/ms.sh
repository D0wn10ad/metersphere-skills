#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# 自调用入口（split-create 编排复用既有 file create / batch-create / attachment relate）。
MS_SH_SELF="${BASH_SOURCE[0]}"
# v2 脚本位于 scripts/v2/，比主包深一层：技能根目录（.env 所在）为上两级。
SKILL_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"
ENV_FILE="${SKILL_DIR}/.env"

if [[ -f "$ENV_FILE" ]]; then
  set -a
  source "$ENV_FILE"
  set +a
fi

METERSPHERE_BASE_URL="${METERSPHERE_BASE_URL:-}"
METERSPHERE_ACCESS_KEY="${METERSPHERE_ACCESS_KEY:-${METERSPHERE_ACCESS_KEY:-}}"
METERSPHERE_SECRET_KEY="${METERSPHERE_SECRET_KEY:-${METERSPHERE_SECRET_KEY:-}}"
METERSPHERE_PROJECT_ID="${METERSPHERE_PROJECT_ID:-}"
METERSPHERE_ORGANIZATION_ID="${METERSPHERE_ORGANIZATION_ID:-100001}"
METERSPHERE_WORKSPACE_ID="${METERSPHERE_WORKSPACE_ID:-}"
METERSPHERE_VERSION="${METERSPHERE_VERSION:-}"
METERSPHERE_HEADERS_JSON="${METERSPHERE_HEADERS_JSON:-}"
METERSPHERE_PROTOCOLS_JSON="${METERSPHERE_PROTOCOLS_JSON:-[\"HTTP\"]}"
# api-case generate-create 的 --tags 专用：JSON 编码后的标签数组字符串（如 ["T-story-123"]），
# 未指定 --tags 时保持空 → 载荷整个省略 tags 键。刻意不给环境变量兜底（标签是调用时显式意图）。
API_CASE_TAGS_JSON=""

[[ -n "${METERSPHERE_ORGANIZATION_LIST_PATH:-}" ]] || METERSPHERE_ORGANIZATION_LIST_PATH='/workspace/list/userworkspace'
[[ -n "${METERSPHERE_PROJECT_LIST_PATH:-}" ]] || METERSPHERE_PROJECT_LIST_PATH='/project/list/related'
[[ -n "${METERSPHERE_PROJECT_LIST_SYSTEM_PATH:-}" ]] || METERSPHERE_PROJECT_LIST_SYSTEM_PATH='/project/list/related'
[[ -n "${METERSPHERE_PROJECT_LIST_BY_ORG_PATH:-}" ]] || METERSPHERE_PROJECT_LIST_BY_ORG_PATH='/project/list/related'
[[ -n "${METERSPHERE_FUNCTIONAL_MODULE_TREE_PATH:-}" ]] || METERSPHERE_FUNCTIONAL_MODULE_TREE_PATH='/case/node/list/{projectId}'
[[ -n "${METERSPHERE_FUNCTIONAL_TEMPLATE_FIELD_PATH:-}" ]] || METERSPHERE_FUNCTIONAL_TEMPLATE_FIELD_PATH='/field/template/case/option/{projectId}'
[[ -n "${METERSPHERE_API_MODULE_TREE_PATH:-}" ]] || METERSPHERE_API_MODULE_TREE_PATH='/api/module/list/{projectId}/{protocol}'
[[ -n "${METERSPHERE_FUNCTIONAL_CASE_LIST_PATH:-}" ]] || METERSPHERE_FUNCTIONAL_CASE_LIST_PATH='/test/case/list/{goPage}/{pageSize}'
[[ -n "${METERSPHERE_FUNCTIONAL_CASE_GET_PATH:-}" ]] || METERSPHERE_FUNCTIONAL_CASE_GET_PATH='/test/case/get/{id}'
[[ -n "${METERSPHERE_FUNCTIONAL_CASE_CREATE_PATH:-}" ]] || METERSPHERE_FUNCTIONAL_CASE_CREATE_PATH='/test/case/add'
[[ -n "${METERSPHERE_FUNCTIONAL_CASE_DELETE_PATH:-}" ]] || METERSPHERE_FUNCTIONAL_CASE_DELETE_PATH='/test/case/delete/{id}'
[[ -n "${METERSPHERE_FUNCTIONAL_CASE_REVIEW_LIST_PATH:-}" ]] || METERSPHERE_FUNCTIONAL_CASE_REVIEW_LIST_PATH='/test/review/case/list/{goPage}/{pageSize}'
[[ -n "${METERSPHERE_CASE_REVIEW_LIST_PATH:-}" ]] || METERSPHERE_CASE_REVIEW_LIST_PATH='/test/case/review/list/{goPage}/{pageSize}'
[[ -n "${METERSPHERE_CASE_REVIEW_GET_PATH:-}" ]] || METERSPHERE_CASE_REVIEW_GET_PATH='/test/case/review/get/{id}'
[[ -n "${METERSPHERE_CASE_REVIEW_CREATE_PATH:-}" ]] || METERSPHERE_CASE_REVIEW_CREATE_PATH='/test/case/review/save'
[[ -n "${METERSPHERE_CASE_REVIEW_DETAIL_PAGE_PATH:-}" ]] || METERSPHERE_CASE_REVIEW_DETAIL_PAGE_PATH='/test/review/case/list/{goPage}/{pageSize}'
[[ -n "${METERSPHERE_CASE_REVIEW_MODULE_TREE_PATH:-}" ]] || METERSPHERE_CASE_REVIEW_MODULE_TREE_PATH='/case/review/node/list/{projectId}'
[[ -n "${METERSPHERE_CASE_REVIEW_USER_OPTION_PATH:-}" ]] || METERSPHERE_CASE_REVIEW_USER_OPTION_PATH='/test/case/review/reviewer'
[[ -n "${METERSPHERE_API_DEFINITION_LIST_PATH:-}" ]] || METERSPHERE_API_DEFINITION_LIST_PATH='/api/definition/list/{goPage}/{pageSize}'
[[ -n "${METERSPHERE_API_DEFINITION_GET_PATH:-}" ]] || METERSPHERE_API_DEFINITION_GET_PATH='/api/definition/get/{id}'
[[ -n "${METERSPHERE_API_DEFINITION_CREATE_PATH:-}" ]] || METERSPHERE_API_DEFINITION_CREATE_PATH='/api/definition/create'
[[ -n "${METERSPHERE_API_DEFINITION_IMPORT_PATH:-}" ]] || METERSPHERE_API_DEFINITION_IMPORT_PATH='/api/definition/import'
[[ -n "${METERSPHERE_API_CASE_LIST_PATH:-}" ]] || METERSPHERE_API_CASE_LIST_PATH='/api/testcase/list/{goPage}/{pageSize}'
[[ -n "${METERSPHERE_API_CASE_GET_PATH:-}" ]] || METERSPHERE_API_CASE_GET_PATH='/api/testcase/get-details/{id}'
[[ -n "${METERSPHERE_API_CASE_CREATE_PATH:-}" ]] || METERSPHERE_API_CASE_CREATE_PATH='/api/testcase/create'
[[ -n "${METERSPHERE_COMMENT_LIST_PATH:-}" ]] || METERSPHERE_COMMENT_LIST_PATH='/test/case/comment/list'
[[ -n "${METERSPHERE_COMMENT_GET_PATH:-}" ]] || METERSPHERE_COMMENT_GET_PATH=''
[[ -n "${METERSPHERE_COMMENT_CREATE_PATH:-}" ]] || METERSPHERE_COMMENT_CREATE_PATH='/test/case/comment/save'
[[ -n "${METERSPHERE_COMMENT_EDIT_PATH:-}" ]] || METERSPHERE_COMMENT_EDIT_PATH='/test/case/comment/edit'
[[ -n "${METERSPHERE_COMMENT_DELETE_PATH:-}" ]] || METERSPHERE_COMMENT_DELETE_PATH='/test/case/comment/delete'
[[ -n "${METERSPHERE_ATTACHMENT_UPLOAD_PATH:-}" ]] || METERSPHERE_ATTACHMENT_UPLOAD_PATH='/attachment/testcase/upload'
[[ -n "${METERSPHERE_ATTACHMENT_LIST_PATH:-}" ]] || METERSPHERE_ATTACHMENT_LIST_PATH='/attachment/metadata/list'
[[ -n "${METERSPHERE_ATTACHMENT_DOWNLOAD_PATH:-}" ]] || METERSPHERE_ATTACHMENT_DOWNLOAD_PATH='/attachment/download'
[[ -n "${METERSPHERE_ATTACHMENT_DELETE_PATH:-}" ]] || METERSPHERE_ATTACHMENT_DELETE_PATH='/attachment/delete/testcase'
# v2 项目文件库（可共享附件）：create 为 multipart（request=FileMetadataCreateRequest + file=@），
# exists 仅作批量 id 校验。page / name 过滤端点实测损坏，刻意不暴露 list/get。
[[ -n "${METERSPHERE_FILE_METADATA_CREATE_PATH:-}" ]] || METERSPHERE_FILE_METADATA_CREATE_PATH='/file/metadata/create'
[[ -n "${METERSPHERE_FILE_METADATA_EXISTS_PATH:-}" ]] || METERSPHERE_FILE_METADATA_EXISTS_PATH='/file/metadata/exists'
# 库文件 → 用例关联：POST {belongId, belongType:"testcase", metadataRefIds:[…]}。
[[ -n "${METERSPHERE_ATTACHMENT_RELATE_PATH:-}" ]] || METERSPHERE_ATTACHMENT_RELATE_PATH='/attachment/testcase/metadata/relate'
# 库文件 → 用例取消关联（relate 的配对操作）：POST 同形状 {belongId, belongType, metadataRefIds}。
[[ -n "${METERSPHERE_ATTACHMENT_UNRELATE_PATH:-}" ]] || METERSPHERE_ATTACHMENT_UNRELATE_PATH='/attachment/testcase/metadata/unrelated'
# 功能用例 excel/xmind 导入（.xmind 同端点，服务端按扩展名分发到 XmindCaseParser，v2.10 TestCaseService.java:1127）。
[[ -n "${METERSPHERE_CASE_IMPORT_PATH:-}" ]] || METERSPHERE_CASE_IMPORT_PATH='/test/case/import'
# 功能用例导入模板下载（二进制 xlsx；importType 仅 Create|Update，v2.10 ExcelImportType 枚举）。
[[ -n "${METERSPHERE_CASE_TEMPLATE_PATH:-}" ]] || METERSPHERE_CASE_TEMPLATE_PATH='/test/case/export/template/{projectId}/{importType}'
# v2 项目文件库列表/详情（v2.10 FileMetadataController：list=分页 POST、info=GET 返回文件字节流）。
[[ -n "${METERSPHERE_FILE_METADATA_LIST_PATH:-}" ]] || METERSPHERE_FILE_METADATA_LIST_PATH='/file/metadata/project/{projectId}/{goPage}/{pageSize}'
[[ -n "${METERSPHERE_FILE_METADATA_INFO_PATH:-}" ]] || METERSPHERE_FILE_METADATA_INFO_PATH='/file/metadata/info/{id}'
# v2 项目文件库文件夹树（v2.10 FileModuleController；body 里的 moduleId=文件夹 id，实测）。
[[ -n "${METERSPHERE_FILE_MODULE_CREATE_PATH:-}" ]] || METERSPHERE_FILE_MODULE_CREATE_PATH='/file/module/add'
[[ -n "${METERSPHERE_FILE_MODULE_LIST_PATH:-}" ]] || METERSPHERE_FILE_MODULE_LIST_PATH='/file/module/list/{projectId}'
# 批量关联需求（需求管理为第三方平台集成，Phabricator 配置后可列出）：完整字面路径
# /test/case + /batch/relate/demand（类级 @RequestMapping("/test/case")，v2.10 TestCaseController.java:363）。
[[ -n "${METERSPHERE_RELATE_DEMAND_PATH:-}" ]] || METERSPHERE_RELATE_DEMAND_PATH='/test/case/batch/relate/demand'

die() { echo "错误: $*" >&2; exit 1; }

require_project_id() {
  # 写入安全：拒绝在未显式设置 METERSPHERE_PROJECT_ID 时写入（防止误写硬编码项目）。
  [[ -n "$METERSPHERE_PROJECT_ID" ]] || die "未设置 METERSPHERE_PROJECT_ID，拒绝写入（防止误写硬编码项目）"
}

detect_version() {
  # 返回 v2 或 v3。METERSPHERE_VERSION 环境变量可强制指定。
  if [[ -n "$METERSPHERE_VERSION" ]]; then
    echo "$METERSPHERE_VERSION"
    return 0
  fi
  need_base_url
  # v3 有 /system/version/current；v2 只有 /system/version
  local v3_status
  v3_status="$(curl -sS -o /dev/null -w '%{http_code}' --max-time 5 "${METERSPHERE_BASE_URL%/}/system/version/current" 2>/dev/null || true)"
  if [[ "$v3_status" == "200" ]]; then
    echo "v3"
  else
    echo "v2"
  fi
}

need_base_url() {
  [[ -n "$METERSPHERE_BASE_URL" ]] || die "未设置 METERSPHERE_BASE_URL"
}

need_keys() {
  [[ -n "$METERSPHERE_ACCESS_KEY" ]] || die "未设置 METERSPHERE_ACCESS_KEY"
  [[ -n "$METERSPHERE_SECRET_KEY" ]] || die "未设置 METERSPHERE_SECRET_KEY"
}

generate_signature() {
  python3 - <<'PY' "$METERSPHERE_ACCESS_KEY" "$METERSPHERE_SECRET_KEY"
import sys, uuid, time, base64
from subprocess import run, PIPE
access_key, secret_key = sys.argv[1], sys.argv[2]
plain = f"{access_key}|{uuid.uuid4()}|{int(time.time()*1000)}"
key_hex = secret_key.encode('utf-8').hex()
iv_hex = access_key.encode('utf-8').hex()
proc = run([
    'openssl', 'enc', '-aes-128-cbc', '-K', key_hex, '-iv', iv_hex,
    '-base64', '-A', '-nosalt'
], input=plain.encode('utf-8'), stdout=PIPE, stderr=PIPE, check=True)
print(proc.stdout.decode('utf-8').strip())
PY
}

build_header_args() {
  local tmp_file="$1"
  local signature
  signature="$(generate_signature)"
  {
    printf '%s\n' '-H' 'Content-Type: application/json'
    printf '%s\n' '-H' "accessKey: $METERSPHERE_ACCESS_KEY"
    printf '%s\n' '-H' "signature: $signature"
    if [[ -n "$METERSPHERE_HEADERS_JSON" ]]; then
      python3 - <<'PY' "$METERSPHERE_HEADERS_JSON"
import json,sys
headers=json.loads(sys.argv[1])
for k,v in headers.items():
    print('-H')
    print(f'{k}: {v}')
PY
    fi
  } > "$tmp_file"
}

default_list_payload() {
  local resource="${1:-}"
  local keyword="${2:-}"
  python3 - <<'PY' "$resource" "$keyword" "$METERSPHERE_PROJECT_ID" "$METERSPHERE_WORKSPACE_ID" "$METERSPHERE_PROTOCOLS_JSON"
import json,sys
resource, keyword, project_id, workspace_id, protocols_json = sys.argv[1:6]
payload = {}
if keyword:
    payload["keyword"] = keyword
if project_id:
    payload["projectId"] = project_id
if workspace_id:
    payload["workspaceId"] = workspace_id
if resource in ("api", "api-case"):
    try:
        payload["protocols"] = json.loads(protocols_json)
    except Exception:
        payload["protocols"] = ["HTTP"]
print(json.dumps(payload, ensure_ascii=False))
PY
}

normalize_json_with_defaults() {
  local resource="$1"
  local body="$2"
  python3 - <<'PY' "$resource" "$body" "$METERSPHERE_PROJECT_ID" "$METERSPHERE_WORKSPACE_ID" "$METERSPHERE_PROTOCOLS_JSON"
import json,sys
resource, body, project_id, workspace_id, protocols_json = sys.argv[1:6]
data = json.loads(body)
if isinstance(data, dict):
    if project_id and not data.get("projectId"):
        data["projectId"] = project_id
    if workspace_id and not data.get("workspaceId"):
        data["workspaceId"] = workspace_id
    if resource in ("api", "api-case") and not data.get("protocols"):
        try:
            data["protocols"] = json.loads(protocols_json)
        except Exception:
            pass
print(json.dumps(data, ensure_ascii=False))
PY
}

# api-case create 的缺省补齐：只在缺省时注入 id（uuid4）与 priority（P1）。
# 服务端依据：v2.10 ApiTestCaseService.createTest() 只做 test.setId(request.getId()) /
# test.setPriority(request.getPriority())，该类零 IDGenerator 调用 → 服务端不再兜底，
# 缺 id 落库即报 Column 'id' cannot be null（服务端 error.log 实测）。
# 刻意做成独立函数而非并入 normalize_json_with_defaults：后者还有 list 分支的调用点，
# 在那里注入会把 id/priority 泄进查询体，被服务端当过滤条件而静默筛掉结果。
inject_api_case_create_defaults() {
  local body="$1"
  python3 - "$body" <<'PY'
import json, sys, uuid
data = json.loads(sys.argv[1])
if isinstance(data, dict):
    req = data.get("request")
    if req is None or req == "" or (isinstance(req, dict) and len(req) == 0):
        print("错误: api-case create 的 request 字段缺失、为空或无效。该用例创建后将无法在 MeterSphere GUI 编辑。请改用 'ms api-case generate-create' 生成完整的 request。", file=sys.stderr)
        sys.exit(1)
    if not data.get("id"):
        data["id"] = str(uuid.uuid4())
    if not data.get("priority"):
        data["priority"] = "P1"
print(json.dumps(data, ensure_ascii=False))
PY
}

service_prefix() {
  # v2 网关 discovery locator：/{serviceId}/** 剥掉首段 serviceId 后转发到对应微服务。
  # track：功能模块/功能用例/评审系；project：功能模板；其余（含 raw）走 api。
  case "$1" in
    functional-module|functional-case|functional-case-review|case-review|case-review-detail|case-review-module|case-review-user|comment|attachment|file|file-module)
      echo "track"
      ;;
    functional-template)
      echo "project"
      ;;
    *)
      echo "api"
      ;;
  esac
}

request() {
  local method="$1" path="$2" body="${3:-}" prefix="${4:-api}"
  need_base_url
  need_keys
  local url="${METERSPHERE_BASE_URL%/}/${prefix}${path}"
  local header_file
  header_file="$(mktemp)"
  build_header_args "$header_file"
  local -a header_args=()
  while IFS= read -r line; do
    header_args+=("$line")
  done < "$header_file"
  if [[ -n "$body" ]]; then
    curl -sS -X "$method" "$url" "${header_args[@]}" -d "$body"
  else
    curl -sS -X "$method" "$url" "${header_args[@]}"
  fi
  rm -f "$header_file"
}

path_fill() {
  local template="$1" value="$2"
  template="${template/\{id\}/$value}"
  template="${template/\{organizationId\}/$value}"
  template="${template/\{projectId\}/$value}"
  template="${template/\{workspaceId\}/$value}"
  template="${template/\{goPage\}/1}"
  template="${template/\{pageSize\}/20}"
  echo "$template"
}

resource_paths() {
  case "$1" in
    organization|workspace)
      echo "$METERSPHERE_ORGANIZATION_LIST_PATH||"
      ;;
    project)
      echo "$METERSPHERE_PROJECT_LIST_PATH||"
      ;;
    functional-module)
      echo "$METERSPHERE_FUNCTIONAL_MODULE_TREE_PATH||"
      ;;
    functional-template)
      echo "$METERSPHERE_FUNCTIONAL_TEMPLATE_FIELD_PATH||"
      ;;
    api-module)
      echo "$METERSPHERE_API_MODULE_TREE_PATH||"
      ;;
    functional-case)
      echo "$METERSPHERE_FUNCTIONAL_CASE_LIST_PATH|$METERSPHERE_FUNCTIONAL_CASE_GET_PATH|$METERSPHERE_FUNCTIONAL_CASE_CREATE_PATH"
      ;;
    functional-case-review)
      echo "$METERSPHERE_FUNCTIONAL_CASE_REVIEW_LIST_PATH||"
      ;;
    case-review)
      echo "$METERSPHERE_CASE_REVIEW_LIST_PATH|$METERSPHERE_CASE_REVIEW_GET_PATH|$METERSPHERE_CASE_REVIEW_CREATE_PATH"
      ;;
    case-review-detail)
      echo "$METERSPHERE_CASE_REVIEW_DETAIL_PAGE_PATH||"
      ;;
    case-review-module)
      echo "$METERSPHERE_CASE_REVIEW_MODULE_TREE_PATH||"
      ;;
    case-review-user)
      echo "$METERSPHERE_CASE_REVIEW_USER_OPTION_PATH||"
      ;;
    api)
      echo "$METERSPHERE_API_DEFINITION_LIST_PATH|$METERSPHERE_API_DEFINITION_GET_PATH|$METERSPHERE_API_DEFINITION_CREATE_PATH|$METERSPHERE_API_DEFINITION_IMPORT_PATH"
      ;;
    api-case)
      echo "$METERSPHERE_API_CASE_LIST_PATH|$METERSPHERE_API_CASE_GET_PATH|$METERSPHERE_API_CASE_CREATE_PATH"
      ;;
    comment)
      echo "$METERSPHERE_COMMENT_LIST_PATH|$METERSPHERE_COMMENT_GET_PATH|$METERSPHERE_COMMENT_CREATE_PATH"
      ;;
    attachment)
      echo "$METERSPHERE_ATTACHMENT_LIST_PATH|$METERSPHERE_ATTACHMENT_DOWNLOAD_PATH|$METERSPHERE_ATTACHMENT_UPLOAD_PATH"
      ;;
    file-module)
      echo "$METERSPHERE_FILE_MODULE_LIST_PATH|$METERSPHERE_FILE_MODULE_CREATE_PATH"
      ;;
    file)
      echo "$METERSPHERE_FILE_METADATA_LIST_PATH|$METERSPHERE_FILE_METADATA_INFO_PATH|$METERSPHERE_FILE_METADATA_CREATE_PATH"
      ;;
    *)
      die "不支持的资源: $1"
      ;;
  esac
}

usage() {
  cat <<'EOF'
ms — MeterSphere CLI (v2 模式)

本脚本面向 MeterSphere v2 分支（自动嗅探版本，或设 METERSPHERE_VERSION=v2 强制）。
v2 使用 workspace 而非 organization；分页为路径参数 {goPage}/{pageSize}。

用法:
  ms <resource> <action> [args...]
  ms raw <METHOD> <PATH> [JSON]
  ms reviewed-summary <projectId> [keyword]
  ms case-report <projectId> <caseId>
  ms case-report-md <projectId> <caseId>

资源:
  organization (v2 中为 workspace 列表)
  project
  functional-module
  functional-template
  api-module
  functional-case
  functional-case-review
  case-review
  case-review-detail
  case-review-module
  case-review-user
  api
  api-case
  comment
  attachment
  file
  file-module

动作:
  list [关键词|JSON]
  get <id>
  create <JSON>
  create <JSON> <local-file>  (file: 创建项目文件库文件，multipart 上传)
  exists <fileId>...  (file: 批量校验文件元数据 id 是否存在)
  relate <caseId> <fileId>...  (attachment: 将库文件关联为用例附件)
  unrelated <caseId> <metadataRefId>...  (attachment: 取消库文件与用例附件的关联)
  template <projectId> [importType] [outfile]  (functional-case: 下载 excel 导入模板，importType 仅 Create|Update)
  import <projectId> <excelFile> [--import-type Create|Update] [--version-id <id>]  (functional-case: excel/xmind 导入，multipart 双 part)
  relate-demand <projectId> <demandId> <caseId>... [--demand-name <name>]  (functional-case: 批量关联需求，demandId 为 other 时 --demand-name 必填)
  batch-create <json-array-file> [--file-id <fileMetadataId>]  (functional-case: 可选把库文件关联进每条用例)
  split-create <projectId> <file> [moduleId] [--link-mode same-call|separate]  (functional-case: docx/pdf/xlsx/xmind 一键拆分写入并关联原文件)
  generate-create <projectId> [<definitionId>...]  (api-case: 定义 → 接口用例批量生成写入)
  generate-create [--tags <标签[,标签...]>] <projectId> [<definitionId>...]  (api-case: 额外写入 phabricator 标签，--tags 可重复)
  import-generate <projectId> <spec> [moduleId] (api: 导入 spec 生成定义+用例计划，不写入用例)
  import-create <projectId> <spec> [moduleId] (api: 导入 spec → 定义 → 用例，幂等去重)
  help

示例:
  ms organization list
  ms project list
  ms project list all
  ms project list <workspaceId>
  ms functional-module list <projectId>
  ms functional-template list <projectId>
  ms api-module list <projectId>
  ms functional-case list "登录"
  ms functional-case get <caseId>
  ms functional-case create '{"name":"登录用例","nodeId":"<moduleId>","projectId":"<projectId>"}'
  ms functional-case generate <projectId> <moduleId> <templateId> <requirement-file>
  ms functional-case batch-create <json-array-file>
   ms functional-case batch-create <json-array-file> --file-id <fileMetadataId>
   ms functional-case split-create <projectId> /path/to/cases.xlsx
   ms functional-case split-create <projectId> /path/to/cases.xmind <moduleId>
   ms functional-case split-create <projectId> /path/to/cases.docx - --link-mode separate
  ms functional-case generate-create <projectId> - <templateId> <requirement-file>
  ms functional-case delete <caseId>
  ms case-review list '{"projectId":"<your-project-id>"}'
  ms case-review get <review-id>
  ms case-review-user list <review-id>
  ms api list '{"keyword":"用户"}'
  ms api-case create '{"name":"获取用户详情-200","apiDefinitionId":"<definitionId>","request":{"type":"HTTPSamplerProxy","method":"GET","url":"http://example.com/api/user/1","httpSamplerArguments":[],"headers":[],"postBodyProcessor":"NONE"}}'  # 缺少 request 会被拒绝;请优先用 generate-create 自动生成
  ms api-case generate-create <projectId>
  ms api-case generate-create <projectId> <definitionId> [<definitionId>...]
  ms api-case generate-create --tags T-story-123,T-tech-456 <projectId>
  ms api-case generate-create --tags T-story-123 --tags T-tech-456 <projectId>
  ms api import-create <projectId> /path/to/openapi.json
  ms api import-generate <projectId> https://example.com/api-docs
  ms comment save <caseId> <description> [type] [belongId]
  ms comment list <caseId> [type [belongId]]
  ms comment delete <commentId>
  ms comment edit <commentId> <caseId> <description> [type] [belongId]
  ms attachment upload <caseId> <file>
  ms attachment list <caseId>
  ms attachment relate <caseId> <fileId> [<fileId>...]
  ms attachment unrelated <caseId> <metadataRefId> [<metadataRefId>...]
  ms attachment download <attachmentId> <isLocal> <outfile>
  ms attachment delete <attachmentId>
  ms functional-case template <projectId> [Create|Update] [outfile]
   ms functional-case import <projectId> <excel-or-xmind-file> --import-type Create [--fix-status <v>] [--default-maintainer <user>]
  ms functional-case relate-demand <projectId> <demandId> <caseId> [<caseId>...]
  ms file list <projectId> [goPage] [pageSize]
  ms file get <fileId> [outfile]
   ms file create '{"id":"<uuid4>","projectId":"<projectId>","storage":"MINIO","name":"a.txt"}' <local-file>
    ms file-module list <projectId>
   ms file-module create <name> [parentId]
  ms file exists <fileId> [<fileId>...]
   ms raw GET /system/version [--service <resource>]
EOF
}

cmd="${1:-}"
[[ -n "$cmd" ]] || { usage; exit 1; }
shift || true

if [[ "$cmd" == "help" || "$cmd" == "-h" || "$cmd" == "--help" ]]; then
  usage
  exit 0
fi

if [[ "$cmd" == "raw" ]]; then
  method="${1:-}"; shift || die "raw 需要 METHOD"
  path="${1:-}"; shift || die "raw 需要 PATH"
  body=""
  body_seen=0
  raw_service=""
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --service=*)
        raw_service="${1#--service=}"
        ;;
      --service)
        shift
        raw_service="${1:-}"
        [[ -n "$raw_service" ]] || die "raw --service 需要资源名"
        ;;
      *)
        if [[ "$body_seen" -eq 0 ]]; then
          body="$1"
          body_seen=1
        elif [[ -z "$raw_service" ]]; then
          raw_service="$1"
        else
          die "raw 多余参数: $1"
        fi
        ;;
    esac
    shift
  done
  # 默认仍走 api 前缀；给了资源名则经 service_prefix 解析（如 functional-template → project），
  # 用于显式命中单前缀路径（如 project-management 服务的 /project/list/related）。
  raw_prefix="api"
  [[ -z "$raw_service" ]] || raw_prefix="$(service_prefix "$raw_service")"
  request "$method" "$path" "$body" "$raw_prefix"
  exit 0
fi

if [[ "$cmd" == "doctor" ]]; then
  doctor_failed=0
  echo "MeterSphere Skill v2 自检（ms doctor）"
  for bin in python3 openssl curl; do
    if command -v "$bin" >/dev/null 2>&1; then
      echo "OK   二进制: $bin"
    else
      echo "缺失 二进制: $bin（必装）"
      doctor_failed=1
    fi
  done
  for var in METERSPHERE_BASE_URL METERSPHERE_ACCESS_KEY METERSPHERE_SECRET_KEY; do
    if [[ -n "${!var:-}" ]]; then
      echo "OK   env: $var 已设置"
    else
      echo "缺失 env: $var（必填，见 .env）"
      doctor_failed=1
    fi
  done
  version="$(python3 -c "import json;print(json.load(open('$SKILL_DIR/skill-metadata.json')).get('version','unknown'))" 2>/dev/null || echo unknown)"
  sha="$(git -C "$SKILL_DIR" rev-parse --short HEAD 2>/dev/null || true)"
  if [[ -n "$sha" ]]; then
    echo "版本: $version (git $sha)"
  else
    echo "版本: $version（非 git 树，跳过短 SHA）"
  fi
  if [[ -n "${METERSPHERE_BASE_URL:-}" ]]; then
    code="$(curl -sS -o /dev/null -w '%{http_code}' --max-time 5 "${METERSPHERE_BASE_URL%/}/system/version/current" 2>/dev/null || true)"
    [[ -n "$code" ]] || code="000"
    echo "连通性: HTTP $code（仅探测可达性，非鉴权校验）"
  fi
  if [[ "$doctor_failed" -ne 0 ]]; then
    die "doctor 检查未通过：请补齐上方缺失项"
  fi
  echo "doctor 完成: 全部通过"
  exit 0
fi

if [[ "$cmd" == "reviewed-summary" ]]; then
  project_id="${1:-${METERSPHERE_PROJECT_ID:-}}"
  keyword="${2:-}"
  [[ -n "$project_id" ]] || die "reviewed-summary 需要 projectId"
  python3 "$SCRIPT_DIR/ms_review_summary.py" "$project_id" "$keyword"
  exit 0
fi

if [[ "$cmd" == "case-report" ]]; then
  project_id="${1:-${METERSPHERE_PROJECT_ID:-}}"
  case_id="${2:-}"
  [[ -n "$project_id" ]] || die "case-report 需要 projectId"
  [[ -n "$case_id" ]] || die "case-report 需要 caseId"
  python3 "$SCRIPT_DIR/ms_case_report.py" "$project_id" "$case_id"
  exit 0
fi

if [[ "$cmd" == "case-report-md" ]]; then
  project_id="${1:-${METERSPHERE_PROJECT_ID:-}}"
  case_id="${2:-}"
  [[ -n "$project_id" ]] || die "case-report-md 需要 projectId"
  [[ -n "$case_id" ]] || die "case-report-md 需要 caseId"
  python3 "$SCRIPT_DIR/ms_case_report_md.py" "$project_id" "$case_id"
  exit 0
fi

resource="$cmd"
action="${1:-}"
[[ -n "$action" ]] || die "缺少 action"
shift || true
IFS='|' read -r list_path get_path create_path <<< "$(resource_paths "$resource")"
service_prefix="$(service_prefix "$resource")"

# 批量校验文件元数据 id 是否存在于项目文件库（POST /file/metadata/exists，载荷为 id 数组）。
# 服务端仅回显存在的 id。返回 0 = 全部存在；返回 1 = 有缺失。响应存入 FILE_EXISTS_RESP。
file_metadata_exists() {
  local -a ids=("$@")
  local body
  body="$(python3 - "${ids[@]}" <<'PY'
import json, sys
print(json.dumps(list(sys.argv[1:]), ensure_ascii=False))
PY
)"
  local resp
  resp="$(request POST "$METERSPHERE_FILE_METADATA_EXISTS_PATH" "$body" "$service_prefix")"
  FILE_EXISTS_RESP="$resp"
  python3 - "$resp" "${ids[@]}" <<'PY'
import json, sys
raw, requested = sys.argv[1], sys.argv[2:]
try:
    resp = json.loads(raw) if raw else []
except Exception:
    resp = []
present = set()
def add(x):
    if isinstance(x, str):
        present.add(x)
    elif isinstance(x, dict) and x.get('id'):
        present.add(x['id'])
if isinstance(resp, list):
    for x in resp:
        add(x)
elif isinstance(resp, dict):
    data = resp.get('data')
    if isinstance(data, list):
        for x in data:
            add(x)
missing = [i for i in requested if i not in present]
sys.exit(0 if not missing else 1)
PY
}

# 批量创建功能用例：读取 JSON 数组文件，逐元素 POST /track/test/case/add（multipart）。
# nodePath 占位符（"/"+nodeId，来自 ms_generate.py）会按模块树解析为真实路径；
# 解析失败则透传，由服务端校验。
batch_create_functional_cases() {
  local json_file="$1"
  local skip_existing="${2:-0}"
  shift
  if [[ $# -gt 0 ]]; then
    shift
  fi
  local -a attach_ids=("$@")
  local project_id="$METERSPHERE_PROJECT_ID"
  local tmp_dir
  tmp_dir="$(mktemp -d)"
  trap 'rm -rf "$tmp_dir"' EXIT
  python3 - "$json_file" "$tmp_dir/elements.jsonl" "${attach_ids[@]}" <<'PY'
import json, sys
path, out = sys.argv[1], sys.argv[2]
attach_ids = [str(x) for x in sys.argv[3:] if x]
try:
    data = json.load(open(path, encoding='utf-8'))
except Exception as e:
    print(f'错误: 无法解析 JSON 数组文件: {e}', file=sys.stderr)
    sys.exit(1)
if not isinstance(data, list):
    print('错误: batch-create 需要 JSON 数组文件', file=sys.stderr)
    sys.exit(1)
with open(out, 'w', encoding='utf-8') as f:
    for i, el in enumerate(data):
        if not isinstance(el, dict):
            print(f'错误: 第 {i+1} 个元素不是 JSON 对象', file=sys.stderr)
            sys.exit(1)
        if attach_ids:
            existing = el.get('relateFileMetaIds')
            if isinstance(existing, list):
                ids = [str(x) for x in existing if x]
            elif existing:
                ids = [str(existing)]
            else:
                ids = []
            for aid in attach_ids:
                if aid not in ids:
                    ids.append(aid)
            el['relateFileMetaIds'] = ids
        f.write(json.dumps(el, ensure_ascii=False) + '\n')
PY
  local skipped=0
  if [[ "$skip_existing" == "1" ]]; then
    local existing_names
    existing_names="$(fetch_functional_case_names "$project_id")"
    if [[ "$existing_names" == ERR:* ]]; then
      die "batch-create --skip-existing 失败: 无法拉取已存在用例名称 (${existing_names#ERR:})"
    fi
    local names_file="$tmp_dir/existing_names.txt"
    printf '%s' "$existing_names" > "$names_file"
    skipped="$(python3 - "$tmp_dir/elements.jsonl" "$names_file" <<'PY'
import json, sys
elements_path, names_path = sys.argv[1], sys.argv[2]
names = set()
with open(names_path, encoding='utf-8') as f:
    for line in f:
        nm = line.rstrip('\n')
        if nm:
            names.add(nm)
kept, skipped = [], 0
with open(elements_path, encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        el = json.loads(line)
        nm = el.get('name')
        if isinstance(nm, str) and nm in names:
            skipped += 1
            continue
        kept.append(el)
with open(elements_path, 'w', encoding='utf-8') as f:
    for el in kept:
        f.write(json.dumps(el, ensure_ascii=False) + '\n')
print(skipped)
PY
)"
  fi
  local need_resolve
    need_resolve="$(python3 - "$tmp_dir/elements.jsonl" <<'PY'
import json, sys
for line in open(sys.argv[1], encoding='utf-8'):
    el = json.loads(line)
    node_id = el.get('nodeId') or ''
    node_path = el.get('nodePath') or ''
    if node_id in ('default-module', '') or node_path == '' or node_path == '/' + node_id:
        print('1')
        sys.exit(0)
print('0')
PY
)"
  local module_tree=""
  if [[ "$need_resolve" == "1" ]]; then
    module_tree="$(request GET "$(path_fill "$METERSPHERE_FUNCTIONAL_MODULE_TREE_PATH" "$project_id")" "" "track")"
  fi
  local count=0 created=0
  while IFS= read -r element; do
    count=$((count + 1))
    if [[ "$need_resolve" == "1" ]]; then
      element="$(python3 - "$element" "$module_tree" <<'PY'
import json, sys
el = json.loads(sys.argv[1])
node_id = el.get('nodeId') or ''
node_path = el.get('nodePath') or ''
sentinel = node_id in ('default-module', '') or node_path == '' or node_path == '/' + node_id
if sentinel and sys.argv[2]:
    try:
        resp = json.loads(sys.argv[2])
        tree = resp.get('data') if isinstance(resp, dict) else resp
        if not isinstance(tree, list):
            tree = [tree]
        nodes = {}
        def walk(items):
            for n in items or []:
                if not isinstance(n, dict):
                    continue
                nodes[n.get('id')] = n
                walk(n.get('children'))
        walk(tree)
        # name-match for unplanned
        if node_id in ('default-module', ''):
            for n in nodes.values():
                if n.get('name') == '未规划用例' and n.get('parentId') is None and n.get('level') == 1:
                    el['nodeId'] = n.get('id')
                    el['nodePath'] = '/' + n.get('name')
                    print(json.dumps(el, ensure_ascii=False))
                    sys.exit(0)
        parts = []
        cur = nodes.get(node_id)
        seen = set()
        while cur and cur.get('id') not in seen:
            seen.add(cur.get('id'))
            name = cur.get('name')
            if name:
                parts.insert(0, name)
            pid = cur.get('parentId')
            cur = nodes.get(pid) if pid else None
        if parts:
            el['nodePath'] = '/' + '/'.join(parts)
    except Exception:
        pass
print(json.dumps(el, ensure_ascii=False))
PY
)"
    fi
    # post-resolution hard-fail
    element="$(python3 - "$element" <<'PY'
import json, sys
el = json.loads(sys.argv[1])
node_id = el.get('nodeId') or ''
node_path = el.get('nodePath') or ''
sentinel = node_id in ('default-module', '')
if node_path == '' or node_path.startswith('/default-module') or sentinel or node_path == '/' + node_id:
    print('ERR')
    sys.exit(0)
print(json.dumps(el, ensure_ascii=False))
PY
)"
    if [[ "$element" == "ERR" ]]; then
      die "batch-create 第 $count 个用例解析失败: nodePath 无效或未能解析模块"
    fi
    local tmp_json
    tmp_json="$(mktemp)"
    printf '%s' "$element" > "$tmp_json"
    need_base_url
    need_keys
    local signature
    signature="$(generate_signature)"
    local resp
    resp="$(curl -sS -X POST \
      -H "accessKey: $METERSPHERE_ACCESS_KEY" \
      -H "signature: $signature" \
      -F "request=@${tmp_json};type=application/json" \
      "${METERSPHERE_BASE_URL%/}/track${METERSPHERE_FUNCTIONAL_CASE_CREATE_PATH}")"
    rm -f "$tmp_json"
    printf '%s\n' "$resp"
    [[ "$resp" != *'"success":false'* ]] || die "batch-create 第 $count 个用例创建失败: $resp"
    local case_id
    case_id="$(printf '%s' "$resp" | python3 -c 'import json,sys
try:
    d=json.load(sys.stdin)
except Exception:
    sys.exit(0)
data=d.get("data")
if isinstance(data, str) and data:
    print(data)
elif isinstance(data, dict) and data.get("id"):
    print(data["id"])
' 2>/dev/null || true)"
    if [[ -n "$case_id" ]]; then
      echo "已创建用例: $case_id"
      created=$((created + 1))
    fi
  done < "$tmp_dir/elements.jsonl"
  if [[ "$skip_existing" == "1" ]]; then
    echo "batch-create 完成: 共 $((count + skipped)) 个元素，成功创建 $created 个用例，跳过 $skipped 个已存在"
  else
    echo "batch-create 完成: 共 $count 个元素，成功创建 $created 个用例"
  fi
  rm -rf "$tmp_dir"
  trap - EXIT
}

# 一键拆分写入：测试用例文件（docx/pdf/xlsx/xmind）→ ms_split_cases.py 拆分草稿 →
# moduleId 解析注入 nodeId → name 查重 → 项目文件上传原文件一次（复用 file create）→
# batch-create --file-id 写入并同调用关联（复用既有实现）→ 计数清单。
# 中途失败即停：已完成步骤打印到 stdout，die 消息携带失败步骤（可重跑，幂等）。
# --link-mode separate 降级：对每个新 caseId 调既有 attachment relate（同一 fileId）。
split_create_functional_cases() {
  local project_id="$1" source_file="$2" module_id="$3" link_mode="${4:-same-call}"
  [[ -f "$source_file" ]] || die "split-create 文件不存在: $source_file"
  [[ "$link_mode" == "same-call" || "$link_mode" == "separate" ]] || die "split-create link-mode 仅支持 same-call|separate"
  require_project_id
  local tmp_dir
  tmp_dir="$(mktemp -d)"
  trap "rm -rf '$tmp_dir'" EXIT

  echo "步骤 ①/⑤ 拆分 $source_file"
  python3 "$SCRIPT_DIR/ms_split_cases.py" "$source_file" --project-id "$project_id" -o "$tmp_dir/drafts.json" || {
    die "split-create 步骤 ① 拆分失败（已完成步骤：无）"
  }
  local total
  total="$(python3 -c 'import json,sys; print(len(json.load(open(sys.argv[1], encoding="utf-8"))))' "$tmp_dir/drafts.json")"
  echo "步骤 ①/⑤ 完成: 拆分 $total 条草稿"

  echo "步骤 ②/⑤ 解析 moduleId 并注入 nodeId"
  cat > "$tmp_dir/inject_node.py" <<'PY'
import json, sys
drafts_path, module_id, tree_raw = sys.argv[1], sys.argv[2], sys.argv[3]
with open(drafts_path, encoding="utf-8") as fh:
    drafts = json.load(fh)
if module_id not in ("", "-"):
    for d in drafts:
        d["nodeId"] = module_id
else:
    try:
        resp = json.loads(tree_raw)
    except json.JSONDecodeError:
        resp = None
    tree = resp.get("data") if isinstance(resp, dict) else resp
    if not isinstance(tree, list):
        tree = [tree]
    paths = {}
    def walk(items, prefix):
        for n in items or []:
            if not isinstance(n, dict):
                continue
            name = str(n.get("name") or "").strip()
            if name:
                full = prefix + "/" + name
                paths.setdefault(full, n.get("id"))
                paths.setdefault(full.lstrip("/"), n.get("id"))
                walk(n.get("children"), full)
            else:
                walk(n.get("children"), prefix)
    walk(tree, "")
    unresolved = []
    for d in drafts:
        np = str(d.get("nodePath") or "").strip().lstrip("/")
        candidates = []
        if np in paths:
            candidates.append(paths[np])
        else:
            for p, nid in paths.items():
                if p.endswith("/" + np) and nid:
                    candidates.append(nid)
        candidates = [c for c in dict.fromkeys(candidates) if c]
        if len(candidates) == 1:
            d["nodeId"] = candidates[0]
        else:
            unresolved.append(np)
    if unresolved:
        print("ERR:" + ", ".join(sorted(set(unresolved))))
        sys.exit(0)
with open(drafts_path, "w", encoding="utf-8") as fh:
    json.dump(drafts, fh, ensure_ascii=False)
PY
  local module_tree="" inject_out
  if [[ -z "$module_id" || "$module_id" == "-" ]]; then
    module_tree="$(request GET "$(path_fill "$METERSPHERE_FUNCTIONAL_MODULE_TREE_PATH" "$project_id")" "" "track")" || {
      die "split-create 步骤 ② 模块树查询失败（已完成步骤：① 拆分 $total 条草稿）"
    }
  fi
  inject_out="$(python3 "$tmp_dir/inject_node.py" "$tmp_dir/drafts.json" "$module_id" "$module_tree")" || {
    die "split-create 步骤 ② moduleId 解析失败（已完成步骤：① 拆分 $total 条草稿）"
  }
  if [[ "$inject_out" == ERR:* ]]; then
    die "split-create 步骤 ② 以下 nodePath 在模块树中 0 或多个匹配，不自动选择: ${inject_out#ERR:}（已完成步骤：① 拆分 $total 条草稿）"
  fi
  echo "步骤 ②/⑤ 完成: moduleId 解析注入"

  echo "步骤 ③/⑤ 按 name 查重"
  cat > "$tmp_dir/dedup_filter.py" <<'PY'
import json, sys, urllib.error, urllib.request
drafts_path, project_id, base_url, access_key, signature, list_path = sys.argv[1:7]
with open(drafts_path, encoding="utf-8") as fh:
    drafts = json.load(fh)
names, go_page, page_size = [], 1, 100
while True:
    url = "%s/track%s" % (base_url, list_path.replace("{goPage}", str(go_page)).replace("{pageSize}", str(page_size)))
    body = json.dumps({"projectId": project_id}, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("accessKey", access_key)
    req.add_header("signature", signature)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            doc = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print("ERR:HTTP %d %s" % (e.code, e.reason)); sys.exit(0)
    except urllib.error.URLError as e:
        print("ERR:%s" % e.reason); sys.exit(0)
    data = (doc or {}).get("data")
    batch, page_count = [], None
    if isinstance(data, list):
        batch, page_count = data, None
    elif isinstance(data, dict):
        batch = data.get("listObject") or []
        page_count = data.get("pageCount")
    else:
        print("ERR:响应 data 结构无法识别"); sys.exit(0)
    for it in batch:
        nm = it.get("name") if isinstance(it, dict) else None
        if nm:
            names.append(str(nm))
    if page_count is None:
        if len(batch) < page_size:
            break
    elif go_page >= int(page_count or 1):
        break
    go_page += 1
existing = set(names)
kept, skipped = [], []
for d in drafts:
    name = str(d.get("name") or "").strip()
    if name in existing:
        skipped.append(name)
    else:
        kept.append(d)
with open(drafts_path, "w", encoding="utf-8") as fh:
    json.dump(kept, fh, ensure_ascii=False)
print(json.dumps({"kept": len(kept), "skipped": len(skipped)}, ensure_ascii=False))
PY
  need_base_url
  need_keys
  local signature dedup_out
  signature="$(generate_signature)"
  dedup_out="$(python3 "$tmp_dir/dedup_filter.py" "$tmp_dir/drafts.json" "$project_id" "${METERSPHERE_BASE_URL%/}" "$METERSPHERE_ACCESS_KEY" "$signature" "$METERSPHERE_FUNCTIONAL_CASE_LIST_PATH")" || {
    die "split-create 步骤 ③ 查重查询失败: ${dedup_out#ERR:}（已完成步骤：① 拆分 $total 条草稿、② moduleId 注入）"
  }
  if [[ "$dedup_out" == ERR:* ]]; then
    die "split-create 步骤 ③ 查重查询失败: ${dedup_out#ERR:}（已完成步骤：① 拆分 $total 条草稿、② moduleId 注入）"
  fi
  local kept_count skipped_count
  kept_count="$(printf '%s' "$dedup_out" | python3 -c 'import json,sys; print(json.load(sys.stdin)["kept"])')"
  skipped_count="$(printf '%s' "$dedup_out" | python3 -c 'import json,sys; print(json.load(sys.stdin)["skipped"])')"
  echo "步骤 ③/⑤ 完成: 去重跳过 $skipped_count 条，待写入 $kept_count 条"

  if [[ "$kept_count" -eq 0 ]]; then
    echo "split-create 完成: 拆分 $total 条 / 去重跳过 $skipped_count 条 / 写入 0 条（全部已存在，幂等跳过）"
    rm -rf "$tmp_dir"
    trap - EXIT
    return 0
  fi

  echo "步骤 ④/⑤ 上传原文件到项目文件库"
  local file_name file_body upload_out file_id
  file_name="$(basename "$source_file")"
  file_body="{\"id\":\"$(python3 -c 'import uuid; print(uuid.uuid4())')\",\"projectId\":\"$project_id\",\"storage\":\"MINIO\",\"name\":\"$file_name\"}"
  upload_out="$(bash "$MS_SH_SELF" file create "$file_body" "$source_file")" || {
    printf '%s\n' "$upload_out" >&2
    die "split-create 步骤 ④ 项目文件上传失败（已完成步骤：① 拆分 $total 条草稿、② moduleId 注入、③ 查重跳过 $skipped_count 条）"
  }
  file_id="$(printf '%s' "$upload_out" | python3 -c 'import json,sys
try:
    d = json.load(sys.stdin)
except Exception:
    sys.exit(0)
if isinstance(d, dict):
    d = d.get("data")
if isinstance(d, list) and d and isinstance(d[0], dict) and d[0].get("id"):
    print(d[0]["id"])
' 2>/dev/null || true)"
  [[ -n "$file_id" ]] || die "split-create 步骤 ④ 上传响应未包含文件 id（已完成步骤：① 拆分 $total 条草稿、② moduleId 注入、③ 查重跳过 $skipped_count 条）"
  echo "步骤 ④/⑤ 完成: fileId=$file_id"

  echo "步骤 ⑤/⑤ batch-create 写入并关联原文件"
  local batch_out created_count=0
  batch_out="$(bash "$MS_SH_SELF" functional-case batch-create "$tmp_dir/drafts.json" --file-id "$file_id")" || {
    printf '%s\n' "$batch_out" >&2
    die "split-create 步骤 ⑤ batch-create 失败（已完成步骤：① 拆分 $total 条草稿、② moduleId 注入、③ 查重跳过 $skipped_count 条、④ 上传 fileId=$file_id）"
  }
  printf '%s\n' "$batch_out"
  local case_ids
  case_ids="$(printf '%s\n' "$batch_out" | python3 -c 'import sys
ids = [line[len("已创建用例: "):].strip() for line in sys.stdin if line.startswith("已创建用例: ")]
print("\n".join(ids))
' 2>/dev/null || true)"
  if [[ -n "$case_ids" ]]; then
    created_count="$(printf '%s\n' "$case_ids" | wc -l | tr -d ' ')"
  fi

  if [[ "$link_mode" == "separate" ]]; then
    echo "separate 模式: 逐条关联附件（attachment relate）"
    local related=0
    for cid in $case_ids; do
      bash "$MS_SH_SELF" attachment relate "$cid" "$file_id" || {
        die "split-create separate 关联失败: caseId=$cid（已完成步骤：① 拆分 $total、② moduleId 注入、③ 查重跳过 $skipped_count、④ 上传 fileId=$file_id、⑤ 写入 $created_count 条）"
      }
      related=$((related + 1))
    done
    echo "separate 模式完成: 关联 $related 条用例附件"
  fi

  echo "split-create 完成: 拆分 $total 条 / 去重跳过 $skipped_count 条 / 写入 $created_count 条 / fileId=$file_id"
  rm -rf "$tmp_dir"
  trap - EXIT
}

# 批量生成并创建接口用例：读取接口定义详情 → ms_generate_case.py 生成变体 →
# 逐条 multipart POST /api/testcase/create。
# 与 batch_create_functional_cases 不同：单条失败继续处理，仅当 0 条创建成功时非零退出。
# 关键（T1 实测 wire proof）：create 载荷的 request 字段必须是嵌套对象——
# 服务端对 request-as-JSON-string 返回 HTTP 400（@RequestPart("request") 绑定拒绝）。
# 因此生成器输出的紧凑 JSON 字符串 request 在此 json.loads 回对象后再写入载荷文件。
generate_create_api_cases() {
  local project_id="$1"
  shift || true
  local -a def_ids=("$@")

  need_base_url
  need_keys

  local tmp_dir
  tmp_dir="$(mktemp -d)"
  trap 'rm -rf "$tmp_dir"' EXIT

  # 1) 无显式定义 id → 分页列出项目全部 HTTP 定义
  #    实测响应（POST /api/api/definition/list/{goPage}/{pageSize}）：
  #    data.listObject（数组）/ data.itemCount（总数）/ data.pageCount（总页数）。
  #    分页检测：有 pageCount 时按 page >= pageCount 停止；否则 listObject 长度 < pageSize 即末页。
  if [[ ${#def_ids[@]} -eq 0 ]]; then
    local page=1 page_size=500
    local list_path="${METERSPHERE_API_DEFINITION_LIST_PATH/\{goPage\}/$page}"
    list_path="${list_path/\{pageSize\}/$page_size}"
    local body
    body="$(python3 - "$project_id" "$METERSPHERE_PROTOCOLS_JSON" <<'PY'
import json, sys
project_id, protocols_json = sys.argv[1], sys.argv[2]
try:
    protocols = json.loads(protocols_json)
except Exception:
    protocols = ["HTTP"]
print(json.dumps({"projectId": project_id, "protocols": protocols}, ensure_ascii=False))
PY
)"
    while :; do
      local resp
      resp="$(request POST "$list_path" "$body" "api")"
      local ids
      ids="$(printf '%s' "$resp" | python3 -c '
import json, sys
try:
    d = json.load(sys.stdin)
except Exception:
    sys.exit(1)
data = d.get("data") or {}
items = data.get("listObject") or []
for it in items:
    if isinstance(it, dict) and it.get("id"):
        print(it["id"])
')" || die "定义列表解析失败: $resp"
      while IFS= read -r id; do
        [[ -n "$id" ]] && def_ids+=("$id")
      done <<< "$ids"
      local page_count item_count got
      page_count="$(printf '%s' "$resp" | python3 -c '
import json, sys
try:
    d = json.load(sys.stdin)
except Exception:
    sys.exit(0)
data = d.get("data") or {}
pc = data.get("pageCount")
print(pc if isinstance(pc, int) else "")
')"
      item_count="$(printf '%s' "$resp" | python3 -c '
import json, sys
try:
    d = json.load(sys.stdin)
except Exception:
    sys.exit(0)
data = d.get("data") or {}
ic = data.get("itemCount")
print(ic if isinstance(ic, int) else "")
')"
      got="$(printf '%s' "$ids" | grep -c . || true)"
      if [[ -n "$page_count" ]] && (( page >= page_count )); then
        break
      fi
      if [[ -z "$page_count" ]] && (( got < page_size )); then
        break
      fi
      page=$((page + 1))
      list_path="${METERSPHERE_API_DEFINITION_LIST_PATH/\{goPage\}/$page}"
      list_path="${list_path/\{pageSize\}/$page_size}"
    done
    echo "共发现 ${#def_ids[@]} 个接口定义（项目 $project_id）"
  fi

  local total=0 created=0
  local def_id
  for def_id in "${def_ids[@]}"; do
    local detail_file="$tmp_dir/detail.json"
    local resp
    resp="$(request GET "$(path_fill "$METERSPHERE_API_DEFINITION_GET_PATH" "$def_id")" "" "api")"
    printf '%s' "$resp" > "$detail_file"
    local variants_file="$tmp_dir/variants.json"
    if ! python3 "$SCRIPT_DIR/ms_generate_case.py" "$detail_file" > "$variants_file" 2> "$tmp_dir/gen.err"; then
      echo "定义 $def_id 生成用例失败: $(cat "$tmp_dir/gen.err")"
      continue
    fi
    # 变体 request（紧凑 JSON 字符串）→ 嵌套对象，逐行输出完整 create 载荷
    # 服务端实测（error.log）：不传 id 报 Column 'id' cannot be null——每条用例必须显式携带 uuid4 id。
    # 第三个参数是 --tags 归一化后的 JSON 编码字符串；v2.10 的 tags 是 String
    # （if (StringUtils.equals("[]", request.getTags()))），故必须是编码后的字符串而非裸数组；
    # 为空则整个省略 tags 键（连 "[]" 都不发）。
    local payloads_file="$tmp_dir/payloads.jsonl"
    if ! python3 - "$variants_file" "$payloads_file" "${API_CASE_TAGS_JSON:-}" <<'PY'
import json, sys, uuid
variants = json.load(open(sys.argv[1], encoding='utf-8'))
tags_json = sys.argv[3]
if not isinstance(variants, list):
    print('错误: 生成器输出不是 JSON 数组', file=sys.stderr)
    sys.exit(1)
with open(sys.argv[2], 'w', encoding='utf-8') as f:
    for v in variants:
        if not isinstance(v, dict):
            print('错误: 变体不是 JSON 对象', file=sys.stderr)
            sys.exit(1)
        req = v.get('request')
        if isinstance(req, str):
            try:
                v['request'] = json.loads(req)
            except ValueError as exc:
                print(f'错误: 变体 request 不是合法 JSON: {exc}', file=sys.stderr)
                sys.exit(1)
        if not v.get('id'):
            v['id'] = str(uuid.uuid4())
        if not v.get('priority'):
            v['priority'] = 'P1'
        if tags_json:
            v['tags'] = tags_json
        f.write(json.dumps(v, ensure_ascii=False) + '\n')
PY
    then
      echo "定义 $def_id 载荷转换失败: $(cat "$tmp_dir/gen.err" 2>/dev/null || true)"
      continue
    fi
    # 逐条 multipart 创建：复用 generate_signature，绝不手写签名
    local line
    while IFS= read -r line; do
      total=$((total + 1))
      local tmp_json="$tmp_dir/payload.json"
      printf '%s' "$line" > "$tmp_json"
      local signature
      signature="$(generate_signature)"
      local cresp
      cresp="$(curl -sS -X POST \
        -H "accessKey: $METERSPHERE_ACCESS_KEY" \
        -H "signature: $signature" \
        -F "request=@${tmp_json};type=application/json" \
        "${METERSPHERE_BASE_URL%/}/api${METERSPHERE_API_CASE_CREATE_PATH}")"
      local case_id case_name
      case_name="$(printf '%s' "$line" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("name") or "")' 2>/dev/null || true)"
      case_id="$(printf '%s' "$cresp" | python3 -c 'import json,sys
try:
    d=json.load(sys.stdin)
except Exception:
    sys.exit(0)
data=d.get("data")
if isinstance(data, str) and data:
    print(data)
elif isinstance(data, dict) and data.get("id"):
    print(data["id"])
' 2>/dev/null || true)"
      if [[ -n "$case_id" ]]; then
        echo "已创建用例: $case_id ($case_name)"
        created=$((created + 1))
      else
        echo "用例创建失败: $case_name — $cresp"
      fi
    done < "$payloads_file"
  done

  echo "generate-create 完成: 共 $total 个用例，成功创建 $created 个"
  rm -rf "$tmp_dir"
  trap - EXIT
  if (( created == 0 )); then
    return 1
  fi
  return 0
}

# ===== import 相关（M2: spec → 定义 → 用例，含去重）=====

# 导入 spec 文件到定义；回显原始 import 响应 JSON（definitions 数组在 data.data）
# 参数: project_id spec_path module_id(可空)
import_definitions() {
  local project_id="$1" spec_path="$2" module_id="${3:-}"
  need_base_url
  need_keys
  require_project_id
  local import_body tmp_json signature resp
  # 构建 ApiTestImportRequest（moduleId 为空时省略键）
  import_body="$(python3 - "$project_id" "$module_id" <<'PY'
import json, sys
project_id, module_id = sys.argv[1], sys.argv[2]
body = {"projectId": project_id, "platform": "Swagger2", "modeId": "fullCoverage", "protocol": "HTTP", "origin": "skill"}
if module_id:
    body["moduleId"] = module_id
print(json.dumps(body, ensure_ascii=False))
PY
)"
  tmp_json="$(mktemp)"
  printf '%s' "$import_body" > "$tmp_json"
  signature="$(generate_signature)"
  resp="$(curl -sS -X POST \
    -H "accessKey: ${METERSPHERE_ACCESS_KEY}" \
    -H "signature: ${signature}" \
    -F "file=@${spec_path};type=application/json" \
    -F "request=@${tmp_json};type=application/json" \
    "${METERSPHERE_BASE_URL%/}/api${METERSPHERE_API_DEFINITION_IMPORT_PATH}")"
  rm -f "$tmp_json"
  echo "$resp"
}

# definition_ids_by_name: 分页拉取项目持久化定义列表，输出 "id|name|method" 行
# 参数: project_id
# 背景: fullCoverage 重复导入按 path 去重不落新行，但导入响应 data.data[] 返回
#       解析阶段新生成、不可查询的 id（GET → data:null）。须按 name 从持久化
#       列表解析真实 id（详见 references/ms-api.md「接口定义导入幂等语义」）。
definition_ids_by_name () {
  local project_id="$1"
  local page=1 page_size=500
  local list_path="${METERSPHERE_API_DEFINITION_LIST_PATH/\{goPage\}/$page}"
  list_path="${list_path/\{pageSize\}/$page_size}"
  local body
  body="$(python3 - "$project_id" "$METERSPHERE_PROTOCOLS_JSON" <<'PY'
import json, sys
project_id, protocols_json = sys.argv[1], sys.argv[2]
try:
    protocols = json.loads(protocols_json)
except Exception:
    protocols = ["HTTP"]
print(json.dumps({"projectId": project_id, "protocols": protocols}, ensure_ascii=False))
PY
)"
  while :; do
    local resp
    resp="$(request POST "$list_path" "$body" "api")" || return 1
    printf '%s' "$resp" | python3 -c '
import json, sys
try:
    d = json.load(sys.stdin)
except Exception:
    sys.exit(1)
data = d.get("data") or {}
items = data.get("listObject") or []
for it in items:
    if isinstance(it, dict) and it.get("id"):
        print("%s|%s|%s" % (it["id"], it.get("name") or "", it.get("method") or ""))
' || return 1
    local page_count got
    page_count="$(printf '%s' "$resp" | python3 -c '
import json, sys
try:
    d = json.load(sys.stdin)
except Exception:
    sys.exit(0)
data = d.get("data") or {}
pc = data.get("pageCount")
print(pc if isinstance(pc, int) else "")
')"
    got="$(printf '%s' "$resp" | python3 -c '
import json, sys
try:
    d = json.load(sys.stdin)
except Exception:
    sys.exit(0)
data = d.get("data") or {}
print(len(data.get("listObject") or []))
')"
    if [[ -n "$page_count" ]] && (( page >= page_count )); then
      break
    fi
    # 无 pageCount 时：本页行数 < page_size 即末页（与 generate_create_api_cases 一致）
    if [[ -z "$page_count" ]] && (( got < page_size )); then
      break
    fi
    page=$((page + 1))
    list_path="${METERSPHERE_API_DEFINITION_LIST_PATH/\{goPage\}/$page}"
    list_path="${list_path/\{pageSize\}/$page_size}"
  done
  return 0
}

# import-generate: 只导入定义 + 生成用例计划（不写入用例）
# 参数: project_id spec_source module_id(可空)
import_generate () {
  local project_id="$1" spec_source="$2" module_id="${3:-}"
  local resolved name spec_path resp defs_json
  resolved="$(python3 "$SCRIPT_DIR/ms_import_helper.py" resolve "$spec_source")"
  spec_path="${resolved%%|*}"
  name="${resolved##*|}"
  echo "已解析 spec: $name" >&2
  resp="$(import_definitions "$project_id" "$spec_path" "$module_id")"
  # 解析 data.data -> [{id,name}]
  defs_json="$(printf '%s' "$resp" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(json.dumps((d.get("data") or {}).get("data", []), ensure_ascii=False))')"
  local tmp_dir def_lines def_id def_name def_method resolved_def_id name_map detail_file variants_file variants
  tmp_dir="$(mktemp -d)"
  trap 'rm -rf "$tmp_dir"' EXIT
  def_lines="$(printf '%s' "$defs_json" | python3 -c 'import json,sys; print("\n".join("%s|%s|%s" % (x.get("id",""), x.get("name") or "", x.get("method") or "") for x in json.load(sys.stdin)))')"
  echo '{"definitions":' > "$tmp_dir/out.json"
  printf '%s' "$defs_json" >> "$tmp_dir/out.json"
  echo ',"cases_plan":[' >> "$tmp_dir/out.json"
  # 拉取持久化定义列表（一次/运行，dry-run 容错）：重复导入时响应 id 可能未持久化
  name_map="$(definition_ids_by_name "$project_id")" || true
  local first=1
  while IFS= read -r def_line; do
    [[ -n "$def_line" ]] || continue
    def_id="${def_line%%|*}"
    local rest="${def_line#*|}"
    def_name="${rest%|*}"
    def_method="${rest##*|}"
    resolved_def_id="$def_id"
    if [[ -n "$def_name" && -n "$name_map" ]]; then
      resolved_def_id="$(python3 -c '
import sys
name_map, def_name, def_method, resp_id = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
rows = [l.split("|", 2) for l in name_map.splitlines() if l.strip()]
cands = [r for r in rows if len(r) >= 2 and r[1] == def_name]
if len(cands) == 1:
    print(cands[0][0])
elif len(cands) > 1:
    pick = cands[0][0]
    if def_method:
        m = [r for r in cands if len(r) >= 3 and r[2] == def_method]
        if len(m) == 1:
            pick = m[0][0]
    print("WARN|" + pick)
else:
    print(resp_id)
' "$name_map" "$def_name" "$def_method" "$def_id")" || resolved_def_id="$def_id"
      if [[ "$resolved_def_id" == "WARN|"* ]]; then
        echo "警告: 同名定义多个，取首个（${resolved_def_id#WARN|}）" >&2
        resolved_def_id="${resolved_def_id#WARN|}"
      fi
    fi
    detail_file="$tmp_dir/detail_${resolved_def_id}.json"
    if ! request GET "$(path_fill "$METERSPHERE_API_DEFINITION_GET_PATH" "$resolved_def_id")" "" "api" > "$detail_file"; then
      echo "定义 $def_name：导入响应 id $def_id 未持久化（解析 id $resolved_def_id，GET data:null），跳过" >&2
      continue
    fi
    variants_file="$tmp_dir/variants_${resolved_def_id}.json"
    if ! python3 "$SCRIPT_DIR/ms_generate_case.py" "$detail_file" > "$variants_file" 2> "$tmp_dir/gen.err"; then
      echo "定义 $def_id 生成用例失败: $(cat "$tmp_dir/gen.err")" >&2
      continue
    fi
    variants="$(python3 -c 'import json,sys; print(",".join('"'"'\"%s\"'"'"' % v["name"] for v in json.load(open(sys.argv[1]))))' "$variants_file")"
    if (( first )); then first=0; else printf ',' >> "$tmp_dir/out.json"; fi
    printf '{"definitionId":"%s","variants":[%s]}' "$resolved_def_id" "$variants" >> "$tmp_dir/out.json"
  done <<< "$def_lines"
  echo ']}' >> "$tmp_dir/out.json"
  cat "$tmp_dir/out.json"
  rm -rf "$tmp_dir"
  trap - EXIT
}

# import-create: 导入定义 + 写入用例（幂等：已存在同名变体则跳过）
# 参数: project_id spec_source module_id(可空)
import_create () {
  local project_id="$1" spec_source="$2" module_id="${3:-}"
  need_base_url
  need_keys
  require_project_id
  local resolved spec_path
  resolved="$(python3 "$SCRIPT_DIR/ms_import_helper.py" resolve "$spec_source")"
  spec_path="${resolved%%|*}"
  local resp defs_json tmp_dir def_lines def_id def_name def_method resolved_def_id existing detail_file variants_file payloads_file
  resp="$(import_definitions "$project_id" "$spec_path" "$module_id")"
  if ! printf '%s' "$resp" | grep -q '"success":true'; then
    die "导入定义失败: $resp"
  fi
  defs_json="$(printf '%s' "$resp" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(json.dumps((d.get("data") or {}).get("data", []), ensure_ascii=False))')"
  tmp_dir="$(mktemp -d)"
  trap 'rm -rf "$tmp_dir"' EXIT
  def_lines="$(printf '%s' "$defs_json" | python3 -c 'import json,sys; print("\n".join("%s|%s|%s" % (x.get("id",""), x.get("name") or "", x.get("method") or "") for x in json.load(sys.stdin)))')"
  local total=0 created=0 skipped=0 failed=0
  local headers signature existing_names name_map
  # existing_case_names 需要 {header:value} dict；复用 generate_signature，绝不手写签名
  signature="$(generate_signature)"
  headers="$(python3 -c 'import json,sys; print(json.dumps({"accessKey": sys.argv[1], "signature": sys.argv[2]}))' "$METERSPHERE_ACCESS_KEY" "$signature")"
  # 拉取持久化定义列表（一次/运行）：重复导入时响应 id 可能未持久化，按 name 解析真实 id
  name_map="$(definition_ids_by_name "$project_id")" || die "定义列表拉取失败（无法解析持久化 id）"
  local case_name case_id cresp
  while IFS= read -r def_line; do
    [[ -n "$def_line" ]] || continue
    def_id="${def_line%%|*}"
    local rest="${def_line#*|}"
    def_name="${rest%|*}"
    def_method="${rest##*|}"
    resolved_def_id="$def_id"
    if [[ -n "$def_name" && -n "$name_map" ]]; then
      resolved_def_id="$(python3 -c '
import sys
name_map, def_name, def_method, resp_id = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
rows = [l.split("|", 2) for l in name_map.splitlines() if l.strip()]
cands = [r for r in rows if len(r) >= 2 and r[1] == def_name]
if len(cands) == 1:
    print(cands[0][0])
elif len(cands) > 1:
    pick = cands[0][0]
    if def_method:
        m = [r for r in cands if len(r) >= 3 and r[2] == def_method]
        if len(m) == 1:
            pick = m[0][0]
    print("WARN|" + pick)
else:
    print(resp_id)
' "$name_map" "$def_name" "$def_method" "$def_id")" || resolved_def_id="$def_id"
      if [[ "$resolved_def_id" == "WARN|"* ]]; then
        echo "警告: 同名定义多个，取首个（${resolved_def_id#WARN|}）" >&2
        resolved_def_id="${resolved_def_id#WARN|}"
      fi
    fi
    # 去重预检：取该定义下已有用例名集合（ms_import_helper 未暴露 CLI 子命令，经模块导入调用）
    existing="$(python3 -c '
import sys, json
sys.path.insert(0, sys.argv[1])
from ms_import_helper import existing_case_names
names = existing_case_names(sys.argv[2], sys.argv[3], sys.argv[4], json.loads(sys.argv[5]))
print("\n".join(sorted(names)))
' "$SCRIPT_DIR" "$project_id" "$resolved_def_id" "$METERSPHERE_BASE_URL" "$headers")" || die "已存在用例预检失败（定义 $def_name / $resolved_def_id）"
    existing_names="|$(printf '%s\n' "$existing" | tr '\n' '|')"
    detail_file="$tmp_dir/detail_${resolved_def_id}.json"
    if ! request GET "$(path_fill "$METERSPHERE_API_DEFINITION_GET_PATH" "$resolved_def_id")" "" "api" > "$detail_file"; then
      echo "定义 $def_name：detail GET 失败（id $resolved_def_id），跳过" >&2
      failed=$(( failed + 1 ))
      continue
    fi
    if ! python3 -c '
import json, sys
d = json.load(open(sys.argv[1]))
data = d.get("data")
raise SystemExit(0 if isinstance(data, dict) else 1)
' "$detail_file"; then
      echo "定义 $def_name：导入响应 id $def_id 未持久化（解析 id $resolved_def_id，GET data:null），跳过" >&2
      failed=$(( failed + 1 ))
      continue
    fi
    variants_file="$tmp_dir/variants_${resolved_def_id}.json"
    if ! python3 "$SCRIPT_DIR/ms_generate_case.py" "$detail_file" > "$variants_file" 2> "$tmp_dir/gen.err"; then
      echo "定义 $def_id 生成用例失败: $(cat "$tmp_dir/gen.err")" >&2
      continue
    fi
    payloads_file="$tmp_dir/payloads_${def_id}.jsonl"
    if ! python3 - "$variants_file" "$payloads_file" <<'PY'
import json, sys, uuid
variants = json.load(open(sys.argv[1]))
with open(sys.argv[2], "w") as f:
    for v in variants:
        if isinstance(v.get("request"), str):
            v["request"] = json.loads(v["request"])
        if not v.get("id"):
            v["id"] = str(uuid.uuid4())
        if not v.get("priority"):
            v["priority"] = "P1"
        f.write(json.dumps(v, ensure_ascii=False) + "\n")
PY
    then
      echo "定义 $def_id 载荷转换失败" >&2
      continue
    fi
    while IFS= read -r line; do
      [[ -n "$line" ]] || continue
      total=$(( total + 1 ))
      case_name="$(printf '%s' "$line" | python3 -c 'import json,sys; print(json.loads(sys.stdin.read())["name"])')"
      if [[ -n "$existing_names" ]] && [[ "$existing_names" == *"|${case_name}|"* ]]; then
        echo "跳过(已存在): $case_name"
        skipped=$(( skipped + 1 ))
        continue
      fi
      tmp_json="$tmp_dir/payload_$$.json"
      printf '%s' "$line" > "$tmp_json"
      signature="$(generate_signature)"
      cresp="$(curl -sS -X POST \
        -H "accessKey: ${METERSPHERE_ACCESS_KEY}" \
        -H "signature: ${signature}" \
        -F "request=@${tmp_json};type=application/json" \
        "${METERSPHERE_BASE_URL%/}/api${METERSPHERE_API_CASE_CREATE_PATH}")"
      rm -f "$tmp_json"
      case_id="$(printf '%s' "$cresp" | python3 -c 'import json,sys
try:
    d=json.load(sys.stdin)
except Exception:
    print(""); raise SystemExit
data=d.get("data")
if isinstance(data, str) and data:
    print(data)
elif isinstance(data, dict):
    print(data.get("id") or "")
else:
    print("")')"
      if [[ -n "$case_id" ]]; then
        echo "已创建用例: $case_id ($case_name)"
        created=$(( created + 1 ))
      else
        echo "用例创建失败: $case_name — $cresp"
      fi
    done < "$payloads_file"
  done <<< "$def_lines"
  if (( failed > 0 )); then
    echo "import-create 完成: 共 $total 个用例，新增 $created 个，跳过 $skipped 个，失败 $failed 个（详见上方诊断）"
  else
    echo "import-create 完成: 共 $total 个用例，新增 $created 个，跳过 $skipped 个"
  fi
  rm -rf "$tmp_dir"
  trap - EXIT
  if (( created == 0 && skipped == 0 )); then
    return 1
  fi
  return 0
}

# 分页拉取项目内功能用例名（POST /track/test/case/list/{n}/{size}，body {projectId}）。
# 输出：每行一个用例名；失败时输出 ERR:...（调用方需检查 ERR: 前缀）。
fetch_functional_case_names() {
  local project_id="$1"
  need_base_url
  need_keys
  local signature
  signature="$(generate_signature)"
  python3 - "$project_id" "${METERSPHERE_BASE_URL%/}" "$METERSPHERE_ACCESS_KEY" "$signature" "$METERSPHERE_FUNCTIONAL_CASE_LIST_PATH" <<'PY'
import json, sys, urllib.error, urllib.request
project_id, base_url, access_key, signature, list_path = sys.argv[1:6]
names, go_page, page_size = [], 1, 100
while True:
    url = "%s/track%s" % (base_url, list_path.replace("{goPage}", str(go_page)).replace("{pageSize}", str(page_size)))
    body = json.dumps({"projectId": project_id}, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("accessKey", access_key)
    req.add_header("signature", signature)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            doc = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print("ERR:HTTP %d %s" % (e.code, e.reason)); sys.exit(0)
    except urllib.error.URLError as e:
        print("ERR:%s" % e.reason); sys.exit(0)
    data = (doc or {}).get("data")
    batch, page_count = [], None
    if isinstance(data, list):
        batch, page_count = data, None
    elif isinstance(data, dict):
        batch = data.get("listObject") or []
        page_count = data.get("pageCount")
    else:
        print("ERR:响应 data 结构无法识别"); sys.exit(0)
    for it in batch:
        nm = it.get("name") if isinstance(it, dict) else None
        if nm:
            names.append(str(nm))
    if page_count is None:
        if len(batch) < page_size:
            break
    elif go_page >= int(page_count or 1):
        break
    go_page += 1
print("\n".join(names))
PY
}

case "$action" in
  list)
    arg="${1:-}"
    if [[ "$resource" == "organization" ]]; then
      # v2: workspace list 是 GET，无 body
      request GET "$METERSPHERE_ORGANIZATION_LIST_PATH" "" "$service_prefix"
    elif [[ "$resource" == "project" ]]; then
      # v2: /project/list/related 是 POST，body 传 workspaceId（BaseProjectController）
      if [[ -n "$arg" && "$arg" != "all" ]]; then
        request POST "$METERSPHERE_PROJECT_LIST_BY_ORG_PATH" "{\"workspaceId\":\"$arg\"}" "$service_prefix"
      elif [[ -n "$METERSPHERE_WORKSPACE_ID" ]]; then
        request POST "$METERSPHERE_PROJECT_LIST_PATH" "{\"workspaceId\":\"$METERSPHERE_WORKSPACE_ID\"}" "$service_prefix"
      else
        request POST "$METERSPHERE_PROJECT_LIST_SYSTEM_PATH" "{}" "$service_prefix"
      fi
    elif [[ "$resource" == "functional-module" ]]; then
      project_id="${arg:-$METERSPHERE_PROJECT_ID}"
      [[ -n "$project_id" ]] || die "functional-module list 需要 projectId"
      request GET "$(path_fill "$METERSPHERE_FUNCTIONAL_MODULE_TREE_PATH" "$project_id")" "" "$service_prefix"
    elif [[ "$resource" == "functional-template" ]]; then
      project_id="${arg:-$METERSPHERE_PROJECT_ID}"
      [[ -n "$project_id" ]] || die "functional-template list 需要 projectId"
      request GET "$(path_fill "$METERSPHERE_FUNCTIONAL_TEMPLATE_FIELD_PATH" "$project_id")" "" "$service_prefix"
    elif [[ "$resource" == "api-module" ]]; then
      project_id="${arg:-$METERSPHERE_PROJECT_ID}"
      [[ -n "$project_id" ]] || die "api-module list 需要 projectId"
      # v2: /api/module/list/{projectId}/{protocol} 是 GET 路径参数
      protocol="$(printf '%s' "$METERSPHERE_PROTOCOLS_JSON" | python3 -c 'import json,sys; print(json.load(sys.stdin)[0])' 2>/dev/null || echo HTTP)"
      api_module_path="${METERSPHERE_API_MODULE_TREE_PATH/\{protocol\}/$protocol}"
      request GET "$(path_fill "$api_module_path" "$project_id")" "" "$service_prefix"
    elif [[ "$resource" == "case-review-module" ]]; then
      project_id="${arg:-$METERSPHERE_PROJECT_ID}"
      [[ -n "$project_id" ]] || die "case-review-module list 需要 projectId"
      request POST "$(path_fill "$METERSPHERE_CASE_REVIEW_MODULE_TREE_PATH" "$project_id")" "" "$service_prefix"
    elif [[ "$resource" == "case-review-user" ]]; then
      review_id="${arg:-}"
      [[ -n "$review_id" ]] || die "case-review-user list 需要 reviewId"
      request POST "$METERSPHERE_CASE_REVIEW_USER_OPTION_PATH" "{\"id\":\"$review_id\"}" "$service_prefix"
    elif [[ "$resource" == "comment" ]]; then
      # v2: GET /test/case/comment/list/{caseId}[/{type}[/{belongId}]]
      case_id="${1:-}"
      [[ -n "$case_id" ]] || die "comment list 需要 caseId"
      type="${2:-}"
      belong_id="${3:-}"
      if [[ -n "$belong_id" ]]; then
        resp="$(request GET "${METERSPHERE_COMMENT_LIST_PATH}/${case_id}/${type}/${belong_id}" "" "$service_prefix")"
      elif [[ -n "$type" ]]; then
        resp="$(request GET "${METERSPHERE_COMMENT_LIST_PATH}/${case_id}/${type}" "" "$service_prefix")"
      else
        resp="$(request GET "${METERSPHERE_COMMENT_LIST_PATH}/${case_id}" "" "$service_prefix")"
      fi
      printf '%s\n' "$resp"
      [[ "$resp" != *'"success":false'* ]] || die "comment list 失败: $resp"
    elif [[ "$resource" == "attachment" ]]; then
      case_id="${1:-}"
      [[ -n "$case_id" ]] || die "attachment list 需要 caseId"
      resp="$(request POST "$METERSPHERE_ATTACHMENT_LIST_PATH" "{\"belongId\":\"$case_id\",\"belongType\":\"testcase\"}" "$service_prefix")"
      printf '%s\n' "$resp"
      [[ "$resp" != *'"success":false'* ]] || die "attachment list 失败: $resp"
    elif [[ "$resource" == "file" ]]; then
      project_id="${arg:-$METERSPHERE_PROJECT_ID}"
      [[ -n "$project_id" ]] || die "file list 需要 projectId"
      go_page="${2:-1}"
      page_size="${3:-20}"
      file_list_path="${METERSPHERE_FILE_METADATA_LIST_PATH/\{goPage\}/$go_page}"
      file_list_path="${file_list_path/\{pageSize\}/$page_size}"
      request POST "$(path_fill "$file_list_path" "$project_id")" "{}" "$service_prefix"
    elif [[ "$resource" == "file-module" ]]; then
      project_id="${arg:-$METERSPHERE_PROJECT_ID}"
      [[ -n "$project_id" ]] || die "file-module list 需要 projectId"
      request GET "$(path_fill "$METERSPHERE_FILE_MODULE_LIST_PATH" "$project_id")" "" "$service_prefix"
    elif [[ "$resource" == "functional-case" ]]; then
      # 分页循环拉全并合并：body 的 pageSize 仅作每页大小，goPage 由脚本循环控制，
      # 输出 {"success":true,"data":[全部页合并后的用例数组]}
      list_body="${arg:-}"
      if [[ -z "$list_body" || "$list_body" == "-" ]]; then
        [[ -n "${METERSPHERE_PROJECT_ID:-}" ]] || die "functional-case list 需要 JSON body（含 projectId）或设置 METERSPHERE_PROJECT_ID"
        list_body="{\"projectId\":\"$METERSPHERE_PROJECT_ID\"}"
      fi
      need_base_url
      need_keys
      signature="$(generate_signature)"
      python3 - "$list_body" "${METERSPHERE_BASE_URL%/}" "$METERSPHERE_ACCESS_KEY" "$signature" "$METERSPHERE_FUNCTIONAL_CASE_LIST_PATH" <<'PY'
import json, sys, urllib.error, urllib.request
body_raw, base_url, access_key, signature, list_path = sys.argv[1:6]
try:
    user_body = json.loads(body_raw)
    if not isinstance(user_body, dict):
        raise ValueError
except Exception:
    print("ERR:functional-case list body 需为 JSON 对象", file=sys.stderr); sys.exit(1)
if not user_body.get("projectId"):
    print("ERR:functional-case list body 需要 projectId", file=sys.stderr); sys.exit(1)
page_size = int(user_body.get("pageSize") or 100)
items, go_page = [], 1
while True:
    url = "%s/track%s" % (base_url, list_path.replace("{goPage}", str(go_page)).replace("{pageSize}", str(page_size)))
    data_bytes = json.dumps(user_body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data_bytes, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("accessKey", access_key)
    req.add_header("signature", signature)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            doc = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print("ERR:HTTP %d %s" % (e.code, e.reason), file=sys.stderr); sys.exit(1)
    except urllib.error.URLError as e:
        print("ERR:%s" % e.reason, file=sys.stderr); sys.exit(1)
    if isinstance(doc, dict) and doc.get("success") is False:
        print("ERR:%s" % json.dumps(doc, ensure_ascii=False), file=sys.stderr); sys.exit(1)
    data = (doc or {}).get("data")
    if isinstance(data, list):
        batch, page_count = data, None
    elif isinstance(data, dict):
        batch = data.get("listObject") or []
        page_count = data.get("pageCount")
    else:
        batch, page_count = [], None
    items.extend(batch)
    if page_count is None:
        if len(batch) < page_size:
            break
    elif go_page >= int(page_count or 1):
        break
    go_page += 1
print(json.dumps({"success": True, "data": items}, ensure_ascii=False))
PY
    else
      if [[ -n "$arg" && "$arg" == \{* ]]; then
        body="$(normalize_json_with_defaults "$resource" "$arg")"
      else
        body="$(default_list_payload "$resource" "$arg")"
      fi
      request POST "$(path_fill "$list_path" "")" "$body" "$service_prefix"
    fi
    ;;
  get)
    id="${1:-}"
    [[ -n "$id" ]] || die "get 需要 id"
    if [[ "$resource" == "file" ]]; then
      outfile="${2:-}"
      need_base_url
      need_keys
      signature="$(generate_signature)"
      if [[ -n "$outfile" ]]; then
        curl -sS -o "$outfile" -X GET \
          -H "accessKey: $METERSPHERE_ACCESS_KEY" \
          -H "signature: $signature" \
          "${METERSPHERE_BASE_URL%/}/track$(path_fill "$METERSPHERE_FILE_METADATA_INFO_PATH" "$id")"
        if grep -q '"success":false' "$outfile" 2>/dev/null; then
          cat "$outfile" >&2
          rm -f "$outfile"
          die "file get 失败"
        fi
        bytes="$(wc -c < "$outfile")"
        echo "已下载 $bytes 字节到 $outfile"
      else
        curl -sS -X GET \
          -H "accessKey: $METERSPHERE_ACCESS_KEY" \
          -H "signature: $signature" \
          "${METERSPHERE_BASE_URL%/}/track$(path_fill "$METERSPHERE_FILE_METADATA_INFO_PATH" "$id")"
      fi
    else
      request GET "$(path_fill "$get_path" "$id")" "" "$service_prefix"
    fi
    ;;
  create)
    if [[ "$resource" == "file" ]]; then
      body="${1:-}"
      local_file="${2:-}"
      [[ -n "$body" ]] || die "file create 需要 JSON body"
      [[ -n "$local_file" ]] || die "file create 需要 local-file"
      [[ -f "$local_file" ]] || die "file create 文件不存在: $local_file"
      require_project_id
      tmp_json="$(mktemp)"
      printf '%s' "$body" > "$tmp_json"
      need_base_url
      need_keys
      signature="$(generate_signature)"
      resp="$(curl -sS -X POST \
        -H "accessKey: $METERSPHERE_ACCESS_KEY" \
        -H "signature: $signature" \
        -F "request=@${tmp_json};type=application/json" \
        -F "file=@${local_file}" \
        "${METERSPHERE_BASE_URL%/}/track${METERSPHERE_FILE_METADATA_CREATE_PATH}")"
      rm -f "$tmp_json"
      printf '%s\n' "$resp"
      [[ "$resp" != *'"success":false'* ]] || die "file create 失败: $resp"
      file_id="$(printf '%s' "$resp" | python3 -c 'import json,sys
try:
    d = json.load(sys.stdin)
except Exception:
    sys.exit(0)
if isinstance(d, dict):
    d = d.get("data")
if isinstance(d, list) and d and isinstance(d[0], dict) and d[0].get("id"):
    print(d[0]["id"])
' 2>/dev/null || true)"
      [[ -n "$file_id" ]] || die "file create 失败: 响应未包含文件 id: $resp"
      exit 0
    fi
    if [[ "$resource" == "file-module" ]]; then
      name="${1:-}"
      parent_id="${2:-}"
      [[ -n "$name" ]] || die "file-module create 需要 name"
      require_project_id
      if [[ -z "$parent_id" || "$parent_id" == "-" || "$parent_id" == "NONE" ]]; then
        parent_id="NONE"
        level=1
      else
        tree_json="$(request GET "$(path_fill "$METERSPHERE_FILE_MODULE_LIST_PATH" "$METERSPHERE_PROJECT_ID")" "" "$service_prefix")" || true
        level="$(printf '%s' "$tree_json" | parent_id="$parent_id" python3 -c '
import json,sys,os
parent_id = os.environ["parent_id"]
try:
    tree = json.load(sys.stdin)["data"]
except Exception:
    print("ERR: file-module list 响应无法解析"); raise SystemExit(1)
def walk(nodes, depth):
    for n in nodes:
        if n.get("id") == parent_id:
            yield depth
        yield from walk(n.get("children") or [], depth + 1)
levels = list(walk(tree, 1))
if not levels:
    print("ERR: 父文件夹不存在: %s" % parent_id); raise SystemExit(1)
print(levels[0] + 1)
')" || true
        [[ "$level" != ERR* ]] || die "${level#ERR: }"
        [[ -n "$level" ]] || die "file-module create 失败: 无法解析父文件夹层级"
      fi
      body="$(python3 - "$METERSPHERE_PROJECT_ID" "$name" "$parent_id" "$level" <<'PY'
import json,sys
project_id, name, parent_id, level = sys.argv[1:5]
print(json.dumps({"projectId": project_id, "name": name,
                  "parentId": parent_id, "level": int(level),
                  "moduleType": "module"}, ensure_ascii=False))
PY
)"
      resp="$(request POST "$METERSPHERE_FILE_MODULE_CREATE_PATH" "$body" "$service_prefix")"
      printf '%s\n' "$resp"
      [[ "$resp" != *'"success":false'* ]] || die "file-module create 失败: $resp"
      exit 0
    fi
    body="${1:-}"
    [[ -n "$body" ]] || die "create 需要 JSON body"
    require_project_id
    body="$(normalize_json_with_defaults "$resource" "$body")"
    if [[ "$resource" == "case-review" ]]; then
      # v2: case-review 创建端点为 @RequestBody 纯 JSON（POST /test/case/review/save）
      request POST "$create_path" "$body" "$service_prefix"
    else
      if [[ "$resource" == "api-case" ]]; then
        body="$(inject_api_case_create_defaults "$body")"
      fi
      # v2: 其余创建端点为 multipart/form-data（request=JSON 文件字段）
      tmp_json="$(mktemp)"
      printf '%s' "$body" > "$tmp_json"
      need_base_url
      need_keys
      signature="$(generate_signature)"
      curl -sS -X POST \
        -H "accessKey: $METERSPHERE_ACCESS_KEY" \
        -H "signature: $signature" \
        -F "request=@${tmp_json};type=application/json" \
        "${METERSPHERE_BASE_URL%/}/${service_prefix}${create_path}"
      rm -f "$tmp_json"
    fi
    ;;
  save)
    [[ "$resource" == "comment" ]] || die "save 仅支持 comment 资源"
    case_id="${1:-}"
    description="${2:-}"
    [[ -n "$case_id" ]] || die "comment save 需要 caseId"
    [[ -n "$description" ]] || die "comment save 需要 description"
    type="${3:-CASE}"
    belong_id="${4:-}"
    body="$(python3 - <<'PY' "$case_id" "$description" "$type" "$belong_id"
import json,sys
case_id, description, ctype, belong_id = sys.argv[1:5]
print(json.dumps({"caseId": case_id, "description": description, "type": ctype, "belongId": belong_id}, ensure_ascii=False))
PY
)"
    resp="$(request POST "$METERSPHERE_COMMENT_CREATE_PATH" "$body" "$service_prefix")"
    printf '%s\n' "$resp"
    [[ "$resp" != *'"success":false'* ]] || die "comment save 失败: $resp"
    ;;
  delete)
    if [[ "$resource" == "comment" ]]; then
      comment_id="${1:-}"
      [[ -n "$comment_id" ]] || die "comment delete 需要 commentId"
      resp="$(request GET "${METERSPHERE_COMMENT_DELETE_PATH}/${comment_id}" "" "$service_prefix")"
      printf '%s\n' "$resp"
      [[ "$resp" != *'"success":false'* ]] || die "comment delete 失败: $resp"
    elif [[ "$resource" == "attachment" ]]; then
      attachment_id="${1:-}"
      [[ -n "$attachment_id" ]] || die "attachment delete 需要 attachmentId"
      resp="$(request GET "${METERSPHERE_ATTACHMENT_DELETE_PATH}/${attachment_id}" "" "$service_prefix")"
      printf '%s\n' "$resp"
      [[ "$resp" != *'"success":false'* ]] || die "attachment delete 失败: $resp"
    elif [[ "$resource" == "functional-case" ]]; then
      case_id="${1:-}"
      [[ -n "$case_id" ]] || die "functional-case delete 需要 caseId"
      require_project_id
      resp="$(request POST "$(path_fill "$METERSPHERE_FUNCTIONAL_CASE_DELETE_PATH" "$case_id")" "" "$service_prefix")"
      printf '%s\n' "$resp"
      [[ "$resp" != *'"success":false'* ]] || die "functional-case delete 失败: $resp"
    else
      die "delete 仅支持 comment / attachment / functional-case 资源"
    fi
    ;;
  edit)
    [[ "$resource" == "comment" ]] || die "edit 仅支持 comment 资源"
    comment_id="${1:-}"
    case_id="${2:-}"
    description="${3:-}"
    [[ -n "$comment_id" ]] || die "comment edit 需要 commentId"
    [[ -n "$case_id" ]] || die "comment edit 需要 caseId"
    [[ -n "$description" ]] || die "comment edit 需要 description"
    type="${4:-CASE}"
    belong_id="${5:-}"
    body="$(python3 - <<'PY' "$comment_id" "$case_id" "$description" "$type" "$belong_id"
import json,sys
comment_id, case_id, description, ctype, belong_id = sys.argv[1:6]
print(json.dumps({"id": comment_id, "caseId": case_id, "description": description, "type": ctype, "belongId": belong_id}, ensure_ascii=False))
PY
)"
    resp="$(request POST "$METERSPHERE_COMMENT_EDIT_PATH" "$body" "$service_prefix")"
    printf '%s\n' "$resp"
    [[ "$resp" != *'"success":false'* ]] || die "comment edit 失败: $resp"
    ;;
  exists)
    [[ "$resource" == "file" ]] || die "exists 仅支持 file 资源"
    [[ $# -ge 1 ]] || die "file exists 需要至少一个 fileId"
    if ! file_metadata_exists "$@"; then
      printf '%s\n' "$FILE_EXISTS_RESP"
      die "file exists 校验失败: 存在未找到的 fileId"
    fi
    printf '%s\n' "$FILE_EXISTS_RESP"
    ;;
  relate)
    [[ "$resource" == "attachment" ]] || die "relate 仅支持 attachment 资源"
    case_id="${1:-}"
    [[ -n "$case_id" ]] || die "attachment relate 需要 caseId"
    shift || true
    [[ $# -ge 1 ]] || die "attachment relate 需要至少一个 fileId"
    require_project_id
    body="$(python3 - "$case_id" "$@" <<'PY'
import json, sys
print(json.dumps({"belongId": sys.argv[1], "belongType": "testcase", "metadataRefIds": list(sys.argv[2:])}, ensure_ascii=False))
PY
)"
    need_base_url
    need_keys
    signature="$(generate_signature)"
    http_out="$(curl -sS -w $'\n%{http_code}' -X POST \
      -H "Content-Type: application/json" \
      -H "accessKey: $METERSPHERE_ACCESS_KEY" \
      -H "signature: $signature" \
      -d "$body" \
      "${METERSPHERE_BASE_URL%/}/track${METERSPHERE_ATTACHMENT_RELATE_PATH}")"
    http_code="${http_out##*$'\n'}"
    resp="${http_out%$'\n'*}"
    printf '%s\n' "$resp"
    [[ "$http_code" == "200" ]] || die "attachment relate 失败 (HTTP $http_code): $resp"
    [[ "$resp" != *'"success":false'* ]] || die "attachment relate 失败: $resp"
    ;;
  generate)
    [[ "$resource" == "functional-case" ]] || die "generate 仅支持 functional-case 资源"
    project_id="${1:-}"
    module_id="${2:-}"
    template_id="${3:-}"
    req_file="${4:-}"
    [[ -n "$project_id" ]] || die "generate 需要 projectId"
    if [[ -z "$module_id" || "$module_id" == "-" ]]; then
      module_id="default-module"
    fi
    [[ -n "$template_id" ]] || die "generate 需要 templateId"
    [[ -n "$req_file" ]] || die "generate 需要 requirement-file"
    python3 "$SCRIPT_DIR/ms_generate.py" functional-cases "$project_id" "$module_id" "$req_file" --templateId "$template_id"
    ;;
  batch-create)
    [[ "$resource" == "functional-case" ]] || die "batch-create 仅支持 functional-case 资源"
    # --file-id / --skip-existing 必须在读取位置参数之前剥离（镜像 api-case generate-create 的 --tags 剥离），
    # 否则会把字面量 "--file-id" 当成 json 文件名。
    batch_file_ids=()
    batch_skip_existing=0
    batch_args=()
    while [[ $# -gt 0 ]]; do
      case "$1" in
        --file-id)
          [[ $# -ge 2 ]] || die "--file-id 需要文件元数据 id"
          batch_file_ids+=("$2")
          shift 2
          ;;
        --file-id=*)
          batch_file_ids+=("${1#--file-id=}")
          shift
          ;;
        --skip-existing)
          batch_skip_existing=1
          shift
          ;;
        *)
          batch_args+=("$1")
          shift
          ;;
      esac
    done
    json_file="${batch_args[0]:-}"
    [[ -n "$json_file" ]] || die "batch-create 需要 JSON 数组文件"
    [[ -f "$json_file" ]] || die "batch-create 文件不存在: $json_file"
    require_project_id
    batch_unique_ids=()
    fid=""
    existing_id=""
    already=0
    for fid in "${batch_file_ids[@]}"; do
      [[ -n "$fid" ]] || continue
      already=0
      for existing_id in "${batch_unique_ids[@]}"; do
        if [[ "$existing_id" == "$fid" ]]; then
          already=1
          break
        fi
      done
      [[ "$already" == "1" ]] || batch_unique_ids+=("$fid")
    done
    if [[ ${#batch_unique_ids[@]} -gt 0 ]]; then
      file_metadata_exists "${batch_unique_ids[@]}" || die "batch-create --file-id 校验失败: 文件元数据不存在或不可用: ${batch_unique_ids[*]}"
    fi
    batch_create_functional_cases "$json_file" "$batch_skip_existing" "${batch_unique_ids[@]}"
    ;;
  generate-create)
    if [[ "$resource" == "functional-case" ]]; then
      project_id="${1:-}"
      module_id="${2:-}"
      template_id="${3:-}"
      req_file="${4:-}"
      [[ -n "$project_id" ]] || die "generate-create 需要 projectId"
      if [[ -z "$module_id" || "$module_id" == "-" ]]; then
        module_id="default-module"
      fi
      [[ -n "$template_id" ]] || die "generate-create 需要 templateId"
      [[ -n "$req_file" ]] || die "generate-create 需要 requirement-file"
      require_project_id
      tmp_json="$(mktemp)"
      python3 "$SCRIPT_DIR/ms_generate.py" functional-cases "$project_id" "$module_id" "$req_file" --templateId "$template_id" > "$tmp_json"
      batch_create_functional_cases "$tmp_json" 0
      rm -f "$tmp_json"
    elif [[ "$resource" == "api-case" ]]; then
      if [[ "${1:-}" == "--help" || "${1:-}" == "-h" || "${1:-}" == "help" ]]; then
        usage
        exit 0
      fi
      # --tags 必须在位置参数赋值之前剥离：project_id 读的是 $1，若不剥离，
      # `generate-create --tags T1 <projectId>` 会把字面量 "--tags" 当成 projectId
      # （非空、能过守卫）从而把写入瞄准到不存在的项目。
      api_case_tags_raw=()
      api_case_args=()
      while [[ $# -gt 0 ]]; do
        case "$1" in
          --help|-h|help)
            usage
            exit 0
            ;;
          --tags)
            [[ $# -ge 2 ]] || die "--tags 需要标签值，例如 --tags T-story-123（可重复；值内可用逗号或空格分隔多个标签）"
            api_case_tags_raw+=("$2")
            shift 2
            ;;
          --tags=*)
            api_case_tags_raw+=("${1#--tags=}")
            shift
            ;;
          *)
            api_case_args+=("$1")
            shift
            ;;
        esac
      done
      if [[ ${#api_case_tags_raw[@]} -gt 0 ]]; then
        if ! API_CASE_TAGS_JSON="$(python3 - "${api_case_tags_raw[@]}" <<'PY'
import json, sys
tags = []
for raw in sys.argv[1:]:
    for part in raw.replace(',', ' ').split():
        if part not in tags:
            tags.append(part)
if not tags:
    sys.exit(1)
print(json.dumps(tags, ensure_ascii=False))
PY
)"; then
          die "--tags 标签非法：标签值不能为空，多个标签用逗号或空格分隔"
        fi
      fi
      project_id="${api_case_args[0]:-${METERSPHERE_PROJECT_ID:-}}"
      [[ -n "$project_id" ]] || die "api-case generate-create 需要 projectId 参数或设置 METERSPHERE_PROJECT_ID（防止误写硬编码项目）"
      if [[ ${#api_case_args[@]} -gt 1 ]]; then
        generate_create_api_cases "$project_id" "${api_case_args[@]:1}"
      else
        generate_create_api_cases "$project_id"
      fi
      exit $?
    else
      die "generate-create 仅支持 functional-case / api-case 资源"
    fi
    ;;
  template)
    [[ "$resource" == "functional-case" ]] || die "template 仅支持 functional-case 资源"
    project_id="${1:-${METERSPHERE_PROJECT_ID:-}}"
    [[ -n "$project_id" ]] || die "functional-case template 需要 projectId"
    import_type="${2:-Create}"
    [[ "$import_type" == "Create" || "$import_type" == "Update" ]] || die "importType 仅支持 Create|Update（ExcelImportType 枚举）"
    outfile="${3:-}"
    need_base_url
    need_keys
    signature="$(generate_signature)"
    template_path="${METERSPHERE_CASE_TEMPLATE_PATH/\{projectId\}/$project_id}"
    template_path="${template_path/\{importType\}/$import_type}"
    if [[ -n "$outfile" ]]; then
      curl -sS -o "$outfile" -X GET \
        -H "accessKey: $METERSPHERE_ACCESS_KEY" \
        -H "signature: $signature" \
        "${METERSPHERE_BASE_URL%/}/track${template_path}"
      if grep -q '"success":false' "$outfile" 2>/dev/null; then
        cat "$outfile" >&2
        rm -f "$outfile"
        die "functional-case template 下载失败"
      fi
      bytes="$(wc -c < "$outfile")"
      echo "已下载 $bytes 字节到 $outfile"
    else
      curl -sS -X GET \
        -H "accessKey: $METERSPHERE_ACCESS_KEY" \
        -H "signature: $signature" \
        "${METERSPHERE_BASE_URL%/}/track${template_path}"
    fi
    ;;
  import)
    [[ "$resource" == "functional-case" ]] || die "import 仅支持 functional-case 资源"
    import_type="Create"
    version_id=""
    fix_status=""
    default_maintainer=""
    import_args=()
    while [[ $# -gt 0 ]]; do
      case "$1" in
        --import-type)
          [[ $# -ge 2 ]] || die "--import-type 需要值（Create|Update）"
          import_type="$2"
          shift 2
          ;;
        --import-type=*)
          import_type="${1#--import-type=}"
          shift
          ;;
        --version-id)
          [[ $# -ge 2 ]] || die "--version-id 需要版本 id"
          version_id="$2"
          shift 2
          ;;
        --version-id=*)
          version_id="${1#--version-id=}"
          shift
          ;;
        --fix-status)
          [[ $# -ge 2 ]] || die "--fix-status 需要值（模板字段选项，如 Finished）"
          fix_status="$2"
          shift 2
          ;;
        --fix-status=*)
          fix_status="${1#--fix-status=}"
          shift
          ;;
        --default-maintainer)
          [[ $# -ge 2 ]] || die "--default-maintainer 需要值（项目成员名或 ID）"
          default_maintainer="$2"
          shift 2
          ;;
        --default-maintainer=*)
          default_maintainer="${1#--default-maintainer=}"
          shift
          ;;
        *)
          import_args+=("$1")
          shift
          ;;
      esac
    done
    [[ "$import_type" == "Create" || "$import_type" == "Update" ]] || die "importType 仅支持 Create|Update（ExcelImportType 枚举）"
    project_id="${import_args[0]:-${METERSPHERE_PROJECT_ID:-}}"
    [[ -n "$project_id" ]] || die "functional-case import 需要 projectId 参数或设置 METERSPHERE_PROJECT_ID（防止误写硬编码项目）"
    excel_file="${import_args[1]:-}"
    [[ -n "$excel_file" ]] || die "functional-case import 需要 excel/xmind 文件"
    [[ -f "$excel_file" ]] || die "functional-case import 文件不存在: $excel_file"
    norm_dir=""
    if [[ -n "$fix_status" || -n "$default_maintainer" ]]; then
      [[ "${excel_file##*.}" == "xlsx" ]] || die "--fix-status/--default-maintainer 仅支持 .xlsx（xmind 无列概念）"
      norm_dir="$(mktemp -d)"
      normalized_file="$norm_dir/$(basename "$excel_file")"
      cp "$excel_file" "$normalized_file"
      norm_out="$(python3 - "$normalized_file" "$fix_status" "$default_maintainer" <<'PY'
import sys
try:
    from openpyxl import load_workbook
    from openpyxl.cell.cell import MergedCell
except ImportError:
    print("ERR:需要 openpyxl（pip install openpyxl）"); sys.exit(1)
src, fix_status, default_maintainer = sys.argv[1:4]
wb = load_workbook(src)
ws = wb.active
header = {}
for c in ws[1]:
    if c.value is not None:
        header.setdefault(str(c.value).strip().casefold(), c.column)
status_col = header.get("case status") or header.get("用例状态")
maintainer_col = header.get("maintainer") or header.get("责任人")
fixed_status = fixed_maintainer = 0
for row in ws.iter_rows(min_row=2):
    sc = row[status_col - 1] if status_col else None
    if fix_status and sc is not None and not isinstance(sc, MergedCell) \
            and sc.value not in (None, ""):
        sc.value = fix_status
        fixed_status += 1
    mc = row[maintainer_col - 1] if maintainer_col else None
    if default_maintainer and mc is not None and not isinstance(mc, MergedCell) \
            and mc.value in (None, ""):
        mc.value = default_maintainer
        fixed_maintainer += 1
wb.save(src)
print("OK:%d:%d" % (fixed_status, fixed_maintainer))
PY
)" || { rm -rf "$norm_dir"; die "functional-case import 预处理失败: ${norm_out#ERR:}"; }
      [[ "$norm_out" == OK:* ]] || { rm -rf "$norm_dir"; die "functional-case import 预处理失败: $norm_out"; }
      IFS=: read -r _ fixed_status_n fixed_maintainer_n <<< "$norm_out"
      excel_file="$normalized_file"
      echo "已生成规范化副本（原文件未改动）: 用例状态改写 ${fixed_status_n} 行 / 责任人补填 ${fixed_maintainer_n} 行"
    fi
    require_project_id
    import_body="{\"projectId\":\"$project_id\",\"importType\":\"$import_type\",\"ignore\":false"
    if [[ -n "$version_id" ]]; then
      import_body="${import_body},\"versionId\":\"$version_id\""
    fi
    import_body="${import_body}}"
    tmp_json="$(mktemp)"
    printf '%s' "$import_body" > "$tmp_json"
    need_base_url
    need_keys
    signature="$(generate_signature)"
    before_names="$(fetch_functional_case_names "$project_id")" || {
      rm -f "$tmp_json"
      [[ -z "$norm_dir" ]] || rm -rf "$norm_dir"
      die "functional-case import 导入前用例列表查询失败"
    }
    if [[ "$before_names" == ERR:* ]]; then
      rm -f "$tmp_json"
      [[ -z "$norm_dir" ]] || rm -rf "$norm_dir"
      die "functional-case import 导入前用例列表查询失败: ${before_names#ERR:}"
    fi
    http_out="$(curl -sS -w $'\n%{http_code}' -X POST \
      -H "accessKey: $METERSPHERE_ACCESS_KEY" \
      -H "signature: $signature" \
      -F "request=@${tmp_json};type=application/json" \
      -F "file=@${excel_file}" \
      "${METERSPHERE_BASE_URL%/}/track${METERSPHERE_CASE_IMPORT_PATH}")"
    rm -f "$tmp_json"
    [[ -z "$norm_dir" ]] || rm -rf "$norm_dir"
    http_code="${http_out##*$'\n'}"
    resp="${http_out%$'\n'*}"
    printf '%s\n' "$resp"
    [[ "$http_code" == "200" ]] || die "functional-case import 失败 (HTTP $http_code): $resp"
    success_check="$(printf '%s' "$resp" | python3 -c '
import json, sys
raw = sys.stdin.read()
try:
    doc = json.loads(raw)
except Exception:
    print("OK" if "\"success\":true" in raw else "FAIL|响应非 JSON 且不含 success:true")
    sys.exit(0)
if isinstance(doc, dict) and doc.get("success") is True:
    print("OK")
else:
    parts = []
    if isinstance(doc, dict):
        if doc.get("message"):
            parts.append(str(doc["message"]))
        if doc.get("errList"):
            parts.append("errList=" + json.dumps(doc["errList"], ensure_ascii=False))
    print("FAIL|" + ("; ".join(parts) if parts else "success 非 true"))
')"
    if [[ "$success_check" != "OK" ]]; then
      import_fail_msg="${success_check#FAIL|}"
      import_hint=""
      if [[ "$resp" == *"用例状态"* ]]; then
        import_hint="；提示: 「用例状态」列按列名匹配项目模板字段，值须为该字段的选项之一（典型模板为 Finished/Running/Prepare；Pass/UN_PASS 是评审状态，不是用例状态）"
      fi
      if [[ "$resp" == *"责任人"* ]]; then
        import_hint="${import_hint}；提示: 「责任人」为模板必填字段，须填项目成员（姓名或 ID），不能留空"
      fi
      die "functional-case import 失败: ${import_fail_msg}${import_hint}"
    fi
    after_names="$(fetch_functional_case_names "$project_id")" || {
      die "functional-case import 导入后用例列表查询失败"
    }
    if [[ "$after_names" == ERR:* ]]; then
      die "functional-case import 导入后用例列表查询失败: ${after_names#ERR:}"
    fi
    delta="$(python3 - "$before_names" "$after_names" <<'PY'
import sys
before = set(sys.argv[1].splitlines())
after = set(sys.argv[2].splitlines())
print(len(after - before))
PY
)"
    if [[ "$delta" -eq 0 ]]; then
      die "functional-case import 服务端返回 success:true 但落库增量为 0（上游 getImportResponse 契约弱点：success 仅由 errList 为空决定，与 isUpdated/实际落库无关）——请检查导入文件格式或服务端日志"
    fi
    echo "import 完成: 新增 $delta 条"
    ;;
  unrelated)
    [[ "$resource" == "attachment" ]] || die "unrelated 仅支持 attachment 资源"
    case_id="${1:-}"
    [[ -n "$case_id" ]] || die "attachment unrelated 需要 caseId"
    shift || true
    [[ $# -ge 1 ]] || die "attachment unrelated 需要至少一个 metadataRefId（库文件引用 id）"
    require_project_id
    body="$(python3 - "$case_id" "$@" <<'PY'
import json, sys
print(json.dumps({"belongId": sys.argv[1], "belongType": "testcase", "metadataRefIds": list(sys.argv[2:])}, ensure_ascii=False))
PY
)"
    need_base_url
    need_keys
    signature="$(generate_signature)"
    http_out="$(curl -sS -w $'\n%{http_code}' -X POST \
      -H "accessKey: $METERSPHERE_ACCESS_KEY" \
      -H "signature: $signature" \
      -H "Content-Type: application/json" \
      -d "$body" \
      "${METERSPHERE_BASE_URL%/}/track${METERSPHERE_ATTACHMENT_UNRELATE_PATH}")"
    http_code="${http_out##*$'\n'}"
    resp="${http_out%$'\n'*}"
    printf '%s\n' "$resp"
    [[ "$http_code" == "200" ]] || die "attachment unrelated 失败 (HTTP $http_code): $resp"
    [[ "$resp" != *'"success":false'* ]] || die "attachment unrelated 失败: $resp"
    ;;
  relate-demand)
    [[ "$resource" == "functional-case" ]] || die "relate-demand 仅支持 functional-case 资源"
    demand_name=""
    relate_demand_args=()
    while [[ $# -gt 0 ]]; do
      case "$1" in
        --demand-name)
          [[ $# -ge 2 ]] || die "--demand-name 需要需求名称"
          demand_name="$2"
          shift 2
          ;;
        --demand-name=*)
          demand_name="${1#--demand-name=}"
          shift
          ;;
        *)
          relate_demand_args+=("$1")
          shift
          ;;
      esac
    done
    project_id="${relate_demand_args[0]:-${METERSPHERE_PROJECT_ID:-}}"
    [[ -n "$project_id" ]] || die "functional-case relate-demand 需要 projectId 参数或设置 METERSPHERE_PROJECT_ID（防止误写硬编码项目）"
    demand_id="${relate_demand_args[1]:-}"
    [[ -n "$demand_id" ]] || die "functional-case relate-demand 需要 demandId（需求管理中的第三方平台需求 id）"
    if [[ ${#relate_demand_args[@]} -lt 3 ]]; then
      die "functional-case relate-demand 需要至少一个 caseId"
    fi
    if [[ "$demand_id" == "other" && -z "$demand_name" ]]; then
      die "demandId 为 other 时必须提供 --demand-name（v2.10 batchRelateDemand：demandId==other 时 demandName 必填）"
    fi
    require_project_id
    body="$(python3 - "$demand_id" "$demand_name" "${relate_demand_args[@]:2}" <<'PY'
import json, sys
print(json.dumps({"ids": list(sys.argv[3:]), "demandId": sys.argv[1], "demandName": sys.argv[2]}, ensure_ascii=False))
PY
)"
    need_base_url
    need_keys
    signature="$(generate_signature)"
    http_out="$(curl -sS -w $'\n%{http_code}' -X POST \
      -H "accessKey: $METERSPHERE_ACCESS_KEY" \
      -H "signature: $signature" \
      -H "Content-Type: application/json" \
      -d "$body" \
      "${METERSPHERE_BASE_URL%/}/track${METERSPHERE_RELATE_DEMAND_PATH}")"
    http_code="${http_out##*$'\n'}"
    resp="${http_out%$'\n'*}"
    printf '%s\n' "$resp"
    [[ "$http_code" == "200" ]] || die "functional-case relate-demand 失败 (HTTP $http_code): $resp"
    [[ "$resp" != *'"success":false'* ]] || die "functional-case relate-demand 失败: $resp"
    ;;
  split-create)
    [[ "$resource" == "functional-case" ]] || die "split-create 仅支持 functional-case 资源"
    link_mode="same-call"
    split_create_args=()
    while [[ $# -gt 0 ]]; do
      case "$1" in
        --link-mode)
          [[ $# -ge 2 ]] || die "--link-mode 需要值（same-call|separate）"
          link_mode="$2"
          shift 2
          ;;
        --link-mode=*)
          link_mode="${1#--link-mode=}"
          shift
          ;;
        *)
          split_create_args+=("$1")
          shift
          ;;
      esac
    done
    project_id="${split_create_args[0]:-${METERSPHERE_PROJECT_ID:-}}"
    [[ -n "$project_id" ]] || die "functional-case split-create 需要 projectId 参数或设置 METERSPHERE_PROJECT_ID（防止误写硬编码项目）"
    source_file="${split_create_args[1]:-}"
    [[ -n "$source_file" ]] || die "functional-case split-create 需要 docx/pdf/xlsx/xmind 文件"
    module_id="${split_create_args[2]:--}"
    split_create_functional_cases "$project_id" "$source_file" "$module_id" "$link_mode"
    exit $?
    ;;
  upload)
    [[ "$resource" == "attachment" ]] || die "upload 仅支持 attachment 资源"
    case_id="${1:-}"
    file="${2:-}"
    [[ -n "$case_id" ]] || die "attachment upload 需要 caseId"
    [[ -n "$file" ]] || die "attachment upload 需要 file"
    [[ -f "$file" ]] || die "attachment upload 文件不存在: $file"
    require_project_id
    need_base_url
    need_keys
    signature="$(generate_signature)"
    resp="$(curl -sS -X POST \
      -H "accessKey: $METERSPHERE_ACCESS_KEY" \
      -H "signature: $signature" \
      -F "sourceId=$case_id" \
      -F "file=@$file" \
      "${METERSPHERE_BASE_URL%/}/track${METERSPHERE_ATTACHMENT_UPLOAD_PATH}")"
    printf '%s\n' "$resp"
    [[ "$resp" != *'"success":false'* ]] || die "attachment upload 失败: $resp"
    ;;
  download)
    [[ "$resource" == "attachment" ]] || die "download 仅支持 attachment 资源"
    attachment_id="${1:-}"
    is_local="${2:-}"
    outfile="${3:-}"
    [[ -n "$attachment_id" ]] || die "attachment download 需要 attachmentId"
    [[ -n "$is_local" ]] || die "attachment download 需要 isLocal (true/false)"
    [[ -n "$outfile" ]] || die "attachment download 需要 outfile"
    need_base_url
    need_keys
    signature="$(generate_signature)"
    curl -sS -o "$outfile" -X GET \
      -H "accessKey: $METERSPHERE_ACCESS_KEY" \
      -H "signature: $signature" \
      "${METERSPHERE_BASE_URL%/}/track${METERSPHERE_ATTACHMENT_DOWNLOAD_PATH}/${attachment_id}/${is_local}"
    if grep -q '"success":false' "$outfile" 2>/dev/null; then
      cat "$outfile" >&2
      rm -f "$outfile"
      die "attachment download 失败"
    fi
    bytes="$(wc -c < "$outfile")"
    echo "已下载 $bytes 字节到 $outfile"
    ;;
  import-generate)
    [[ "$resource" == "api" ]] || die "import-generate 仅支持 api 资源"
    project_id="${1:-${METERSPHERE_PROJECT_ID:-}}"
    [[ -n "$project_id" ]] || die "import-generate 需要 projectId 参数或设置 METERSPHERE_PROJECT_ID（防止误写硬编码项目）"
    spec_source="${2:-}"
    [[ -n "$spec_source" ]] || die "import-generate 需要 spec 文件路径或 URL"
    import_generate "$project_id" "$spec_source" "${3:-}"
    exit $?
    ;;
  import-create)
    [[ "$resource" == "api" ]] || die "import-create 仅支持 api 资源"
    project_id="${1:-${METERSPHERE_PROJECT_ID:-}}"
    [[ -n "$project_id" ]] || die "import-create 需要 projectId 参数或设置 METERSPHERE_PROJECT_ID（防止误写硬编码项目）"
    spec_source="${2:-}"
    [[ -n "$spec_source" ]] || die "import-create 需要 spec 文件路径或 URL"
    import_create "$project_id" "$spec_source" "${3:-}"
    exit $?
    ;;
  help|-h|--help)
    usage
    ;;
  *)
    die "不支持的 action: $action"
    ;;
esac
