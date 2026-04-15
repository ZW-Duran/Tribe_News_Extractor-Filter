import requests
import re
import time

# url from newspaper's website
base_url = "https://tulalipnews.com/category/tulalip-news/see-yaht-sub-pdfs/page/{}/"
all_pdf_links = set() ## use a set to automatically handle duplicates, no need for extra code to remove duplicates later

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

for page_num in range(1, 62):
    target_url = base_url.format(page_num)
    print(f"Scanning page {page_num}...")
    
    try:
        response = requests.get(target_url, headers=headers, timeout=15)
        links = re.findall(r'href="([^"]+\.pdf)"', response.text)
        for link in links:
            all_pdf_links.add(link)
            
    except Exception as e:
        print(f"Fail to load {target_url}: {e}")
    
    time.sleep(0.1) # be polite and avoid overwhelming the server, adjust as needed

# Save links to .txt file
with open("pdf_list.txt", "w", encoding="utf-8") as f:
    for link in sorted(all_pdf_links):
        f.write(link + "\n")

print(f"\n Finished! After deduplication, there are {len(all_pdf_links)} PDF links, which have been saved to pdf_list.txt")