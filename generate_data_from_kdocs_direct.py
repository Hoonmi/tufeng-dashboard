"""
Generate data.js from KDocs - download all sheets directly and parse
"""
import json
import os
import subprocess
import time
from collections import defaultdict
from datetime import datetime, timedelta

OUTPUT_JS = r"C:\Users\Administrator\WorkBuddy\2026-07-01-14-22-16\data.js"
DRIVE_ID = "2098975036"

STORES = [
    "宜昌天元", "哈尔滨机场路", "重庆汽博", "长沙中南汽车", "深圳信义汽车城",
    "重庆金菱车世界", "昆明新希望", "徐州欣欣路", "重庆大学城", "昆明东三环",
    "徐州三环东路", "毕节佰润汽车公园", "中山西区彩虹大道", "长沙麓谷汽车世界",
    "杭州国际汽车城", "成都和顺道"
]

# Store file IDs (from previous downloads, need to search if not available)
# I'll search for all stores first
STORE_FILE_IDS = {}

def search_file_id(store_name):
    cmd = f'"C:\\Users\\Administrator\\AppData\\Local\\kdocs-cli\\kdocs-cli.exe" drive search-files keyword="{store_name}" drive-id="{DRIVE_ID}" type="file_name"'
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    try:
        data = json.loads(result.stdout)
        if data.get('code') == 0:
            items = data.get('data', {}).get('data', {}).get('items', [])
            if items:
                return items[0]['file']['id']
    except:
        pass
    return None

def download_sheet(file_id, sheet_name):
    """Download sheet from KDocs, return parsed JSON"""
    cmd = f'"C:\\Users\\Administrator\\AppData\\Local\\kdocs-cli\\kdocs-cli.exe" drive read-file file_id="{file_id}" drive-id="{DRIVE_ID}" sheet_name="{sheet_name}"'
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    try:
        return json.loads(result.stdout)
    except:
        return None

def normalize_date(val):
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.strftime("%Y-%m-%d")
    if isinstance(val, str):
        val = val.strip()
        if not val:
            return None
        parts = val.split('-')
        if len(parts) == 3:
            try:
                return f"{int(parts[0])}-{int(parts[1]):02d}-{int(parts[2]):02d}"
            except:
                pass
        return None
    if isinstance(val, (int, float)) and val > 40000:
        try:
            dt = datetime(1899, 12, 30) + timedelta(days=int(val))
            return dt.strftime("%Y-%m-%d")
        except:
            pass
    return None

def safe_float(v):
    try:
        return float(v)
    except:
        return 0

def parse_sheet_data(json_data, sheet_name, store_name):
    """Parse data from a sheet's JSON response"""
    if not json_data or json_data.get('code') != 0:
        return []
    
    try:
        cells = json_data['data']['content']['range_data']['detail']['rangeData']
    except:
        return []
    
    if sheet_name == "销售部（大定）":
        return parse_sales(cells, store_name)
    elif sheet_name == "交付":
        return parse_delivery(cells, store_name)
    elif sheet_name == "售后":
        return parse_aftersales(cells, store_name)
    elif sheet_name == "基盘数":
        return parse_jipan(cells, store_name)
    return []

def parse_sales(cells, store_name):
    records = []
    # Build a grid for easier access
    grid = {}
    for cell in cells:
        r, c = cell['rowFrom'], cell['colFrom']
        grid[(r, c)] = cell.get('understandableType', {}).get('value', '')
    
    # Parse data rows (starting from row 2, 0-based)
    for r in range(2, 1000):  # Max 1000 rows
        date_val = grid.get((r, 1), '')  # Column 1 = date
        if not date_val:
            break
        
        date_str = normalize_date(date_val)
        if not date_str:
            continue
        
        model = str(grid.get((r, 3), '')).strip()  # Column 3 = model
        count = safe_float(grid.get((r, 4), 0))    # Column 4 = count
        
        if model and count > 0:
            records.append({
                "date": date_str, "store": store_name,
                "model": model, "count": count,
            })
    
    return records

def parse_delivery(cells, store_name):
    records = []
    grid = {}
    for cell in cells:
        r, c = cell['rowFrom'], cell['colFrom']
        grid[(r, c)] = cell.get('understandableType', {}).get('value', '')
    
    for r in range(2, 1000):
        date_val = grid.get((r, 1), '')
        if not date_val:
            break
        
        date_str = normalize_date(date_val)
        if not date_str:
            continue
        
        m5 = safe_float(grid.get((r, 4), 0))
        m6 = safe_float(grid.get((r, 5), 0))
        m7 = safe_float(grid.get((r, 6), 0))
        m8 = safe_float(grid.get((r, 7), 0))
        m9 = safe_float(grid.get((r, 8), 0))
        total = safe_float(grid.get((r, 9), 0))
        
        if total == 0:
            total = m5 + m6 + m7 + m8 + m9
        
        if total > 0 or m5 > 0 or m6 > 0 or m7 > 0 or m8 > 0 or m9 > 0:
            records.append({
                "date": date_str, "store": store_name,
                "total": round(total, 1),
                "m5": round(m5, 1), "m6": round(m6, 1),
                "m7": round(m7, 1), "m8": round(m8, 1),
                "m9": round(m9, 1),
            })
    
    return records

def parse_aftersales(cells, store_name):
    records = []
    grid = {}
    for cell in cells:
        r, c = cell['rowFrom'], cell['colFrom']
        grid[(r, c)] = cell.get('understandableType', {}).get('value', '')
    
    for r in range(2, 1000):
        date_val = grid.get((r, 1), '')
        if not date_val:
            break
        
        date_str = normalize_date(date_val)
        if not date_str:
            continue
        
        prop_type = str(grid.get((r, 3), '')).strip()
        count = safe_float(grid.get((r, 4), 0))
        value = safe_float(grid.get((r, 5), 0))
        
        if count > 0 or value > 0:
            records.append({
                "date": date_str, "store": store_name,
                "model": prop_type if prop_type else "未知",
                "count": count, "value": round(value, 2),
            })
    
    return records

def parse_jipan(cells, store_name):
    """Parse 基盘数 - only one row of data"""
    grid = {}
    for cell in cells:
        r, c = cell['rowFrom'], cell['colFrom']
        grid[(r, c)] = cell.get('understandableType', {}).get('value', '')
    
    # Look for the row with store name
    for r in range(1, 10):
        store_val = str(grid.get((r, 0), '')).strip()
        if store_name in store_val or store_val in store_name:
            count = safe_float(grid.get((r, 1), 0))
            if count > 0:
                return {"store": store_name, "count": int(count)}
    
    return None

print("=== Generating data.js from KDocs ===")
print()

# Step 1: Get file IDs for all stores
print("Step 1: Getting file IDs...")
for store in STORES:
    if store not in STORE_FILE_IDS:
        print(f"  Searching {store}...", end=" ")
        file_id = search_file_id(store)
        if file_id:
            STORE_FILE_IDS[store] = file_id
            print(f"OK")
        else:
            print("NOT FOUND")
        time.sleep(0.3)

print(f"\nFound {len(STORE_FILE_IDS)} / {len(STORES)} stores")
print()

# Step 2: Download and parse all data
print("Step 2: Downloading and parsing data from KDocs...")
print("(This will take several minutes...)")
print()

all_sales = []
all_delivery = []
all_aftersales = []
all_jipan = []

for store in STORES:
    if store not in STORE_FILE_IDS:
        print(f"  SKIP {store} (no file ID)")
        continue
    
    file_id = STORE_FILE_IDS[store]
    print(f"\n{store}:")
    
    # Download each sheet
    for sheet_name in ["销售部（大定）", "交付", "售后", "基盘数"]:
        print(f"  {sheet_name}...", end=" ")
        data = download_sheet(file_id, sheet_name)
        if data:
            records = parse_sheet_data(data, sheet_name, store)
            if sheet_name == "销售部（大定）":
                all_sales.extend(records)
                print(f"OK ({len(records)} rows)")
            elif sheet_name == "交付":
                all_delivery.extend(records)
                print(f"OK ({len(records)} rows)")
            elif sheet_name == "售后":
                all_aftersales.extend(records)
                print(f"OK ({len(records)} rows)")
            elif sheet_name == "基盘数":
                if records:
                    all_jipan.append(records)
                    print(f"OK ({records['count']})")
                else:
                    print("No data")
        else:
            print("FAILED")
        
        time.sleep(0.3)  # Rate limit

# Sort 基盘数 by count descending
all_jipan.sort(key=lambda x: x['count'], reverse=True)

print()
print("=== Final ===")
print(f"  Sales: {len(all_sales)} records")
print(f"  Delivery: {len(all_delivery)} records")
print(f"  Aftersales: {len(all_aftersales)} records")
print(f"  基盘数: {len(all_jipan)} stores")

# Generate data.js
all_stores = sorted(set(r['store'] for r in all_sales))
all_models = sorted(set(r['model'] for r in all_sales if r.get('model')))
avail_months = sorted(set(r['date'][:7] for r in all_sales if r['date'][:4] == '2026'))

js_lines = [
    "// Auto-generated on 2026-07-02",
    "// All data from KDocs",
    "",
    f"var availableMonths = {json.dumps(avail_months, ensure_ascii=False)};",
    f"var allStores = {json.dumps(all_stores, ensure_ascii=False)};",
    f"var allModels = {json.dumps(all_models, ensure_ascii=False)};",
    "",
    "window.rawData = {",
    f'  "sales": {json.dumps(all_sales, ensure_ascii=False)},',
    f'  "delivery": {json.dumps(all_delivery, ensure_ascii=False)},',
    f'  "aftersales": {json.dumps(all_aftersales, ensure_ascii=False)},',
    f'  "jipan": {json.dumps(all_jipan, ensure_ascii=False)}',
    "};",
]

with open(OUTPUT_JS, 'w', encoding='utf-8') as f:
    f.write('\n'.join(js_lines))

file_size = os.path.getsize(OUTPUT_JS)
print(f"\nGenerated {OUTPUT_JS} ({file_size:,} bytes)")
print("\n=== Done ===")
