#!/bin/zsh
# geo_weekly.sh — 叽里呱啦 GEO 周度监控脚本
# 每周一自动采集 → 打分 → 推企业微信报告
# cron: 0 9 * * 1 (每周一 09:00)

set -e

PYTHON="/Library/Frameworks/Python.framework/Versions/3.11/bin/python3"
GEO_ROOT="/Users/alex/Documents/电脑同步/jiliguala2.0/GEO/GEO_Claude"
BASELINE_DIR="$GEO_ROOT/baseline_T0"
LOG_DIR="$GEO_ROOT/scripts/logs"

# 加载 zsh 环境变量（API Keys 都在 ~/.zshrc）
source ~/.zshrc 2>/dev/null || true

# 本轮标签（W + 从 T0 起算的周数）
T0_DATE="2026-04-27"
TODAY=$(date +%Y-%m-%d)
WEEKS=$(( ( $(date -j -f "%Y-%m-%d" "$TODAY" "+%s") - $(date -j -f "%Y-%m-%d" "$T0_DATE" "+%s") ) / 604800 ))
LABEL="W${WEEKS}"

mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/geo_${TODAY}.log"

echo "=============================" | tee -a "$LOG"
echo "GEO 周度监控 $LABEL  $(date)" | tee -a "$LOG"
echo "=============================" | tee -a "$LOG"

# 1. 采集
echo "[1/3] 采集中..." | tee -a "$LOG"
cd "$BASELINE_DIR"
$PYTHON -u collectors/api_runner.py --force 2>&1 | tee -a "$LOG"

# 2. 打分
echo "[2/3] 打分中..." | tee -a "$LOG"
$PYTHON scoring/auto_scorer.py 2>&1 | tee -a "$LOG"

# 3. 推企业微信
echo "[3/3] 推送周报 $LABEL ..." | tee -a "$LOG"
$PYTHON "$GEO_ROOT/scripts/push_weekly_report.py" --label "$LABEL" 2>&1 | tee -a "$LOG"

echo "完成 $(date)" | tee -a "$LOG"
