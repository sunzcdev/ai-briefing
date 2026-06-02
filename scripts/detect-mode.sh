#!/bin/bash
# 检测工作流模式：daily / weekly / monthly
# 输出到 GITHUB_OUTPUT，供后续步骤使用

if [[ "${{ github.event_name }}" == "workflow_dispatch" ]]; then
  MODE="${{ github.event.inputs.mode }}"
else
  DOM=$(date +%d)
  DOW=$(date +%u)
  if [[ "$DOM" == "01" ]]; then
    MODE=monthly
  elif [[ "$DOW" == "1" ]]; then
    MODE=weekly
  else
    MODE=daily
  fi
fi

echo "mode=$MODE" >> "$GITHUB_OUTPUT"
echo "[lwf] mode=$MODE"
