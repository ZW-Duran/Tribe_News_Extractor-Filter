import fitz
import os
import re
from multiprocessing import Pool, cpu_count

# setup
source_dir = "./original"
output_dir = "./relevant"
os.makedirs(output_dir, exist_ok=True)

# filter (保持不变)
logic_patterns = {
    "gender": re.compile(r"(women|woman|girl|female)", re.I),
    "violence": re.compile(r"(violence|murder|victim)", re.I),
    "native": re.compile(r"(native|native american|indigenous|indian)", re.I),
    "mmiw": re.compile(r"(MMIW|MMIWG|Missing and Murdered Indigenous Women)", re.I)
}

highlight_words = [
    "women", "woman", "girl", "female", 
    "violence", "murder", "victim", 
    "native", "native american", "indigenous", "indian",
    "MMIW", "MMIWG", "Missing and Murdered Indigenous Women"
]

def process_single_pdf(filename):
    """
    filename 此时是相对路径，例如 "2002/document.pdf"
    """
    if not filename.endswith(".pdf"): 
        return f"[ ] Skip: {filename}"
    
    file_path = os.path.join(source_dir, filename)
    output_path = os.path.join(output_dir, filename)
    
    # --- 关键改进：自动创建输出文件的父目录 ---
    output_subdir = os.path.dirname(output_path)
    if not os.path.exists(output_subdir):
        os.makedirs(output_subdir, exist_ok=True)
    # ---------------------------------------

    try:
        with fitz.open(file_path) as doc:
            # 提取文本进行逻辑判断
            full_text = "".join([page.get_text() for page in doc])
            
            has_gender = logic_patterns["gender"].search(full_text)
            has_violence = logic_patterns["violence"].search(full_text)
            has_native = logic_patterns["native"].search(full_text)
            has_mmiw = logic_patterns["mmiw"].search(full_text)

            if (has_gender and has_violence and has_native) or has_mmiw:
                # 重新处理并高亮
                temp_pdf = doc.tobytes(clean=True, deflate=True, garbage=4)
                with fitz.open("pdf", temp_pdf) as clean_doc:
                    for page in clean_doc:
                        for word in highlight_words:
                            for inst in page.search_for(word):
                                annot = page.add_highlight_annot(inst)
                                annot.set_colors(stroke=(0, 1, 1))
                                annot.update()
                    
                    clean_doc.save(output_path, garbage=4, deflate=True, clean=True)
                return f"[*] Match: {filename}"
            else:
                return f"[ ] Irrelevant: {filename}"
    except Exception as e:
        return f"[!] Error {filename}: {e}"

if __name__ == "__main__":
    all_files = []
    # 递归遍历所有子文件夹
    for root, dirs, files in os.walk(source_dir):
        for f in files:
            if f.endswith(".pdf"):
                # 获取相对于 source_dir 的路径，保持目录结构
                rel_path = os.path.relpath(os.path.join(root, f), source_dir)
                all_files.append(rel_path)
    
    cores = max(1, cpu_count()-1)
    print(f"--- MultiProcess | Cores: {cores} | Tasks: {len(all_files)} ---")
    
    # 使用进程池处理
    with Pool(processes=cores) as pool:
        for result in pool.imap_unordered(process_single_pdf, all_files):
            print(result)

    print("--- All tasks completed ---")