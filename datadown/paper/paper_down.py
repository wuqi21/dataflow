import requests
import random
import argparse
import pathlib
import sys
import os
import re
import hashlib
import pandas as pd
from bs4 import BeautifulSoup


PUBMED_ARTICLE_URL_PREFIX = 'https://pubmed.ncbi.nlm.nih.gov/'
PUBMED_ARTICLE_DL_URL_PREFIX = "https://pmc.ncbi.nlm.nih.gov/articles/"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36'
}


def print_progress_bar(iteration, total, prefix='', length=50):
    percent = (iteration / total) * 100
    filled_length = int(length * iteration // total)
    bar = '█' * filled_length + '-' * (length - filled_length)
    sys.stdout.write(f'\r{iteration}/{total}{prefix} |{bar}| {percent:.2f}% Complete')
    sys.stdout.flush()


def sha256_hash(POW_CHALLENGE, POW_DIFFICULTY):
    o = 0
    r = ""
    if POW_DIFFICULTY is None:
        POW_DIFFICULTY = 4
    for index in range(POW_DIFFICULTY):
        r = r + "0"
    while True:
        c = POW_CHALLENGE + str(o)
        sha256 = hashlib.sha256()
        sha256.update(c.encode('utf-8'))
        i = sha256.hexdigest()
        if i.startswith(r):
            return o
        o = o + 1


def get_soup(url: str):
    response = requests.get(url, headers=HEADERS)
    return BeautifulSoup(response.text, 'html.parser')


def get_var_val(dom):
    # 查找所有<script>标签
    script_tags = dom.find_all('script')

    # 遍历找到的<script>标签
    for script in script_tags:
        if script.string:  # 确保标签内存在内容
            # 使用正则表达式查找变量
            match = re.search(r'POW_CHALLENGE = "(.*?)"', script.string)
            if match:
                return match.group(1)
    return None


def dl_pubmed_article(doi,pmid,outdir):
    outname = f"{outdir}/{pmid}.pdf" if pd.isna(doi) else f"{outdir}/{doi.replace('/', '_')}.pdf"
    deatil_soup = get_soup(f"{PUBMED_ARTICLE_URL_PREFIX}{pmid}/")
    pmcid_dom = deatil_soup.find('a', attrs={'data-ga-action': 'PMCID'})
    if not pmcid_dom is None:
        pmc_url = pmcid_dom.attrs['href']
        pmcid = pmcid_dom.text.strip()
        article_soup = get_soup(pmc_url)
        dl_dom = article_soup.find('a', attrs={'data-ga-label': 'pdf_download_desktop'})
        if not dl_dom is None:
            pdf_url = dl_dom.attrs['href']
            dl_url = f"{PUBMED_ARTICLE_DL_URL_PREFIX}{pmcid}/{pdf_url}"
            cookie_val = get_var_val(get_soup(dl_url))
            if not cookie_val is None:
                cookie = {
                    'cloudpmc-viewer-pow': cookie_val + "," + str(sha256_hash(cookie_val, 4))
                }
                dl_res = requests.get(dl_url, headers=HEADERS, cookies=cookie, stream=True)
                if dl_res.status_code == 200 and len(dl_res.content) > 0:
                    with open(outname, 'wb+') as pdf_file:
                        pdf_file.write(dl_res.content)
                        return True
            else:
                return False
        else:
            return False
    else:
        return False
    

def download_paper(doi,outdir):
    # sci-hub
    url = "https://www.sci-hub.ren/" + doi + "#"
    head = {
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.117 Safari/537.36"
            }
    
    try:
        download_url = ""
        r = requests.get(url, headers=head)
        #r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        
        if soup.iframe == None:
            download_url = "https:" + soup.embed.attrs["src"]
        else:
            download_url = soup.iframe.attrs["src"]
        
        download_url = f'https:{download_url.split("https:")[-1]}'
        download_r = requests.get(download_url, headers=head)
        download_r.raise_for_status()
        with open(outdir + doi.replace("/", "_") + ".pdf", "wb+") as temp:
            temp.write(download_r.content)
        return True
    except Exception as e:
        # unpywall
        try:
            EMAIL='muio123@qq.com'
            api_url = f"https://api.unpaywall.org/v2/{doi}?email={EMAIL}"
            response = requests.get(api_url)
            data = response.json()
            oa_locations = data['oa_locations']
            if len(oa_locations) > 0:
                for oa_location in oa_locations:
                    pdf_url = oa_location['url_for_pdf']
                    if pdf_url is None or pdf_url == '':
                        continue
                    try:
                        dl_res = requests.get(pdf_url, stream=True)
                        if dl_res.status_code == 200 and len(dl_res.content) > 0:
                            with open(outdir + doi.replace("/", "_") + ".pdf", "wb+") as f:
                                f.write(dl_res.content)
                                return True
                    except Exception as e:
                        return False
            else:
                return False
        except Exception as e:
            return False

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--doi_file',help='doi_file')
    parser.add_argument('--outdir',help='outdir')
    
    args = parser.parse_args()
    doi_file = args.doi_file
    outdir = args.outdir
    
    pathlib.Path(outdir).mkdir(parents=True,exist_ok=True)

    df = pd.read_csv(doi_file, encoding='utf-8')
    num_file = df.shape[0]
    for index,row in df.iterrows():
        bools = False
        print_progress_bar(index+1,num_file)
        doi = row['DOI']
        pmid = row['PMID']
        if not pd.isna(doi):
            if not pathlib.Path(outdir + doi.replace("/", "_") + ".pdf").exists():
                bools = download_paper(doi,outdir)
                if not bools:
                    try:
                        bools = dl_pubmed_article(doi,pmid,outdir)
                    except:
                        print(f'{pmid} error')
            else:
                continue
        else:
            if not pathlib.Path(f"{outdir}/{pmid}.pdf").exists():

                try:
                    bools = dl_pubmed_article(doi,pmid,outdir)
                except:
                    print(f'{pmid} error')
            else:
                continue


    exis_pdf = set()
    for pdf in pathlib.Path(outdir).rglob('*pdf'):
        exis_pdf.add(pdf.name.rsplit('.pdf',1)[0])
    with open(f'{outdir}/error.log','w') as of:
        of.write(f'PMID\tDOI\n')
        for index,row in df.iterrows():
            doi = row['DOI']
            pmid = row['PMID']
            _doi = 'None' if pd.isna(doi) else doi.replace("/", "_")
            if (_doi not in exis_pdf) and (pmid not in exis_pdf):
                of.write(f'{pmid}\t{doi}\n')
    print(f"下载完成：{len(exis_pdf)};总共：{num_file}")
