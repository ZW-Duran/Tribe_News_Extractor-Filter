import google.generativeai as genai
import streamlit as st

# --- 1. Page Configuration ---
st.set_page_config(
    page_title="News Text Quantitative Coding Tool", page_icon="📝", layout="wide"
)

# --- 2. Core Prompt with Evidence Tracking ---
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
  "tribe_gov_officials": {
    "count": 0,
    "evidence": ""
  },
  "state_local_gov_officials": {
    "count": 0,
    "evidence": ""
  },
  "federal_gov_officials": {
    "count": 0,
    "evidence": ""
  },
  "law_enforcement": {
    "count": 0,
    "evidence": ""
  },
  "legal_professionals": {
    "count": 0,
    "evidence": ""
  }
}
"""

# --- 3. Output Sanitizer (Strips Thinking/Thoughts text) ---
def clean_and_parse_output(raw_text):
  if not raw_text:
    return ""
  try:
    # Locate the first occurrence of '{' to cut off any preceding thought text
    start_idx = raw_text.find("{")
    if start_idx == -1:
      return raw_text
    
    # Locate the last occurrence of '}' to trim trailing noise
    end_idx = raw_text.rfind("}")
    if end_idx == -1 or end_idx < start_idx:
      return raw_text[start_idx:]
      
    return raw_text[start_idx:end_idx + 1]
  except Exception:
    return raw_text

# --- 4. Core API Execution Function (Dual-Key Round-Robin) ---
def run_model_analysis(text, api_key_1, api_key_2):
  prompt = f"{SYSTEM_INSTRUCTION}\n\nArticle Text:\n{text}"

  # Dual-key load balancing / fallback logic
  if not api_key_2 or not api_key_2.strip():
    current_api_key = api_key_1
    key_label = "Key 1 (Single Channel)"
  else:
    if "key_toggle" not in st.session_state:
      st.session_state.key_toggle = 0

    if st.session_state.key_toggle % 2 == 0:
      current_api_key = api_key_1
      key_label = "Key 1 (Dual Channel Alternate)"
    else:
      current_api_key = api_key_2
      key_label = "Key 2 (Dual Channel Alternate)"

    st.session_state.key_toggle += 1

  try:
    genai.configure(api_key=current_api_key)
    model = genai.GenerativeModel("gemma-4-31b-it")

    with st.spinner(f"Analyzing via [{key_label}]..."):
      response = model.generate_content(
          prompt,
          generation_config=genai.types.GenerationConfig(
              temperature=0.0,  # Zero temperature for maximum stability
          ),
      )

    return response.text, key_label

  except Exception as e:
    st.error(f"API Error: {e}")
    return None, key_label

# --- 5. Streamlit Frontend Layout ---
def main():
  st.title("📰 News Text Quantitative Coding Assistant")
  st.markdown(
      "Paste your newspaper article text below to extract structured counts and evidence securely."
  )

  # Sidebar: API Key Configuration
  st.sidebar.header("🔑 API Key Configuration")
  api_key_1 = st.sidebar.text_input(
      "API Key 1 (Primary)", type="password", placeholder="Required: Google AI Studio Key"
  )
  api_key_2 = st.sidebar.text_input(
      "API Key 2 (Backup / Optional)",
      type="password",
      placeholder="Optional: Enables load-balancing",
  )

  st.sidebar.markdown("---")
  st.sidebar.info(
      "Tip: Entering one key operates on a dedicated channel. Entering both keys automatically alternates requests to distribute rate limits."
  )

  # Main Interface: Text Input Area
  article_text = st.text_area(
      "Paste Article Text Here:", height=300, placeholder="Enter article content..."
  )

  if st.button("🚀 Start Analysis", type="primary"):
    if not api_key_1:
      st.warning("⚠️ Please provide **API Key 1** in the sidebar to proceed.")
      return

    if not article_text.strip():
      st.warning("⚠️ Please enter article text before running analysis.")
      return

    # Execute Model Analysis
    raw_result_text, channel_used = run_model_analysis(
        article_text, api_key_1, api_key_2
    )

    if raw_result_text:
      st.success(f"🎉 Analysis Complete! (Channel: {channel_used})")

      # Sanitize and truncate raw output to isolate the clean JSON block
      clean_json_output = clean_and_parse_output(raw_result_text)

      # Display clean JSON block
      st.markdown("### 📊 Structured Coding Output:")
      st.code(clean_json_output, language="json")

      # Expandable section to review raw thoughts/logs if needed for audit
      with st.expander("🔍 View Raw Model Output & Reasoning Log"):
        st.text(raw_result_text)

      # Download button for the clean result
      st.download_button(
          label="📥 Download JSON Results",
          data=clean_json_output,
          file_name="coding_output.json",
          mime="application/json",
      )


if __name__ == "__main__":
  main()