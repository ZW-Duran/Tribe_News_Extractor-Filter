#!/bin/bash
cd "$(dirname "$0")"

# 1. 核心配置
PYTHON_EXEC="/opt/homebrew/Caskroom/miniforge/base/bin/python3"
SITE_PACKAGES="/opt/homebrew/Caskroom/miniforge/base/lib/python3.13/site-packages"
UPLOAD_DIR="./original"
OUTPUT_DIR="./ocred"
THREADS=4 

mkdir -p "$UPLOAD_DIR" "$OUTPUT_DIR"

# 2. 生成任务列表
find "$UPLOAD_DIR" -maxdepth 1 -name "*.pdf" -exec basename {} \; > all_list.txt
touch done_list.txt
ls -1 "$OUTPUT_DIR" 2>/dev/null | sed 's/\.txt$//' > done_list.txt 
grep -vxFf done_list.txt all_list.txt > pending_tasks.txt

if [ ! -s pending_tasks.txt ]; then
    echo "没有待处理文件。"
    rm -f all_list.txt done_list.txt pending_tasks.txt
    exit 0
fi

echo "启动多线程 Surya-OCR 0.20+ 终极清洗任务 (并发: $THREADS)..."

# 3. 使用 Parallel 并行执行
cat pending_tasks.txt | parallel --jobs "$THREADS" --progress '
    export PYTHONPATH="'"$SITE_PACKAGES"':$PYTHONPATH"
    '"$PYTHON_EXEC"' -c "
import sys, os
sys.path.insert(0, \"'"$SITE_PACKAGES"'\")

from surya.layout import parse_layout
from surya.recognition import RecognitionPredictor
from pdf2image import convert_from_path
from PIL import Image

# 实例化识别预测器
rec_predictor = RecognitionPredictor()

def process(filename):
    input_path = os.path.join(\"'"$UPLOAD_DIR"'\", filename)
    output_path = os.path.join(\"'"$OUTPUT_DIR"'\", os.path.splitext(filename)[0] + \".txt\")
    
    # 获取当前进程 ID 用于生成唯一的临时图片名，防止并发冲突
    pid = os.getpid()
    
    try:
        images = convert_from_path(input_path)
        full_text = []
        
        for idx, img in enumerate(images):
            # 将 PIL 对象保存为临时本地文件，彻底解决 'PpmImageFile' 对象的类型冲突
            temp_img_path = f\"temp_{pid}_{idx}.png\"
            img.save(temp_img_path)
            
            try:
                # 1. 传入临时文件路径给新版 API
                layout_result = parse_layout(temp_img_path)
                
                # 2. 过滤多栏排版中的正文和标题
                boxes = [b for b in layout_result.bboxes if b.label in [\"Text\", \"Title\"]]
                
                if not boxes:
                    continue
                    
                # 3. 识别器同样接受重新用 PIL 打开的干净图像对象或路径
                # 经过测试，包装在标准 PIL.Image 里的对象或者路径均可，这里使用重新打开的干净对象
                with Image.open(temp_img_path) as clean_img:
                    predictions = rec_predictor([clean_img], [[\"en\"]], [boxes])[0]
                    page_text = \"\n\".join([p.text for p in predictions.text_lines])
                    full_text.append(page_text)
            finally:
                # 无论成功失败，立刻擦除临时图片，不占硬盘空间
                if os.path.exists(temp_img_path):
                    os.remove(temp_img_path)
        
        with open(output_path, \"w\", encoding=\"utf-8\") as f:
            f.write(\"\n\n\".join(full_text))
            
    except Exception as e:
        print(f\"处理失败 {filename}: {e}\")

process(\"{}\")
"
'

# 4. 清理临时文件
rm -f all_list.txt done_list.txt pending_tasks.txt
echo "--- 全部任务已完成！ ---"