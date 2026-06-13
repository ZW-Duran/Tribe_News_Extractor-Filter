import streamlit as st
import spacy
import json
import ollama
import re
import pandas as pd

# --- 1. 初始化配置与页面设置 ---
st.set_page_config(page_title="Text Semantic Coder & Highlighter", layout="wide")

@st.cache_resource
def load_model():
    # 保持原有的 spaCy 预训练模型
    return spacy.load("en_core_web_trf")

nlp = load_model()

LOCAL_MODEL_NAME = "e4b"  # 继承自你的本地 Ollama 模型配置

# --- 2. 强约束 Prompt (移除了对 PDF 的表述，完美适配纯文本) ---
SYSTEM_INSTRUCTION = """
You are an expert sociological research assistant reading newspaper archives. Your task is to perform qualitative text coding to identify specific semantic themes within the provided article.

CRITICAL INSTRUCTIONS:
1. For every variable you code as 1, you MUST provide the exact, verbatim sentence (evidence) from the text that justifies your choice.
2. If the text does not implicitly or explicitly discuss the theme, set the value to 0 and leave the evidence string completely empty ("").
3. Keep the "evidence" string as short as possible—a single, precise verbatim sentence is preferred.

--- CODEBOOK & BOUNDARY DEFINITIONS ---
1. "mmiwg_mentioned": 1 if the text addresses the topic of Missing and Murdered Indigenous Women and Girls.
2. "mmiwg_movement": 1 if the text references activism, community awareness, protests, marches, etc.
3. "specific_case": 1 if the text discusses a particular individual's disappearance or murder case.
4. "multiple_cases": 1 if the text refers to the broader, systemic nature of the crisis or aggregates data.
5. "legal_protection": 1 if the text references laws, tribal sovereignty, jurisdictional conflicts, etc.
6. "family_friends_referenced": 1 if the text quotes or references the victim's family members/friends.
7. "details_victim_life": 1 if the text gives biographical context to who the victim was.
8. "details_perpetrator": 1 if the text discusses the suspect, perpetrator, or court proceedings.

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

# --- 3. 核心大模型分析与流修复函数 ---
def analyze_text_with_ollama(text):
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
            # 引入你原脚本中优秀的边界正则修复逻辑
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
        st.error(f"Ollama Call Error: {e}")
        return None

# --- 4. 纯文本 HTML 高亮渲染核心引擎 ---
def generate_html_highlighter(text, rules):
    """利用 spaCy 提取实体，并将其转换为内联 CSS 高亮 HTML"""
    doc = nlp(text)
    
    # 构建快速匹配字典映射
    active_rules = {}
    for r in rules:
        if r['label'].strip():
            active_rules[r['label'].strip().upper()] = r['color']

    # 收集需要高亮的实体区间，并进行防重叠过滤
    spans_to_highlight = []
    for ent in doc.ents:
        if ent.label_ in active_rules:
            spans_to_highlight.append((ent.start_char, ent.end_char, ent.label_, ent.text))
            
    # 按起始位置倒序排序（从后往前替换，避免破坏前半段的索引位置）
    spans_to_highlight = sorted(spans_to_highlight, key=lambda x: x[0], reverse=True)
    
    html_text = text
    for start, end, label, ent_text in spans_to_highlight:
        color_rgb = active_rules[label]
        # 将用户输入的 "(1, 0, 0)" 字符串转换为标准的 css rgba 格式，增加 0.3 的不透明度，提升阅读感
        try:
            rgb_tuple = eval(color_rgb)
            css_color = f"rgba({int(rgb_tuple[0]*255)}, {int(rgb_tuple[1]*255)}, {int(rgb_tuple[2]*255)}, 0.3)"
            border_color = f"rgb({int(rgb_tuple[0]*255)}, {int(rgb_tuple[1]*255)}, {int(rgb_tuple[2]*255)})"
        except:
            css_color = "rgba(255, 255, 0, 0.3)" # 备用黄色
            border_color = "rgb(255, 255, 0)"

        highlighted_node = (
            f'<mark style="background-color: {css_color}; '
            f'border-bottom: 2px solid {border_color}; '
            f'padding: 2px 4px; margin: 0 2px; border-radius: 4px; cursor: help;" '
            f'title="{label}">'
            f'{html_text[start:end]}<span style="font-size: 0.7em; color: gray; margin-left: 4px;">[{label}]</span>'
            f'</mark>'
        )
        html_text = html_text[:start] + highlighted_node + html_text[end:]
        
    # 保留换行符格式
    html_text = html_text.replace("\n", "<br>")
    
    # 根据用户请求，为背景框设置反转色，以适应深色模式
    # 这里将背景设为较浅的灰色，文字设为较深的灰色，以确保在深色模式下清晰可见
    return f'<div style="font-family: sans-serif; line-height: 1.6; padding: 15px; border: 1px solid #ddd; border-radius: 5px; background-color: #f0f0f0; color: #333;">{html_text}</div>'

# --- 5. 侧边栏交互配置 ---
with st.sidebar:
    access_code = st.text_input("Access Code", type="password")
    if access_code != "MMIWG":
        st.warning("Please Provide Correct Password")
        st.stop()

    st.header("Custom Highlighting Rules")
    if 'rules' not in st.session_state:
        st.session_state.rules = [{"label": "GPE", "color": "(0, 1, 1)"}, {"label": "PERSON", "color": "(1, 0, 0)"}]

    updated_rules = []
    for i, rule in enumerate(st.session_state.rules):
        with st.expander(f"Rule {i+1}", expanded=True):
            col_l, col_c = st.columns([1.5, 1])
            new_l = col_l.text_input("Label", value=rule['label'], key=f"l_{i}")
            new_c = col_c.text_input("RGB", value=rule['color'], key=f"c_{i}")
            if st.button(f"🗑️ Remove", key=f"del_{i}"):
                st.session_state.rules.pop(i)
                st.rerun()
            updated_rules.append({"label": new_l, "color": new_c})
    st.session_state.rules = updated_rules

    if st.button("➕ Add New Rule"):
        st.session_state.rules.append({"label": "", "color": "(0, 0, 1)"})
        st.rerun()

# --- 6. 主控制流程区 ---
st.title("Semantic Text Coder & NLP Enhancer")

if 'session_analysis_data' not in st.session_state:
    st.session_state.session_analysis_data = None

with st.form("text_processor_form"):
    input_text = st.text_area("Paste your article plain text here:", height=300, 
                              placeholder="Type or paste the news contents here for automatic qualitative coding...")
    submitted = st.form_submit_button("🚀 Run Analysis & Coding")

if submitted and input_text.strip():
    with st.spinner("Processing NLP Highlighting & Ollama Coding..."):
        # 1. 基础字数统计
        word_count = len(input_text.split())
        
        # 2. 调用本地 Ollama 进行定性编码
        analysis = analyze_text_with_ollama(input_text)
        
        # 3. 运行 spaCy 进行前端高亮文本生成
        highlighted_html = generate_html_highlighter(input_text, st.session_state.rules)
        
        if analysis:
            # 建立映射：构建扁平化、符合你原本 CSV 顺序的结构
            analysis_lower = {k.lower(): v for k, v in analysis.items()}
            
            def parse_block(key):
                block = analysis_lower.get(key.lower(), {})
                val = block.get("value", 0) if isinstance(block, dict) else 0
                evid = block.get("evidence", "") if isinstance(block, dict) else ""
                return val, evid

            # 解析各字段数值与证据
            mmiwg_m, mmiwg_m_ev = parse_block("mmiwg_mentioned")
            mmiwg_mv, mmiwg_mv_ev = parse_block("mmiwg_movement")
            spec_c, spec_c_ev = parse_block("specific_case")
            mult_c, mult_c_ev = parse_block("multiple_cases")
            legal_p, legal_p_ev = parse_block("legal_protection")
            fam_r, fam_r_ev = parse_block("family_friends_referenced")
            vic_l, vic_l_ev = parse_block("details_victim_life")
            perp, perp_ev = parse_block("details_perpetrator")

            # 组装成 Pandas Dataframe 作为编辑数据源
            coding_row = {
                "Word Count": word_count,
                "mmiwg_mentioned": mmiwg_m, "mmiwg_mentioned_evidence": mmiwg_m_ev,
                "mmiwg_movement": mmiwg_mv, "mmiwg_movement_evidence": mmiwg_mv_ev,
                "specific_case": spec_c, "specific_case_evidence": spec_c_ev,
                "multiple_cases": mult_c, "multiple_cases_evidence": mult_c_ev,
                "legal_protection": legal_p, "legal_protection_evidence": legal_p_ev,
                "family_friends_referenced": fam_r, "family_friends_referenced_evidence": fam_r_ev,
                "details_victim_life": vic_l, "details_victim_life_evidence": vic_l_ev,
                "details_perpetrator": perp, "details_perpetrator_evidence": perp_ev,
            }
            
            st.session_state.session_analysis_data = {
                "dataframe": pd.DataFrame([coding_row]),
                "html": highlighted_html
            }
        else:
            st.error("Failed to generate qualitative coding from Ollama.")

# --- 7. 结果可视化与编辑回填区 ---
if st.session_state.session_analysis_data:
    res = st.session_state.session_analysis_data
    
    st.divider()
    
    # 单元格数据回填与交互式编辑
    st.subheader("📊 Automated Qualitative Coding Results (Editable Table)")
    edited_df = st.data_editor(res["dataframe"], hide_index=True, use_container_width=True)
    
    # 导出的快捷下载按钮
    csv_buffer = edited_df.to_csv(index=False, encoding="utf-8-sig")
    st.download_button(
        label="📥 Export Coded Data to CSV",
        data=csv_buffer,
        file_name="coded_text_output.csv",
        mime="text/csv"
    )
    
    # 高亮文本预览区
    st.subheader("🔍 Entity Semantic Enhancement View")
    st.markdown(res["html"], unsafe_allow_html=True)