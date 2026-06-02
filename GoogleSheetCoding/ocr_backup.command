#!/bin/bash

# 1. 切换到脚本目录
cd "$(dirname "$0")"

# 配置路径和参数
THREADS=10 # 建议根据CPU核心数调整，避免并发过多导致内存溢出
UPLOAD_DIR="./original"
OCRED_DIR="./ocred"

mkdir -p "$OCRED_DIR"

# 导出变量供子进程使用
export OCRED_DIR
export -f process_file

# 2. 定义处理函数
process_file() {
    local file="$1"
    local base_name=$(basename "$file")
    local output_file="$OCRED_DIR/$base_name"
    local temp_file="$OCRED_DIR/temp_$base_name"

    # 跳过已存在的文件
    if [ -f "$output_file" ]; then
        return
    fi

    echo "正在预处理 (降采样至 300 DPI): $base_name"
    
    # 使用 ghostscript 将 PDF 转换为 300 DPI 的 PDF
    # 这是最有效的降低内存占用并解决 DecompressionBomb 的方法
    gs -sDEVICE=pdfwrite -dCompatibilityLevel=1.4 -dPDFSETTINGS=/printer \
       -dColorImageResolution=300 -dGrayImageResolution=300 -dMonoImageResolution=300 \
       -dNOPAUSE -dBATCH -sOutputFile="$temp_file" "$file" > /dev/null 2>&1

    echo "正在 OCR: $base_name"
    # 执行 OCR
    ocrmypdf --force-ocr --clean --deskew --jobs 1 "$temp_file" "$output_file" > /dev/null 2>&1
    
    # 清理临时文件
    rm "$temp_file"
}
export -f process_file

# 3. 执行多线程任务
echo "正在开始处理 (并发数: $THREADS)..."
find "$UPLOAD_DIR" -type f -name "*.pdf" -print0 | xargs -0 -n 1 -P "$THREADS" -I {} bash -c 'process_file "{}"'

echo "--- 所有任务已完成！ ---"
read -n 1