#!/bin/bash
cd "$(dirname "$0")"
export MAX_IMAGE_PIXELS=1000000000
UPLOAD_DIR="./original"
OCRED_DIR="./ocred"
THREADS=2

# 1. 确保目录存在
mkdir -p "$UPLOAD_DIR" "$OCRED_DIR"

# 2. 生成文件列表
cd "$UPLOAD_DIR" && all_files=$(ls -1 *.pdf 2>/dev/null)
cd - > /dev/null

cd "$OCRED_DIR" && done_files=$(ls -1 *.pdf 2>/dev/null)
cd - > /dev/null

# 3. 计算数量
TOTAL=$(echo "$all_files" | wc -l | tr -d ' ')
[ -z "$all_files" ] && TOTAL=0

# 4. 生成待处理列表
echo "$all_files" > all_list.txt
echo "$done_files" > done_list.txt
grep -vxFf done_list.txt all_list.txt > pending_tasks.txt

PENDING=$(wc -l < pending_tasks.txt | tr -d ' ')

echo "=========================================="
echo "总文件数 (All): $TOTAL"
echo "待处理 (Pending): $PENDING"
echo "=========================================="

if [ "$PENDING" -eq 0 ]; then
    echo "没有待处理文件。"
    rm -f all_list.txt done_list.txt pending_tasks.txt
    exit 0
fi

echo "正在启动并行处理..."

# 5. 执行任务 (已移除 macOS 的 /opt/homebrew/bin/ 前缀)
cat pending_tasks.txt | parallel --jobs "$THREADS" --keep-order --progress '
    file="'"$UPLOAD_DIR"'/{}"
    output_file="'"$OCRED_DIR"'/{}"
    temp_file="'"$OCRED_DIR"'/temp_{}"

    gs -sDEVICE=pdfwrite -dCompatibilityLevel=1.4 -dPDFSETTINGS=/printer \
       -dColorImageResolution=300 -dGrayImageResolution=300 -dMonoImageResolution=300 \
       -dNOPAUSE -dBATCH -sOutputFile="$temp_file" "$file" > /dev/null 2>&1
    
    ocrmypdf --force-ocr --clean "$temp_file" "$output_file" > /dev/null 2>&1
    
    rm -f "$temp_file"
    echo "处理完成: {}"
'

echo "正在验证所有任务结果..."

# 重新核对数量
FINAL_DONE=$(ls -1 "$OCRED_DIR"/*.pdf 2>/dev/null | wc -l | tr -d ' ')

if [ "$FINAL_DONE" -lt "$TOTAL" ]; then
    echo "⚠️ 警告: 处理任务完成后，发现生成的 PDF 数量 ($FINAL_DONE) 小于原始总数 ($TOTAL)！"
    echo "请检查以下未生成的任务:"
    ls -1 "$UPLOAD_DIR"/*.pdf | xargs -n1 basename > all_list.txt
    ls -1 "$OCRED_DIR"/*.pdf | xargs -n1 basename > done_list.txt
    comm -23 all_list.txt done_list.txt
else
    echo "✅ 所有任务验证通过！"
fi

rm -f all_list.txt done_list.txt pending_tasks.txt
echo "--- 全部任务已完成！ ---"