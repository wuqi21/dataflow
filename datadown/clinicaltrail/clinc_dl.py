import json
import pandas as pd
import requests
import sys
import pathlib
import os

in_file = sys.argv[1]
out_dir = sys.argv[2]

pathlib.Path(out_dir).mkdir(parents=True,exist_ok=True)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36'
}

def request_api(study_id:str):
    url = f"https://clinicaltrials.gov/api/v2/studies/{study_id}"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        data = response.json()
        return data
    return None


df = pd.read_csv(in_file)
for nct in set(df['NCT Number'].to_list()):
    if os.path.exists(f'{out_dir}/{nct}.json'):
        continue
    try:
        data = request_api(nct)
        with open(f'{out_dir}/{nct}.json','w') as out:
            json.dump(data, out, indent=4)
    except:
        print(f'{nct} error')
