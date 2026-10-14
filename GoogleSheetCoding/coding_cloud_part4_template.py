import os
import csv
import json
import fitz  # PyMuPDF
import re
import google.generativeai as genai
from concurrent.futures import ThreadPoolExecutor

# --- 1. 路径与 API 配置 ---
CSV_PATH = "./list.csv"
OUTPUT_CSV_PATH = "./list_coded.csv"  
OCRED_DIR = "./ocred"

API_KEY_ODD = ""   # 负责奇数行
API_KEY_EVEN = "" # 负责偶数行
CLOUD_MODEL_NAME = "gemma-4-31b-it" 

# --- 2. 程序 4 专属 System Prompt (受害者明细与交叉汇总) ---
SYSTEM_INSTRUCTION = """
You are an expert sociological research assistant reading US newspaper archives. Your task is to perform qualitative and quantitative coding for ALL VICTIMS referenced in the text.

CRITICAL INSTRUCTIONS:
1. GEOGRAPHIC BOUNDARY: Process ONLY victims within the USA. EXCLUDE any victims outside of the USA.
2. INDIVIDUALIZATION: Extract every distinct victim mentioned.
3. STATUS CATEGORIES:
   - "murdered_or_missing": Victim was murdered, killed, disappeared, or is currently missing.
   - "general_violence": Victim suffered non-fatal violence (e.g., physical assault, domestic violence, abuse, kidnapping survivor) but is NOT murdered or missing.
4. GENDER CATEGORIES: "male", "female", "nonbinary", "unknown".
5. RACE / TRIBAL AFFILIATION: Extract exact race/ethnicity and tribal affiliation if mentioned (e.g., "Navajo Nation", "Cherokee"). Use "Unknown" if not mentioned.

--- OUTPUT FORMAT ---
1. Step-by-step list each victim identified, verifying their status, gender, race, tribal affiliation, and age.
2. At the VERY END, output EXACTLY ONE final JSON object containing both the list of individual victims and the summary count matrix.

Final JSON format:
{
  "victims": [
    {
      "name": "Victim Name or 'Unknown'",
      "race": "Victim Race or 'Unknown'",
      "tribal_affiliation": "Tribal Affiliation or 'Unknown'",
      "age": "Age or 'Unknown'",
      "gender": "female", 
      "status": "murdered_or_missing" 
    }
  ],
  "counts": {
    "mm_id_male": 0,
    "mm_id_female": 0,
    "mm_id_nonbinary": 0,
    "mm_gender_non_id": 0,
    "gv_id_male": 0,
    "gv_id_female": 0,
    "gv_id_nonbinary": 0,
    "gv_gender_non_id": 0
  }
}
"""

def locate_pdf_by_row_index(row_idx, directory):
    if not os.path.exists(directory): 
        return None
    target_filename = f"{str(row_idx).zfill(3)}.pdf"
    full_path = os.path.join(directory, target_filename)
    if os.path.exists(full_path):
        return full_path
    return None

def analyze_text_with_gemini(text, row_idx):
    prompt = f"{SYSTEM_INSTRUCTION}\n\nArticle Text:\n{text}"
    current_api_key = API_KEY_ODD if row_idx % 2 != 0 else API_KEY_EVEN
    
    try:
        genai.configure(api_key=current_api_key)
        model = genai.GenerativeModel(CLOUD_MODEL_NAME)
        
        response = model.generate_content(prompt)
        raw_response = response.text.strip()
        if not raw_response: 
            return None
        
        # 🛠️ 精准倒序捕获最后一个包含 "victims" 和 "counts" 的 JSON 块
        try:
            json_blocks = re.findall(r'\{[^{}]*"victims"[^{}]*\}', raw_response, re.DOTALL)
            if json_blocks:
                return json.loads(json_blocks[-1])
            else:
                # 应对可能嵌套较深的完整 JSON 正则匹配
                match = re.search(r'(\{.*"victims".*"counts".*\})', raw_response, re.DOTALL)
                if match:
                    return json.loads(match.group(1))
                return None
                
        except Exception as parse_e:
            print(f"   ⚠️ 行号 [{row_idx}] 受害者 JSON 解析报错: {parse_e}")
            return None
                
    except Exception as e:
        print(f"   ⚠️ Cloud API 通道报错 (行号 {row_idx}): {e}")
        return None

# --- 3. 核心异步线程工作函数 ---
def process_single_row(task):
    idx, row = task
    pdf_path = locate_pdf_by_row_index(idx, OCRED_DIR)
    
    if not pdf_path:
        print(f"⏭️ 行号 [{idx}]: 未找到对应的 OCR 文件，跳过。")
        return idx, row, False

    print(f"🚀 行号 [{idx}] ──> 正在提取受害者明细与交叉统计: {os.path.basename(pdf_path)}")

    try:
        doc = fitz.open(pdf_path)
        text_blocks = []
        for page in doc:
            blocks = page.get_text("blocks")
            for b in blocks:
                if b[4].strip():
                    text_blocks.append(b[4].strip())
        full_text = "\n\n".join(text_blocks)
        doc.close()
    except Exception as e:
        print(f"   ❌ 行号 [{idx}] 读取 PDF 失败: {e}")
        return idx, row, False

    if not full_text.strip():
        return idx, row, False

    analysis = analyze_text_with_gemini(full_text, idx)
    if not analysis:
        return idx, row, False

    try:
        counts = analysis.get("counts", {})
        victims = analysis.get("victims", [])
        
        # 1. 填入 AW ~ BD 列 (索引 48 到 55) 的汇总计数
        def safe_get(c_key):
            try: return int(counts.get(c_key, 0))
            except: return 0

        # 确保行数组长度至少覆盖到 BD 列 (55)
        while len(row) <= 55:
            row.append("")

        row[48] = safe_get("mm_id_male")          # AW
        row[49] = safe_get("mm_id_female")        # AX
        row[50] = safe_get("mm_id_nonbinary")      # AY
        row[51] = safe_get("mm_gender_non_id")    # AZ
        row[52] = safe_get("gv_id_male")          # BA
        row[53] = safe_get("gv_id_female")        # BB
        row[54] = safe_get("gv_id_nonbinary")      # BC
        row[55] = safe_get("gv_gender_non_id")    # BD

        # 2. 从 BE 列 (索引 56) 开始，每 6 列循环填入受害者明细
        base_offset = 56 # BE 列的索引
        
        for i, v in enumerate(victims):
            v_start = base_offset + (i * 6)
            
            # 动态扩展列长以适配多个受害者
            while len(row) < v_start + 6:
                row.append("")
                
            row[v_start]     = str(v.get("name", ""))               # BE, BK, BQ...
            row[v_start + 1] = str(v.get("race", ""))               # BF, BL, BR...
            row[v_start + 2] = str(v.get("tribal_affiliation", ""))# BG, BM, BS...
            row[v_start + 3] = str(v.get("age", ""))                # BH, BN, BT...
            row[v_start + 4] = str(v.get("gender", ""))             # BI, BO, BU...
            row[v_start + 5] = str(v.get("status", ""))             # BJ, BP, BV...

        print(f"   └─ ✅ 行号 [{idx}] 已提取 {len(victims)} 名受害者明细，回填 AW~BD 汇总与 BE+ 明细列。")
        return idx, row, True
        
    except Exception as e:
        print(f"   ❌ 行号 [{idx}] 数据回填错误: {e}")
        return idx, row, False

# --- 4. 主控制流 ---
def main():
    try:
        genai.configure(api_key=API_KEY_ODD)
    except Exception as e:
        print(f"❌ SDK 初始化失败，请检查 API_KEY_ODD: {e}")
        return

    if os.path.exists(OUTPUT_CSV_PATH):
        current_csv_source = OUTPUT_CSV_PATH
        print(f"🔄 检测到历史数据，自动加载续传表: {current_csv_source}")
    else:
        current_csv_source = CSV_PATH
        print(f"📖 未检测到历史缓存，加载初始基础表: {current_csv_source}")

    with open(current_csv_source, mode='r', encoding='utf-8', newline='') as f:
        rows = list(csv.reader(f))

    todo_tasks = []
    for idx, row in enumerate(rows, start=1):
        if idx == 1 or len(row) < 4:
            continue
            
        d_col_val = row[3].strip() if len(row) > 3 else ""
        
        # 以 AW 列 (索引 48) 是否填有数据作为断点续传判断依据
        aw_col_val = row[48].strip() if len(row) > 48 else ""
        
        if d_col_val and aw_col_val == "":
            todo_tasks.append((idx, row))

    print(f"⚡️ [程序4] 过滤完毕，当前共有 {len(todo_tasks)} 行数据待处理。")

    success_count = 0
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = executor.map(process_single_row, todo_tasks)
        
        for idx, updated_row, is_success in results:
            if is_success:
                success_count += 1
                with open(OUTPUT_CSV_PATH, mode='w', encoding='utf-8', newline='') as f_write:
                    writer = csv.writer(f_write, quoting=csv.QUOTE_MINIMAL)
                    writer.writerows(rows)

    print("\n" + "="*40)
    print("🎉 程序 4 (受害者明细与交叉汇总) 运行结束！")
    print(f"   - 本次成功提取并落盘: {success_count} 行")
    print("="*40)

if __name__ == "__main__":
    main()