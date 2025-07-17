import pandas as pd
from loguru import logger
from metadata import get_session
import requests
import time
from datetime import datetime, timedelta
import os
from concurrent.futures import ThreadPoolExecutor, as_completed, wait, FIRST_COMPLETED
import hashlib
import sys
import pathlib

outdir = sys.argv[1]
pathlib.Path(f'{outdir}/downloads/').mkdir(parents=True,exist_ok=True)

metadata = pd.read_csv(f"{outdir}/search_results.csv")
# 初始化session相关变量
token = get_session()
last_refresh_time = datetime.now()
SESSION_REFRESH_INTERVAL = timedelta(minutes=10)


def refresh_session_if_needed():
    global token, last_refresh_time
    current_time = datetime.now()

    # 检查是否需要刷新session
    if current_time - last_refresh_time >= SESSION_REFRESH_INTERVAL:
        logger.info("[session] 正在刷新session token...")
        token = get_session()
        last_refresh_time = current_time
        logger.success("[session] session token已更新")

    return token


def download_pdf(url, patent_number,outdir):
    # 检查文件是否已存在
    file_path = f"{outdir}/downloads/{patent_number}.pdf"
    cache_path = f"{outdir}/downloads/{patent_number}.cache"

    if os.path.exists(file_path):
        logger.warning(f"专利 {patent_number} 已存在,跳过下载")
        return

    response = requests.get(url, stream=True)
    total_size = int(response.headers.get("content-length", 0))

    dynamic_symbols = ['→', '↗', '↑', '↖', '←', '↙', '↓', '↘']
    symbol_idx = 0

    with open(cache_path, "wb") as f:
        if total_size == 0:
            f.write(response.content)
        else:
            downloaded = 0
            for data in response.iter_content(chunk_size=4096):
                downloaded += len(data)
                f.write(data)
                progress = int(50 * downloaded / total_size)
                
                symbol_idx = (symbol_idx + 1) % len(dynamic_symbols)  
                remaining_space = 50 - progress
                progress_bar = (
                    f"\r专利 {patent_number} 下载中: "
                    f"[{'=' * progress}{dynamic_symbols[symbol_idx]}{' ' * (remaining_space - 1)}] "
                    f"{downloaded}/{total_size} bytes"
                )
                print(progress_bar, end="", flush=True)  
            print(f"\r专利 {patent_number} 下载完成: [{'=' * 50}] {downloaded}/{total_size} bytes", flush=True)

    # 检查是否返回了请求过多的错误
    with open(cache_path, "rb") as f:
        # 计算md5
        md5_hash = hashlib.md5(f.read()).hexdigest()
        if md5_hash == "442cca13b23848b3956ad3f1891e8a1f":
            logger.warning(f"专利 {patent_number} 内容无效,删除缓存文件")
            os.remove(cache_path)
            return

    # 下载完成后将cache文件重命名为pdf
    os.rename(cache_path, file_path)


# 获取初始token
refresh_session_if_needed()
# 顺序下载所有专利
for index, row in metadata.iterrows():
    patent_number = row["patentNumber"]
    document_id = row["documentId"]
    patent_type = row["type"]
    url = f"https://ppubs.uspto.gov/api/pdf/downloadPdf/{patent_number}?requestToken={token}"

    logger.info(f"正在处理第 ({index+1}/{len(metadata)}) 个专利: {document_id}")

    try:
        download_pdf(url, document_id,outdir)
    except Exception as e:
        logger.error(f"下载任务失败: {e}")
