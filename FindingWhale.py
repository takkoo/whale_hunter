
import time
import requests
import socket
import uuid
import FinanceDataReader as fdr
import urllib.request
import zipfile
import os
import json
import asyncio
import websockets
from datetime import datetime
from supabase import create_client

import sys

# ⚡ [강제 수집 옵션 감지] python FindingWhale.py --force 명령어로 실행 시 시간/휴일 차단벽 우회
FORCE_RUN = "--force" in sys.argv or "--ignore-time" in sys.argv

def get_market_holidays(supabase_client):
    try:
        res = supabase_client.table("market_holidays").select("holiday_date").execute()
        if res.data:
            return [item['holiday_date'] for item in res.data]
        return []
    except Exception as e:
        return []


import os

# ==========================================
# [ 클라우드 DB 및 인증 정보 세팅 ]
# ==========================================
# .streamlit/secrets.toml 파일을 직접 읽어서 파싱합니다. (streamlit 모듈 없이 동작)
SUPABASE_URL = ""
SUPABASE_KEY = ""
APP_KEY = ""
APP_SECRET = ""
secrets_path = ".streamlit/secrets.toml"

if os.path.exists(secrets_path):
    with open(secrets_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("url") and "=" in line:
                SUPABASE_URL = line.split("=", 1)[1].strip().strip('"\'')
            elif line.startswith("key") and "=" in line:
                SUPABASE_KEY = line.split("=", 1)[1].strip().strip('"\'')
            elif line.startswith("app_key") and "=" in line:
                APP_KEY = line.split("=", 1)[1].strip().strip('"\'')
            elif line.startswith("app_secret") and "=" in line:
                APP_SECRET = line.split("=", 1)[1].strip().strip('"\'')

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

import re

def is_pure_stock(name):
    if not name: return False
    if re.search(r'우$|우B$|우\([A-Za-z0-9]+\)$|우[A-Z]$', name): return False
    if re.search(r'KODEX|TIGER|KINDEX|KBSTAR|ARIRANG|KOSEF|HANARO|ACE|SOL|TIMEFOLIO|히어로즈|스팩|ETN|제\d+호|PLUS|RISE|WON', name, re.IGNORECASE): return False
    return True

# ==========================================
# [ 한국투자증권 Open API 인증 정보 (실전투자) ]
# ==========================================
BASE_URL = "https://openapi.koreainvestment.com:9443"
USER_ID = "VictorLi"


# 글로벌 매핑 테이블 및 마스터 세트
master_stock_dict = {}
hantoo_kospi = set()
hantoo_kosdaq = set()
etf_set = set()
tracked_stocks = set()

# ==========================================
# [ 글로벌 설정 및 실시간 메모리 레지스터 ]
# ==========================================
# 장중 실시간으로 상한가 진입한 종목들을 담아둘 캐시 (당일 🔴상 판독용)
today_upper_limit_set = set()

# 사령탑 설정 기간 내에 과거 상한가 갔던 종목들을 담아둘 캐시 (⭐전상 판독용)
recent_upper_stocks_cache = set()

# ==========================================
# [ 텔레그램 무선 안테나 최종 결선 ]
# ==========================================
TELEGRAM_BOT_TOKEN = "8020734787:AAHjYSfOkK7FsXmINiA7RxepUEd9tHlUUtM"
TELEGRAM_CHANNEL_ID = "-1004375198152"  

# ==========================================
# [1. 초기화 및 환경설정 섹션]
# ==========================================
def get_access_token():
    import json
    import os
    import time
    
    token_file = "kis_token.json"
    
    # 1. 로컬 파일에서 유효한 토큰 읽기 시도
    if os.path.exists(token_file):
        try:
            with open(token_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if time.time() - data.get("timestamp", 0) < 82800:
                    print("✅ 기존 토큰 재사용 (kis_token.json)")
                    return data["token"]
        except Exception as e:
            print(f"⚠️ 기존 토큰 읽기 실패: {e}")

    # 2. 토큰이 없거나 만료된 경우 새로 발급
    print("🔑 한투 서버에 접속하고, 24시간용 보안 토큰 발급 요청.")
    headers = {"content-type": "application/json"}
    body = {
        "grant_type": "client_credentials",
        "appkey": APP_KEY,
        "appsecret": APP_SECRET
    }
    url = f"{BASE_URL}/oauth2/tokenP"
    res = requests.post(url, headers=headers, json=body)
    
    if res.status_code == 200:
        print("✅ 토큰 발급 성공")
        new_token = res.json()["access_token"]
        try:
            with open(token_file, "w", encoding="utf-8") as f:
                json.dump({"token": new_token, "timestamp": time.time()}, f)
        except Exception as e:
            print(f"⚠️ 새 토큰 저장 실패: {e}")
        return new_token
    else:
        print("❌ 토큰 발급 실패:", res.text)
        return None
    
def get_my_ipv4():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    except Exception: 
        ip = '127.0.0.1'
    finally: 
        s.close()
    return ip

def get_my_mac():
    mac_num = hex(uuid.getnode()).replace('0x', '').upper()
    return ':'.join(mac_num[i: i + 2] for i in range(0, 11, 2))

def get_websocket_approval_key():
    print("🔑 실시간 웹소켓 전용 Approval Key 발급 요청 중...")
    url = f"{BASE_URL}/oauth2/Approval"
    headers = {"content-type": "application/json"}
    body = {
        "grant_type": "client_credentials",
        "appkey": APP_KEY,
        "secretkey": APP_SECRET
    }
    res = requests.post(url, headers=headers, data=json.dumps(body))
    if res.status_code == 200:
        print("✅ 웹소켓 승인키 발급 완료!")
        return res.json().get('approval_key')
    else:
        raise Exception(f"❌ 승인키 발급 실패: {res.text}")

def get_hantoo_market_sets():
    kospi_set = set()
    kosdaq_set = set()
    urls = {
        "KOSPI": "https://new.real.download.dws.co.kr/common/master/kospi_code.mst.zip",
        "KOSDAQ": "https://new.real.download.dws.co.kr/common/master/kosdaq_code.mst.zip"
    }
    
    for market, url in urls.items():
        filename = f"{market}_code.mst"
        zip_filename = f"{filename}.zip"
        try:
            urllib.request.urlretrieve(url, zip_filename)
            with zipfile.ZipFile(zip_filename, 'r') as zip_ref:
                zip_ref.extractall()
            
            with open(filename, "r", encoding="cp949") as f:
                for line in f:
                    code = line[:6].strip()
                    if code:
                        if market == "KOSPI":
                            kospi_set.add(code)
                        else:
                            kosdaq_set.add(code)
            os.remove(zip_filename)
            os.remove(filename)
        except Exception as e:
            print(f"한투 마스터 로딩 실패 ({market}): {e}")
            
    return kospi_set, kosdaq_set

# 글로벌 선언부에 추가
ordinary_stock_set = set()

def load_master_data():
    global hantoo_kospi, hantoo_kosdaq, etf_set, master_stock_dict, ordinary_stock_set  
    print("📊 한투 서버에서 KOSPI/KOSDAQ 마스터 파일 직접 수신 및 정밀 분석 중...")
    
    try:
        # 1. Base 결선: KRX 표준 데이터 수신 및 일반 주식 맵핑
        df_krx = fdr.StockListing('KRX')
        
        # 파생 노이즈 키워드 정의
        noise_keywords = ('ETF', 'ETN', 'KODEX', 'TIGER', 'ACE', 'SOL', 'RISE', 'KBSTAR', 'ARIRANG', 'HANARO', 'KOSEF', 'PLUS', 'TIME', '인버스', '레버리지')
        
        ordinary_stock_set.clear() # 레지스터 초기화
        
        for _, row in df_krx.iterrows():
            clean_code = str(row['Code']).strip().zfill(6)
            stock_name = str(row['Name']).strip()
            
            master_stock_dict[clean_code] = stock_name
            
            # 🚨 [핵심 필터링]: 이름에 파생 키워드가 단 하나도 없는 녀석만 '진짜 개별주'로 인정!
            if not any(kw in stock_name.upper() for kw in noise_keywords):
                ordinary_stock_set.add(clean_code)
                #print(f"Ord: {clean_code, stock_name} 추가")

            
        # 2. 한투 서버 순정 마스터 파일 로드
        hantoo_kospi, hantoo_kosdaq = get_hantoo_market_sets()
        
        # 3. 🚨 데이터 타입 불일치 방지 가드레일 장착
        clean_hantoo_kospi = {str(c).strip().zfill(6) for c in hantoo_kospi}
        clean_hantoo_kosdaq = {str(c).strip().zfill(6) for c in hantoo_kosdaq}
        
        hantoo_kospi = clean_hantoo_kospi
        hantoo_kosdaq = clean_hantoo_kosdaq
        
        all_hantoo_codes = hantoo_kospi.union(hantoo_kosdaq)
        etf_keywords = ('ETF', 'ETN', 'KODEX', 'TIGER', 'ACE', 'SOL', 'RISE', 'KBSTAR', 'ARIRANG', 'HANARO', 'KOSEF', 'PLUS', 'TIME', '인버스', '레버리지')
        
        etf_count = 0
        
        # [A회로] 기존 KRX 주식 리스트 명단 중 ETF 키워드 필터링
        for code, name in list(master_stock_dict.items()):
            if any(kw in name.upper() for kw in etf_keywords):
                if code not in etf_set:
                    etf_set.add(code)
                    etf_count += 1

        # [B회로] 한투 마스터에는 살아있으나 KRX 주식 명단에는 없는 레어 소자(ETF/ETN) 강제 병합
        for code in all_hantoo_codes:
            if code not in master_stock_dict:
                etf_set.add(code)
                etf_count += 1
                master_stock_dict[code] = f"미분류_파생소자({code})"

        
        print(f"✅ 한투 마스터 기반 동적 필터링 및 통합 성공!")
        print(f"   📊 분류된 ETF/ETN 고주파 소자: {etf_count}개 셋업 완료")
        print(f"   🏛️ 필터링 완료된 순정 개별 주식 레지스터: {len(ordinary_stock_set)}개 탑재")
        print(f"🎯 총 {len(master_stock_dict)}개 종목의 [코드:이름] 레지스터 빌드 완료!")

    except Exception as e:
        print(f"❌ [마스터 로더 코어 충돌] 정밀 결선 중 예외 발생: {e}")


def clean_old_data():
    from datetime import datetime, timedelta
    one_year_ago = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
    one_month_ago = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    try:
        # 1. 1년 넘은 모든 오래된 데이터 삭제 (개별주 포함)
        supabase.table("whale_log").delete().lt("date", one_year_ago).execute()
        # 2. 1개월 넘은 ETF/ETN 데이터 집중 삭제
        supabase.table("whale_log").delete().eq("asset_type", "ETF").lt("date", one_month_ago).execute()
        
        print(f"🧹 [시스템 초기화] {one_year_ago} 이전 전체 데이터 & {one_month_ago} 이전 ETF 데이터 청소 완료!")
    except Exception as e:
        print(f"⚠️ 시스템 청소 중 알림: {e}")

def init_network_and_tokens():
    global TOKEN, MY_IP, MY_MAC
    TOKEN = get_access_token()
    MY_IP = get_my_ipv4()
    MY_MAC = get_my_mac()
    print(f"📡 IP: {MY_IP} / MAC: {MY_MAC} / 시스템 초기화 완료")

def check_market_open():
    if FORCE_RUN:
        print("⚡ [--force 옵션 감지] 장외시간 및 휴장일 검사를 우회하고 즉시 수집을 진행합니다.")
        return
        
    today_str = datetime.now().strftime('%Y%m%d')
    url = "https://openapi.koreainvestment.com:9443/uapi/domestic-stock/v1/quotations/chk-holiday"
    headers = {
        "content-type": "application/json; charset=utf-8",
        "authorization": f"Bearer {TOKEN}",
        "appkey": APP_KEY,
        "appsecret": APP_SECRET,
        "tr_id": "CTCA0903R"
    }
    params = {'BASS_DT': today_str, 'CTX_AREA_NK': '', 'CTX_AREA_FK': ''}
    try:
        res = requests.get(url, headers=headers, params=params, timeout=5)
        if res.status_code == 200:
            data = res.json().get('output', [])
            if data:
                opnd_yn = data[0].get('opnd_yn', 'Y')
                if opnd_yn == 'N':
                    from datetime import timedelta
                    now = datetime.now()
                    tomorrow = now + timedelta(days=1)
                    target_time = tomorrow.replace(hour=8, minute=0, second=0, microsecond=0)
                    sleep_seconds = (target_time - now).total_seconds()
                    
                    msg = f"🚫 [휴장일 대기] KIS API 확인 결과, 오늘은 휴장일({today_str})입니다. 내일 아침 08:00 까지 대기합니다."
                    print(msg)
                    send_telegram_broadcast(msg)
                    
                    import time
                    time.sleep(sleep_seconds)
                    raise Exception("HOLIDAY_WAIT")
                else:
                    print(f"✅ [개장일 확인] KIS API 결과 오늘은 정상 영업일({today_str})입니다.")
    except Exception as e:
        if str(e) == "HOLIDAY_WAIT":
            raise e
        print(f"⚠️ 휴장일 조회 중 에러 발생 (무시하고 계속 진행): {e}")

# 🚀 [진단 칩셋 복제] 텔레그램 응답을 강제로 화면에 덤프하는 함수
def send_telegram_broadcast(text):
    """
    수집기 엔진이 포착한 메시지를 텔레그램 채널 안테나로 브로드캐스팅하는 송신기
    """
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHANNEL_ID,
        "text": text,
        "parse_mode": "Markdown"
    }
    try:
        if TELEGRAM_BOT_TOKEN != "YOUR_BOT_TOKEN":
            res = requests.post(url, json=payload, timeout=3)
            
            # 🎯 [디버깅 오실로스코프] 텔레그램 서버가 응답한 텍스트를 터미널에 강제로 출력!
            print(f"\n📡 [텔레그램 응답 계측] Status: {res.status_code} | Response: {res.text}\n")
            
    except Exception as e:
        print(f"⚠️ 텔레그램 송신 안테나 노이즈 발생: {e}")

# ==========================================
# [2. 비동기 코어 서킷 섹션]
# ==========================================

def fetch_hantoo_asking_price_residual(code, token, appkey, secret):
    """
    [REST API 저격 프로브] 총 매수 잔량(tot_bidp_rsqn) 핀으로 최종 결선 변경 버전
    """
    try:
        url = "https://openapi.koreainvestment.com:9443/uapi/domestic-stock/v1/quotations/inquire-price"
        
        headers = {
            "content-type": "application/json",
            "authorization": f"Bearer {token}",
            "appkey": appkey, 
            "appsecret": secret,
            "tr_id": "FHKST01010100"
        }
        params = {
            "FID_COND_MRKT_DIV_CODE": "J",
            "FID_INPUT_ISCD": code
        }
        
        import requests
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        res = requests.get(url, headers=headers, params=params, timeout=2, verify=False)
        if res.status_code == 200:
            res_json = res.json()
            # 🟢 상한가 안착 시 총 매수 호가 잔량이 곧 진짜 상한가 대기 물량입니다!
            tot_bidp_rsqn = res_json.get("output", {}).get("tot_bidp_rsqn", "0")
            return f"{int(tot_bidp_rsqn):,}"
        else:
            print(f"⚠️ [한투 서버 거절 응답] Code: {res.status_code} | Reason: {res.text}")
            if "EGW00123" in res.text or "만료된" in res.text:
                raise Exception("EXPIRED_TOKEN")
    except Exception as e:
        if "EXPIRED_TOKEN" in str(e):
            raise
        print(f"⚠️ [REST 프로브] 호가 잔량 획득 실패 (사유: {e})")
    return "계측 실패"



# 🚀 [코어 A 정밀 튜닝] 1분마다 신규 고래 검색 + 수신 즉시 거래대금 상위 순 리소트(Re-sort) 장치
# 글로벌 감시 채널 레지스터 (현재 웹소켓에 실제 등록된 코드 세트)
# 최초 가동 시에는 비어있다가, 장중에 35개 채널이 동적으로 채워지고 빠집니다.
# tracked_stocks = set() 

# 🚀 [코어 A 초고속 엔진 리빌드] 100개 종목 동시 병렬 틱 스캔 및 실시간 스와핑 서킷
async def start_whale_hunting(websocket_queue, db_queue):
    global tracked_stocks, hantoo_kospi, TOKEN, APP_KEY, APP_SECRET, MY_MAC, MY_IP, ordinary_stock_set
    
    # 🟢 개별 종목의 틱을 초고속으로 독립 찌르기 하는 하위 비동기 프로브 소자
    async def probe_single_stock_whale(stock_packet):
        s_code = stock_packet['code']
        s_name = stock_packet['name']
        #today_str = datetime.now().strftime('%Y-%m-%d')
        
        tick_headers = {
            "content-type": "application/json",
            "authorization": f"Bearer {TOKEN}",
            "appkey": APP_KEY, "appsecret": APP_SECRET,
            "tr_id": "FHKST01010300", "custtype": "P"
        }
        tick_params = {"FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": s_code}
        tick_url = f"{BASE_URL}/uapi/domestic-stock/v1/quotations/inquire-ccnl"
        
        whale_score = 0
        valid_ticks_to_save = []
        
        try:
            # 타임아웃을 짧게 주어 한투 서버 응답 지연으로 인한 전체 락인(Lock-in) 방쇄
            res = await asyncio.to_thread(requests.get, tick_url, headers=tick_headers, params=tick_params, timeout=1.5)
            if res.status_code != 200 and ("EGW00123" in res.text or "만료된" in res.text):
                raise Exception("EXPIRED_TOKEN")
            if res.status_code == 200:
                tick_data = res.json()
                ticks = tick_data.get('output', [])
                
                last_price = None
                trade_side = "매수"
                
                for t in reversed(ticks):
                    try:
                        price = int(t['stck_prpr'])
                        volume = int(t['cntg_vol'])
                        amount = price * volume
                        
                        if last_price is not None:
                            if price > last_price:
                                trade_side = "매수"
                            elif price < last_price:
                                trade_side = "매도"
                            # price == last_price 인 경우 이전 방향(trade_side)을 유지 (Zero-tick Rule)
                        else:
                            # 🚀 첫 번째 틱(last_price가 없을 때): 전일종가/시가 대비 매수/매도 분기 (방향미상 완전 철거!)
                            base_prc = int(t.get('stck_sdpr', 0) or t.get('stck_oprc', 0) or price)
                            if base_prc > 0 and price < base_prc:
                                trade_side = "매도"
                            else:
                                trade_side = "매수"
                            
                        last_price = price

                        if amount >= 30000000:
                            t_time = t['stck_cntg_hour']
                            formatted_time = f"{t_time[:2]}:{t_time[2:4]}:{t_time[4:6]}"
                            
                            # 🚨 [신규 수정]: 날짜 파싱 로직 강화 및 '미래 시간(어제 종가)' 필터링
                            t_date = t.get('stck_bsop_date', '')
                            # 현재 PC의 시간(HH:MM:SS)을 가져와서 비교합니다.
                            current_sys_time = datetime.now().strftime('%H:%M:%S')
                            
                            # 1. API가 날짜를 명확히 준 경우
                            if len(t_date) == 8:
                                formatted_date = f"{t_date[:4]}-{t_date[4:6]}-{t_date[6:8]}"
                            # 2. 날짜가 없지만, 틱의 체결 시간이 '현재 PC 시간'보다 미래인 경우
                            # -> 이건 100% 어제(또는 과거)의 장 후반 거래 찌꺼기입니다! 버립니다!
                            elif formatted_time > current_sys_time:
                                continue # 👈 이 틱은 무시하고 다음 틱으로 넘어갑니다.
                            # 3. 날짜가 없고, 틱 시간도 현재 시간 이전인 경우 (오늘 거래로 추정)
                            else:
                                formatted_date = datetime.now().strftime('%Y-%m-%d') # 부득이하게 오늘 날짜 사용
                                
                            # 10억 이상 대왕고래 10점, 1억 이상 왕고래 1점 가중치 연산
                            if amount >= 1000000000:
                                whale_score += 10
                            elif amount >= 100000000:
                                whale_score += 3
                            elif amount >= 30000000:
                                whale_score += 1
                                
                            valid_ticks_to_save.append({
                                "date": formatted_date, 
                                "time": formatted_time, "price": price, "volume": volume,
                                "amount_krw": amount, "side": trade_side
                            })

                    except ValueError:
                        continue
        except Exception as probe_err:
            if "EXPIRED_TOKEN" in str(probe_err):
                raise
            # 특정 소자 통신 불량 시 에러 무시하고 0점 처리하여 생존성 확보
            pass
            
        return {"code": s_code, "name": s_name, "score": whale_score, "ticks": valid_ticks_to_save}

    # 메인 그랜드 레이더 루프
    while True:
        try:
            today_str = datetime.now().strftime('%Y-%m-%d')
            
            # 🕰️ [시간/휴일 차단벽] (--force 옵션이 없을 때만 가동)
            if not FORCE_RUN:
                now_time = datetime.now().time()
                market_start = datetime.strptime("09:00:00", "%H:%M:%S").time()
                market_end = datetime.strptime("15:35:00", "%H:%M:%S").time()
                
                if now_time < market_start or now_time > market_end:
                    await asyncio.sleep(60)
                    continue
                    
                if datetime.now().weekday() >= 5:
                    await asyncio.sleep(60)
                    continue
                
                if today_str in get_market_holidays(supabase):
                    await asyncio.sleep(60)
                    continue

            print(f"\n🔍 [{datetime.now().strftime('%H:%M:%S')}] 조건검색 레이더 가동 (100개 전수조사 시작)...")
            
            headers = {
                "content-type": "application/json",
                "authorization": f"Bearer {TOKEN}",
                "appkey": APP_KEY, "appsecret": APP_SECRET,
                "tr_id": "HHKST03900400", "custtype": "P"
            }
            params = {
                "user_id": USER_ID, "seq": "2",
                "mac_address": MY_MAC, "ip": MY_IP
            }
            
            url = f"{BASE_URL}/uapi/domestic-stock/v1/quotations/psearch-result"
            res = await asyncio.to_thread(requests.get, url, headers=headers, params=params)
            
            if res.status_code != 200:
                print("❌ [코어 A] 조건검색 API 호출 실패:", res.text)
                await asyncio.sleep(10)
                continue
                
            data = res.json()
            raw_stock_list = data.get('output2', [])
            print(f"🔥 조건식 포착 원시 소자: {len(raw_stock_list)}개 발견")
            
            if not raw_stock_list:
                await asyncio.sleep(60)
                continue

            print("📡 [고속 병렬 채널 개통] 100개 종목 동시 고속 스캔 슛...")
            tasks = [probe_single_stock_whale(stock) for stock in raw_stock_list]
            scored_stocks = await asyncio.gather(*tasks)

            # ------------------------------------------------------------------
            # 🔌 [ 역발상 마스터 스펙: 순정 개별주 검전 및 파생 소자 바닥 침전 필터 ]
            # ------------------------------------------------------------------
            # 🚨 [핵심 결선]: 누락되었던 파생 상품 키워드 전하 공급 레지스터 선언!
            noise_keywords = ('ETF', 'ETN', 'KODEX', 'TIGER', 'ACE', 'SOL', 'RISE', 'KBSTAR', 'ARIRANG', 'HANARO', 'KOSEF', 'PLUS', 'TIME', '인버스', '레버리지')
            
            for s in scored_stocks:
                clean_target_code = str(s.get('code', '')).strip().zfill(6)
                s_name = str(s.get('name', '')).strip()
                
                # 가드 A: 이름 기반 1차 검전 (이제 정상 가동!)
                is_etf_name = any(kw in s_name.upper() for kw in noise_keywords)
                
                # 우선주 필터링 (이름이 '우' 또는 '우B' 등으로 끝나고, 종목코드가 '0'으로 끝나지 않는 경우)
                is_preferred = (s_name.endswith('우') or s_name.endswith('우B') or s_name.endswith('우C') or s_name.endswith('우(전환)')) and clean_target_code[-1] != '0'
                
                # 가드 B: 확실한 정품 개별주 세트 대조 (문자열 대 문자열 직결)
                is_not_ordinary = (clean_target_code not in ordinary_stock_set)
                
                # 둘 중 하나라도 걸리면 파생 노이즈로 낙인찍어 맨 밑바닥으로 수몰시킵니다.
                if is_etf_name or is_not_ordinary or is_preferred:
                    s['score'] = -9999
            
            # 고래 점수 기반으로 내림차순 정렬
            scored_stocks.sort(key=lambda x: x['score'], reverse=True)
            
            # 최정예 35종목 추출 및 동적 스와핑
            top_35_list = scored_stocks[:35]
            current_top_35_codes = {s['code'] for s in top_35_list}
            
            # 채널 아웃된 소자 해제
            unreg_targets = tracked_stocks - current_top_35_codes
            for old_code in unreg_targets:
                await websocket_queue.put(f"UNREG:{old_code}")
                tracked_stocks.remove(old_code)
                print(f"📉 [채널 오프로드] 수급 이탈 종목 소켓 해제: {master_stock_dict.get(old_code, old_code)}")
            
            print("\n📊 [레이더 고속 재정렬 완료 - 최정예 실시간 관제 라인업 5] 📊")
            for idx, s in enumerate(top_35_list[:5]):
                print(f"  [{idx+1}위] {s['name']}({s['code']}) -> 고래 활동지수: {s['score']}점")
            print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")

            today_str = datetime.now().strftime('%Y-%m-%d')
            
            # 신규 소자 채널 등록 및 과거 데이터 백업
            for target in top_35_list:
                s_code = target['code']
                s_name = target['name']
                
                if s_code not in tracked_stocks:
                    # 🚨 [신규 추가]: 틱 데이터가 있으면 진짜 날짜를 뽑고, 없으면 DB 체크를 스킵합니다.
                    if target['ticks']:
                        target_date = target['ticks'][0]['date']
                        print(f"🚀 [채널 온로드] 신규 고래 진입 소켓 등록: {s_name}({s_code}) [기준 영업일: {target_date}]")
                        
                        try:
                            # 🚨 [핵심 수정]: PC 날짜(today_str) 대신 API 진짜 날짜(target_date)로 DB 조회!
                            exist_res = await asyncio.to_thread(
                                supabase.table("whale_log")
                                .select("time, volume")
                                .eq("date", target_date) 
                                .eq("code", s_code)
                                .execute
                            )
                            already_saved = {(r['time'], int(r['volume'])) for r in exist_res.data} if exist_res.data else set()
                        except:
                            already_saved = set()
                    else:
                        # 고래 틱이 없으면 중복 검사할 필요 없이 빈 세트로 넘깁니다.
                        print(f"🚀 [채널 온로드] 신규 고래 진입 소켓 등록: {s_name}({s_code}) [틱 대기중]")
                        already_saved = set()

                    for tick in target['ticks']:
                        if (tick['time'], tick['volume']) not in already_saved:
                            a_type = "ETF" if s_code in etf_set else "개별주식"
                            m_type = "KOSPI" if s_code in hantoo_kospi else "KOSDAQ"
                            
                            await db_queue.put({
                                "task_type": "INSERT_LOG",
                                "data": {
                                    "date": tick['date'], # 👈 INSERT 할 때도 개별 틱의 진짜 날짜로 꽂아 넣습니다!
                                    "time": tick['time'],
                                    "code": s_code, "name": s_name,
                                    "price": tick['price'], "volume": tick['volume'],
                                    "amount_krw": tick['amount_krw'], "asset_type": a_type,
                                    "market_type": m_type, "side": tick['side']
                                }
                            })

                            #==========================================================================
                            # 🚨 [신규 배선]: Core A 백업 레이더 전용 텔레그램 패스트 트랙 개통
                            # =========================================================================
                            # 웹소켓 미등록 종목이 기습적으로 3억 이상 터뜨렸을 때 최초 1회 즉시 속보 격발!
                            if tick['amount_krw'] >= 300000000 and is_pure_stock(s_name):
                                is_upper_today = s_name in today_upper_limit_set
                                is_upper_recent = s_name in recent_upper_stocks_cache
                                
                                # 뱃지 낙인 처리
                                if is_upper_today:
                                    badge = "[🔴상]"
                                elif is_upper_recent:
                                    badge = "[⭐전상]"
                                else:
                                    badge = "[Whale]"
                                    
                                whale_msg = f"🐳 *{badge} 백업 레이더 고래 포착!*\n" \
                                            f"━━━━━━━━━━━━━━━\n" \
                                            f"▪️ *종목명:* {s_name} ({s_code})\n" \
                                            f"▪️ *포지션:* {tick['side']}\n" \
                                            f"▪️ *체결가:* {tick['price']:,}원\n" \
                                            f"▪️ *체결액:* *{tick['amount_krw'] / 100000000:,.1f}억* 원\n" \
                                            f"▪️ *시간:* {tick['time']} (백업 포착)\n" \
                                            f"━━━━━━━━━━━━━━━"
                                            
                                await db_queue.put({"task_type": "TELEGRAM_SEND", "message": whale_msg})
                                print(f"   📢 [Core A 백업 트리거] {badge} {s_name} | {tick['amount_krw']/100000000:.1f}억 텔레그램 사서함 토스")
                            # =========================================================================
                    
                    tracked_stocks.add(s_code)
                    await websocket_queue.put(f"REG:{s_code}")
            
            # 동적 튜닝 완료 후 60초 대기전압 인가
            await asyncio.sleep(60)

        except Exception as e:
            if "EXPIRED_TOKEN" in str(e):
                print("⚠️ [코어 A] 토큰 만료 감지! 시스템 강제 재기동을 요청합니다.")
                import os
                if os.path.exists("kis_token.json"):
                    os.remove("kis_token.json")
                raise
            print(f"❌ [코어 A 레이더 코어 충돌]: {e}")
            await asyncio.sleep(10)


# 🚀 [코어 B 보수] 한투 전용 PINGPONG 하트비트 반사 릴레이 결선 및 내장 핑 리셋
async def whale_websocket_engine(approval_key, websocket_queue, db_queue):
    global tracked_stocks, master_stock_dict, today_upper_limit_set, recent_upper_stocks_cache
    ws_url = "ws://ops.koreainvestment.com:21000"
    
    while True:
        try:
            print("🔌 [코어 B] 웹소켓 터널 개통 시도 중...")
            # 🟢 [교정] ping_interval=None 으로 설정하여 라이브러리 자체 프로토콜 핑을 차단 (단선 버그 박멸)
            async with websockets.connect(ws_url, ping_interval=None) as websocket:
                print("✅ [코어 B] 웹소켓 서버 연결 완료! 실시간 관제 시작...")
                
                if tracked_stocks:
                    for code in list(tracked_stocks):
                        sub_req = {"header": {"approval_key": approval_key, "custtype": "P", "tr_type": "1", "content-type": "utf-8"}, "body": {"input": {"tr_id": "H0STCNT0", "tr_key": code}}}
                        await websocket.send(json.dumps(sub_req))
                        await asyncio.sleep(0.1)
                
                async def queue_listener():
                    try:
                        while True:
                            code = await websocket_queue.get()
                            sub_req = {"header": {"approval_key": approval_key, "custtype": "P", "tr_type": "1", "content-type": "utf-8"}, "body": {"input": {"tr_id": "H0STCNT0", "tr_key": code}}}
                            await websocket.send(json.dumps(sub_req))
                            await asyncio.sleep(0.1)
                    except asyncio.CancelledError:
                        pass
                
                listener_task = asyncio.create_task(queue_listener())
                
                try:
                    while True:
                        recv_data = await websocket.recv()
                        
                        # 🟢 [하트비트 루프 결선] 한투가 보낸 텍스트 PINGPONG을 그대로 반사(Echo) 송신하여 세션 무한 유지!
                        if "PINGPONG" in recv_data:
                            await websocket.send(recv_data)
                            continue
                        
                        if recv_data.startswith('0|') or recv_data.startswith('1|'):
                            parts = recv_data.split('|')
                            if len(parts) >= 4:
                                tick_str = parts[3]
                                t_data = tick_str.split('^')
                                
                                if len(t_data) >= 22:
                                    code = t_data[0]
                                    time_str = t_data[1]
                                    price = int(t_data[2])
                                    volume = int(t_data[12]) 
                                    acml_vol = int(t_data[13]) 
                                    amount = price * volume
                                    
                                    try:
                                        fluct_rate = float(t_data[5])
                                    except:
                                        fluct_rate = 0.0
                                        
                                    trade_side = "매수" if t_data[21] == '5' else "매도"
                                    s_name = master_stock_dict.get(code, code)
                                    today_str = datetime.now().strftime('%Y-%m-%d')
                                    formatted_time = f"{time_str[:2]}:{time_str[2:4]}:{time_str[4:6]}"
                                    
                                    if fluct_rate >= 29.5 and (s_name not in today_upper_limit_set):
                                        print(f"🚨 [🔴상방 최초 진입 속보!] {formatted_time} | {s_name} 상한가 도달!")
                                        today_upper_limit_set.add(s_name)
                                        
                                        await db_queue.put({
                                            "task_type": "INSERT_UPPER_LIMIT",
                                            "data": {"code": code, "name": s_name, "recorded_date": today_str}
                                        })
                                        
                                        await db_queue.put({
                                            "task_type": "TELEGRAM_SEND_UPPER_LIMIT",
                                            "code": code, "name": s_name, "price": price,
                                            "acml_vol": acml_vol, "time": formatted_time
                                        })

                                    if amount >= 30000000:
                                        a_type = "ETF" if code in etf_set else "개별주식"
                                        m_type = "KOSPI" if code in hantoo_kospi else "KOSDAQ"
                                        
                                        # 1. DB 로그 저장은 3천만 원 이상 전수 수집
                                        await db_queue.put({
                                            "task_type": "INSERT_LOG",
                                            "data": {
                                                "date": today_str, "time": formatted_time, "code": code, "name": s_name,
                                                "price": price, "volume": volume, "amount_krw": amount,
                                                "asset_type": a_type, "market_type": m_type, "side": trade_side
                                            }
                                        })
                                        
                                        # =========================================================================
                                        # 🚨 [신규 배선]: 10억 차단벽 제거 및 상한가/전상 가속 패스 채널 개통
                                        # =========================================================================
                                        # 현재 종목이 상한가 세트나 전상 캐시에 존재하는지 검전
                                        is_upper_today = s_name in today_upper_limit_set
                                        is_upper_recent = s_name in recent_upper_stocks_cache
                                        
                                        # [필터 기준 선언]: 특수 종목이거나, 일반 종목이면서 3억 이상 터진 경우 텔레그램 트리거 가동!
                                        # (단, ETF와 우선주는 텔레그램 송출 대상에서 제외)
                                        if (is_upper_today or is_upper_recent or (amount >= 300000000)) and is_pure_stock(s_name):
                                            
                                            # 뱃지 낙인 처리
                                            if is_upper_today:
                                                badge = "[🔴상]"
                                            elif is_upper_recent:
                                                badge = "[⭐전상]"
                                            else:
                                                badge = "[Whale]"
                                                
                                            whale_msg = f"🐳 *{badge} 거대 고래 포착!*\n" \
                                                        f"━━━━━━━━━━━━━━━\n" \
                                                        f"▪️ *종목명:* {s_name} ({code})\n" \
                                                        f"▪️ *포지션:* {trade_side}\n" \
                                                        f"▪️ *체결가:* {price:,}원 ({fluct_rate:+.2f}%)\n" \
                                                        f"▪️ *체결액:* *{amount / 100000000:,.1f}억* 원\n" \
                                                        f"▪️ *시간:* {formatted_time}\n" \
                                                        f"━━━━━━━━━━━━━━━"
                                                        
                                            await db_queue.put({"task_type": "TELEGRAM_SEND", "message": whale_msg})
                                            print(f"   🚀 [텔레그램 큐 송신 완료] {badge} {s_name} | {amount/100000000:.1f}억")
                                        # =========================================================================
                finally:
                    listener_task.cancel()
                    
        except Exception as e:
            print(f"❌ [코어 B] 실시간 터널 단선 감지 (사유: {e})")
            await asyncio.sleep(5)

# 🎯 [Core C] 23시간 30분짜리 시스템 리셋 타이머 소자
async def token_lifecycle_timer():
    reboot_delay = 23.5 * 3600  
    await asyncio.sleep(reboot_delay)
    print("\n⏰ [타이머 인터럽트] 토큰 발급 후 23시간 30분이 경과하여 소프트 리셋을 트리거합니다...")
    raise Exception("SCHEDULED_TOKEN_REFRESH")


# 🗄️ [Core D 개조] 비동기 non-blocking DB 인서트 + 텔레그램 발송 분기 워커
async def supabase_db_worker(db_queue):
    print("🗄️ [Core D] 백그라운드 DB 저장 및 텔레그램 사서함 가동 완료.")
    while True:
        try:
            task_packet = await db_queue.get()
            task_type = task_packet.get("task_type", "INSERT_LOG")
            
            # [분기 1] 일반/고래 체결 로그 DB 저장
            if task_type == "INSERT_LOG":
                insert_data = task_packet["data"]
                await asyncio.to_thread(supabase.table("whale_log").insert(insert_data).execute)
                
            # [분기 2] 실시간 상한가 종목 DB 기록
            elif task_type == "INSERT_UPPER_LIMIT":
                upper_data = task_packet["data"]
                await asyncio.to_thread(supabase.table("upper_limit_stocks").insert(upper_data).execute)
            
            # 🟢 [분기 3 신설] 상한가 실시간 안착 전용 비동기 스나이퍼 버퍼 회로
            elif task_type == "TELEGRAM_SEND_UPPER_LIMIT":
                code = task_packet["code"]
                s_name = task_packet["name"]
                price = task_packet["price"]
                acml_vol = task_packet["acml_vol"]
                formatted_time = task_packet["time"]
                
                # 1. 백그라운드에서 한투 REST API 딱 한 발만 사격 (0.08초 레이턴시 혼자 감당)
                residual_shares = await asyncio.to_thread(
                    fetch_hantoo_asking_price_residual, 
                    code, 
                    TOKEN,
                    APP_KEY, 
                    APP_SECRET
                )
                
                # 2. 중복 퍼센트 제거하고 대기물량 + 당일총거래량 결선 가공
                compact_upper_msg = (
                    f"📢 *[🔴상] 상한가 실시간 안착 속보*\n\n"
                    f"▪️ *종목명:* {s_name}\n"
                    f"▪️ *안착가:* {price:,}원 (대기잔량: {residual_shares} 주)\n"
                    f"▪️ *총거래량:* {acml_vol:,} 주\n\n"
                    f"⚡ 시장 주도주 족보 등록 완료!"
                )
                
                # 3. 텔레그램 무선 안테나 발송
                await asyncio.to_thread(send_telegram_broadcast, compact_upper_msg)
                
            # [분기 4] 일반 텔레그램 브로드캐스팅
            elif task_type == "TELEGRAM_SEND":
                msg_text = task_packet["message"]
                await asyncio.to_thread(send_telegram_broadcast, msg_text)
                
            db_queue.task_done()
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"⚠️ [Core D] 백그라운드 워커 처리 실패 사유: {e}")
            await asyncio.sleep(1)


# 🔍 [Core E 개조] 1분 주기 조건검색 기반 상한가 전수조사 스캐너
async def upper_limit_poller_engine(db_queue):
    global TOKEN, APP_KEY, APP_SECRET, MY_MAC, MY_IP, today_upper_limit_set
    print("📡 [Core E] 1분 주기 상한가 전수조사 폴러 (조건검색 엔진) 가동 준비 완료.")
    
    # 우리가 매일 잘 쓰고 있는 그 튼튼한 조건검색 URL!
    url = f"{BASE_URL}/uapi/domestic-stock/v1/quotations/psearch-result"
    
    headers = {
        "content-type": "application/json",
        "authorization": f"Bearer {TOKEN}",
        "appkey": APP_KEY, "appsecret": APP_SECRET,
        "tr_id": "HHKST03900400", # 조건검색 전용 TR ID (이건 검증됨!)
        "custtype": "P"
    }
    
    while True:
        try:
            today_str = datetime.now().strftime('%Y-%m-%d')
            current_time_str = datetime.now().strftime('%H:%M:%S')
            
            # 🕰️ [시간 차단벽]: 장시간(09:00 ~ 15:35) 외에는 상한가 폴러 가동 중지 (--force 옵션 시 우회)
            if not FORCE_RUN:
                now_time = datetime.now().time()
                market_start = datetime.strptime("09:00:00", "%H:%M:%S").time()
                market_end = datetime.strptime("15:35:00", "%H:%M:%S").time()
                
                if now_time < market_start or now_time > market_end:
                    await asyncio.sleep(60)
                    continue
                    
                # 🕰️ [주말/휴일 차단벽]
                if datetime.now().weekday() >= 5:
                    await asyncio.sleep(60)
                    continue
                
                if today_str in get_market_holidays(supabase):
                    await asyncio.sleep(60)
                    continue
                
            current_time_str = datetime.now().strftime('%H:%M:%S')
            
            print(f"📡 [Core E] 상한가 전수 스캔 시작... ({current_time_str})")
            
            # 🚨 [주의]: HTS에서 만드신 '상한가 전용 조건식'의 시퀀스 번호(seq)를 여기에 꼭 적어주세요!
            # 예: 일반 고래 조건식이 1번이면, 상한가 조건식은 2번
            UPPER_LIMIT_SEQ = "1" 
            
            params = {
                "user_id": USER_ID, "seq": UPPER_LIMIT_SEQ,
                "mac_address": MY_MAC, "ip": MY_IP
            }
            
            try:
                res = await asyncio.to_thread(requests.get, url, headers=headers, params=params, timeout=5)
                
                if res.status_code == 200:
                    data = res.json()
                    upper_list = data.get('output2', [])
                    
                    if upper_list:
                        print(f"🔥 [Core E] 상한가 검색식 포착: {len(upper_list)}개 발견")
                        
                    for item in upper_list:
                        s_name = item.get('name', '').strip()
                        code = item.get('code', '')
                        
                        # 조건검색 결과에는 현재가나 누적거래량이 안 들어올 수 있으므로 기본값 0 처리
                        # (정확한 가격/거래량은 텔레그램 보낼 때 fetch_hantoo_asking_price_residual 에서 가져와도 됩니다)
                        price = 0
                        acml_vol = 0 
                        
                        if s_name and (s_name not in today_upper_limit_set):
                            print(f"🔥 [상한가 폴러 락온!] {s_name}({code}) 신규 상한가 감지!")
                            today_upper_limit_set.add(s_name)
                            
                            await db_queue.put({
                                "task_type": "INSERT_UPPER_LIMIT",
                                "data": {"code": code, "name": s_name, "recorded_date": today_str}
                            })
                            
                            # 텔레그램 송출은 ETF 및 우선주(순수 주식이 아닌 경우) 제외
                            if is_pure_stock(s_name):
                                await db_queue.put({
                                    "task_type": "TELEGRAM_SEND_UPPER_LIMIT",
                                    "code": code, "name": s_name, "price": price,
                                    "acml_vol": acml_vol, "time": current_time_str
                                })
                else:
                    print(f"⚠️ [Core E] 조건검색 스캔 실패 (상태코드: {res.status_code}, 메시지: {res.text})")
                    if "EGW00123" in res.text or "만료된" in res.text:
                        raise Exception("EXPIRED_TOKEN")
            
            except Exception as api_err:
                if "EXPIRED_TOKEN" in str(api_err):
                    print("⚠️ [Core E] 토큰 만료 감지! 시스템 강제 재기동을 요청합니다.")
                    import os
                    if os.path.exists("kis_token.json"):
                        os.remove("kis_token.json")
                    raise
                print(f"⚠️ [Core E] API 호출 타임아웃/에러: {api_err}")
            
            await asyncio.sleep(60)
            
        except Exception as e:
            print(f"❌ [Core E] 폴러 메인 루프 치명적 에러: {e}")
            await asyncio.sleep(10)


# 🎛️ [메인 부트로더 개조] 가동 시 사령탑 설정 동기화 배선 연결
async def main_async_executor():
    global recent_upper_stocks_cache, today_upper_limit_set
    websocket_queue = asyncio.Queue()
    db_queue = asyncio.Queue() 
    
    # ------------------------------------------------------------------
    # 🔌 [신규 회로] 부팅 시 대시보드 사령탑의 '전상 기한 레지스터' 동기화
    # ------------------------------------------------------------------
    print("🛰️ 사령탑 시스템 제어 레지스터 동기화 중...")
    try:
        settings_res = supabase.table("system_settings").select("*").eq("key", "prev_upper_limit_window_days").execute()
        window_days = int(settings_res.data[0]['value']) if settings_res.data else 3
        print(f"✅ 동기화 완료! 현재 사령탑 지정 [전상 윈도우]: {window_days}일")
        
        # 설정된 일수 범위 내의 과거 상한가 기록 긁어와서 캐시에 적재
        # Supabase SQL 표기법 상 'recorded_date'가 현재 날짜로부터 window_days 이내인 것 스캔
        from datetime import datetime, timedelta
        start_date = (datetime.now() - timedelta(days=window_days)).strftime('%Y-%m-%d')
        
        past_upper_res = supabase.table("upper_limit_stocks").select("name").gte("recorded_date", start_date).execute()
        if past_upper_res.data:
            recent_upper_stocks_cache = set([item['name'] for item in past_upper_res.data])
        print(f"🧠 [⭐전상] 후보군 족보 명단 {len(recent_upper_stocks_cache)}개 RAM 탑재 완료!")
        
        # ------------------------------------------------------------------
        # 🔌 [당일 상한가 알림 중복 방지] 재가동 시 이미 DB에 있는 오늘 상한가 종목 불러오기
        # ------------------------------------------------------------------
        today_str = datetime.now().strftime('%Y-%m-%d')
        today_upper_res = supabase.table("upper_limit_stocks").select("name").eq("recorded_date", today_str).execute()
        if today_upper_res.data:
            today_upper_limit_set = set([item['name'] for item in today_upper_res.data])
            print(f"🔄 [재가동 복구] 금일 기발송 상한가 종목 {len(today_upper_limit_set)}개 텔레그램 중복 발송 차단 완료!")
    except Exception as e:
        print(f"⚠️ 사령탑 동기화 중 노이즈 발생 (기본값 3일 가동): {e}")
    # ------------------------------------------------------------------
    
    approval_key = get_websocket_approval_key()
    print("🚀 [오위일체 레이더 점화] 모든 시스템 코어를 스케줄러에 등록합니다.")
    
    await asyncio.gather(
        start_whale_hunting(websocket_queue, db_queue),                  # Core A
        whale_websocket_engine(approval_key, websocket_queue, db_queue), # Core B
        token_lifecycle_timer(),                                         # Core C
        supabase_db_worker(db_queue),                                    # Core D
        upper_limit_poller_engine(db_queue),                             # 🚨 Core E (1분 주기 상한가 스캐너 신설!)
        metadata_updater_loop()                                          # 💡 Core F (메타데이터 자동 갱신!)
    )

async def metadata_updater_loop():
    """매 1시간마다 stock_metadata.json을 확인하여 당일 데이터가 아니면 백그라운드 갱신"""
    import subprocess
    import json
    import os
    import sys
    from datetime import datetime
    
    script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scripts", "fetch_stock_metadata.py")
    metadata_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stock_metadata.json")
    
    while True:
        try:
            today_str = datetime.now().strftime("%Y-%m-%d")
            needs_update = True
            
            if os.path.exists(metadata_path):
                with open(metadata_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    last_updated = data.get("_meta", {}).get("last_updated_date", "")
                    if last_updated == today_str:
                        needs_update = False
                        
            if needs_update:
                print(f"🔄 [메타데이터 갱신] 금일({today_str}) 시장 경보 데이터가 없습니다. 자동 수집을 시작합니다.")
                # subprocess로 실행하여 비동기 루프 차단 방지
                subprocess.Popen([sys.executable, script_path])
                
        except Exception as e:
            print(f"⚠️ 메타데이터 갱신 루프 오류: {e}")
            
        # 1시간 대기
        await asyncio.sleep(3600)


# 💡 무인 가동 그랜드 루프
if __name__ == "__main__":
    while True:  
        try:
            print("🚀 [엔진 초기 기동] 시스템을 초기화 기동합니다...")
            init_network_and_tokens() 
            check_market_open()

            if FORCE_RUN:
                import subprocess
                print("⚡ [--force 옵션 감지] 오늘자 외/기 TOP100 및 메타데이터 자동 수집을 즉시 시작합니다.")
                top200_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scripts", "fetch_daily_top200.py")
                meta_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scripts", "fetch_stock_metadata.py")
                subprocess.Popen([sys.executable, top200_script])
                subprocess.Popen([sys.executable, meta_script])

            # ------------------------------------------------------------------
            #send_telegram_broadcast("🚨 [관제탑] 수집기 메인 안테나 수동 기동 테스트! 통신 양호한가?")
            # ------------------------------------------------------------------

            print("데이터베이스 확인 및 정리 준비중...")
            clean_old_data()
            load_master_data() 
            
            # 비동기 영역 런타임 가동
            asyncio.run(main_async_executor())
            
        except Exception as e:
            print(f"\n🚨 [비상 하드웨어 와치독] 시스템 DOWN !! 에러 원인: {e}")
            print("⏳ 30초간 시스템 안정화 후, 자동으로 마스터 리셋 진행..\n")
            time.sleep(30)