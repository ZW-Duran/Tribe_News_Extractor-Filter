import re
import requests

# 1. 这种网站通常需要更完整的 Headers
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
}

target_url = "https://www.muckleshoot.nsn.us/messenger-past-editions"

try:
    response = requests.get(target_url, headers=headers, timeout=15)
    html_content = response.text
    
    # 2. 暴力提取：直接匹配所有 CDN 上的 PDF 字符串
    # 这种写法不依赖 href="" 的结构，只要字符串里有这个 URL 就能抓出来
    regex = r'https://cdn\.prod\.website-files\.com/[\w\d/_.-]+\.pdf'
    links = re.findall(regex, html_content, re.IGNORECASE)
    
    # 3. 去重
    unique_links = sorted(list(set(links)))
    
    print(f"成功抓取到 {len(unique_links)} 个链接")
    for l in unique_links:
        print(l)

except Exception as e:
    print(f"错误: {e}")