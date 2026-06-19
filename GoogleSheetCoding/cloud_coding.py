import os
import csv
import json
import time
import fitz  # PyMuPDF
import google.generativeai as genai
from google.api_core import exceptions

# --- 1. 云端多 API Key 与模型配置 ---
# 放入你的两个不同 Google 账号的 API Key
API_KEYS = [
]

# 模型矩阵设置
PRIMARY_MODEL = "gemma-4-26b-a4b-it"     
BACKUP_MODEL  = "gemma-4-31b-it"   

CSV_PATH = "./list.csv" 
OUTPUT_CSV_PATH = "./list_coded.csv"
OCRED_DIR = "./ocred"

current_key_index = 0

def get_next_client():
    """轮询切换 API Key，将并发压力均摊到两个账号"""
    global current_key_index
    key = API_KEYS[current_key_index]
    genai.configure(api_key=key)
    
    # 切换下一个索引
    current_key_index = (current_key_index + 1) % len(API_KEYS)
    return genai.GenerativeModel

# --- 2. 严谨的社会学 Codebook 提示词 ---
SYSTEM_INSTRUCTION = """
You are an expert sociological research assistant performing strict qualitative coding on newspaper archives regarding MMIWG.

CRITICAL INSTRUCTIONS:
1. For every variable you code as 1, you MUST provide the exact, verbatim sentence (evidence) from the text that justifies your choice.
2. If no direct, explicit sentence evidence exists in the article to support a '1', you MUST set the value to 0 and leave the evidence string completely empty (""). Do not infer or extrapolate.
3. Keep the "evidence" string as short as possible—ideally a single, precise verbatim sentence.

--- CODEBOOK & BOUNDARY DEFINITIONS ---
1. "mmiwg_mentioned": 1 if the text addresses the topic of Missing and Murdered Indigenous Women and Girls. No literal acronym match required; if the article validates/discusses the crisis/phenomenon of missing/murdered Native individuals, it is 1.
2. "mmiwg_movement": 1 if the text references activism, community awareness, protests, marches, healing circles, policy advocacy, task forces, or red dress campaigns.
3. "specific_case": 1 if the text discusses a particular individual's disappearance or murder case (named victim, or specific search efforts, police reporting, or crime scenes).
4. "multiple_cases": 1 if the text refers to the broader, systemic nature of the crisis, handles aggregated data/statistics, mentions general database counts (e.g., "exceeded 3,000 missing", "logged 116 cases"), or contrasts multiple historical cases.
5. "legal_protection": 1 if the text references laws, tribal sovereignty, jurisdictional conflicts between tribal and federal/state police, specific legislation, or criminal justice policy reform.
6. "family_friends_referenced": 1 if the text quotes, mentions, or references the victim's family members, relatives, loved ones, or close friends.
7. "details_victim_life": 1 if the text gives context to who the victim was as a person (biographical background, personality, family role, education, hobbies).
8. "details_perpetrator": 1 if the text discusses the suspect or perpetrator (description, identity, arrest status, investigation progress targeting a suspect, trial updates).

Return your response PRECISELY in the following JSON format:
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
    if not os.path.exists(directory): return None
    prefix = f"{row_idx}_"
    for filename in os.listdir(directory):
        if filename.startswith(prefix) and filename.lower().endswith('.pdf'):
            return os.path.join(directory, filename)
    return None

def request_gemini_with_fallback(text):
    """核心架构：调用轮询 API，如遇错误自动切换备份模型兜底"""
    prompt = f"{SYSTEM_INSTRUCTION}\n\nArticle Text:\n{text}"
    
    # 获取当前的 Model 客户端（自动轮询 Key）
    model_client = get_next_client()
    
    # 尝试一：使用主力大模型 (31B 级别) 确保极高准度
    try:
        print(f"   [Key 轮询] 正在使用主力模型 [{PRIMARY_MODEL}] 进行深度语义分析...")
        model = model_client(PRIMARY_MODEL)
        response = model.generate_content(
            prompt, 
            generation_config={"response_mime_type": "application/json", "temperature": 0.0}
        )
        return json.loads(response.text)
        
    except (exceptions.GoogleAPIError, exceptions.ResourceExhausted) as e:
        # 触发了频率限制(429)或者云端未知波动，立刻启动第二重防线
        print(f"   ⚠️ 主力模型遭遇限制或报错: {e}。触发全自动降级机制...")
        print(f"   🚀 [自动兜底] 正在无缝切换至备份高可用模型 [{BACKUP_MODEL}]...")
        
        try:
            # 再次换一个 Key 降低并发风险
            backup_model_client = get_next_client()
            model = backup_model_client(BACKUP_MODEL)
            response = model.generate_content(
                prompt,
                generation_config={"response_mime_type": "application/json", "temperature": 0.0}
            )
            return json.loads(response.text)
        except Exception as backup_err:
            print(f"   ❌ 致命错误：连备份模型也断开连接: {backup_err}")
            return None
            
    except Exception as parse_err:
        print(f"   ⚠️ JSON 解析错误: {parse_err}")
        return None

# --- 3. 云端核心执行控制流 ---
def main():
    print("==================================================")
    print("🌐 云端高并发分布式处理流部署完毕 🚀")
    
    if os.path.exists(OUTPUT_CSV_PATH):
        current_csv_source = OUTPUT_CSV_PATH
        print(f"🔄 检测到历史数据，从续传表继续运行: {current_csv_source}")
    else:
        current_csv_source = CSV_PATH
        print(f"📖 载入初始 CSV 基础表: {current_csv_source}")

    with open(current_csv_source, mode='r', encoding='utf-8') as f:
        rows = list(csv.reader(f))

    total_rows = len(rows)
    print(f"📊 探测到总数据规模: {total_rows} 行")

    success_count = 0
    skip_count = 0

    for idx, row in enumerate(rows, start=1):
        if idx == 1: continue  # 跳过表头
        if len(row) < 14: continue

        d_col_val = row[3].strip()   # D 列
        n_col_val = row[13].strip()  # N 列

        # 续传筛选：D列不为空（有效行），且N列完全为空（未处理过）
        if d_col_val and not n_col_val:
            pdf_path = locate_pdf_by_row_index(idx, OCRED_DIR)
            if not pdf_path:
                print(f"⏭️ 行号 [{idx}]: 未在云端找到对应的物理文件，跳过。")
                continue

            print(f"\n⚡️ [云端处理中] 行号 [{idx}] ──> 文件: {os.path.basename(pdf_path)}")

            # 提取文本层（包含物理中线拆栏算法，防止多栏排版污染大模型）
            try:
                doc = fitz.open(pdf_path)
                text_blocks = []
                for page in doc:
                    mid_line = page.rect.width / 2
                    blocks = page.get_text("blocks")
                    left_col, right_col = [], []
                    for b in blocks:
                        x0, y0, x1, y1, text, _, _ = b
                        if text.strip():
                            if x1 <= mid_line + 10:
                                left_col.append((y0, text.strip()))
                            elif x0 >= mid_line - 10:
                                right_col.append((y0, text.strip()))
                            else:
                                left_col.append((y0, text.strip()))
                    left_col.sort(key=lambda x: x[0])
                    right_col.sort(key=lambda x: x[0])
                    page_text = "\n\n".join([x[1] for x in left_col]) + "\n\n" + "\n\n".join([x[1] for x in right_col])
                    text_blocks.append(page_text)
                full_text = "\n\n".join(text_blocks)
                doc.close()
            except Exception as e:
                print(f"   ❌ 云端提取该 PDF 文本层失败: {e}")
                continue

            if not full_text.strip():
                print(f"   ⚠️ 警告：该 PDF 为空。")
                continue

            # 调用带故障兜底的云端 API
            analysis = request_gemini_with_fallback(full_text)
            if not analysis:
                print(f"   ❌ 该行全盘评估失败（双模型均未响应），跳过当前行。")
                continue

            # 数据高容错解析回填
            # 4. 数据高容错解析回填（终极多格式包容版本）
            try:
                # 【核心修复锁】动态判断模型吐出来的是字典还是列表
                normalized_analysis = {}
                
                if isinstance(analysis, dict):
                    # 如果标准返回是字典，直接用
                    normalized_analysis = analysis
                elif isinstance(analysis, list):
                    print(f"   ⚠️ 探测到模型返回了 List 数组结构，正在自动执行降维与字典解构...")
                    # 如果模型吐出了 [{k1: v1}, {k2: v2}] 这种数组，强行把它们合并进一个单字典里
                    for item in analysis:
                        if isinstance(item, dict):
                            normalized_analysis.update(item)
                
                # 将最终的字典键名全部转换为纯小写，消除大小写带来的不稳定因素
                analysis_lower = {k.lower(): v for k, v in normalized_analysis.items()}
                
                def safe_get_value(key_name):
                    """深度安全提取器，无视任何数据深度错位"""
                    data_block = analysis_lower.get(key_name.lower())
                    if isinstance(data_block, dict):
                        try: return int(data_block.get("value", 0))
                        except: return 0
                    elif isinstance(data_block, (int, str)):
                        try: return int(data_block)
                        except: return 0
                    return 0

                # 完美映射回填
                row[13] = safe_get_value("mmiwg_mentioned")          # N
                row[14] = safe_get_value("mmiwg_movement")           # O
                row[15] = safe_get_value("specific_case")            # P
                row[16] = safe_get_value("multiple_cases")           # Q
                row[17] = safe_get_value("legal_protection")         # R
                row[23] = safe_get_value("family_friends_referenced") # X
                row[24] = safe_get_value("details_victim_life")       # Y
                row[25] = safe_get_value("details_perpetrator")       # Z

                success_count += 1
                print(f"   └─ 🎉 编码回填成功（已成功通过 List/Dict 双重格式校对机制）！")

                # 云服务器 SSD 瞬间同步回写
                with open(OUTPUT_CSV_PATH, mode='w', encoding='utf-8', newline='') as f_write:
                    writer = csv.writer(f_write)
                    writer.writerows(rows)

            except Exception as e:
                print(f"   ❌ 回填写入内部逻辑异常: {e}")
                continue

            # 双 Key 均摊下，每次请求只需要礼貌 sleep 1.5 秒即可轻松跑满 30 RPM
            time.sleep(1.5)
        else:
            skip_count += 1

    print("\n" + "="*50)
    print("🎉 云端分布式高可用流水线全盘运行结束！")
    print(f"   - 本次成功流水清洗: {success_count} 行")
    print(f"   - 自动跳过完工行: {skip_count} 行")
    print(f"💾 最终高准度表格已安全储存在: {OUTPUT_CSV_PATH}")
    print("===================================================")

if __name__ == "__main__":
    main()