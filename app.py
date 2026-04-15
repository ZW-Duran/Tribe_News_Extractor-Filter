import fitz
import os
import re

# setup
source_dir = "./original"
output_dir = "./relevant"
os.makedirs(output_dir, exist_ok=True)

# filter
logic_patterns = {
    "gender": re.compile(r"(women|woman|girl|female)", re.I),
    "violence": re.compile(r"(violence|murder|victim)", re.I),
    "native": re.compile(r"(native|native american|indigenous|indian)", re.I),
    "mmiw": re.compile(r"(MMIW|MMIWG|Missing and Murdered Indigenous Women)", re.I)
}

# highlight
highlight_words = [
    "women", "woman", "girl", "female", 
    "violence", "murder", "victim", 
    "native", "native american", "indigenous", "indian",
    "MMIW", "MMIWG", "Missing and Murdered Indigenous Women"
]

def process_pdfs():
    for filename in os.listdir(source_dir):
        if not filename.endswith(".pdf"): continue
        
        file_path = os.path.join(source_dir, filename)
        doc = fitz.open(file_path)
        full_text = ""
        
        # 1. find text
        for page in doc:
            full_text += page.get_text()

        # 2. filter
        has_gender = logic_patterns["gender"].search(full_text)
        has_violence = logic_patterns["violence"].search(full_text)
        has_native = logic_patterns["native"].search(full_text)
        has_mmiw = logic_patterns["mmiw"].search(full_text)

        if (has_gender and has_violence and has_native) or has_mmiw:
            print(f"[*] Match, Highlighting: {filename}")
            
            # try fix
            try:
                # fix xref
                temp_pdf = doc.tobytes(clean=True, deflate=True, garbage=4)
                doc.close()
                doc = fitz.open("pdf", temp_pdf)
            except Exception as e:
                print(f"[!] Failed to xref: {filename}, Error: {e}")
                # if failed, skip the file
                continue

            # highlight
            for page in doc:
                for word in highlight_words:
                    text_instances = page.search_for(word)
                    for inst in text_instances:
                        annot = page.add_highlight_annot(inst)
                        annot.set_colors(stroke=(0, 1, 1))
                        annot.update()
            
            # fix method 2
            try:
                # garbage=4:
                # expand=True
                doc.save(os.path.join(output_dir, filename), 
                         garbage=4, 
                         deflate=True, 
                         clean=True)
            except Exception as e:
                 print(f"[!] Final fix Failed: {filename}, Error: {e}")
        else:
            print(f"[ ] Irrelevant: {filename}")
            
        doc.close()

if __name__ == "__main__":
    process_pdfs()