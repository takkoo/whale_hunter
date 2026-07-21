import os
import sys
import time
import datetime
import urllib.parse
import re
import requests
import pandas as pd
import toml
from supabase import create_client

# ------------------------------------------------------------------
# 1. 설정 및 시크릿 로드
# ------------------------------------------------------------------
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SECRETS_PATH = os.path.join(PROJECT_ROOT, '.streamlit', 'secrets.toml')

try:
    with open(SECRETS_PATH, 'r', encoding='utf-8') as f:
        secrets = toml.load(f)
except Exception as e:
    print(f"Failed to load secrets: {e}")
    sys.exit(1)

SUPABASE_URL = secrets["supabase"]["url"]
SUPABASE_KEY = secrets["supabase"]["key"]
KIS_APP_KEY = secrets["kis"]["app_key"]
KIS_APP_SECRET = secrets["kis"]["app_secret"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ------------------------------------------------------------------
# 2. 한투 OpenAPI 토큰 발급
# ------------------------------------------------------------------
def get_kis_access_token():
    import json
    import os
    import time
    
    # 상위 폴더의 kis_token.json 사용 (경로 주의)
    token_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "kis_token.json")
    
    if os.path.exists(token_file):
        try:
            with open(token_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if time.time() - data.get("timestamp", 0) < 82800:
                    print("✅ 기존 토큰 재사용 (kis_token.json)")
                    return data["token"]
        except Exception as e:
            pass
            
    url = "https://openapi.koreainvestment.com:9443/oauth2/tokenP"
    headers = {"content-type": "application/json"}
    body = {"grant_type": "client_credentials", "appkey": KIS_APP_KEY, "appsecret": KIS_APP_SECRET}
    res = requests.post(url, headers=headers, json=body)
    if res.status_code == 200:
        new_token = res.json()["access_token"]
        try:
            with open(token_file, "w", encoding="utf-8") as f:
                json.dump({"token": new_token, "timestamp": time.time()}, f)
        except Exception:
            pass
        return new_token
    print(f"Failed to get KIS Token: {res.text}")
    return None

# ------------------------------------------------------------------
# 3. 순수 주식 종목 로드
# ------------------------------------------------------------------
def get_pure_stock_codes():
    import FinanceDataReader as fdr
    df_krx = fdr.StockListing('KRX')
    noise_keywords = ('ETF', 'ETN', 'KODEX', 'TIGER', 'ACE', 'SOL', 'RISE', 'KBSTAR', 'ARIRANG', 'HANARO', 'KOSEF', 'PLUS', 'TIME', '인버스', '레버리지', 'WON', '1Q', 'KIWOOM', 'TRUE', 'QV', '선물', '콜', '풋', '옵션')
    pure_stocks = []
    for _, row in df_krx.iterrows():
        name = str(row['Name']).strip()
        code = str(row['Code']).strip().zfill(6)
        market = str(row['MarketId']).strip() # STK or KSQ
        
        if any(kw in name.upper() for kw in noise_keywords):
            continue
        if re.search(r'우$|우B$|우\([A-Za-z0-9]+\)$|우[A-Z]$|스팩|제\d+호', name, re.IGNORECASE):
            continue
            
        market_type = "KOSPI" if market == "STK" else "KOSDAQ"
        pure_stocks.append({"code": code, "name": name, "market": market_type})
    return pure_stocks

# ------------------------------------------------------------------
# 4. 일별 투자자 수급 데이터 패치
# ------------------------------------------------------------------
def fetch_today_net_buying(stock_code, token):
    url = "https://openapi.koreainvestment.com:9443/uapi/domestic-stock/v1/quotations/inquire-investor"
    headers = {
        "content-type": "application/json; charset=utf-8",
        "authorization": f"Bearer {token}",
        "appkey": KIS_APP_KEY,
        "appsecret": KIS_APP_SECRET,
        "tr_id": "FHKST01010900"
    }
    params = {
        "FID_COND_MRKT_DIV_CODE": "J",
        "FID_INPUT_ISCD": stock_code
    }
    try:
        res = requests.get(url, headers=headers, params=params, timeout=5)
        if res.status_code == 200:
            data = res.json().get("output", [])
            if not data:
                return None
            today_data = data[0] # 첫번째 요소가 오늘/최신
            
            # 단위: 백만원 -> 억원 변환, 빈 문자열(0) 처리
            frgn_buy = float(today_data.get('frgn_shnu_tr_pbmn') or 0) / 100
            frgn_sell = float(today_data.get('frgn_seln_tr_pbmn') or 0) / 100
            orgn_buy = float(today_data.get('orgn_shnu_tr_pbmn') or 0) / 100
            orgn_sell = float(today_data.get('orgn_seln_tr_pbmn') or 0) / 100
            
            # 실제 영업일(거래일) 추출 (예: '20260716')
            trade_date_str = today_data.get('stck_bsop_date', '')
            if len(trade_date_str) == 8:
                formatted_date = f"{trade_date_str[:4]}-{trade_date_str[4:6]}-{trade_date_str[6:]}"
            else:
                formatted_date = None
            
            return {
                "trade_date": formatted_date,
                "frgn_buy": round(frgn_buy, 2),
                "frgn_sell": round(frgn_sell, 2),
                "orgn_buy": round(orgn_buy, 2),
                "orgn_sell": round(orgn_sell, 2),
                "total_net": round((frgn_buy - frgn_sell) + (orgn_buy - orgn_sell), 2)
            }
    except Exception as e:
        print(f"Error fetching {stock_code}: {e}")
    return None

def is_today_market_open(token):
    # 오늘이 영업일인지 한투 API를 통해 가장 확실하게 확인하는 방법
    # 삼성전자(005930)의 오늘 데이터를 요청해서 영업일자(stck_bsop_date)가 오늘 날짜와 일치하는지 확인
    net_data = fetch_today_net_buying("005930", token)
    if not net_data or not net_data.get("trade_date"):
        return False
        
    today_kst = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=9)).strftime("%Y-%m-%d")
    return net_data["trade_date"] == today_kst

def main():
    print("Starting Daily TOP 200 Whale Data Collection...")
    token = get_kis_access_token()
    if not token:
        sys.exit(1)
        
    print("Checking if today is a trading day...")
    if not is_today_market_open(token):
        print("Today is not a trading day (weekend or holiday). Skipping collection.")
        sys.exit(0)
        
    stocks = get_pure_stock_codes()
    print(f"Total pure stocks to process: {len(stocks)}")
    
    results = []
    
    # 약 2000+ 종목 처리
    for idx, s in enumerate(stocks):
        net_data = fetch_today_net_buying(s["code"], token)
        if net_data:
            # API에서 날짜를 못 가져온 경우만 오늘 날짜(시스템 시간)로 대체 (Fallback)
            current_trade_date = net_data["trade_date"] if net_data.get("trade_date") else (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=9)).strftime("%Y-%m-%d")
            
            results.append({
                "trade_date": current_trade_date,
                "stock_code": s["code"],
                "stock_name": s["name"],
                "market": s["market"],
                "frgn_buy": net_data["frgn_buy"],
                "frgn_sell": net_data["frgn_sell"],
                "orgn_buy": net_data["orgn_buy"],
                "orgn_sell": net_data["orgn_sell"],
                "total_net": net_data["total_net"]
            })
        
        # 진행상황 표출 (10개마다)
        if (idx + 1) % 10 == 0:
            print(f"Processed {idx + 1} / {len(stocks)} ...", end="\r")
            sys.stdout.flush()
            
        time.sleep(0.05) # 한투 API Rate limit (20 req / sec) 준수를 위한 지연
    print(f"\nProcessed {len(stocks)} / {len(stocks)} DONE!")
        
    df = pd.DataFrame(results)
    if df.empty:
        print("No data collected.")
        sys.exit(1)
        
    # KOSPI / KOSDAQ 분리 후 TOP 100 추출
    df_kospi = df[df["market"] == "KOSPI"].sort_values(by="total_net", ascending=False).head(100)
    df_kosdaq = df[df["market"] == "KOSDAQ"].sort_values(by="total_net", ascending=False).head(100)
    
    final_df = pd.concat([df_kospi, df_kosdaq])
    final_df = final_df.drop(columns=["total_net"]) # DB에 넣을 땐 불필요
    
    records = final_df.to_dict(orient="records")
    print(f"Extracted Top {len(records)} stocks. Upserting to Supabase...")
    
    # DB Upsert (동일 날짜/코드 중복 방지)
    try:
        supabase.table("daily_whale_top200").upsert(records, on_conflict="trade_date,stock_code").execute()
        print("Upsert successful!")
    except Exception as e:
        print(f"Upsert failed: {e}")
        
    # 과거 데이터(3개월 초과) 삭제 처리
    cleanup_date = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=9) - datetime.timedelta(days=90)).strftime("%Y-%m-%d")
    try:
        supabase.table("daily_whale_top200").delete().lt("trade_date", cleanup_date).execute()
        print(f"Cleanup successful for records older than {cleanup_date}.")
    except Exception as e:
        print(f"Cleanup failed: {e}")

if __name__ == "__main__":
    main()
