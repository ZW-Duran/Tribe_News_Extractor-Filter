#!/bin/bash

# 1. 进入工作目录
cd /home/ubuntu/database/tribesNews || { echo "错误: 无法进入目录"; exit 1; }

# 2. 清理目录函数
# 参数 $1 是目标目录路径
clean_directory() {
    local dir=$1
    if [ -d "$dir" ]; then
        echo "正在清理目录: $dir"
        # 查找该目录下所有文件，排除 .gitkeep，然后删除
        find "$dir" -type f ! -name '.gitkeep' -delete
        # 如果你也想删除子目录（保留 .gitkeep 所在的结构），可以使用以下命令：
        # find "$dir" -mindepth 1 ! -name '.gitkeep' -delete
    else
        echo "警告: 目录 $dir 不存在，跳过清理。"
    fi
}

# 执行清理操作
clean_directory "./original"
clean_directory "./relevant"

# 3. 运行 Conda 并执行 Python 脚本
# 注意：在脚本中使用 conda 需先 source conda.sh 路径
# 通常路径为 ~/anaconda3/etc/profile.d/conda.sh 或 ~/miniconda3/etc/profile.d/conda.sh
CONDA_PATH=$(conda info --base)/etc/profile.d/conda.sh
if [ -f "$CONDA_PATH" ]; then
    source "$CONDA_PATH"
    conda activate database
    echo "已激活环境: database"
    
    echo "正在运行 simple_extract.py..."
    python3 simple_extract.py
else
    echo "错误: 找不到 conda.sh，请确认 conda 安装路径。"
    exit 1
fi

echo "任务完成！"
