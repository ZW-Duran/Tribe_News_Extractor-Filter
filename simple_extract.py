import re

print("Please enter the HTML source code (input 'EOF' and press Enter when done, or press Ctrl+D to finish):")


lines = []
while True:
    try:
        line = input()
        if line.strip() == "EOF":
            break
        lines.append(line)
    except EOFError:
        break

html_snippet = "\n".join(lines)
links = re.findall(r'href="([^"]+\.pdf)"', html_snippet)
base_url = "https://ctsi.nsn.us" # 替换为实际域名
full_links = [base_url + l if l.startswith('/') else l for l in links]

print("\n--- PDF Linkes ---")
if full_links:
    print("\n".join(full_links))
else:
    print("No PDF links found.")