#!/usr/bin/env bash
set -euo pipefail

# ==============================================================================
# order-app 镜像构建脚本
#
# 支持三种模式（默认 auto 自动判定）:
#   full  : 全量构建（重新 conda pack + 从 ubuntu 起层）
#   deps  : 增量构建，基于 order-app:latest，在容器内 pip install 新依赖
#   code  : 增量构建，基于 order-app:latest，仅更新代码
#
# 使用:
#   ./build.sh                # 自动判定
#   ./build.sh --full         # 强制全量
#   ./build.sh --incremental  # 强制增量（自动在 deps / code 间选）
#   ./build.sh --mode full|deps|code
# ==============================================================================

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_NAME="${ENV_NAME:-order}"
IMAGE_NAME="${IMAGE_NAME:-order-app}"
ENV_ARCHIVE_DIR="${PROJECT_ROOT}/.docker"
ENV_ARCHIVE_PATH="${ENV_ARCHIVE_DIR}/order-env.tar.gz"
REQ_FILE="${PROJECT_ROOT}/requirements.txt"

MODE="auto"
for arg in "$@"; do
  case "$arg" in
    --full)        MODE="full" ;;
    --incremental) MODE="incremental" ;;
    --mode=*)      MODE="${arg#--mode=}" ;;
    -h|--help)
      sed -n '3,20p' "${BASH_SOURCE[0]}"
      exit 0
      ;;
    *) echo "[WARN] 未知参数: $arg" ;;
  esac
done

log()  { echo "[INFO]  $*"; }
warn() { echo "[WARN]  $*"; }
err()  { echo "[ERROR] $*" >&2; }

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || { err "未找到命令: $1"; exit 1; }
}

require_cmd docker

# ---- 计算 requirements.txt 当前哈希 ----
REQ_SHA256="$(sha256sum "${REQ_FILE}" | awk '{print $1}')"
log "当前 requirements.txt sha256: ${REQ_SHA256}"

# ---- 查找现有镜像与已记录的哈希 ----
get_latest_req_sha() {
  docker image inspect "${IMAGE_NAME}:latest" \
    --format '{{ index .Config.Labels "order.req.sha256" }}' 2>/dev/null || true
}

HAS_LATEST=0
OLD_REQ_SHA=""
if docker image inspect "${IMAGE_NAME}:latest" >/dev/null 2>&1; then
  HAS_LATEST=1
  OLD_REQ_SHA="$(get_latest_req_sha)"
  log "检测到已有镜像 ${IMAGE_NAME}:latest (上次 req sha256: ${OLD_REQ_SHA:-unknown})"
else
  log "未检测到 ${IMAGE_NAME}:latest，将走全量构建"
fi

# ---- 决定模式 ----
case "${MODE}" in
  auto)
    if [ "${HAS_LATEST}" = "0" ]; then
      MODE="full"
    elif [ "${OLD_REQ_SHA}" = "${REQ_SHA256}" ]; then
      MODE="code"
    else
      MODE="deps"
    fi
    ;;
  incremental)
    if [ "${HAS_LATEST}" = "0" ]; then
      warn "指定了增量模式但无 ${IMAGE_NAME}:latest，自动退回 full"
      MODE="full"
    elif [ "${OLD_REQ_SHA}" = "${REQ_SHA256}" ]; then
      MODE="code"
    else
      MODE="deps"
    fi
    ;;
  full|deps|code) ;;
  *) err "未知模式: ${MODE}"; exit 1 ;;
esac

log "最终构建模式: ${MODE}"

# ---- 计算下一个版本号 v1/v2/... ----
# 注意: grep 无匹配会返回非零，pipefail 下会让整个脚本退出，因此这里显式容错
LAST_VERSION="$(
  docker images "${IMAGE_NAME}" --format '{{.Tag}}' 2>/dev/null \
    | { grep -E '^v[0-9]+$' || true; } \
    | sed 's/^v//' \
    | sort -n \
    | tail -1
)"
if [ -z "${LAST_VERSION}" ]; then
  NEXT_VERSION=1
else
  NEXT_VERSION=$((LAST_VERSION + 1))
fi
IMAGE_TAG="v${NEXT_VERSION}"
BUILD_TIME="$(date '+%Y-%m-%d %H:%M:%S %z')"

log "新版本 tag: ${IMAGE_TAG}"

# ==============================================================================
# 模式分派
# ==============================================================================

build_full() {
  log "==== FULL 构建 ===="
  require_cmd conda

  log "校验 conda 环境: ${ENV_NAME}"
  if ! conda run -n "${ENV_NAME}" python -c "import sys" >/dev/null 2>&1; then
    err "conda 环境不存在或不可用: ${ENV_NAME}"
    echo "    可先执行: conda create -n ${ENV_NAME} python=3.12 -y"
    exit 1
  fi

  log "在宿主机 conda 环境 ${ENV_NAME} 中同步 requirements.txt"
  conda run -n "${ENV_NAME}" pip install --upgrade -r "${REQ_FILE}"

  if ! command -v conda-pack >/dev/null 2>&1; then
    log "未检测到 conda-pack，安装到 base..."
    conda install -n base -y -c conda-forge conda-pack
  fi

  mkdir -p "${ENV_ARCHIVE_DIR}"
  log "打包 conda 环境 -> ${ENV_ARCHIVE_PATH}"
  rm -f "${ENV_ARCHIVE_PATH}"
  conda pack -n "${ENV_NAME}" -o "${ENV_ARCHIVE_PATH}" --force

  log "构建镜像 ${IMAGE_NAME}:${IMAGE_TAG} (Dockerfile)"
  docker build \
    -f "${PROJECT_ROOT}/Dockerfile" \
    -t "${IMAGE_NAME}:${IMAGE_TAG}" \
    --build-arg "BUILD_VERSION=${IMAGE_TAG}" \
    --build-arg "BUILD_TIME=${BUILD_TIME}" \
    --build-arg "REQ_SHA256=${REQ_SHA256}" \
    "${PROJECT_ROOT}"
}

build_incremental() {
  local install_deps="$1"     # 0/1
  local build_mode="$2"       # deps/code
  log "==== INCREMENTAL (${build_mode}) 构建 ===="
  log "基础镜像: ${IMAGE_NAME}:latest"
  log "是否重装依赖: ${install_deps}"

  docker build \
    -f "${PROJECT_ROOT}/Dockerfile.incremental" \
    -t "${IMAGE_NAME}:${IMAGE_TAG}" \
    --build-arg "BASE_IMAGE=${IMAGE_NAME}:latest" \
    --build-arg "INSTALL_DEPS=${install_deps}" \
    --build-arg "BUILD_VERSION=${IMAGE_TAG}" \
    --build-arg "BUILD_TIME=${BUILD_TIME}" \
    --build-arg "REQ_SHA256=${REQ_SHA256}" \
    --build-arg "BUILD_MODE=${build_mode}" \
    "${PROJECT_ROOT}"
}

case "${MODE}" in
  full) build_full ;;
  deps) build_incremental 1 deps ;;
  code) build_incremental 0 code ;;
esac

# ---- 打 latest tag ----
docker tag "${IMAGE_NAME}:${IMAGE_TAG}" "${IMAGE_NAME}:latest"
log "已更新 ${IMAGE_NAME}:latest -> ${IMAGE_NAME}:${IMAGE_TAG}"

# ---- 镜像清单展示 ----
echo ""
echo "===================== 当前 ${IMAGE_NAME} 版本列表 ====================="
docker images "${IMAGE_NAME}" --format 'table {{.Tag}}\t{{.ID}}\t{{.Size}}\t{{.CreatedAt}}' \
  | (read -r h; echo "$h"; sort -k1,1V)
echo "========================================================================"

cat <<EOF

[DONE] 镜像构建完成
       版本: ${IMAGE_NAME}:${IMAGE_TAG}
       模式: ${MODE}
       时间: ${BUILD_TIME}
       req-hash: ${REQ_SHA256}

[HINT] 运行前置：宿主机已配置 CUPS 队列 (lpstat -p 可见)，且 /run/cups/cups.sock 存在。
[HINT] 运行示例:
       docker run --rm -p 12345:12345 \\
         --env-file .env \\
         -v /run/cups/cups.sock:/run/cups/cups.sock \\
         -e CUPS_SERVER=/run/cups/cups.sock \\
         ${IMAGE_NAME}:latest

[HINT] 容器内自检:
       docker run --rm --entrypoint lpstat \\
         -v /run/cups/cups.sock:/run/cups/cups.sock \\
         -e CUPS_SERVER=/run/cups/cups.sock \\
         ${IMAGE_NAME}:latest -p

[HINT] 回滚到旧版本:
       docker tag ${IMAGE_NAME}:v<N> ${IMAGE_NAME}:latest
EOF
