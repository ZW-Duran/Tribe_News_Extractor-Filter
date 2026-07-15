import os
import re
import csv
import requests

# --- 1. 路径与配置初始化 ---
CSV_PATH = "./list.csv"
OUTPUT_DIR = "./original"

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

# 模拟浏览器 User-Agent，防止被 Google Drive 拒绝访问
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def download_file_from_google_drive(drive_url, save_path):
    """通过 Google Drive 开放下载接口流式下载文件"""
    # 提取 Drive URL 中的 File ID
    match = re.search(r'/d/([^/]+)', drive_url)
    if not match:
        return False, "无法解析的 Google Drive 链接格式"
    
    file_id = match.group(1)
    # 拼接可以直接 Bypass 预览界面的下载直链
    download_url = f"https://docs.google.com/uc?export=download&id={file_id}"
    
    try:
        # 使用 stream=True 避免大文件直接塞满内存
        with requests.get(download_url, headers=HEADERS, stream=True, timeout=30) as r:
            if r.status_code == 200:
                with open(save_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                return True, "成功"
            elif r.status_code == 403:
                return False, "403 Forbidden (可能触发了 Google 流量限制，请稍后再试)"
            else:
                return False, f"HTTP 状态码: {r.status_code}"
    except Exception as e:
        return False, str(e)

# --- 2. 执行主批处理循环 ---
def main():
    print(f"📖 开始读取本地 CSV 配置文件: {CSV_PATH}")
    
    if not os.path.exists(CSV_PATH):
        print(f"❌ 错误：在当前目录下未找到 {CSV_PATH}，请检查文件位置。")
        return

    download_count = 0
    skip_count = 0
    fail_count = 0

    # 一次性将所有行读入内存
    with open(CSV_PATH, mode='r', encoding='utf-8') as f:
        rows = list(csv.reader(f))
        
    for idx, row in enumerate(rows, start=1):
        # 1. 动态过滤完全的空行
        if not row or "".join(row).strip() == "":
            print(f"👻 行号 [{idx}]: 检测到完全空行，自动跳过。")
            continue

        # 2. 动态识别并跳过表头行
        if "Author Last Name" in row or "Newspaper/Publisher" in row:
            print(f"📋 行号 [{idx}]: 检测到表头行，自动跳过。")
            continue

        # 3. 边界安全检查：确保至少有 M 列（索引 12）
        if len(row) < 13:
            continue

        d_col_val = row[3].strip()   # D 列 (Python index 3)
        drive_link = row[12].strip() # M 列 (Python index 12)

        # 4. 核心判断逻辑：只要 D 列有东西就下载
        if d_col_val:
            if not drive_link:
                print(f"⚠️ 行号 [{idx}]: D列有效但 M列链接为空，跳过。")
                continue

            # 生成 004.pdf 格式的文件名（:03d 表示至少3位数字，不足的前面补0）
            # 如果行数可能超过 1000 行，建议把 :03d 改为 :04d
            new_filename = f"{idx:03d}.pdf"
            file_save_path = os.path.join(OUTPUT_DIR, new_filename)

            # --- 断点续传检查 ---
            if os.path.exists(file_save_path):
                print(f"⏭️ 行号 [{idx}]: 检测到本地已存在 {new_filename}，自动跳过。")
                skip_count += 1
                continue

            # --- 执行下载 ---
            print(f"🚀 正在下载行号 [{idx}] ──> 存为: {new_filename}...")
            success, message = download_file_from_google_drive(drive_link, file_save_path)
            
            if success:
                download_count += 1
                print(f"   └─ ✅ 下载完成！")
            else:
                fail_count += 1
                print(f"   └─ ❌ 下载失败原因: {message}")

    print("\n" + "="*40)
    print("🎉 批量流式下载任务执行完毕！")
    print(f"   - 本次成功下载: {download_count} 个文件")
    print(f"   - 本次断点跳过: {skip_count} 个文件")
    print(f"   - 本次下载失败: {fail_count} 个文件")
    print(f"📂 所有原始文件已存入: {OUTPUT_DIR}")
    print("="*40)

if __name__ == "__main__":
    main()