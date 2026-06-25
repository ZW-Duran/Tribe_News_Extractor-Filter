import streamlit as st
import spacy
import json
import ollama
import re
import pandas as pd

# --- 1. 初始化配置与页面设置 ---
st.set_page_config(page_title="Text Semantic Coder & Highlighter", layout="wide")

# 优化为惰性加载：只有当用户开启高亮开关时，该函数才会被触发调用
@st.cache_resource
def load_spacy_model():
    with st.spinner("Initializing spaCy Transformer Model (First-time loading may take a while)..."):
        return spacy.load("en_core_web_trf")

LOCAL_MODEL_NAME = "9b"  # 继承自你的本地 Ollama 模型配置

# --- 2. 强约束 Prompt ---
SYSTEM_INSTRUCTION = """
You are an expert sociological research assistant reading newspaper archives. Your task is to perform qualitative text coding to identify specific semantic themes within the provided article.

CRITICAL INSTRUCTIONS:
1. For every variable you code as 1, you MUST provide the exact, verbatim sentence (evidence) from the text that justifies your choice.
2. If the text does not implicitly or explicitly discuss the theme based on the strict definitions below, set the value to 0 and leave the evidence string completely empty ("").
3. Keep the "evidence" string as short as possible—a single, precise verbatim sentence is preferred.

--- CODEBOOK & BOUNDARY DEFINITIONS ---
1. "mmiwg_mentioned": 1 if the text addresses the topic of Missing and Murdered Indigenous Women and Girls. This does NOT require a literal acronym match; if the article is clearly validating or discussing the crisis/phenomenon of missing/murdered Native individuals, it counts as 1.

2. "mmiwg_movement": 1 if the text references activism, community awareness, protests, marches, healing circles, policy advocacy, task forces, or red dress campaigns dedicated to addressing this crisis.

3. "specific_case": 1 if the text discusses a particular individual's disappearance or murder case. This includes anytime a specific victim is named, or specific incident details (like search efforts, police reporting, or crime scenes) are described.

4. "multiple_cases": 1 if the text acts as an empirical aggregator of the crisis—meaning it provides specific aggregated numbers/statistics, references database counts, or transitions into detailing/contrasting distinct, separate case histories.
   - Core Intent: This captures factual density about more than one case. Do NOT code as 1 for purely rhetorical, commemorative, or emotional expressions of collective grief (e.g., "so many loved ones who have been victims"). It must contain empirical or informational grouping, not just poetic or general acknowledgment of a widespread issue.
5. "legal_protection": 1 if the text references specific, concrete institutional mechanisms—such as passed or proposed statutes (e.g., "Senate Resolution 60", "Savanna's Act"), tribal sovereignty protocols, specific budgetary allocations for policing, jurisdictional rules, or active policy reform measures.
   - STRUCTURAL REQUIREMENT: The evidence must point to a tangible legal instrument, legislative bill, or a specific regulatory action taken/proposed by a government or tribal body.
   - CRITICAL EXCLUSION (HOPE VS. FACT): Do NOT code as 1 for statements expressing how the system *should* behave, personal hopes, future expectations, or moral calls to action (e.g., "I hope it will inform the criminal justice system's response..."). General quotes about the failure, needed awareness, or desired attitude of the justice system do NOT constitute concrete legal protection.
6. "family_friends_referenced": 1 if the text quotes, mentions, or references the victim's family members, relatives, loved ones, or close friends speaking out or being affected.
   - CRITICAL EXCLUSION: Do NOT code as 1 if an individual is described ONLY by their professional, political, or activist title (e.g., "event organizer", "advocate", "chief", "police spokesperson") without the text explicitly stating they have a personal, familial, or friendship bond with a victim. Do not infer personal relationships from social or activist roles.

7. "details_victim_life": 1 if the text provides a humanizing look into who the victim was as a living person *beyond* basic identification markers—such as their personal character, hobbies, career achievements, educational background, personal dreams, or roles within their family/community before the tragedy.
   - STRUCTURAL THRESHOLD: The text must detail their personality or life story. 
   - CRITICAL EXCLUSION: Do NOT code as 1 if the text only mentions basic demographic labels, standard identification markers, or chronological data necessary to describe the crime or a holiday (e.g., mentioning a victim's age, tribal affiliation, or their "birthday" to explain why a commemorative date was selected does NOT count as details of the victim's life).

8. "details_perpetrator": 1 if the text provides substantive information or updates about a specific suspect, person of interest, or perpetrator. This includes physical descriptions, concrete identities, arrest records, investigation progress targeting a specific suspect, trial updates, or court proceedings.
   - CRITICAL EXCLUSION: Do NOT code as 1 for generic, empty statements about the police simply looking for an unknown perpetrator (e.g., "police still finding perpetrator" or "no suspects have been named"). It must contain actual details or updates about a suspect/perpetrator's status or identity.

CONTEXTUAL ALIGNMENT TEST: When evaluating a sentence for a variable, you must ensure the *contextual meaning* of the sentence matches the variable's theme, not just the individual words. Ask yourself: "Is this sentence actually talking about the sociological theme defined, or is it just using a similar word in a completely different context (e.g., an election context vs. a criminal justice context)?" If it's a different context, you MUST code it as 0.

--- TWO-STEP VERIFICATION FILTER (COMPULSORY) ---
Before confirming any variable as 1, you must run this strict linguistic check:
- Step 1 (Noun/Verb Check): Does the sentence physically contain the mandatory nouns/actions required by the category (e.g., kinship nouns for variable 6, legal instruments for variable 5, empirical numbers for variable 4, human character traits for variable 7)?
- Step 2 (Context Check): Is the sentence free of the REJECTION CRITERIA listed under that category?
If the sentence fails either check, you MUST force the value to 0.

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
    """只有在显式调用时，才会激活并加载库"""
    nlp = load_spacy_model()  # 触发惰性加载缓存
    doc = nlp(text)
    
    active_rules = {}
    for r in rules:
        if r['label'].strip():
            active_rules[r['label'].strip().upper()] = r['color']

    spans_to_highlight = []
    for ent in doc.ents:
        if ent.label_ in active_rules:
            spans_to_highlight.append((ent.start_char, ent.end_char, ent.label_, ent.text))
            
    spans_to_highlight = sorted(spans_to_highlight, key=lambda x: x[0], reverse=True)
    
    html_text = text
    for start, end, label, ent_text in spans_to_highlight:
        color_rgb = active_rules[label]
        try:
            rgb_tuple = eval(color_rgb)
            css_color = f"rgba({int(rgb_tuple[0]*255)}, {int(rgb_tuple[1]*255)}, {int(rgb_tuple[2]*255)}, 0.3)"
            border_color = f"rgb({int(rgb_tuple[0]*255)}, {int(rgb_tuple[1]*255)}, {int(rgb_tuple[2]*255)})"
        except:
            css_color = "rgba(255, 255, 0, 0.3)" 
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
        
    html_text = html_text.replace("\n", "<br>")
    return f'<div style="font-family: sans-serif; line-height: 1.6; padding: 15px; border: 1px solid #ddd; border-radius: 5px; background-color: #f0f0f0; color: #333;">{html_text}</div>'

# --- 5. 侧边栏交互配置 ---
with st.sidebar:
    access_code = st.text_input("Access Code", type="password")
    if access_code != "":
        st.warning("Please Provide Correct Password")
        st.stop()

    st.header("⚡ Performance Settings")
    # 🌟 核心功能：添加开关控制是否启动 NLP 高亮渲染，默认关闭以极致追求纯 Coding 效率
    enable_highlighting = st.checkbox("Enable spaCy NLP Highlighting", value=False, 
                                      help="Turning this off bypasses the heavy Transformer model and processes text instantly.")

    # 只有当高亮功能被勾选激活时，侧边栏才展开显示高亮自定义规则面板
    if enable_highlighting:
        st.markdown("---")
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
    # 动态调配 Spinner 的提示语
    spinner_msg = "Running Ollama Coding Analysis..." if not enable_highlighting else "Processing NLP Highlighting & Ollama Coding..."
    
    with st.spinner(spinner_msg):
        # 1. 基础字数统计
        word_count = len(input_text.split())
        
        # 2. 调用本地 Ollama 进行定性编码
        analysis = analyze_text_with_ollama(input_text)
        
        # 3. 运行条件渲染高亮视图
        highlighted_html = None
        if enable_highlighting:
            highlighted_html = generate_html_highlighter(input_text, st.session_state.rules)
        
        if analysis:
            analysis_lower = {k.lower(): v for k, v in analysis.items()}
            
            def parse_block(key):
                block = analysis_lower.get(key.lower(), {})
                val = block.get("value", 0) if isinstance(block, dict) else 0
                evid = block.get("evidence", "") if isinstance(block, dict) else ""
                return val, evid

            mmiwg_m, mmiwg_m_ev = parse_block("mmiwg_mentioned")
            mmiwg_mv, mmiwg_mv_ev = parse_block("mmiwg_movement")
            spec_c, spec_c_ev = parse_block("specific_case")
            mult_c, mult_c_ev = parse_block("multiple_cases")
            legal_p, legal_p_ev = parse_block("legal_protection")
            fam_r, fam_r_ev = parse_block("family_friends_referenced")
            vic_l, vic_l_ev = parse_block("details_victim_life")
            perp, perp_ev = parse_block("details_perpetrator")

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
                "html": highlighted_html # 如果开关未开启，这里为 None
            }
        else:
            st.error("Failed to generate qualitative coding from Ollama.")

# --- 7. 结果可视化与编辑回填区 ---
if st.session_state.session_analysis_data:
    res = st.session_state.session_analysis_data
    
    st.divider()
    
    st.subheader("📊 Automated Qualitative Coding Results (Editable Table)")
    edited_df = st.data_editor(res["dataframe"], hide_index=True, use_container_width=True)
    
    csv_buffer = edited_df.to_csv(index=False, encoding="utf-8-sig")
    st.download_button(
        label="📥 Export Coded Data to CSV",
        data=csv_buffer,
        file_name="coded_text_output.csv",
        mime="text/csv"
    )
    
    # 根据用户之前的开关，条件渲染高亮预览区
    if res["html"]:
        st.subheader("🔍 Entity Semantic Enhancement View")
        st.markdown(res["html"], unsafe_allow_html=True)