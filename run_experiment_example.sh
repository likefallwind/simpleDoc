#!/bin/bash
# Linux/Mac shell脚本示例：运行对比实验

echo "开始运行Prompt方案对比实验..."
echo ""

# 使用示例用户画像运行对比实验
python experiment_simple_prompt.py data/profiles/example_profile.yaml --compare

echo ""
echo "实验完成！结果保存在 experiments/ 目录下"

