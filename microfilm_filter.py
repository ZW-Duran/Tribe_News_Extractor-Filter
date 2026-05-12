import fitz  # PyMuPDF
import os
import re
from multiprocessing import Pool, cpu_count

# 配置路径
SOURCE_DIR = "./original"
OUTPUT_DIR = "./relevant"

# 关键词正则
KEYWORDS_RE = re.compile(
    r"\b(women|woman|girl|female|violence|murder|victim|abuse|abusive|abused|Violence|native|indigenous|indian|MMIW|MMIWG)\b", 
    re.I
)

def process_single_pdf(rel_path):
    """
    rel_path: 相对于 SOURCE_DIR 的路径，例如 'test/April 1991 Press.pdf'
    """
    source_file_path = os.path.join(SOURCE_DIR, rel_path)
    output_file_path = os.path.join(OUTPUT_DIR, rel_path)
    
    # 动态创建输出文件的父级文件夹结构
    output_subdir = os.path.dirname(output_file_path)
    os.makedirs(output_subdir, exist_ok=True)

    try:
        # 使用 context manager (with) 确保资源正确释放
        with fitz.open(source_file_path) as doc:
            matched_any = False
            
            for page in doc:
                page_text = page.get_text()
                # 检查关键词
                matches = KEYWORDS_RE.findall(page_text)
                if matches:
                    matched_any = True
                    # 去重处理，避免同一单词多次高亮重叠
                    unique_matches = set(matches)
                    for word in unique_matches:
                        insts = page.search_for(word)
                        for inst in insts:
                            annot = page.add_highlight_annot(inst)
                            # 设置颜色（cyan/青色）
                            annot.set_colors(stroke=(0, 1, 1))
                            annot.update()

            if matched_any:
                # 存入对应的 relevant 子目录下
                doc.save(output_file_path, garbage=4, deflate=True, clean=True)
                return f"[*] Match & Saved: {rel_path}"
            else:
                return f"[ ] Irrelevant: {rel_path}"

    except Exception as e:
        return f"[!] Error {rel_path}: {str(e)}"

def main():
    # 递归查找所有 PDF
    all_files = []
    if not os.path.exists(SOURCE_DIR):
        print(f"Error: {SOURCE_DIR} 不存在")
        return

    for root, _, files in os.walk(SOURCE_DIR):
        for f in files:
            if f.endswith(".pdf"):
                # 获取相对于 original 的路径，保留子文件夹结构
                rel_path = os.path.relpath(os.path.join(root, f), SOURCE_DIR)
                all_files.append(rel_path)
    
    if not all_files:
        print("未找到任何 PDF 文件。")
        return

    cores = max(1, cpu_count() - 1)
    print(f"--- Filter Processing | Cores: {cores} | Tasks: {len(all_files)} ---")
    
    # 使用 Pool 处理
    with Pool(processes=cores) as pool:
        for result in pool.imap_unordered(process_single_pdf, all_files):
            print(result)

    print("--- All tasks completed ---")

if __name__ == "__main__":
    main()