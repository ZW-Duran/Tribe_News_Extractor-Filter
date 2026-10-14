import os
import csv
import json
import fitz  # PyMuPDF
import re
import time
import google.generativeai as genai
from concurrent.futures import ThreadPoolExecutor

# --- 1. 路径与 API 配置 ---
CSV_PATH = "./list.csv"
OUTPUT_CSV_PATH = "./list_coded.csv"  
OCRED_DIR = "./ocred"

API_KEY_ODD = ""   # 负责奇数行
API_KEY_EVEN = "" # 负责偶数行
CLOUD_MODEL_NAME = "gemma-4-31b-it" 

SYSTEM_INSTRUCTION = """
You are an expert sociological research assistant reading US newspaper archives. Your task is to perform quantitative coding by COUNTING the number of distinct government officials, law enforcement personnel, and legal professionals referenced in the text.

CRITICAL INSTRUCTIONS:
1. GEOGRAPHIC BOUNDARY: Count ONLY individuals located within or representing official bodies within the USA. STRICTLY EXCLUDE any officials, law enforcement, or legal personnel outside of the USA.
2. COUNTING RULE: Return an integer count >= 0 for each category. Count individual persons referenced, NOT mentions/occurrences. If an official is mentioned multiple times, count them ONCE.
3. MUTUAL EXCLUSIVITY: Each referenced individual must be assigned to EXACTLY ONE best-fitting category. Do not double-count the same person in two categories.

--- CATEGORY DEFINITIONS ---

1. "tribe_gov_officials":
   - Count of official leaders, council members, or legislative directors of Native American/Tribal governments (e.g., tribal councilmember, tribal chairman/chairwoman, tribal legislative director).
   - EXCLUSION: Do NOT count tribal police (put in law enforcement) or tribal judges/prosecutors (put in legal professionals).

2. "state_local_gov_officials":
   - Count of state, county, or municipal officials (e.g., state representative, governor, mayor, city councilor, state legislative director, county commissioner).

3. "federal_gov_officials":
   - Count of US Federal Government officials (e.g., Secretary of the Interior, US President, Congressional Representative, US Senator, federal agency heads).

4. "law_enforcement":
   - Count of police officers, sheriffs, deputies, state troopers, federal agents (FBI/BIA law enforcement), including Tribal law enforcement officers/officials.

5. "legal_professionals":
   - Count of judges, magistrates, prosecutors, district attorneys, public defenders, and lawyers/attorneys, including Tribal legal professionals and judges.

--- OUTPUT FORMAT ---
You MUST return your response strictly as a JSON object formatted as follows:

{
  "tribe_gov_officials": 0,
  "state_local_gov_officials": 0,
  "federal_gov_officials": 0,
  "law_enforcement": 0,
  "legal_professionals": 0
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
        
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.0,
                response_mime_type="application/json"
            )
        )
        
        raw_response = response.text.strip()
        if not raw_response: 
            return None
        
        try:
            # 截取纯净 JSON 字符串
            start_idx = min([raw_response.find(x) for x in ['[' , '{'] if raw_response.find(x) != -1], default=0)
            clean_text = raw_response[start_idx:]
            end_idx = max([clean_text.rfind(x) for x in [']', '}'] if clean_text.rfind(x) != -1], default=len(clean_text))
            clean_text = clean_text[:end_idx + 1]
            
            parsed_json = json.loads(clean_text)
            if isinstance(parsed_json, list) and len(parsed_json) > 0:
                parsed_json = parsed_json[0]
                
            return parsed_json
            
        except json.JSONDecodeError:
            print(f"   ⚠️ 行号 [{row_idx}] 尝试正则抢救数值数据...")
            fallback_dict = {}
            keys = [
                "tribe_gov_officials", "state_local_gov_officials", 
                "federal_gov_officials", "law_enforcement", "legal_professionals"
            ]
            for k in keys:
                val_pattern = rf'"{k}"\s*:\s*([0-9]+)'
                val_match = re.search(val_pattern, raw_response, re.IGNORECASE)
                val = int(val_match.group(1)) if val_match else 0
                fallback_dict[k] = val
            return fallback_dict
                
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

    print(f"🚀 行号 [{idx}] ──> 正在提取公职与法律人员计数: {os.path.basename(pdf_path)}")

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
        analysis_lower = {k.lower(): v for k, v in analysis.items()}
        
        # 动态扩展列数，确保能够写入到 AP 列 (索引 41)
        while len(row) <= 41:
            row.append("")
            
        def safe_get_count(key_name):
            val = analysis_lower.get(key_name.lower(), 0)
            try:
                # 确保提取出来的是整数
                if isinstance(val, dict): 
                    val = val.get("count", 0)
                return int(val)
            except:
                return 0

        # 按顺序回填到 AL ~ AP 列 (索引 37 到 41)
        row[37] = safe_get_count("tribe_gov_officials")         # AL 列
        row[38] = safe_get_count("state_local_gov_officials")   # AM 列
        row[39] = safe_get_count("federal_gov_officials")       # AN 列
        row[40] = safe_get_count("law_enforcement")             # AO 列
        row[41] = safe_get_count("legal_professionals")         # AP 列
        
        print(f"   └─ ✅ 行号 [{idx}] 数据已成功填入 AL~AP 列。")
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

    # 断点续传逻辑
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
        
        # 以 AL 列 (索引 37) 是否填有数据作为是否已经编码过的判断依据
        al_col_val = row[37].strip() if len(row) > 37 else ""
        
        if d_col_val and al_col_val == "":
            todo_tasks.append((idx, row))

    print(f"⚡️ [程序1] 过滤完毕，当前共有 {len(todo_tasks)} 行数据待处理。")

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
    print("🎉 程序 1 (公职/法律人员计数) 运行结束！")
    print(f"   - 本次成功提取并落盘: {success_count} 行")
    print("="*40)

if __name__ == "__main__":
    main()