import os
import csv
import json
import fitz  # PyMuPDF
import ollama
import re

# --- 1. 路径与本地 Ollama 配置 ---
CSV_PATH = "./list.csv"
OUTPUT_CSV_PATH = "./list_coded.csv"  # 实时更新与续传的目标文件
OCRED_DIR = "./ocred"
LOCAL_MODEL_NAME = "e4b" 

# --- 2. 强约束 Prompt 与期望的 JSON 结构 ---
SYSTEM_INSTRUCTION = """
You are an expert sociological research assistant reading newspaper archives. Your task is to perform qualitative text coding to identify specific semantic themes within the provided article.

CRITICAL INSTRUCTIONS:
1. For every variable you code as 1, you MUST provide the exact, verbatim sentence (evidence) from the text that justifies your choice.
2. If the text does not implicitly or explicitly discuss the theme, set the value to 0 and leave the evidence string completely empty ("").
3. Keep the "evidence" string as short as possible—a single, precise verbatim sentence is preferred.

--- CODEBOOK & BOUNDARY DEFINITIONS ---
1. "mmiwg_mentioned": 1 if the text addresses the topic of Missing and Murdered Indigenous Women and Girls. This does NOT require a literal acronym match; if the article is clearly validating or discussing the crisis/phenomenon of missing/murdered Native individuals, it counts as 1.
2. "mmiwg_movement": 1 if the text references activism, community awareness, protests, marches, healing circles, policy advocacy, task forces, or red dress campaigns dedicated to addressing this crisis.
3. "specific_case": 1 if the text discusses a particular individual's disappearance or murder case. This includes anytime a specific victim is named, or specific incident details (like search efforts, police reporting, or crime scenes) are described.
4. "multiple_cases": 1 if the text refers to the broader, systemic nature of the crisis, handles aggregated data/statistics, mentions general database counts (e.g., "exceeded 3,000 missing", "logged 116 cases"), or contrasts multiple historical cases within the same reporting.
5. "legal_protection": 1 if the text references laws, tribal sovereignty, jurisdictional conflicts between tribal and federal/state police, specific legislation (like Savanna's Act), or criminal justice policy reform.
6. "family_friends_referenced": 1 if the text quotes, mentions, or references the victim's family members, relatives, loved ones, or close friends speaking out or being affected.
7. "details_victim_life": 1 if the text gives context to who the victim was as a person—their biographical background, personality, family role, education, hobbies, or life story before the tragedy.
8. "details_perpetrator": 1 if the text discusses the suspect, person of interest, or perpetrator. This includes references to their description, identity, arrest, investigation progress targeting a suspect, trial updates, or court proceedings.

You must return your response PRECISELY in the following JSON format:
{
  "mmiwg_mentioned": {"value": 0, "evidence": ""},
  "mmiwg_movement": {"value": 0, "evidence": ""},
  "specific_case": {"value": 0, "evidence": ""},
  "multiple_cases": {"value": 0, "evidence": ""},
  "legal_protection": {"value": 0, "evidence": ""},
  "family_friends_referenced": {"value": 0, "evidence": ""},
  "details_victim_life": {"value": 0, "evidence": ""},
  "details_perpetrator": {"value": 0, "evidence": ""}
}
"""

def locate_pdf_by_row_index(row_idx, directory):
    """根据 CSV 的绝对行号，去文件夹中寻找形如 'row_idx_*.pdf' 的文件"""
    if not os.path.exists(directory):
        return None
    
    prefix = f"{row_idx}_"
    for filename in os.listdir(directory):
        if filename.startswith(prefix) and filename.lower().endswith('.pdf'):
            return os.path.join(directory, filename)
    return None

def analyze_text_with_ollama(text):
    """调用本地 Ollama 模型，强制输出 JSON，并具备自愈修复脏 JSON 字符串的能力"""
    prompt = f"{SYSTEM_INSTRUCTION}\n\nArticle Text:\n{text}"
    
    try:
        response = ollama.generate(
            model=LOCAL_MODEL_NAME,
            prompt=prompt,
            format="json", 
            options={
                "temperature": 0.0,  
                "num_ctx": 16384     
            }
        )
        
        raw_response = response['response'].strip()
        if not raw_response: return None
            
        try:
            return json.loads(raw_response)
        except json.JSONDecodeError:
            try:
                def clean_evidence(match):
                    content = match.group(1)
                    fixed_content = content.replace('"', "'")
                    return f'"evidence": "{fixed_content}"'
                repaired_response = re.sub(r'"evidence"\s*:\s*"(.*?)"', clean_evidence, raw_response, flags=re.DOTALL)
                return json.loads(repaired_response)
            except:
                fallback_dict = {}
                keys = ["mmiwg_mentioned", "mmiwg_movement", "specific_case", "multiple_cases", 
                        "legal_protection", "family_friends_referenced", "details_victim_life", "details_perpetrator"]
                for k in keys:
                    match = re.search(r'"' + k + r'"\s*:\s*\{\s*"value"\s*:\s*([01])', raw_response, re.IGNORECASE)
                    if match:
                        fallback_dict[k] = {"value": int(match.group(1)), "evidence": "Extracted via regex fallback"}
                    else:
                        fallback_dict[k] = {"value": 0, "evidence": ""}
                return fallback_dict
    except Exception as e:
        print(f"   ⚠️ 本地 Ollama 致命报错: {e}")
        return None

# --- 3. 主执行逻辑 ---
def main():
    # 【断点续传逻辑 1】动态检测数据源
    if os.path.exists(OUTPUT_CSV_PATH):
        current_csv_source = OUTPUT_CSV_PATH
        print(f"🔄 检测到上次未完成的进度，自动加载续传表: {current_csv_source}")
    else:
        current_csv_source = CSV_PATH
        print(f"📖 未检测到历史缓存，加载初始基础表: {current_csv_source}")

    # 严格指定 newline='' 读入，彻底锁定换行格式
    with open(current_csv_source, mode='r', encoding='utf-8', newline='') as f:
        reader = csv.reader(f)
        rows = list(reader)  # 保持 100% 原始表格物理结构完整，不在这里剔除任何行

    total_rows = len(rows)
    print(f"📊 探测到大盘物理总行数: {total_rows} 行（含表头）")

    success_count = 0
    skip_count = 0

    # 从第二行开始遍历 (idx 完美对应 Excel/Sheets 左侧的真实物理行号)
    for idx, row in enumerate(rows, start=1):
        if idx == 1:
            continue  # 跳过表头

        # 核心防御：如果这一行彻底为空，或者是格式损坏的残缺行，不满足处理资格，直接安全软跳过（保留行结构）
        if len(row) < 14:
            skip_count += 1
            continue

        d_col_val = row[3].strip()   # D 列 (判断标准)
        n_col_val = row[13].strip()  # N 列 (第一个粉色列)

        # 【核心判断逻辑】只有 D 列有内容，且 N 列为空的行才执行推理
        if d_col_val and not n_col_val:
            pdf_path = locate_pdf_by_row_index(idx, OCRED_DIR)
            
            if not pdf_path:
                print(f"⏭️ 行号 [{idx}]: 未找到对应的 OCR 文件，跳过。")
                continue

            print(f"🚀 [本地推理中] 行号 [{idx}] ──> 匹配文件: {os.path.basename(pdf_path)}")

            # 从 PDF 中使用 Blocks 模式提取文本
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
                print(f"   ❌ 读取 PDF 文本失败: {e}")
                continue

            if not full_text.strip():
                print(f"   ⚠️ 警告：该 PDF 提取出的文本为空，跳过。")
                continue

            # 调用大模型评估
            analysis = analyze_text_with_ollama(full_text)
            if not analysis:
                print(f"   ❌ 获取本地模型分析结果失败，跳过本行。")
                continue

            # 原地精准更新当前行的数据，绝不干扰、增删、或移位其他行
            try:
                analysis_lower = {k.lower(): v for k, v in analysis.items()}
                
                def safe_get_value(key_name):
                    data_block = analysis_lower.get(key_name.lower())
                    if isinstance(data_block, dict):
                        try: return int(data_block.get("value", 0))
                        except: return 0
                    elif isinstance(data_block, (int, str)):
                        try: return int(data_block)
                        except: return 0
                    return 0
            
                row[13] = safe_get_value("mmiwg_mentioned")          # N 列
                row[14] = safe_get_value("mmiwg_movement")           # O 列
                row[15] = safe_get_value("specific_case")            # P 列
                row[16] = safe_get_value("multiple_cases")           # Q 列
                row[17] = safe_get_value("legal_protection")         # R 列
                row[23] = safe_get_value("family_friends_referenced") # X 列
                row[24] = safe_get_value("details_victim_life")       # Y 列
                row[25] = safe_get_value("details_perpetrator")       # Z 列
                
                success_count += 1
                print(f"   └─ ✅ 真实第 [{idx}] 行语义数据原地回填成功，正在保存...")
                
                # 【断点续传与持久化】实时整盘写回，由于 rows 的长度和顺序自始至终未变，无关行完美保留
                with open(OUTPUT_CSV_PATH, mode='w', encoding='utf-8', newline='') as f_write:
                    writer = csv.writer(f_write)
                    writer.writerows(rows)
                
            except Exception as e:
                print(f"   ❌ 回填发生未知错误: {e}，跳过该行。")
                continue
        else:
            # 如果 D 列为空，或者该行已经处理过，直接进入 soft_skip，不做任何更改，原样保留
            skip_count += 1

    print("\n" + "="*40)
    print("🎉 本地全量数据自动化筛查与回填全部结束！")
    print(f"   - 本次运行成功原地编码: {success_count} 行数据")
    print(f"   - 自动跳过（包含D列无内容行与历史已完工行）: {skip_count} 行数据")
    print(f"💾 最终物理对齐的表格已安全保存在: {OUTPUT_CSV_PATH}")
    print("="*40)

if __name__ == "__main__":
    main()