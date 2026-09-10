#!/usr/bin/env bash
# download.sh —— DEM 下载（示例脚本，**未实跑**，端点需按各源最新文档核对）
#
# 用法：
#   ./download.sh --source COP_DEM30 --bbox "85.0,28.0,85.6,28.4" --out ./dem_raw.tif
#   ./download.sh --source ALOS_AW3D  --bbox "..." --out ./dem_raw.tif --token "$JAXA_TOKEN"
#   ./download.sh --source SRTM30     --bbox "..." --out ./dem_raw.tif --token "$NASA_TOKEN"
#
# 依赖：curl（或 wget）、gdal（gdalwarp / gdal_merge.py）、jq（可选，解析 API 响应）
#
# ⚠ 各源的端点、鉴权方式与 URL 规则会变更，**以官方最新文档为准**：
#   · Copernicus DEM   https://portal.opentopography.org / https://registry.opendata.aws/copernicus-dem
#   · ALOS AW3D        https://www.eorc.jaxa.jp/ALOS/en/aw3d30/
#   · SRTM / NASA      https://urs.earthdata.nasa.gov/
#   · 地理空间数据云    https://www.gscloud.cn/
#
# ⚠ 本仓库**不保存任何 token**；token 只从环境变量读取。

set -euo pipefail

SOURCE=""
BBOX=""
OUT=""
TOKEN="${TOKEN:-}"

usage() {
  grep '^#' "$0" | sed -n '2,16p' | sed 's/^# \{0,1\}//'
  exit 1
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --source) SOURCE="$2"; shift 2 ;;
    --bbox)   BBOX="$2";   shift 2 ;;
    --out)    OUT="$2";    shift 2 ;;
    --token)  TOKEN="$2";  shift 2 ;;
    -h|--help) usage ;;
    *) echo "未知参数: $1" >&2; usage ;;
  esac
done

[[ -z "$SOURCE" || -z "$BBOX" || -z "$OUT" ]] && usage

# bbox: "minlon,minlat,maxlon,maxlat"
IFS=',' read -r MINLON MINLAT MAXLON MAXLAT <<< "$BBOX"
echo "[info] source=$SOURCE bbox=$MINLON,$MINLAT,$MAXLON,$MAXLAT out=$OUT"

TMPDIR_DL="$(mktemp -d)"
trap 'rm -rf "$TMPDIR_DL"' EXIT

fetch() {  # fetch <url> <dest>
  local url="$1" dest="$2"
  echo "[get ] $url"
  if [[ -n "$TOKEN" ]]; then
    curl -fL --retry 3 --retry-delay 2 -H "Authorization: Bearer ${TOKEN}" -o "$dest" "$url"
  else
    curl -fL --retry 3 --retry-delay 2 -o "$dest" "$url"
  fi
}

case "$SOURCE" in

  COP_DEM30)
    # ------------------------------------------------------------------
    # Copernicus GLO-30：公开、免登录（AWS Open Data 镜像最省事）
    # 瓦片命名示例：Copernicus_DSM_COG_30_N28_00_E085_00_DEM
    # 做法：按 bbox 展开瓦片列表 → 逐块下载 → gdal_merge 拼 → gdalwarp 裁剪
    # ⚠ 下面只给"展开 + 拼接"的骨架，瓦片索引 URL 需按官方清单核对。
    # ------------------------------------------------------------------
    echo "[warn] COP_DEM30: 请先确认瓦片索引端点（见脚本头部注释），再补全 tile 列表"
    echo "[todo] for lat in ...; for lon in ...; do fetch <tile_url> ...; done"
    # gdal_merge.py -o "$TMPDIR_DL/merged.tif" "$TMPDIR_DL"/*.tif
    # gdalwarp -te "$MINLON" "$MINLAT" "$MAXLON" "$MAXLAT" "$TMPDIR_DL/merged.tif" "$OUT"
    ;;

  ALOS_AW3D)
    # ------------------------------------------------------------------
    # ALOS AW3D30：需 JAXA 注册，登录后取 token
    # 瓦片命名：<5位纬度><方位><5位经度><方位>，如 N028E085
    # ------------------------------------------------------------------
    [[ -z "$TOKEN" ]] && { echo "[err] ALOS_AW3D 需要 --token（JAXA 注册后获取）" >&2; exit 2; }
    echo "[warn] ALOS_AW3D: 补全瓦片下载 URL（见脚本头部注释）"
    # for lat in $(seq ...); do for lon in $(seq ...); do
    #   fetch "https://<endpoint>/ALPSMLC30/${tile}_DSM.tif" "$TMPDIR_DL/${tile}.tif"
    # done; done
    ;;

  SRTM30)
    # ------------------------------------------------------------------
    # SRTM 30 m：需 NASA Earthdata 账号（URS）
    # ------------------------------------------------------------------
    [[ -z "$TOKEN" ]] && { echo "[err] SRTM30 需要 --token（NASA Earthdata）" >&2; exit 2; }
    echo "[warn] SRTM30: 补全瓦片下载 URL（见脚本头部注释）"
    ;;

  GS_CLOUD)
    # ------------------------------------------------------------------
    # 地理空间数据云（国内）：需注册；界面/API 下载，端点随站点改版变化
    # ------------------------------------------------------------------
    echo "[warn] GS_CLOUD: 需注册并手动或按其 API 下载；请补全端点"
    ;;

  *)
    echo "[err] 未知 source: $SOURCE（可选 COP_DEM30 / ALOS_AW3D / SRTM30 / GS_CLOUD）" >&2
    exit 2
    ;;
esac

if [[ -f "$OUT" ]]; then
  echo "[ok ] 写出 $OUT"
  gdalinfo "$OUT" | grep -E "Size is|Coordinate System is|Origin|Pixel Size" || true
else
  echo "[warn] 未产出 $OUT —— 本脚本为骨架，请按各源最新文档补全端点后重跑"
  exit 3
fi
