import streamlit as st
st.set_page_config(page_title="know-lbig radar", page_icon="🐳", layout="wide")
import pandas as pd
pd.set_option("styler.render.max_elements", 10000000)  # 대용량 데이터프레임 스타일링 렌더링 허용 (Styler 제한 해제)

# 🔥 [무적의 스크롤 리셋 꼼수] 메뉴를 이동하면 스크롤이 리셋되는 원리를 이용한 강제 화면 전환!
# (사용자 요청으로 제거됨 - 수동 스크롤 방식으로 변경)
import plotly.express as px
from supabase import create_client
import datetime
from streamlit_autorefresh import st_autorefresh  # 타이머 추가!
import streamlit.components.v1 as components  # 🔌 독립 소자 인가를 위한 컴포넌트 임포트
import hashlib
import base64
import re
import plotly.graph_objects as go  # 🟢 Multi-layer 차트용 소자 임포트
from plotly.subplots import make_subplots
from supabase import create_client  # 🔌 Supabase 커넥터 필수!
from datetime import datetime, timedelta
import FinanceDataReader as fdr
import plotly.express as px
import requests
import json
import uuid
import io
from PIL import Image
from streamlit_paste_button import paste_image_button
import openai
# ------------------------------------------------------------------
# 📡 Supabase 접속 장치 인가 (Streamlit Secrets 사용!)
# ------------------------------------------------------------------
SUPABASE_URL = st.secrets["supabase"]["url"]
SUPABASE_KEY = st.secrets["supabase"]["key"]

# 🚀 [메모리 누수 방어] Streamlit의 캐싱을 통해 커넥션 풀(Connection Pool)이 매 1분마다 무한히 생성되는 것을 막습니다!
@st.cache_resource(show_spinner=False)
def init_supabase_client():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = init_supabase_client()

# ------------------------------------------------------------------
# 🗺️ [내비게이션 동기화] 브라우저 뒤로가기(Query Params) 지원 (상단: URL -> State)
# ------------------------------------------------------------------

# 1. JS popstate로부터 넘어온 raw 쿼리 스트링 처리 (버그 회피용)
raw_qs = st.session_state.get("popstate_sync", "")
if raw_qs:
    # 한 번 읽었으면 위젯 렌더링을 위해 비웁니다.
    st.session_state["popstate_sync"] = ""

# 2. 통신용 숨겨진 텍스트 인풋 렌더링
st.markdown('<div id="url_sync_marker" style="display:none;"></div>', unsafe_allow_html=True)
st.text_input("Popstate Sync", key="popstate_sync", label_visibility="collapsed")
st.markdown("""
<style>
    div[data-testid="stElementContainer"]:has(#url_sync_marker) + div[data-testid="stElementContainer"] {
        display: none !important;
    }
</style>
""", unsafe_allow_html=True)

def apply_query_params(raw_qs):
    params = {}
    if raw_qs:
        import urllib.parse
        if raw_qs.startswith("?"):
            raw_qs = raw_qs[1:]
        parsed = urllib.parse.parse_qs(raw_qs)
        for k, v in parsed.items():
            params[k] = v[0]
    else:
        params = {k: st.query_params.get(k) for k in st.query_params}

    page = params.get("page")
    if page and page != st.session_state.get("last_page"):
        st.session_state['scrn_select_radio'] = page
        st.session_state["last_page"] = page

    upper = params.get("upper")
    if upper is not None and upper != st.session_state.get("last_upper"):
        st.session_state['upper_limit_filter'] = (upper == "true")
        st.session_state["last_upper"] = upper

    view = params.get("view")
    if view and view != st.session_state.get("last_view"):
        st.session_state['brag_view_mode'] = view
        st.session_state["last_view"] = view

    post_id = params.get("post_id")
    if post_id and post_id != st.session_state.get("last_post_id"):
        try:
            st.session_state['brag_selected_post'] = int(post_id)
        except ValueError:
            st.session_state['brag_selected_post'] = post_id
        st.session_state["last_post_id"] = post_id
    elif "post_id" not in params and st.session_state.get("last_post_id") is not None:
        st.session_state['brag_selected_post'] = None
        st.session_state["last_post_id"] = None

apply_query_params(raw_qs)

# 🔒 [전역 보안 점검] 비회원이 URL 조작이나 로그아웃을 통해 회원 전용 화면에 머무는 것 차단
# 위젯이 렌더링되기 전이므로 여기서 session_state를 변경해도 StreamlitAPIException이 발생하지 않습니다.
if not st.session_state.get('authenticated', False):
    _scrn = st.session_state.get('scrn_select_radio', "체결 로그")
    _search = st.session_state.get('search_input_val', "")
    if _scrn in ["TOP 10 화면", "수익율 화면", "상선고 화면", "기간 누적 폭주"] or st.session_state.get('upper_limit_filter', False) or _search:
        st.session_state['scrn_select_radio'] = "체결 로그"
        st.session_state['upper_limit_filter'] = False
        st.session_state['last_search_keyword'] = ""
        st.session_state['search_input_val'] = "" 
        st.query_params.clear()

# 🚀 [브라우저 뒤로가기 강제 동기화 패치]
import streamlit.components.v1 as components
components.html(
    """
    <script>
        const parentWindow = window.parent || window;
        if (!parentWindow.hasPopStateListener) {
            parentWindow.addEventListener("popstate", () => {
                const inputs = parentWindow.document.querySelectorAll('input[aria-label="Popstate Sync"]');
                if (inputs.length > 0) {
                    const input = inputs[0];
                    const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
                    setter.call(input, parentWindow.location.search);
                    input.dispatchEvent(new Event('input', { bubbles: true }));
                    input.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', keyCode: 13, bubbles: true }));
                }
            });
            parentWindow.hasPopStateListener = true;
        }
    </script>
    """,
    height=0, width=0
)

# 🌟 [신규 2026-07-30] 표(st.dataframe) 행(row) 마우스 오버 하이라이트 (하늘색 형광펜 효과)
# 배경: 긴 표(골든픽/실시간/상한가/외기 등)에서 맨 왼쪽~맨 오른쪽 컬럼을 눈으로 따라갈 때
#       지금 보고 있는 행이 어디인지 놓치기 쉬워서, 커서가 위치한 행 전체를 하늘색 반투명으로 강조.
# ⚠️ 참고: st.dataframe은 Glide Data Grid(캔버스) 기반이라 CSS :hover 의사클래스를 행 단위로 못 쓰기 때문에,
#    JS로 마우스 Y좌표 → 행 인덱스를 계산해서 그 위치에 오버레이 박스를 그리는 방식으로 구현함.
#    기본 행높이(ROW_H)/헤더높이(HEADER_H)는 Streamlit 기본값(35px)으로 가정 — 실제 화면에서 밴드 위치가
#    살짝 어긋나 보이면 몇 px 어긋났는지 알려주면 보정 가능.
components.html(
    """
    <script>
        const parentWindow = window.parent || window;
        const ROW_H = 35;
        const HEADER_H = 35;
        const HILITE_COLOR = "rgba(88, 134, 163, 0.28)"; // 🔧 [수정 2026-07-30] 흰 글자가 묻힌다는 피드백으로 하늘색을 35% 더 어둡게 조정

        function bindRowHoverHighlight(container) {
            if (container.dataset.hoverBound === "1") return;
            container.dataset.hoverBound = "1";

            const cs = parentWindow.getComputedStyle(container);
            if (cs.position === "static") {
                container.style.position = "relative";
            }

            const overlay = parentWindow.document.createElement("div");
            overlay.style.position = "absolute";
            overlay.style.left = "0";
            overlay.style.right = "0";
            overlay.style.pointerEvents = "none";
            overlay.style.background = HILITE_COLOR;
            overlay.style.display = "none";
            overlay.style.zIndex = "5";
            overlay.style.borderRadius = "2px";
            container.appendChild(overlay);

            container.addEventListener("mousemove", function(e) {
                const rect = container.getBoundingClientRect();
                const y = e.clientY - rect.top;
                if (y < HEADER_H) {
                    overlay.style.display = "none";
                    return;
                }
                const rowIndex = Math.floor((y - HEADER_H) / ROW_H);
                const top = HEADER_H + rowIndex * ROW_H;
                if (top + ROW_H > rect.height + 1) {
                    overlay.style.display = "none";
                    return;
                }
                overlay.style.top = top + "px";
                overlay.style.height = ROW_H + "px";
                overlay.style.display = "block";
            });

            container.addEventListener("mouseleave", function() {
                overlay.style.display = "none";
            });
        }

        function scanAndBindRowHover() {
            const containers = parentWindow.document.querySelectorAll('div[data-testid="stDataFrame"]');
            containers.forEach(bindRowHoverHighlight);
        }

        scanAndBindRowHover();

        if (!parentWindow.hasRowHoverObserver) {
            const observer = new MutationObserver(function() {
                scanAndBindRowHover();
            });
            observer.observe(parentWindow.document.body, { childList: true, subtree: true });
            parentWindow.hasRowHoverObserver = true;
        }
    </script>
    """,
    height=0, width=0
)
# ------------------------------------------------------------------
# 🎯 [가상 데이터 쾌속 입력 팝업 로직] 상선고 히트맵 셀 클릭 연동
# ------------------------------------------------------------------
if "mock_stock" in st.query_params and "mock_date" in st.query_params:
    st.session_state['show_mock_dialog'] = {
        "stock": st.query_params.get("mock_stock"),
        "date": st.query_params.get("mock_date")
    }
    st.query_params.clear()
    st.rerun()

import google.generativeai as genai
from bs4 import BeautifulSoup

@st.cache_data(ttl=86400)
def get_naver_company_summary(stock_code):
    try:
        url = f"https://finance.naver.com/item/main.naver?code={stock_code}"
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        res.raise_for_status()
        soup = BeautifulSoup(res.text, 'html.parser')
        summary_p = soup.select_one('.summary_info p')
        summary_text = summary_p.text.strip() if summary_p else "네이버 금융에서 기업개요를 찾을 수 없습니다."
        
        news_links = soup.select('.news_section ul li a')
        news_md_items = []
        news_raw_items = []
        for a in news_links:
            title = a.text.strip()
            if "관련" not in title and title:
                href = a.get('href', '')
                if href.startswith('/'):
                    href = "https://finance.naver.com" + href
                news_md_items.append(f"- [{title}]({href})")
                news_raw_items.append(f"- {title}")
                
        news_md = "\n".join(news_md_items[:5]) if news_md_items else "최근 관련 뉴스가 없습니다."
        news_raw = "\n".join(news_raw_items[:5]) if news_raw_items else "최근 관련 뉴스가 없습니다."
        
        fin_info = {'price': 'N/A', 'high52': 'N/A', 'low52': 'N/A', 'per': 'N/A', 'pbr': 'N/A', 'warnings': []}
        try:
            # 시장경보 (투자주의, 투자경고, 투자위험, 관리종목 등)
            warnings = set()
            for em in soup.select('.description em'):
                blind = em.select_one('.blind')
                if blind:
                    text = blind.text.strip()
                    if text in ['투자주의', '투자경고', '투자위험', '단기과열', '거래정지', '관리종목', '투자주의환기종목']:
                        warnings.add(text)
            for img in soup.select('.description img'):
                alt = img.get('alt', '')
                if alt in ['투자주의', '투자경고', '투자위험', '단기과열', '거래정지', '관리종목', '환기종목']:
                    warnings.add(alt)
            fin_info['warnings'] = list(warnings)

            price_tag = soup.select_one('.no_today .blind')
            if price_tag: fin_info['price'] = price_tag.text.strip()
            
            for th in soup.select('th'):
                if '52주최고l최저' in th.text:
                    td = th.find_parent('tr').select_one('td')
                    if td:
                        parts = td.text.strip().split('l')
                        if len(parts) >= 2:
                            fin_info['high52'] = parts[0].strip()
                            fin_info['low52'] = parts[1].strip()
                    break
                    
            per_tag = soup.select_one('#_per')
            if per_tag: fin_info['per'] = per_tag.text.strip()
            pbr_tag = soup.select_one('#_pbr')
            if pbr_tag: fin_info['pbr'] = pbr_tag.text.strip()
            
            # ROE 추출
            cop_table = soup.select_one('.cop_analysis')
            if cop_table:
                for th in cop_table.select('th'):
                    if 'ROE' in th.text:
                        tds = th.find_parent('tr').select('td')
                        vals = [td.text.strip() for td in tds if td.text.strip() and td.text.strip() not in ('-', '', '\xa0')]
                        if vals:
                            fin_info['roe'] = vals[-1]
                        break
        except Exception: pass
        
        return summary_text, news_md, news_raw, fin_info
    except Exception as e:
        return f"요약 정보를 가져오는 중 오류가 발생했습니다: {e}", "", "", {}

def get_chatgpt_company_summary(stock_name, news_text=""):
    gpt_stock_key = f"[GPT]{stock_name}"

    # 2. 오픈AI API 호출
    api_key = st.secrets.get("openai", {}).get("api_key", None)
    if not api_key:
        raise ValueError("OPENAI_API_KEY_MISSING")
        
    client = openai.OpenAI(api_key=api_key)
    
    prompt = f"""한국 주식 시장에 상장된 '{stock_name}' 이라는 기업에 대해 다음 두 가지 항목으로 나누어 분석해줘.
주의: 답변 내용에 '(1~2줄)', '(3~4줄)' 같은 분량 지시어는 절대 출력하지 마.

**1. 기업 개요**
이 회사의 핵심 기술과 주요 사업 내용을 1~2줄로 요약해줘.

**2. 현재 상황 및 평가**
다음 최근 뉴스 제목들을 바탕으로 현재 이 기업의 호재, 악재, 전망을 서술식 말고 보기 좋게 한 줄씩 나열식(Bullet points)으로 명확하게 요약해 줘.
(반드시 아래 예시 포맷을 지켜서 작성할 것)
- [호재] ~~~
- [악재] ~~~
- [전망] ~~~

※ 주의사항: 요약할 때 기사에 언급된 특정 기업명(예: 홈플러스, 엔비디아), 기관명(예: FDA, 식약처), 고유명사 등을 '주요 입점사', '일부 기업', '규제 기관' 등으로 뭉뚱그리지 말고 구체적인 명칭을 반드시 그대로 명시할 것.

뉴스 제목이 없다면 일반적인 최근 시장의 평가를 위 포맷으로 적어줘.

[최근 뉴스 제목]
{news_text}
"""
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "당신은 증권가 최고의 주식 애널리스트입니다."},
            {"role": "user", "content": prompt}
        ],
        timeout=30.0 # 빠른 응답을 위해 30초 타임아웃
    )
    summary = response.choices[0].message.content
    
    # 3. 기존 캐시 삭제 후 새로운 결과 저장
    try:
        gpt_stock_key = f"[GPT]{stock_name}"
        # 같은 종목의 예전 요약본(또는 만료된 캐시)을 깔끔하게 지웁니다
        supabase.table("gemini_summaries").delete().eq("stock_name", gpt_stock_key).execute()
        
        supabase.table("gemini_summaries").insert({
            "stock_name": gpt_stock_key,
            "news_text": news_text,
            "summary": summary
        }).execute()
    except Exception as e:
        return f"ChatGPT 요약 저장 중 오류 발생: {e}"
    
    return summary

def get_gemini_company_summary(stock_name, news_text=""):
    import google.generativeai as genai
    import toml
    import os
    from supabase import create_client

    # 2. 캐시가 없으면 구글 API 호출
    api_key = st.secrets.get("gemini", {}).get("api_key", None)
    if not api_key:
        raise ValueError("API_KEY_MISSING")
        
    genai.configure(api_key=api_key)
    # 원래 작동했던 gemini-flash-latest 모델명으로 원복
    model = genai.GenerativeModel('gemini-flash-latest')
    
    prompt = f"""한국 주식 시장에 상장된 '{stock_name}' 이라는 기업에 대해 다음 두 가지 항목으로 나누어 분석해줘.
주의: 답변 내용에 '(1~2줄)', '(3~4줄)' 같은 분량 지시어는 절대 출력하지 마.

**1. 기업 개요**
이 회사의 핵심 기술과 주요 사업 내용을 1~2줄로 요약해줘.

**2. 현재 상황 및 평가**
다음 최근 뉴스 제목들을 바탕으로 현재 이 기업의 호재, 악재, 전망을 서술식 말고 보기 좋게 한 줄씩 나열식(Bullet points)으로 명확하게 요약해 줘.
(반드시 아래 예시 포맷을 지켜서 작성할 것)
- [호재] ~~~
- [악재] ~~~
- [전망] ~~~

※ 주의사항: 요약할 때 기사에 언급된 특정 기업명(예: 홈플러스, 엔비디아), 기관명(예: FDA, 식약처), 고유명사 등을 '주요 입점사', '일부 기업', '규제 기관' 등으로 뭉뚱그리지 말고 구체적인 명칭을 반드시 그대로 명시할 것.

뉴스 제목이 없다면 일반적인 최근 시장의 평가를 위 포맷으로 적어줘.

[최근 뉴스 제목]
{news_text}
"""
    # 504 타임아웃 방지를 위해 timeout을 60초로 넉넉하게 설정하되,
    # SDK 자체의 무한 재시도(2~3분 대기)를 막기 위해 retry=None 설정
    response = model.generate_content(
        prompt,
        request_options={"timeout": 60.0, "retry": None}
    )
    summary = response.text
    
    # 3. 기존 캐시 삭제 후 새로운 결과 저장
    try:
        # 같은 종목의 예전 요약본(또는 만료된 캐시)을 깔끔하게 지웁니다
        supabase.table("gemini_summaries").delete().eq("stock_name", stock_name).execute()
        
        supabase.table("gemini_summaries").insert({
            "stock_name": stock_name,
            "news_text": news_text,
            "summary": summary
        }).execute()
    except Exception:
        pass  # 저장 실패 시에도 정상적으로 요약본 반환

    return summary

@st.cache_data(ttl=86400)
def get_cached_krx_listing():
    import FinanceDataReader as fdr
    return fdr.StockListing('KRX')

# 🔧 [복원 2026-07-30] BackUp/dashboard_bk.py에는 있었는데 현재 파일에서 누락되어 있던 함수.
# AI 분석 결과(Gemini/ChatGPT)를 "1. 기업개요"/"2. 현재상황및평가" 굵은 빨간 헤더 + "[호재]/[악재]/[전망]" 주홍색 태그 +
# 다크 그린 배경 박스로 예쁘게 렌더링해준다. 이게 빠져있어서 AI 분석창이 그냥 st.success()의 밋밋한 텍스트로만 나오고 있었음.
def render_ai_summary_box(text):
    if not text:
        return
    import re

    # 1. 굵은 글씨 및 줄바꿈 처리
    html_text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
    html_text = html_text.replace("\n", "<br>")

    # 2. "1. 기업 개요", "2. 현재 상황 및 평가" -> 빨간색 (Red: #ff4b4b), 아이콘 이모지 제거
    red_style = "color: #ff4b4b; font-weight: bold; font-size: 1.05em;"
    html_text = re.sub(
        r'1\.\s*(?:🏢|🏫)?\s*기업\s*개요',
        rf'<span style="{red_style}">1. 기업 개요</span>',
        html_text
    )
    html_text = re.sub(
        r'2\.\s*(?:📊|📈)?\s*현재\s*상황\s*및\s*평가',
        rf'<span style="{red_style}">2. 현재 상황 및 평가</span>',
        html_text
    )

    # 3. "[호재]", "[악재]", "[전망]" -> 주홍색 (Orange: #ff7f50)
    orange_style = "color: #ff7f50; font-weight: bold;"
    html_text = re.sub(
        r'(\[호재\]|\[악재\]|\[전망\])',
        rf'<span style="{orange_style}">\1</span>',
        html_text
    )

    # 4. 시인성 높은 다크 그린 배경 컨테이너 렌더링
    container_html = f"""
    <div style="background-color: rgba(30, 50, 35, 0.45); border: 1px solid rgba(46, 125, 50, 0.5); border-radius: 8px; padding: 16px; font-size: 0.95em; line-height: 1.7; color: #e0e0e0; margin-bottom: 12px;">
        {html_text}
    </div>
    """
    st.markdown(container_html, unsafe_allow_html=True)

@st.dialog("🏢 기업 요약 및 AI 분석")
def show_summary_dialog(stock_name, stock_code="", trigger_id=0):
    import FinanceDataReader as fdr

    # 🔧 [수정 2026-07-30] 우측 상단 기본 X 닫기 버튼 제거.
    # X로 닫으면 Streamlit이 스크립트 rerun을 트리거하지 않아서(Streamlit 공식 이슈 #8507) 우리 쪽
    # session_state['show_summary_dialog'] 정리 코드가 아예 실행이 안 되고, 그래서 다음 자동새로고침 때
    # 창이 또 뜨는 버그가 있었음. "닫기 (확인)"/"관심종목 추가" 버튼만 쓰도록 X를 아예 숨김.
    st.markdown(
        '<style>div[aria-label="dialog"]>button[aria-label="Close"] { display: none !important; }</style>',
        unsafe_allow_html=True
    )

    if not stock_code:
        try:
            # 1. 자체 DB(upper_limit_stocks)에서 먼저 조회 시도 (KRX IP 차단 우회 및 속도 향상)
            db_res = supabase.table("upper_limit_stocks").select("code").eq("name", stock_name).limit(1).execute()
            if db_res.data:
                stock_code = db_res.data[0]['code']
        except Exception:
            pass
            
        if not stock_code:
            try:
                krx = get_cached_krx_listing()
                matched = krx[krx['Name'] == stock_name]
                if not matched.empty:
                    stock_code = matched.iloc[0]['Code']
            except Exception as e:
                pass # fallback if KRX blocks scraping
            
    # 렌더링 전 정보 가져오기
    with st.spinner("정보를 가져오는 중..."):
        if stock_code:
            naver_summary, naver_news_md, naver_news_raw, fin_info = get_naver_company_summary(stock_code)
        else:
            naver_summary, naver_news_md, naver_news_raw, fin_info = "종목 코드를 찾을 수 없어 요약을 가져올 수 없습니다.", "", "", {}

    if fin_info:
        warnings = fin_info.get('warnings', [])
        if warnings:
            badges = " ".join([f"<span style='background-color:#ffebee; color:#d32f2f; padding:2px 6px; border-radius:4px; font-size:0.7em; font-weight:bold; margin-right:5px;'>🚨 {w}</span>" for w in warnings])
            st.markdown(badges, unsafe_allow_html=True)
            
        per = fin_info.get('per', 'N/A')
        pbr = fin_info.get('pbr', 'N/A')
        roe = fin_info.get('roe', 'N/A')
        high52 = fin_info.get('high52', 'N/A')
        low52 = fin_info.get('low52', 'N/A')
        price = fin_info.get('price', 'N/A')
        
        roe_str = f"{roe}%" if roe != 'N/A' else 'N/A'
        
        metrics_html = f"""
        <div style='display: flex; align-items: baseline; flex-wrap: wrap; gap: 12px; margin-bottom: 10px;'>
            <h3 style='margin: 0; padding: 0;'>{stock_name} {f'({stock_code})' if stock_code else ''}</h3>
            <div style='font-size: 0.85em; color: #e0e0e0; line-height: 1.4; font-weight: normal;'>
                [ PER {per} / PBR {pbr} / ROE {roe_str} ]<br>
                [ 52주고/저 {high52} / {low52} ] &nbsp;&nbsp;[ 현재가 {price} ]
            </div>
        </div>
        """
        st.markdown(metrics_html, unsafe_allow_html=True)
    else:
        st.markdown(f"<h3 style='margin: 0; padding: 0; margin-bottom: 10px;'>{stock_name} {f'({stock_code})' if stock_code else ''}</h3>", unsafe_allow_html=True)
    
    tab1, tab2, tab3 = st.tabs(["📊 네이버 기업개요", "🤖 Gemini AI 분석", "💡 ChatGPT AI 분석"])
    
    with tab1:
        st.markdown("##### 🏢 기업 개요")
        st.info(naver_summary)
        st.markdown("##### 📰 최근 주요 뉴스")
        st.warning(naver_news_md if naver_news_md else "최근 뉴스가 없습니다.")
        
    with tab2:
        # 1. 먼저 DB에 캐시된 요약본이 있는지 빠르게 확인 (UI 블로킹 방지)
        db_summary = None
        thirty_days_ago = (datetime.utcnow() - timedelta(days=30)).isoformat()
        try:
            db_res = supabase.table("gemini_summaries").select("summary").eq("stock_name", stock_name).eq("news_text", naver_news_raw).gte("created_at", thirty_days_ago).limit(1).execute()
            if db_res.data:
                db_summary = db_res.data[0]['summary']
        except Exception:
            pass

        if db_summary:
            render_ai_summary_box(db_summary)
        else:
            st.info("💡 처음 조회하는 뉴스이거나 기존 분석이 만료(30일 경과)되었습니다. 아래 버튼을 눌러 AI 분석을 갱신하세요.")
            if st.button("🤖 Gemini AI 분석 시작", key=f"gemini_btn_{stock_name}"):
                with st.spinner("Gemini AI가 뉴스를 바탕으로 분석 중입니다..."):
                    try:
                        gemini_summary = get_gemini_company_summary(stock_name, naver_news_raw)
                        render_ai_summary_box(gemini_summary)
                    except Exception as e:
                        err_msg = str(e)
                        if "API_KEY_MISSING" in err_msg:
                            st.warning("⚠️ `.streamlit/secrets.toml` 파일에 Gemini API Key가 설정되지 않았습니다.\n\n[gemini]\napi_key = \"당신의_API_KEY\" 형태로 추가해주세요.")
                        elif "429" in err_msg or "quota" in err_msg.lower():
                            st.warning("⚠️ **Gemini AI 무료 제공량 초과 (Rate Limit)**\n\n단기간에 너무 많은 분석을 요청하여 구글 AI 서버의 **분당 제공량(15회)** 또는 **일일 총 제공량**을 초과했습니다.\n\n만약 1~2분 정도 쉬었다가 다시 시도했는데도 계속 이 에러가 뜬다면, **오늘 하루 치 무료 한도를 전부 다 쓰신 겁니다!** (이 경우 내일 다시 시도하셔야 합니다.) 😭\n\n상세 에러 원문: `" + err_msg.replace('\n', ' ')[:200] + "...`")
                        elif "504" in err_msg or "deadline" in err_msg.lower():
                            st.error("⚠️ **구글 AI 서버 응답 지연 (504 Timeout)**\n\n구글 서버가 분석을 완료하는 데 시간이 너무 오래 걸려 연결이 끊어졌습니다. 잠시 후 버튼을 다시 눌러주세요.")
                        elif "503" in err_msg or "high demand" in err_msg.lower():
                            st.warning("⚠️ **구글 AI 서버 과부하 (503 Service Unavailable)**\n\n현재 전 세계적으로 구글 AI 서버에 요청이 폭주하고 있어 일시적으로 처리가 지연되고 있습니다. 1~2분 정도 후에 다시 시도해 주세요.")
                        else:
                            st.error(f"Gemini AI 호출 중 오류가 발생했습니다: {e}")

        with tab3:
            db_summary_gpt = None
            gpt_stock_key = f"[GPT]{stock_name}"
            thirty_days_ago = (datetime.utcnow() - timedelta(days=30)).isoformat()
            try:
                db_res_gpt = supabase.table("gemini_summaries").select("summary").eq("stock_name", gpt_stock_key).eq("news_text", naver_news_raw).gte("created_at", thirty_days_ago).limit(1).execute()
                if db_res_gpt.data:
                    db_summary_gpt = db_res_gpt.data[0]['summary']
            except Exception:
                pass

            if db_summary_gpt:
                render_ai_summary_box(db_summary_gpt)
            else:
                st.info("💡 구글 서버가 불안정할 때 훌륭한 대안입니다. 버튼을 눌러 최근 30일 내의 새로운 분석을 시작하세요.")
                if st.button("💡 ChatGPT AI 분석 시작", key=f"chatgpt_btn_{stock_name}"):
                    with st.spinner("ChatGPT(gpt-4o-mini)가 뉴스를 바탕으로 분석 중입니다..."):
                        try:
                            chatgpt_summary = get_chatgpt_company_summary(stock_name, naver_news_raw)
                            render_ai_summary_box(chatgpt_summary)
                        except Exception as e:
                            err_msg = str(e)
                            if "OPENAI_API_KEY_MISSING" in err_msg:
                                st.warning("⚠️ `.streamlit/secrets.toml` 파일에 OpenAI API Key가 설정되지 않았습니다.\n\n[openai]\napi_key = \"당신의_API_KEY\" 형태로 추가해주세요.")
                            elif "429" in err_msg or "quota" in err_msg.lower() or "insufficient_quota" in err_msg.lower():
                                st.warning("⚠️ **ChatGPT API 잔액 부족 또는 한도 초과**\n\nOpenAI 계정에 결제 수단이 등록되어 있는지 또는 충전된 잔액($)이 있는지 확인해주세요.")
                            else:
                                st.error(f"ChatGPT API 호출 중 오류가 발생했습니다: {e}")
            
    close_col_dlg, watch_col_dlg = st.columns(2)
    with close_col_dlg:
        if st.button("닫기 (확인)", use_container_width=True):
            st.session_state.pop('show_summary_dialog', None)
            st.rerun()
    with watch_col_dlg:
        # 🌟 [신규 2026-07-30] 이 창에서 바로 관심종목에 추가할 수 있는 버튼
        st.markdown('<div class="btn-style-green"></div>', unsafe_allow_html=True)
        if st.button("⭐ 관심종목 추가", key=f"watch_add_dialog_{stock_name}_{trigger_id}", use_container_width=True):
            if not st.session_state.get('authenticated', False):
                st.warning("🚫 정회원만 이용할 수 있습니다.")
            elif not stock_code:
                st.warning("⚠️ 종목코드를 확인할 수 없어 관심종목에 추가하지 못했습니다.")
            else:
                try:
                    supabase.table("user_watchlist").upsert({
                        "username": st.session_state.get('username', ''),
                        "stock_code": str(stock_code).strip().zfill(6),
                        "stock_name": stock_name,
                    }, on_conflict="username,stock_code").execute()
                    st.toast(f"⭐ '{stock_name}' 관심종목에 추가되었습니다.")
                except Exception as e:
                    st.error(f"추가 실패: {e}")

# ------------------------------------------------------------------
# 🎯 [요약 팝업 로직] 상선고 히트맵 등에서 클릭 연동
# ------------------------------------------------------------------
if "summary_stock" in st.query_params and "summary_code" in st.query_params:
    trigger = st.session_state.get('dialog_trigger_id', 0) + 1
    st.session_state['dialog_trigger_id'] = trigger
    st.session_state['show_summary_dialog'] = {
        "stock": st.query_params.get("summary_stock"),
        "code": st.query_params.get("summary_code"),
        "trigger_id": trigger
    }
    st.query_params.clear()
    st.rerun()
    
if 'show_summary_dialog' in st.session_state:
    data = st.session_state['show_summary_dialog']
    show_summary_dialog(data['stock'], data.get('code', ''), data.get('trigger_id', 0))

@st.dialog("🎯 가상 데이터 (Mock Data) 쾌속 입력")
def mock_data_dialog(stock, date_str):
    st.write(f"**🔹 종목명**: {stock}")
    st.write(f"**🔹 기준일**: {date_str} (기록 시간: 현재시간)")
    st.caption("홍보 영상 제작 등을 위해 임의의 가상 데이터를 DB에 주입합니다.")
    
    amount_100m = st.number_input("순매수 금액 (단위: 억원)", min_value=0.1, max_value=5000.0, value=1.0, step=0.1, format="%.1f")
    
    col_cancel, col_save = st.columns(2)
    with col_cancel:
        if st.button("❌ 취소 (닫기)", use_container_width=True):
            st.session_state.pop('show_mock_dialog', None)
            # st_click_detector의 특성상 last_mock_clicked를 비우면 새로고침 시 무한 팝업 현상이 발생하므로 비우지 않습니다.
            st.rerun()
            
    with col_save:
        save_clicked = st.button("💾 데이터 즉시 저장", use_container_width=True)
        
    if save_clicked:
        with st.spinner("주가 정보 조회 및 저장 중..."):
            try:
                import FinanceDataReader as fdr
                krx = get_cached_krx_listing()
                matched = krx[krx['Name'] == stock]
                if matched.empty:
                    st.error("⚠️ 종목 코드를 찾을 수 없습니다. (상장 폐지 또는 이름 변경 가능성)")
                    return
                code = matched.iloc[0]['Code']
                market = matched.iloc[0]['Market']
                market_type = "KOSPI" if market in ["KOSPI", "KOSPI200"] else "KOSDAQ"
                
                # Fetch price
                df_price = fdr.DataReader(code, start=date_str, end=date_str)
                if df_price.empty:
                    st.error(f"⚠️ {date_str}의 주가 데이터가 없습니다. (휴장일이거나 거래 정지 상태)")
                    return
                
                price = int(df_price['Close'].iloc[0])
                amount = int(amount_100m * 100_000_000)
                volume = int(amount / price) if price > 0 else 0
                
                now = datetime.now()
                time_str = now.strftime("%H:%M:%S")
                
                record = {
                    "date": date_str,
                    "time": time_str,
                    "code": code,
                    "name": stock,
                    "price": price,
                    "volume": volume,
                    "amount_krw": amount,
                    "asset_type": "개별주식",
                    "market_type": market_type,
                    "side": "매수"
                }
                
                res = supabase.table("whale_log").insert(record).execute()
                inserted_id = res.data[0]['id']
                
                track_data = {
                    "key": f"mock_whale_id_{inserted_id}",
                    "value": str(inserted_id)
                }
                supabase.table("system_settings").insert(track_data).execute()
                
                st.session_state.pop('show_mock_dialog', None)
                st.success("✅ 가상 데이터가 성공적으로 입력되었습니다! 화면을 갱신합니다.")
                st.rerun()
            except Exception as e:
                st.error(f"❌ 저장 중 오류 발생: {e}")

# ------------------------------------------------------------------
# 🛡️ [ETF/파생 필터링 코어] 순수 개별종목 캐싱 (하루 1번 갱신)
# ------------------------------------------------------------------
@st.cache_data(ttl=86400)
def get_pure_stock_codes():
    try:
        import FinanceDataReader as fdr
        import re
        df_krx = get_cached_krx_listing()
        noise_keywords = ('ETF', 'ETN', 'KODEX', 'TIGER', 'ACE', 'SOL', 'RISE', 'KBSTAR', 'ARIRANG', 'HANARO', 'KOSEF', 'PLUS', 'TIME', '인버스', '레버리지', 'WON', '1Q', 'KIWOOM', 'TRUE', 'QV', '선물', '콜', '풋', '옵션')
        pure_codes = set()
        for _, row in df_krx.iterrows():
            name = str(row['Name']).strip()
            code = str(row['Code']).strip().zfill(6)
            if any(kw in name.upper() for kw in noise_keywords):
                continue
            if re.search(r'우$|우B$|우\([A-Za-z0-9]+\)$|우[A-Z]$|스팩|제\d+호', name, re.IGNORECASE):
                continue
            pure_codes.add(code)
        return pure_codes
    except Exception as e:
        print(f"FDR 순수 종목 로딩 실패: {e}")
        return None

# ------------------------------------------------------------------
# 🏷️ [테마 칩셋] Supabase를 활용한 테마 저장소
# ------------------------------------------------------------------

def get_global_stock_metadata():
    try:
        import json, os
        meta_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stock_metadata.json")
        if os.path.exists(meta_path):
            with open(meta_path, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception:
        pass
    return {}

def get_warning_text(stock_name, global_meta):
    if not global_meta or stock_name not in global_meta:
        return ""
    info = global_meta.get(stock_name, {})
    if isinstance(info, dict):
        return info.get('warning', '') or info.get('special_note', '') or ""
    return ""

def get_themes_for_stocks(stock_names):
    if not stock_names:
        return {}
    try:
        res = supabase.table('stock_themes').select('stock_name, theme_names').in_('stock_name', stock_names).execute()
        return {row['stock_name']: row['theme_names'] for row in res.data}
    except Exception as e:
        return {}

# 🔧 [수정 2026-07-30] "고래 골든픽" 화면이 화면 안의 아무 버튼(AI 요약 보기, 차트 이동 등)만 눌러도
# 매번 daily_whale_top200/whale_log/upper_limit_stocks를 통째로 다시 조회하고 있어서 클릭할 때마다
# 느려진다는 피드백 — 선택한 날짜(sel_date_str)가 그대로면 굳이 다시 조회할 필요가 없으므로,
# 네트워크 왕복이 제일 비싼 이 부분만 따로 떼어내 st.cache_data로 하루(86400초) 캐싱함.
# ⚠️ 당일 실시간 틱(df, 세션에 이미 로드된 실시간 데이터)을 더하는 부분은 캐시 밖(호출부)에 그대로 남겨둬서
# 캐시가 실시간성을 완전히 죽이지는 않도록 함 — df 병합은 이미 메모리에 있는 데이터라 비용이 거의 없음.
@st.cache_data(ttl=86400, show_spinner=False)
def _fetch_golden_pick_base_data(sel_date_str, start_date_str):
    top_res = supabase.table("daily_whale_top200").select("*").eq("trade_date", sel_date_str).limit(1000).execute()
    hist_res = supabase.table("daily_whale_top200").select("stock_code, trade_date").gte("trade_date", start_date_str).lte("trade_date", sel_date_str).limit(5000).execute()
    upper_res = supabase.table("upper_limit_stocks").select("name").gte("recorded_date", start_date_str).lte("recorded_date", sel_date_str).execute()

    all_w_data = []
    page_size = 1000
    start = 0
    while start < 50000:
        w_res = supabase.table("whale_log").select("code, side, amount_krw").gte("date", start_date_str).lte("date", sel_date_str).order("date", desc=True).order("time", desc=True).range(start, start + page_size - 1).execute()
        if not w_res.data:
            break
        all_w_data.extend(w_res.data)
        if len(w_res.data) < page_size:
            break
        start += page_size

    return {
        "top_data": top_res.data or [],
        "hist_data": hist_res.data or [],
        "upper_data": upper_res.data or [],
        "whale_log_data": all_w_data,
    }


@st.cache_data(ttl=600)
def fetch_kis_daily_volume(stock_code, start_date):
    try:
        # FDR을 사용하여 안정적으로 종가 및 거래량 가져오기 (API 키 필요 없음)
        df = fdr.DataReader(stock_code, start_date)
        if df.empty:
            return pd.DataFrame()
            
        # 거래정지(단기과열 등)로 인해 거래량이 아예 없는 날(Open=0 등)은 차트에서 제외
        df = df[df['Volume'] > 0]
        if df.empty:
            return pd.DataFrame()
        
        # 거래대금 = 거래량 * 종가 (근사치이지만 매우 정확함)
        df['acml_tr_pbmn'] = df['Volume'] * df['Close']
        df['date'] = df.index.date
        return df.reset_index()
    except Exception as e:
        return pd.DataFrame()
# ------------------------------------------------------------------
# 📊 [투자자별 매매동향] 한투 KIS OpenAPI 연동
# ------------------------------------------------------------------
@st.cache_data(ttl=600) # Streamlit 프로세스 메모리 캐시는 짧게만(10분) — 진짜 유효기간 판단은 아래 Supabase 기록 기준
def get_kis_access_token():
    import json
    import time

    # 🔧 [버그 수정 2026-07-30] 로컬 파일(kis_token.json) 대신 Supabase system_settings에 저장/조회하도록 변경.
    # 대시보드는 Streamlit Cloud(클라우드)에서 실행되고 수집기(FindingWhale.py)는 사용자 PC(로컬)에서 실행되므로,
    # 로컬 파일은 애초에 서로 공유될 수 없었음 — 대시보드는 매번 자기만의 로컬 파일(클라우드 컨테이너 안의 파일,
    # 그마저도 재시작되면 사라짐)만 보고 있었고, 그래서 수집기가 멀쩡한 토큰을 갖고 있어도 항상 별도로 새
    # 토큰을 발급받고 있었음 (한투 서버 과다 요청 위험). 이제 두 프로그램이 같은 DB 레코드를 공유한다.
    TOKEN_KEY = "kis_access_token"
    # 🔧 재사용 기준도 82800초(23시간) → 84600초(23시간30분)로 통일 — 수집기의 자체 예약 갱신 주기와 동일하게
    # 맞춰서, 수집기가 스스로 갱신하기 전에 다른 쪽이 "낡았다"고 오판해 중복 발급하는 문제를 없앰.
    TOKEN_TTL = 84600

    # 1. Supabase에서 유효한 토큰 읽기 시도
    try:
        res = supabase.table("system_settings").select("value").eq("key", TOKEN_KEY).execute()
        if res.data:
            data = json.loads(res.data[0]["value"])
            if time.time() - data.get("timestamp", 0) < TOKEN_TTL:
                return data["token"]
    except Exception:
        pass

    # 2. 토큰이 없거나 만료된 경우 API로 새로 발급
    APP_KEY = st.secrets["kis"]["app_key"]
    APP_SECRET = st.secrets["kis"]["app_secret"]
    url = "https://openapi.koreainvestment.com:9443/oauth2/tokenP"
    headers = {"content-type": "application/json"}
    body = {"grant_type": "client_credentials", "appkey": APP_KEY, "appsecret": APP_SECRET}
    res = requests.post(url, headers=headers, json=body)
    if res.status_code == 200:
        new_token = res.json()["access_token"]
        # 새 토큰을 Supabase에 기록 (수집기와 공유)
        try:
            payload = json.dumps({"token": new_token, "timestamp": time.time()})
            supabase.table("system_settings").upsert({"key": TOKEN_KEY, "value": payload}, on_conflict="key").execute()
        except Exception:
            pass
        return new_token
    return None

@st.cache_data(ttl=600)
def fetch_investor_net_buying(stock_code):
    token = get_kis_access_token()
    if not token:
        return pd.DataFrame()
    
    APP_KEY = st.secrets["kis"]["app_key"]
    APP_SECRET = st.secrets["kis"]["app_secret"]
    url = "https://openapi.koreainvestment.com:9443/uapi/domestic-stock/v1/quotations/inquire-investor"
    headers = {
        "content-type": "application/json; charset=utf-8",
        "authorization": f"Bearer {token}",
        "appkey": APP_KEY,
        "appsecret": APP_SECRET,
        "tr_id": "FHKST01010900"
    }
    params = {
        "FID_COND_MRKT_DIV_CODE": "J",
        "FID_INPUT_ISCD": stock_code
    }
    res = requests.get(url, headers=headers, params=params)
    if res.status_code == 200:
        data = res.json().get("output", [])
        if not data:
            return pd.DataFrame()
        
        df = pd.DataFrame(data)
        df['date_str'] = pd.to_datetime(df['stck_bsop_date']).dt.strftime('%m-%d')
        # 단위: 백만원 -> 억원 (나누기 100), 빈 문자열 대비 pd.to_numeric 처리
        df['frgn_buy_100m'] = pd.to_numeric(df['frgn_shnu_tr_pbmn'], errors='coerce').fillna(0) / 100
        df['frgn_sell_100m'] = (pd.to_numeric(df['frgn_seln_tr_pbmn'], errors='coerce').fillna(0) / 100) * -1
        df['orgn_buy_100m'] = pd.to_numeric(df['orgn_shnu_tr_pbmn'], errors='coerce').fillna(0) / 100
        df['orgn_sell_100m'] = (pd.to_numeric(df['orgn_seln_tr_pbmn'], errors='coerce').fillna(0) / 100) * -1
        
        # 순매수(Net) 계산
        df['frgn_net_100m'] = df['frgn_buy_100m'] + df['frgn_sell_100m']
        df['orgn_net_100m'] = df['orgn_buy_100m'] + df['orgn_sell_100m']
        
        return df[['date_str', 'frgn_buy_100m', 'frgn_sell_100m', 'orgn_buy_100m', 'orgn_sell_100m', 'frgn_net_100m', 'orgn_net_100m']]
    return pd.DataFrame()

# ------------------------------------------------------------------
# (set_page_config는 최상단으로 이동됨)

if 'show_mock_dialog' in st.session_state:
    data = st.session_state['show_mock_dialog']
    mock_data_dialog(data['stock'], data['date'])

# ------------------------------------------------------------------
# 🔒 보안용 인코딩/해시 칩셋 함수 정의
# ------------------------------------------------------------------
def encrypt_password(password):
    """비밀번호를 SHA-256 단방향 해시로 복구 불가능하게 인코딩 해 버립니다."""
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def encode_phone(phone):
    """전화번호를 안전하게 Base64로 인코딩합니다."""
    return base64.b64encode(phone.encode('utf-8')).decode('utf-8')

def validate_password(password):
    """숫자, 영어 알파벳, 기호가 혼용된 5자 이상 룰 검사 센서"""
    if len(password) < 5:
        return False
    # 숫자, 영문, 특수문자가 각각 하나 이상 포함되어 있는지 체크
    has_letter = bool(re.search(r"[A-Za-z]", password))
    has_digit = bool(re.search(r"\d", password))
    has_symbol = bool(re.search(r"[!@#$%^&*(),.?\":{}|<>_+-=~`\[\]\\/;']", password))
    return has_letter and has_digit and has_symbol

# ------------------------------------------------------------------
# 🏖️ [신규 배선] Supabase 휴장일 테이블 로더
# ------------------------------------------------------------------
@st.cache_data(ttl=86400) # 하루에 한 번만 DB에 물어보도록 강력한 캐시 적용
def get_market_holidays():
    try:
        # Supabase에서 holiday_date 컬럼만 싹 긁어오기
        res = supabase.table("market_holidays").select("holiday_date").execute()
        if res.data:
            # 날짜(문자열)만 뽑아서 리스트로 반환
            return [item['holiday_date'] for item in res.data]
        return []
    except Exception as e:
        # 테이블이 없거나 에러나면 빈 리스트 반환 (시계가 죽지 않도록 방어)
        return []

# ------------------------------------------------------------------
# 👑 [최고 관리자 전용 제어 스테이션]
# ------------------------------------------------------------------

from datetime import datetime, timedelta
import base64
import streamlit as st

def is_market_open_now():
    now = datetime.utcnow() + timedelta(hours=9)
    # 1. 주말 체크 (월=0, 토=5, 일=6)
    if now.weekday() >= 5:
        return False
        
    # 2. 휴장일 체크
    today_str = now.strftime('%Y-%m-%d')
    holidays = get_market_holidays()
    if today_str in holidays:
        return False
        
    # 3. 시간 체크 (08:30 ~ 15:30)
    current_time = now.time()
    market_start = datetime.strptime("08:30", "%H:%M").time()
    market_end = datetime.strptime("15:30", "%H:%M").time()
    if not (market_start <= current_time <= market_end):
        return False
        
    return True

def get_latest_market_open_date(base_date=None):
    if base_date is None:
        target = datetime.utcnow() + timedelta(hours=9)
    else:
        # datetime 객체가 아니라 date 객체면 변환
        if not hasattr(base_date, 'time'):
            target = datetime.combine(base_date, datetime.min.time())
        else:
            target = base_date
            
    # 오전 9시 전이면 아직 오늘 장이 안 열렸으므로 전날로 기준을 옮김 (평일이더라도)
    if target.time() < datetime.strptime("09:00", "%H:%M").time():
        target -= timedelta(days=1)
        
    holidays = get_market_holidays()
    
    while True:
        if target.weekday() >= 5: # 5: 토, 6: 일
            target -= timedelta(days=1)
            continue
        if target.strftime('%Y-%m-%d') in holidays:
            target -= timedelta(days=1)
            continue
        break
    return target.date()

def render_profile_edit_panel(user_data, current_id, db_phone):
    st.subheader("📝 내 정보 수정")
    st.write("---")
    
    msg_container = st.empty()
    
    # 자가 정비 폼 버퍼 구성
    with st.form("profile_edit_form"):
        st.markdown("🛰️ 비상 연락망 및 필수 보안 설정")
        
        # ID는 읽기 전용으로 안전성 확보, 실명(닉네임)은 수정 가능
        st.text_input("ID", value=current_id, disabled=True)
        new_nickname = st.text_input("닉네임", value=user_data['name'])
        
        # 🛠️ 수정 가능한 소자들 배치
        up_phone = st.text_input("비상 연락처 수정", value=db_phone)
        
        # 🔄 [사용자 맞춤 설정] 자동 새로고침 토글
        current_auto_refresh = user_data.get('auto_refresh_enabled', True)
        up_auto_refresh = st.checkbox("목록 자동 새로고침 켜기 (끄면 증시 휴장일처럼 타이머 대기모드 전환)", value=current_auto_refresh)

        # 🔐 [보안 필터 배선] 패스워드 변경 제어반
        st.markdown("🔐 보안 비밀번호 수정 (변경할 경우에만 입력)")
        old_pw = st.text_input("기존 비밀번호 입력", type="password", placeholder="현재 사용 중인 비밀번호")
        new_pw = st.text_input("새로운 비밀번호 설정", type="password", placeholder="영문 + 숫자 + 특수문자 포함 5자 이상")            
        new_pw_confirm = st.text_input("새로운 비밀번호 재확인", type="password", placeholder="새로운 비밀번호 다시 입력")

        submit_edit = st.form_submit_button("자격 정보 업데이트 💾", use_container_width=True)
        
    if submit_edit:
        if up_phone:
            # 🎯 전화번호는 반드시 기존 인코딩 칩셋을 거쳐 보안화 한 뒤 인서트!
            encoded_phone = base64.b64encode(up_phone.encode('utf-8')).decode('utf-8')
            
            # 닉네임 중복 체크
            if new_nickname != user_data['name']:
                name_check = supabase.table("users").select("id").eq("name", new_nickname).execute()
                if name_check.data:
                    msg_container.error(f"❌ '{new_nickname}' 닉네임은 이미 사용 중입니다. 다른 이름을 입력해 주십시오.")
                    import time
                    time.sleep(1.5)
                    msg_container.empty()
                    st.stop()
            
            # Supabase 창고 업데이트 슛!
            update_payload = {
                "name": new_nickname,
                "phone_encoded": encoded_phone,
                "auto_refresh_enabled": up_auto_refresh
            }
            
            st.session_state['current_user'] = new_nickname
            st.session_state['auto_refresh_enabled'] = up_auto_refresh
            
            # 🎯 2. 패스워드 교체 인터럽트 분기 회로 가동
            if new_pw or new_pw_confirm:
                if new_pw != new_pw_confirm:
                    st.error("❌ 새로운 비밀번호가 서로 일치하지 않습니다.")
                    st.stop()
                    
                # 🛑 1: 기존 비번이 창고(DB)에 저장된 해시값과 일치하는지 스캔
                # ※ encrypt_password 함수는 기존에 쓰던 암호화 함수명을 그대로 매핑.
                if encrypt_password(old_pw) != user_data['password_hash']:
                    st.error("❌ 기존 비밀번호 인증 실패: 현재 비밀번호가 일치하지 않아 기판을 잠급니다.")
                    st.stop()
                    
                # 🛑 2: 현대식 보안 영점 조절 (최소 5자 이상 + 영문 + 숫자 + 특수문자 필수 혼합)
                pw_pattern = r"^(?=.*[a-zA-Z])(?=.*\d)(?=.*[^a-zA-Z\d]).{5,}$"
                
                if not re.match(pw_pattern, new_pw):
                    st.error("🛑 비밀번호 규격 미달: 최소 5글자 이상이어야 하며, 알파벳, 숫자, 특수문자를 각각 최소 1개 이상 무조건 혼합해야 합니다!")
                    st.stop()
                
                # 🎉 모든 보안 센서 통과 시 암호화 패킷 탑재!
                update_payload["password_hash"] = encrypt_password(new_pw)
                
            # 3. Supabase 데이터베이스 메인 창고로 패킷 발송!
            supabase.table("users").update(update_payload).eq("username", current_id).execute()

            st.success("✅ 자격 정보 및 알림 설정이 메모리에 성공적으로 반영되었습니다!")
            st.session_state['force_menu_change'] = "🏠 홈화면"
            st.rerun()
        else:
            st.warning("⚠️ 비상 연락처는 공백으로 둘 수 없습니다.")


def render_admin_panel():
    st.subheader("🛠️ 최고 관리자 사령탑 v2.7 (Global Settings)")
    st.write("---")
    
    # ==================================================================
    # 🎛️ [신규 증설] 시스템 글로벌 전압 제어반 (상단 배치)
    # ==================================================================
    st.markdown("🎛️ 시스템 글로벌 제어반")
    st.caption("🛰️ 수집기 엔진의 전상(전일 상한가) 인정 범위를 튜닝합니다.")
    
    # 1. DB에서 현재 설정값 읽어오기
    settings_res = supabase.table("system_settings").select("*").eq("key", "prev_upper_limit_window_days").execute()
    
    if settings_res.data:
        current_window = int(settings_res.data[0]['value'])
    else:
        current_window = 3 # DB가 비어있을 경우 기본값
        
    # 2. 전상 인정 기간 설정 노브 
    col_s1, col_s2 = st.columns([3, 1])
    with col_s1:
        new_window = st.number_input(
            "⭐ 전상(전일 상한가) 인정 기간 설정 (일)", 
            min_value=1, 
            max_value=30, 
            value=current_window,
            help="이 날짜 범위 내에 상한가를 쳤던 종목들은 고래 포착 시 [⭐전상] 뱃지를 달고 송신됩니다."
        )
    with col_s2:
        st.write("") # 수직 중앙 정렬용 공백
        st.write("") 
        if st.button("시스템 영점 저장 💾", use_container_width=True):
            try:
                supabase.table("system_settings").upsert({
                    "key": "prev_upper_limit_window_days",
                    "value": str(new_window),
                    "updated_at": datetime.now().isoformat()
                }).execute()
                st.success(f"✅ 전상 인정 기간이 {new_window}일로 동기화되었습니다!")
                st.rerun()
            except Exception as e:
                st.error(f"❌ 설정 저장 실패: {e}")

    # 3. 수익율 자랑 조회수 표시 제어 노브
    st.write("---")
    views_res = supabase.table("system_settings").select("*").eq("key", "brag_board_show_views").execute()
    current_show_views = "비공개 (사령관만 보임)" if views_res.data and views_res.data[0]['value'] == "False" else "전체 공개"
    
    col_v1, col_v2 = st.columns([3, 1])
    with col_v1:
        new_show_views = st.radio(
            "👀 수익율 자랑 조회수 표시 모드",
            options=["비공개 (사령관만 보임)", "전체 공개"],
            index=0 if current_show_views == "비공개 (사령관만 보임)" else 1,
            horizontal=True,
            help="일반 유저에게 조회수를 숨겨 초기 트래픽 부족을 감추거나, 충분히 활성화된 뒤에 공개할 수 있습니다."
        )
    with col_v2:
        st.write("") 
        if st.button("조회수 모드 적용 💾", use_container_width=True):
            try:
                val = "False" if new_show_views == "비공개 (사령관만 보임)" else "True"
                supabase.table("system_settings").upsert({
                    "key": "brag_board_show_views",
                    "value": val,
                    "updated_at": datetime.now().isoformat()
                }).execute()
                st.success(f"✅ 조회수 표시 모드가 [{new_show_views}]로 변경되었습니다!")
                st.rerun()
            except Exception as e:
                st.error(f"❌ 설정 변경 실패: {e}")

    st.write("---")
    # ==================================================================
    
    # 기존 관제사 관리 탭 구조 시작
    tab1, tab2, tab3, tab4 = st.tabs(["👥 전체 관제사 관리", "🚨 신규 권한 신청 현황", "🏷️ 테마 관리", "🗄️ DB 관리"])
    
    # ==================================================================
    # 👥 탭 1: 전체 관제사 관리 (이중 안전 영구 삭제 회로 탑재)
    # ==================================================================
    with tab1:
        st.markdown("📋 전체 사용자 데이터베이스")
        
        users_res = supabase.table("users").select("*").order("created_at", desc=True).execute()
        
        if users_res.data:
            # 레지스터 사전 채집 (체크박스 스캔)
            selected_user_ids = [
                user['id'] for user in users_res.data 
                if st.session_state.get(f"tab1_chk_{user['id']}")
            ]
            
            # 🔥 일괄 제어 마스터 스위치 블록
            col_b1, col_b2, col_b3, col_b4 = st.columns(4)
            if col_b1.button("🔒 선택 차단", key="bulk_block"):
                if selected_user_ids:
                    supabase.table("users").update({"is_allowed": False}).in_("id", selected_user_ids).execute()
                    st.success("✅ 선택된 계정이 일괄 차단되었습니다.")
                    st.rerun()
                else:
                    st.warning("⚠️ 제어할 관제사를 왼쪽 체크박스에서 선택해 주십시오.")
                    
            if col_b2.button("🔓 선택 재승인", key="bulk_approve"):
                if selected_user_ids:
                    supabase.table("users").update({"is_allowed": True}).in_("id", selected_user_ids).execute()
                    st.success("✅ 선택된 계정이 일괄 승인되었습니다.")
                    st.rerun()
                else:
                    st.warning("⚠️ 제어할 관제사를 왼쪽 체크박스에서 선택해 주십시오.")
                    
            if col_b3.button("⏳ 기간 연장 (+1개월)", key="bulk_extend"):
                if selected_user_ids:
                    new_expire = (datetime.now() + timedelta(days=30)).isoformat()
                    supabase.table("users").update({"valid_until": new_expire}).in_("id", selected_user_ids).execute()
                    st.success("⏳ 선택된 계정의 유효기간이 30일 연장되었습니다.")
                    st.rerun()
                else:
                    st.warning("⚠️ 제어할 관제사를 왼쪽 체크박스에서 선택해 주십시오.")
                    
            # 🎯 [이중 안전 보호막 결선 지점]
            if col_b4.button("🗑️ 선택 영구 삭제", type="primary", key="bulk_delete"):
                if selected_user_ids:
                    # 1단계 필터: 선택된 ID들 중에서 오직 현재 차단 상태(is_allowed == False)인 유저의 ID만 골라냅니다.
                    blocked_selected_ids = [
                        user['id'] for user in users_res.data
                        if user['id'] in selected_user_ids and not user['is_allowed']
                    ]
                    
                    if blocked_selected_ids:
                        # 2단계 실행: 차단된 유저들만 골라서 창고에서 파쇄!
                        supabase.table("users").delete().in_("id", blocked_selected_ids).execute()
                        
                        # 만약 정상 유저가 섞여 있어서 제외되었다면 안내 신호 다르게 인가
                        skipped_count = len(selected_user_ids) - len(blocked_selected_ids)
                        if skipped_count > 0:
                            st.success(f"✅ 차단 상태였던 사용자 {len(blocked_selected_ids)}명이 영구 삭제되었습니다. (정상 사용자는 안전 보호를 위해 {skipped_count}명 제외됨)")
                        else:
                            st.success("🗑️ 선택된 차단 사용자가 창고에서 완벽하게 영구 삭제되었습니다.")
                        st.rerun()
                    else:
                        # 선택된 유저 중 차단된 사람이 단 한 명도 없을 때 경고 브레이커 작동
                        st.error("🛑 영구 삭제 실패: 정상 가동 중인 사용자는 삭제할 수 없습니다! 삭제를 원하시면 먼저 '🔒 선택 차단'을 단행하여 전원을 내리십시오.")
                else:
                    st.warning("⚠️ 제어할 관제사를 왼쪽 체크박스에서 선택해 주십시오.")
            
            st.write("---")
            st.caption("💡 본인 계정 외의 관제사들을 체크하여 상단 버튼으로 일괄 제어할 수 있습니다.")
            
            # 명단 출력 레일
            for user in users_res.data:
                col_chk, col_id, col_name, col_status, col_time = st.columns([0.5, 2, 1.5, 1.5, 2.5])
                
                is_allowed = user['is_allowed']
                expire_data = user.get('valid_until')
                is_expired = False
                
                if expire_data:
                    expire_datetime = datetime.fromisoformat(expire_data).replace(tzinfo=None)
                    if expire_datetime < datetime.now():
                        is_expired = True
                
                if user['username'] == st.session_state.get('username'):
                    col_chk.write("👑")
                    col_id.write(f"**{user['username']}**")
                    col_status.write("✅ 마스터")
                else:
                    col_chk.checkbox("", key=f"tab1_chk_{user['id']}")
                    col_id.write(user['username'])
                    
                    if is_expired:
                        col_status.write("⚠️ 만료됨")
                    else:
                        status_text = "✅ 허용됨" if is_allowed else "❌ 차단됨"
                        col_status.write(status_text)
                
                col_name.write(user['name'])
                
                if expire_data:
                    expire_str = datetime.fromisoformat(expire_data).replace(tzinfo=None).strftime('%Y-%m-%d %H:%M')
                    if is_expired:
                        col_time.write(f"🛑 {expire_str} (만료)")
                    else:
                        col_time.write(f"📅 ~ {expire_str}")
                else:
                    col_time.write("♾️ 무제한")
        else:
            st.info("등록된 관제사가 없습니다.")

    # ==================================================================
    # 🚨 탭 2: 신규 권한 신청 현황 (가변 유효기간 분배 노브 탑재)
    # ==================================================================
    with tab2:
        st.markdown("📥 신규 권한 신청 현황")
        
        pending_res = supabase.table("users").select("*").eq("is_allowed", False).execute()
        
        if pending_res.data:
            selected_pending_ids = [
                p['id'] for p in pending_res.data 
                if st.session_state.get(f"tab2_pchk_{p['id']}")
            ]
            all_pending_ids = [p['id'] for p in pending_res.data]
            
            duration_options = [f"{i}개 월" for i in range(1, 13)] + ["무제한"]
            selected_duration = st.selectbox("⏳ 승인 시 인가할 유효기간 선택", duration_options, index=0, key="select_duration_knob")
            
            if selected_duration == "무제한":
                calculated_expire = None
            else:
                months_num = int(selected_duration.replace("개 월", "").replace("개월", ""))
                calculated_expire = (datetime.now() + timedelta(days=30 * months_num)).isoformat()
            
            st.write("") 
            col_p1, col_p2 = st.columns(2)
            
            if col_p1.button("🚀 신청자 전체 승인", use_container_width=True, key="btn_approve_all"):
                supabase.table("users").update({
                    "is_allowed": True, 
                    "valid_until": calculated_expire  
                }).in_("id", all_pending_ids).execute()
                st.success(f"🚀 모든 신청자가 승인되었으며, {selected_duration} 권한이 인가되었습니다.")
                st.rerun()
                
            if col_p2.button("🎯 선택된 신청자만 승인", use_container_width=True, key="btn_approve_selected"):
                if selected_pending_ids:
                    supabase.table("users").update({
                        "is_allowed": True, 
                        "valid_until": calculated_expire  
                    }).in_("id", selected_pending_ids).execute()
                    st.success(f"🎯 선택된 신청자들의 권한이 개방되었습니다 ({selected_duration} 인가).")
                    st.rerun()
                else:
                    st.warning("⚠️ 승인할 신청자를 아래 명단에서 체크해 주십시오.")
            
            st.write("---")
            
            for p_user in pending_res.data:
                col_pchk, col_pid, col_pname, col_pphone = st.columns([0.5, 2, 2, 3])
                
                col_pchk.checkbox("", key=f"tab2_pchk_{p_user['id']}")
                col_pid.write(p_user['username'])
                col_pname.write(p_user['name'])
                
                try:
                    raw_phone = base64.b64decode(p_user['phone_encoded']).decode('utf-8')
                except:
                    raw_phone = "번호 오류"
                col_pphone.write(raw_phone)
        else:
            st.success("✅ 대기 중인 신규 신청서가 없습니다. 평온한 상태입니다.")

    # ==================================================================
    # 🏷️ 탭 3: 테마 관리 (Theme Management)
    # ==================================================================
    with tab3:
        st.markdown("🏷️ 종목 테마 데이터베이스 관리")
        st.caption("주식 종목별 테마를 지정하면 TOP 10 화면에서 시황을 분석하는 데 강력한 무기가 됩니다.")
        
        # 1. 새 테마 등록/수정 패널
        with st.expander("➕ 새 종목 테마 등록 / 덮어쓰기", expanded=True):
            tc1, tc2 = st.columns([1, 2])
            with tc1:
                t_stock = st.text_input("종목명", placeholder="예: SK하이닉스")
            with tc2:
                t_themes = st.text_input("테마 (복수일 경우 콤마로 구분)", placeholder="예: 반도체, HBM, AI")
            
            if st.button("테마 저장 💾", use_container_width=True):
                if t_stock.strip() and t_themes.strip():
                    try:
                        supabase.table("stock_themes").upsert({
                            "stock_name": t_stock.strip(),
                            "theme_names": t_themes.strip(),
                            "updated_at": datetime.now().isoformat()
                        }).execute()
                        st.success(f"✅ {t_stock.strip()} 종목의 테마가 [{t_themes.strip()}]로 저장/덮어쓰기 완료되었습니다!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ 데이터베이스 저장 실패: {e}")
                else:
                    st.error("종목명과 테마를 모두 입력해 주십시오.")
                    
        # 2. 엑셀(CSV) 일괄 대량 업로드
        with st.expander("🚀 엑셀(CSV) 일괄 대량 업로드 (Bulk Upload)", expanded=False):
            st.info("💡 엑셀 파일 작성법: 엑셀에서 A열에 [테마명], B열에 [종목명들(콤마로 구분)]을 적어주세요.\n\n예시)\nA열: 반도체\nB열: 삼성전자, SK하이닉스, 한미반도체\n\n작성 후 **[파일 -> 다른 이름으로 저장 -> CSV(쉼표로 분리)]** 형식으로 저장해서 올려주세요.")
            uploaded_file = st.file_uploader("CSV 파일 선택", type=['csv'])
            if uploaded_file is not None:
                try:
                    df_upload = pd.read_csv(uploaded_file, encoding='utf-8', header=None)
                    if len(df_upload.columns) >= 2:
                        if st.button("파일 데이터 DB에 일괄 저장 🚀"):
                            stock_to_themes = {}
                            now_str = datetime.now().isoformat()
                            
                            for _, row in df_upload.iterrows():
                                theme = str(row.iloc[0]).strip()
                                stocks_str = str(row.iloc[1]).strip()
                                
                                # 사용자가 첫 줄에 제목(헤더)을 적었을 경우 스킵
                                if theme in ['테마', '테마명', '테마이름', 'theme'] or stocks_str in ['종목', '종목명', '종목이름', '종목들', 'stock']:
                                    continue
                                
                                if theme and theme != 'nan' and stocks_str and stocks_str != 'nan':
                                    # 콤마로 구분된 종목명들을 리스트로 분리
                                    stocks = [s.strip() for s in stocks_str.split(',') if s.strip()]
                                    for stock in stocks:
                                        if stock not in stock_to_themes:
                                            stock_to_themes[stock] = []
                                        # 중복 테마 방지
                                        if theme not in stock_to_themes[stock]:
                                            stock_to_themes[stock].append(theme)
                            
                            bulk_data = []
                            for stock, themes_list in stock_to_themes.items():
                                bulk_data.append({
                                    "stock_name": stock,
                                    "theme_names": ", ".join(themes_list),
                                    "updated_at": now_str
                                })
                            
                            if bulk_data:
                                # Supabase bulk upsert (기존 데이터가 있다면 덮어씁니다)
                                supabase.table("stock_themes").upsert(bulk_data).execute()
                                st.success(f"✅ 총 {len(bulk_data)}개 종목의 테마 세팅이 완벽하게 업로드되었습니다!")
                                st.rerun()
                            else:
                                st.warning("유효한 데이터가 없습니다. 형식을 확인해 주세요.")
                    else:
                        st.error("CSV 파일에 최소 2개의 열(A열: 테마, B열: 종목들)이 필요합니다.")
                except UnicodeDecodeError:
                    st.error("엑셀에서 CSV로 저장하실 때 'CSV UTF-8 (쉼표로 분리)' 형식으로 저장해 주십시오.")
                except Exception as e:
                    st.error(f"파일 처리 중 오류 발생: {e}")

        # 3. 현재 등록된 테마 목록 조회 (삭제 포함)
        st.markdown("##### 📚 현재 등록된 테마 목록")
        try:
            theme_res = supabase.table("stock_themes").select("*").order("updated_at", desc=True).execute()
            if theme_res.data:
                theme_df = pd.DataFrame(theme_res.data)
                theme_df.rename(columns={"stock_name": "종목명", "theme_names": "테마", "updated_at": "업데이트 시간"}, inplace=True)
                
                st.dataframe(theme_df, use_container_width=True, hide_index=True)
                
                with st.expander("🗑️ 종목 테마 삭제"):
                    del_stock = st.selectbox("삭제할 종목 선택", theme_df['종목명'].tolist())
                    if st.button("해당 종목 테마 영구 삭제 🚨"):
                        supabase.table("stock_themes").delete().eq("stock_name", del_stock).execute()
                        st.success(f"🗑️ {del_stock}의 테마 정보가 삭제되었습니다.")
                        st.rerun()
            else:
                st.info("현재 저장된 테마 정보가 없습니다.")
        except Exception as e:
            st.error(f"DB 통신 오류: {e}")

    # ==================================================================
    # 🗄️ 탭 4: DB 관리 (Mock Data Management)
    # ==================================================================
    with tab4:
        st.markdown("### 🗄️ 가상 데이터(Mock Data) 관리")
        st.info("홍보 영상 제작 등을 위해 임의의 가상 데이터를 DB(whale_log)에 넣고, 한 번에 지울 수 있는 기능입니다.")
        
        with st.expander("➕ 새 가상 데이터 등록", expanded=True):
            st.markdown("**(입력 양식)** `날짜, 시간, 종목코드, 종목명, 체결가, 거래량, 체결금액, 자산타입, 시장타입, 매매방향`")
            st.markdown("*예시: 2026-08-01, 09:30:00, 005930, 삼성전자, 85000, 10000, 850000000, 개별주식, KOSPI, 매수*")
            
            mock_input = st.text_input("위 양식에 맞춰 콤마(,)로 구분하여 데이터를 입력하세요.")
            if st.button("가상 데이터 입력 💾"):
                if mock_input:
                    try:
                        import re
                        # 콤마 또는 탭 기준으로 우선 분리
                        parts = [p.strip() for p in re.split(r'[,\t]', mock_input) if p.strip()]
                        
                        # 콤마나 탭이 없었다면 공백 기준으로 분리 (표에서 복사 후 공백으로 구분된 경우 대비)
                        if len(parts) < 10:
                            parts = [p.strip() for p in mock_input.split() if p.strip()]
                            
                        if len(parts) >= 10:
                            insert_data = None
                            
                            # 1. 표에서 바로 복사해서 붙여넣은 경우 (맨 앞에 ID가 오고, 날짜가 뒤쪽에 위치)
                            # 표 순서: ID, Time, Code, Name, Price, Vol, Amt, Date, Asset, Market, Side
                            if ":" in parts[1] and "-" in parts[-4]:
                                insert_data = {
                                    "time": parts[1],
                                    "code": parts[2],
                                    "name": " ".join(parts[3:len(parts)-7]), # 이름에 띄어쓰기가 있을 경우 병합
                                    "price": int(parts[-7].replace(',', '')),
                                    "volume": int(parts[-6].replace(',', '')),
                                    "amount_krw": int(parts[-5].replace(',', '')),
                                    "date": parts[-4],
                                    "asset_type": parts[-3],
                                    "market_type": parts[-2],
                                    "side": parts[-1]
                                }
                            # 2. 직접 콤마나 공백으로 입력한 경우 (제시된 템플릿 순서)
                            # 순서: Date, Time, Code, Name, Price, Vol, Amt, Asset, Market, Side
                            elif "-" in parts[0] and ":" in parts[1]:
                                insert_data = {
                                    "date": parts[0],
                                    "time": parts[1],
                                    "code": parts[2],
                                    "name": " ".join(parts[3:len(parts)-6]),
                                    "price": int(parts[-6].replace(',', '')),
                                    "volume": int(parts[-5].replace(',', '')),
                                    "amount_krw": int(parts[-4].replace(',', '')),
                                    "asset_type": parts[-3],
                                    "market_type": parts[-2],
                                    "side": parts[-1]
                                }
                            else:
                                st.error("입력하신 데이터의 날짜와 시간 위치를 인식할 수 없습니다. 양식에 맞추거나 표의 한 줄을 그대로 복사해 주세요.")
                                
                            if insert_data:
                                # 1. whale_log에 삽입
                                res = supabase.table("whale_log").insert(insert_data).execute()
                                if res.data and len(res.data) > 0:
                                    inserted_id = res.data[0]['id']
                                    
                                    # 2. system_settings에 ID 기록
                                    track_data = {
                                        "key": f"mock_whale_id_{inserted_id}",
                                        "value": str(inserted_id)
                                    }
                                    supabase.table("system_settings").insert(track_data).execute()
                                    
                                    st.success(f"✅ 가상 데이터가 성공적으로 등록되었습니다. (ID: {inserted_id})")
                                else:
                                    st.error("DB 삽입에 실패했습니다.")
                        else:
                            st.error(f"입력 형식이 맞지 않습니다. (10개의 항목 필요, 현재 {len(parts)}개)")
                    except Exception as e:
                        st.error(f"입력 처리 중 오류 발생: {e}")
                else:
                    st.warning("데이터를 입력해 주세요.")
        
        st.markdown("---")
        st.markdown("### 🗑️ 가상 데이터 일괄 삭제")
        st.write("이전에 등록한 모든 가상 데이터를 한 번에 삭제합니다.")
        if st.button("🚨 추적된 가상 데이터 일괄 삭제 🚨"):
            try:
                # 1. system_settings에서 기록된 ID 가져오기
                mock_ids_res = supabase.table("system_settings").select("value").like("key", "mock_whale_id%").execute()
                if mock_ids_res.data:
                    deleted_count = 0
                    # 2. whale_log에서 삭제
                    for item in mock_ids_res.data:
                        del_id = int(item['value'])
                        supabase.table("whale_log").delete().eq("id", del_id).execute()
                        deleted_count += 1
                    
                    # 3. system_settings에서 기록 지우기
                    supabase.table("system_settings").delete().like("key", "mock_whale_id%").execute()
                    st.success(f"🗑️ 총 {deleted_count}개의 가상 데이터가 안전하게 삭제되었습니다.")
                else:
                    st.info("삭제할 가상 데이터 기록이 없습니다.")
            except Exception as e:
                st.error(f"가상 데이터 삭제 중 오류 발생: {e}")
                
        st.markdown("---")
        st.markdown("### 📅 특정 날짜 데이터 조회")
        selected_date = st.date_input("조회할 날짜 선택")
        if selected_date:
            try:
                date_str = selected_date.strftime('%Y-%m-%d')
                logs_res = supabase.table("whale_log").select("*").eq("date", date_str).order("time", desc=True).limit(500).execute()
                if logs_res.data:
                    logs_df = pd.DataFrame(logs_res.data)
                    st.write(f"**{date_str}**의 고래 로그 목록 (최대 500건)")
                    st.dataframe(logs_df, use_container_width=True)
                else:
                    st.info(f"{date_str}의 데이터가 없습니다.")
            except Exception as e:
                st.error(f"조회 중 오류 발생: {e}")


################################################################################
# 30일 단일 종목 일별 거래금액 막대그래프 및 백테스트
################################################################################
def calculate_backtest_yield(chart_df):
    if chart_df.empty:
        return []
    
    # 1. 일별 순매수 및 종가(마지막 체결가) 추출
    daily_stats = []
    for date, group in chart_df.groupby('date'):
        buy_sum = group[group['side'] == '매수']['amount_krw'].sum()
        sell_sum = group[group['side'] == '매도']['amount_krw'].sum()
        net_buy = buy_sum - sell_sum
        
        # 해당 날짜의 체결 데이터 중 가장 마지막 시간을 종가로 간주
        last_price = group.sort_values('time').iloc[-1]['price']
        daily_stats.append({
            'date': date,
            'net_buy': net_buy,
            'last_price': last_price
        })
    
    stats_df = pd.DataFrame(daily_stats).sort_values('date').reset_index(drop=True)
    if len(stats_df) < 4:
        return []
        
    # 2. 결과 검증을 위해 최소 5일 이후의 데이터가 존재하는 날짜만 추출 (최근 5일 제외)
    valid_df = stats_df.iloc[:-5].copy()
    if valid_df.empty:
        return []
        
    # 3. 과거 한 달 중 순매수가 가장 강력했던 Top 2 날짜 선정
    top_2 = valid_df.nlargest(2, 'net_buy')
    if top_2['net_buy'].max() <= 0:
        return [] # 매수 폭주가 없었음
        
    results = []
    for _, row in top_2.iterrows():
        if row['net_buy'] <= 0: continue
        
        t_date = row['date']
        t_price = row['last_price']
        
        t_idx = stats_df[stats_df['date'] == t_date].index[0]
        # T+1일 ~ T+5일 (영업일 기준)
        end_idx = min(t_idx + 5, len(stats_df) - 1)
        
        # T+1 ~ T+5일 사이의 데이터 중 최고가(last_price)를 기록한 날 찾기
        future_window = stats_df.iloc[t_idx+1 : end_idx+1]
        if future_window.empty:
            continue
            
        best_idx = future_window['last_price'].idxmax()
        best_row = future_window.loc[best_idx]
        
        t3_date = best_row['date']
        t3_price = best_row['last_price']
        
        yield_pct = ((t3_price - t_price) / t_price) * 100
        
        # 마이너스 수익률이거나 0이면 표시하지 않음
        if yield_pct <= 0: continue
        
        results.append({
            't_date': t_date.strftime('%m월 %d일'),
            't3_date': t3_date.strftime('%m월 %d일'),
            'net_buy': row['net_buy'],
            'yield_pct': yield_pct,
            't_price': t_price,
            't3_price': t3_price
        })
        
    return results

def get_hot_signals(df):
    if df.empty:
        return []
        
    # 오늘 날짜(가장 최근 날짜)만 필터링
    latest_date = df['datetime'].dt.floor('D').max()
    today_df = df[df['datetime'].dt.floor('D') == latest_date]
    if today_df.empty:
        return []
        
    # 종목별 순매수액(Net Buy) 및 매수 횟수 계산
    buy_df = today_df[today_df['side'] == '매수']
    sell_df = today_df[today_df['side'] == '매도']
    
    buy_sum = buy_df.groupby('name')['amount_krw'].sum()
    sell_sum = sell_df.groupby('name')['amount_krw'].sum()
    buy_count = buy_df.groupby('name').size()
    
    # 데이터프레임 조인
    summary = pd.DataFrame({
        'buy_amount': buy_sum,
        'sell_amount': sell_sum,
        'buy_count': buy_count
    }).fillna(0)
    
    summary['net_buy'] = summary['buy_amount'] - summary['sell_amount']
    
    # 순매수(net_buy)가 0보다 큰(양수) 종목 전체를 대상으로 함 (빈 화면 방지)
    hot_df = summary[summary['net_buy'] > 0].copy()
    if hot_df.empty:
        return []
        
    import math
    # 점수화 (로그 스케일 적용): 10억(log 9) = 50점, 1조(log 12) = 90점 기준
    # 대형주와 중소형주의 체급 차이를 로가리즘으로 자연스럽게 보정합니다.
    hot_df['log_buy'] = hot_df['net_buy'].apply(lambda x: math.log10(x) if x > 0 else 0)
    hot_df['log_cnt'] = hot_df['buy_count'].apply(lambda x: math.log10(x) if x > 0 else 0)
    hot_df['score'] = 50.0 + (hot_df['log_buy'] - 9.0) * 13.33 + (hot_df['log_cnt'] * 3.0)
    hot_df['score'] = hot_df['score'].apply(lambda x: max(0.0, min(float(x), 99.9)))
    
    # 30점 미만의 자잘한 신호는 취급하지 않음 ("우린 짜잔한거 취급 안한다!")
    # hot_df = hot_df[hot_df['score'] >= 30.0]
    
    # 상위 3개 추출
    top3 = hot_df.sort_values(by=['score', 'net_buy'], ascending=False).head(3)
    
    result = []
    for name, row in top3.iterrows():
        score = row['score']
        if score >= 95:
            icon = "👑"
        elif score >= 90:
            icon = "🔥"
        elif score >= 70:
            icon = "💥"
        elif score >= 30:
            icon = "✨"
        else:
            icon = "🌱"
            
        result.append({
            'name': name,
            'score': score,
            'net_buy': row['net_buy'],
            'buy_count': row['buy_count'],
            'icon': icon
        })
    return result

def get_accumulated_hot_signals(df):
    if df.empty:
        return []
        
    # 기간 누적: latest_date 필터링 없이 전체 df 사용
    
    # 종목별 순매수액(Net Buy) 및 매수 횟수 계산
    buy_df = df[df['side'] == '매수']
    sell_df = df[df['side'] == '매도']
    
    buy_sum = buy_df.groupby('name')['amount_krw'].sum()
    sell_sum = sell_df.groupby('name')['amount_krw'].sum()
    buy_count = buy_df.groupby('name').size()
    
    # 데이터프레임 조인
    summary = pd.DataFrame({
        'buy_amount': buy_sum,
        'sell_amount': sell_sum,
        'buy_count': buy_count
    }).fillna(0)
    
    summary['net_buy'] = summary['buy_amount'] - summary['sell_amount']
    
    # 순매수(net_buy)가 0보다 큰(양수) 종목 전체를 대상으로 함 (빈 화면 방지)
    hot_df = summary[summary['net_buy'] > 0].copy()
    if hot_df.empty:
        return []
            
    import math
    hot_df['log_buy'] = hot_df['net_buy'].apply(lambda x: math.log10(x) if x > 0 else 0)
    hot_df['log_cnt'] = hot_df['buy_count'].apply(lambda x: math.log10(x) if x > 0 else 0)
    hot_df['score'] = 50.0 + (hot_df['log_buy'] - 9.0) * 13.33 + (hot_df['log_cnt'] * 3.0)
    hot_df['score'] = hot_df['score'].apply(lambda x: max(0.0, min(float(x), 99.9)))
    
    # 30점 미만 필터링
    # hot_df = hot_df[hot_df['score'] >= 30.0]
    
    # 상위 10개 추출
    top10 = hot_df.sort_values(by=['score', 'net_buy'], ascending=False).head(10)
    
    result = []
    for name, row in top10.iterrows():
        score = row['score']
        if score >= 95:
            icon = "👑"
        elif score >= 90:
            icon = "🔥"
        elif score >= 70:
            icon = "💥"
        elif score >= 30:
            icon = "✨"
        else:
            icon = "🌱"
            
        result.append({
            'name': name,
            'score': score,
            'icon': icon,
            'net_buy': row['net_buy'],
            'buy_count': row['buy_count']
        })
        
    return result

def draw_whale_bar_chart(target_code, target_name, df):
    """특정 종목의 한 달 치 수급 누적 바 차트를 그리는 함수 (30일 고정 스케일 적용)"""
    st.markdown(f"### 📊 [{target_name}] 고래 수급 일별 현황 (최근 1개월)")
    
    # 1. 타겟 종목 데이터 추출 및 날짜 변환
    chart_df = df[df['code'] == target_code].copy()
    
    if chart_df.empty:
        st.warning(f"⚠️ '{target_name}' 종목은 최근 기간 내에 고래 수급 데이터가 없습니다.")
        return

    chart_df['date'] = pd.to_datetime(chart_df['date']).dt.date
    
    # 2. 실제 데이터 그룹화 (매수/매도 합산)
    grouped_df = chart_df.groupby(['date', 'side'])['amount_krw'].sum().reset_index()

    # =========================================================================
    # 🚨 [신규 튜닝]: 오늘 기준 과거 30일 치 '빈 달력 뼈대' 만들기
    # =========================================================================
    today = get_latest_market_open_date()
    # 최근 30일 날짜 리스트 생성
    date_list = [today - timedelta(days=x) for x in range(30)]
    
    # 빈 뼈대 데이터프레임 만들기 (모든 날짜에 대해 매수/매도/방향미상 0원으로 세팅)
    skeleton_data = []
    for d in date_list:
        skeleton_data.append({'date': d, 'side': '매수', 'amount_krw': 0})
        skeleton_data.append({'date': d, 'side': '매도', 'amount_krw': 0})
        skeleton_data.append({'date': d, 'side': '방향미상', 'amount_krw': 0})
        
    skeleton_df = pd.DataFrame(skeleton_data)
    
    # 뼈대(skeleton)와 실제 데이터(grouped_df) 병합 완료 후!
    merged_df = pd.concat([skeleton_df, grouped_df]).groupby(['date', 'side'])['amount_krw'].sum().reset_index()
    
    # =========================================================================
    # 🚨 [신규 튜닝]: X축 라벨 가독성 극대화 (연도 제거, 월-일 포맷으로 강제 변환)
    # =========================================================================
    merged_df['date_str'] = pd.to_datetime(merged_df['date']).dt.strftime('%m-%d')
    merged_df['amount_krw_100m'] = merged_df['amount_krw'] / 100000000
    # 시장 전체 일일 거래대금 (FDR 연동)
    target_code = chart_df['code'].iloc[0]
    thirty_days_ago = today - timedelta(days=30)
    kis_df = fetch_kis_daily_volume(target_code, thirty_days_ago)
    
    if not kis_df.empty:
        kis_df['date_str'] = pd.to_datetime(kis_df['date']).dt.strftime('%m-%d')
        kis_df['amount_100m'] = kis_df['acml_tr_pbmn'] / 100000000

    # 투자자별 매매동향 (외국인/기관) 가져오기
    investor_df = fetch_investor_net_buying(target_code)
    valid_dates = merged_df['date_str'].unique()
    if not investor_df.empty:
        # 30일(달력기준) 이내의 데이터만 남기기 (주말 등 제외로 데이터가 많아지는 현상 방지)
        investor_df = investor_df[investor_df['date_str'].isin(valid_dates)]
    
    # 4. 차트 레이아웃 구성 (위: 고래 수급, 2: 시장 거래대금, 3: 외인/기관 수급, 4: 캔들차트)
    fig_bar = make_subplots(
        rows=4, cols=1, 
        shared_xaxes=True, 
        row_heights=[0.35, 0.15, 0.25, 0.25], 
        vertical_spacing=0.06,
        subplot_titles=(f"[{target_name}] 고래 수급 누적 (30일)", "시장 전체 일일 거래대금", "외국인/기관 상세 수급", "주가 흐름 (OHLC)")
    )
    
    # 🌟 [초지능형 튜닝]: 최근 30일 일별 골든스코어(Golden Score) 실시간 정밀 산출
    golden_scores = {}
    golden_scores_breakdown = {}
    is_trading_day = {}
    try:
        fortyfive_days_str = (today - timedelta(days=45)).strftime("%Y-%m-%d")
        clean_target_name = target_name.replace("🚀","").replace("👑","").replace("🔥","").replace("💥","").replace("✨","").replace("🌱","").strip()
        
        # 🎯 안전한 예외 없는 2중 쿼리로 Supabase APIError 원천 차단
        hist_top_res = supabase.table("daily_whale_top200").select("*").gte("trade_date", fortyfive_days_str).eq("stock_name", clean_target_name).order("trade_date", desc=True).limit(1000).execute()
        if not hist_top_res.data:
            hist_top_res = supabase.table("daily_whale_top200").select("*").gte("trade_date", fortyfive_days_str).eq("stock_code", target_code).order("trade_date", desc=True).limit(1000).execute()
        
        hist_top_dict = {}
        if hist_top_res.data:
            for r_item in hist_top_res.data:
                d_m = pd.to_datetime(r_item['trade_date']).strftime('%m-%d')
                hist_top_dict[d_m] = r_item
                
        # 🎯 실제 DB에 수집된 거래일 목록만 가져오기 (스크래퍼 누락 시 억울한 점수 삭감 방지)
        all_db_trade_dates_res = supabase.table("daily_whale_top200").select("trade_date").gte("trade_date", fortyfive_days_str).order("trade_date", desc=True).limit(5000).execute()
        all_db_trade_dates = sorted(list(set([pd.to_datetime(r['trade_date']).date() for r in all_db_trade_dates_res.data]))) if all_db_trade_dates_res.data else []

        investor_dict = {}
        if not investor_df.empty:
            for _, inv_row in investor_df.iterrows():
                investor_dict[inv_row['date_str']] = (inv_row['frgn_net_100m'], inv_row['orgn_net_100m'])

        upper_res = supabase.table("upper_limit_stocks").select("recorded_date").eq("name", clean_target_name).execute()
        upper_dates = set([pd.to_datetime(r['recorded_date']).strftime('%m-%d') for r in upper_res.data]) if upper_res.data else set()

        global_meta = get_global_stock_metadata()
        warning_text = get_warning_text(clean_target_name, global_meta)

        # 🌟 [초지능형 튜닝]: 오늘 실시간 데이터를 백만 단위로 집계 (rt_buy 용도)
        whale_daily_buy = {}
        if not merged_df.empty:
            w_grouped = merged_df[merged_df['side'] == '매수'].groupby('date_str')['amount_krw'].sum() / 1_000_000
            whale_daily_buy = w_grouped.to_dict()

        # 🐳 14일 롤링 고래 수급 합산을 위한 과거 45일 로그 가져오기 (PostgREST 1000건 리밋 우회 위해 최신순 정렬)
        # 🔧 [버그 수정 2026-07-29]: name(종목명) exact-match는 whale_log에 이모지/공백 등 표기 변형이 섞여 있으면
        # 조용히 일부 행을 놓친다 (골든픽 화면은 Python 쪽에서 이모지를 지우고 매칭해서 덜 놓쳤음 → 두 화면 rt_buy 불일치 원인).
        # code(종목코드)는 표기 변형이 없는 고유값이라 여기로 통일.
        w_hist_res = supabase.table("whale_log").select("date, side, amount_krw").gte("date", fortyfive_days_str).eq("code", target_code).order("date", desc=True).limit(5000).execute()
        whale_history = pd.DataFrame(w_hist_res.data) if w_hist_res.data else pd.DataFrame(columns=['date', 'side', 'amount_krw'])
        if not whale_history.empty:
            whale_history['date'] = pd.to_datetime(whale_history['date']).dt.date

        holidays = get_market_holidays()

        for d_dt in merged_df['date'].unique():
            if isinstance(d_dt, str):
                d_dt = pd.to_datetime(d_dt).date()
            d_str = d_dt.strftime('%m-%d')

            r_val = hist_top_dict.get(d_str)
            has_investor = d_str in investor_dict
            has_whale = d_str in whale_daily_buy and whale_daily_buy[d_str] > 0
            
            # 주말/휴장일 판독 (DB 수급, 외인/기관 수급, 고래 체결이 모두 없으면 휴장일)
            if not r_val and not has_investor and not has_whale:
                is_trading_day[d_str] = False
                golden_scores[d_str] = None
                continue
                
            is_trading_day[d_str] = True
            
            if r_val:
                f_buy = int(r_val.get('frgn_buy', 0))
                f_sell = int(r_val.get('frgn_sell', 0))
                o_buy = int(r_val.get('orgn_buy', 0))
                o_sell = int(r_val.get('orgn_sell', 0))
                frgn_net = f_buy - f_sell
                orgn_net = o_buy - o_sell
            elif has_investor:
                frgn_net, orgn_net = investor_dict[d_str]
            else:
                frgn_net, orgn_net = 0, 0
                
            total_net = frgn_net + orgn_net

            score = 25
            start_date_dt = d_dt - timedelta(days=14)

            # 🌟 [튜닝 2026-07-29] 고래매수 일평균을 위해 14일 윈도의 "실제 거래일수"를 먼저 구한다 (아래 rt_buy에서 사용)
            period_trading_days = [td for td in all_db_trade_dates if start_date_dt <= td <= d_dt]
            total_trading_days = len(period_trading_days) if period_trading_days else 1

            # 🌟 14일 롤링 고래 수급 (과거 14일 DB 합계)
            past_14_buy_sum = 0
            if not whale_history.empty:
                # Dashboard와 완벽히 동일하게 당일(d_dt) 포함 합산
                w_14d = whale_history[(whale_history['date'] >= start_date_dt) & (whale_history['date'] <= d_dt)]
                past_14_buy_sum = w_14d[w_14d['side'] == '매수']['amount_krw'].sum() / 1_000_000

            # 🔧 [버그 수정 2026-07-29]: whale_history 쿼리는 gte(45일 전)만 걸려있어 '오늘' 체결분까지 이미 포함됨.
            # 예전엔 여기서 today_rt_buy(=merged_df/chart_df 기준 당일 매수액)를 별도로 한 번 더 더했는데,
            # 그러면 당일 매수액이 과거 14일 합계 안에 이미 들어있는 채로 중복 가산되어 버렸음.
            # 🔧 [튜닝 2026-07-29] 14일 "합계"를 그대로 문턱값과 비교하면 거래일이 쌓일수록 점수가 계속 부풀려지므로,
            # 실제 거래일수(total_trading_days)로 나눈 "일평균 고래매수"를 점수 산출에 사용 (골든픽 화면과 동일한 기준으로 통일)
            rt_buy = past_14_buy_sum / total_trading_days

            # 🔧 [튜닝 2026-07-29] 강세장에서 여러 종목이 동시에 100점 상한에 몰려 변별력이 사라지는 문제 수정.
            # 기존 만점 총합(25+25+25+15+15+10+5=120, 100점 클리핑)을 실질 상한 82점대로 압축 (약 0.6배율, 아래 전 항목 동일 적용).
            if rt_buy >= 1000: s_rt = 15
            elif rt_buy >= 100: s_rt = 9
            elif rt_buy > 0: s_rt = 5
            else: s_rt = -9
            score += s_rt

            if total_net >= 300: s_tot = 15
            elif total_net >= 100: s_tot = 12
            elif total_net >= 50: s_tot = 9
            elif total_net >= 20: s_tot = 6
            elif total_net > 0: s_tot = 2
            else: s_tot = 0
            score += s_tot

            if frgn_net > 0 and orgn_net > 0: s_pair = 9
            elif frgn_net < -100 or orgn_net < -100: s_pair = -12
            else: s_pair = 0
            score += s_pair

            # 🌟 [신규 튜닝] 수급 지속성(연속 출현) 판단 — 위에서 구한 14일 윈도(period_trading_days) 재사용
            app_count = sum(1 for td in period_trading_days if td.strftime('%m-%d') in hist_top_dict)

            # 🔧 [버그 수정 2026-07-29]: DB 쿼리가 일시적으로 비어있으면(네트워크 지연 등) app_count=0,
            # total_trading_days=1로 폴백되는데, "0 >= 1-1(=0)"이 참이 되어 실제로는 단 하루도
            # TOP200에 출현하지 않은 종목에게 "수급 지속성 우수" 보너스가 잘못 부여되는 함정이 있었음
            # (같은 종목/같은 날짜인데도 화면마다 골든스코어가 달라지던 원인 중 하나로 추정).
            # app_count>0(실제로 최소 1일은 출현) 조건을 추가해 이 오탐을 차단.
            if app_count >= total_trading_days: s_cont = 9
            elif app_count > 0 and app_count >= total_trading_days - 1: s_cont = 5
            else: s_cont = 0
            score += s_cont

            # 🌟 [신규 튜닝] 상한가 이력 판독 14일 윈도우 계산
            # Dashboard는 최근 14일 이내 상한가 이력이 있으면 가산점을 부여하므로, Chart도 동일하게 맞춤
            upper_in_14d = any(start_date_dt <= pd.to_datetime(f"{today.year}-{u_d}").date() <= d_dt for u_d in upper_dates)

            if upper_in_14d:
                # 🔧 [버그 수정 2026-07-29]: 위와 동일한 app_count>0 함정 방지
                if app_count > 0 and app_count >= total_trading_days - 1: s_upper = 6
                else: s_upper = -18
            else:
                s_upper = 0
            score += s_upper

            if not warning_text: s_warn = 3
            else: s_warn = -9
            score += s_warn

            golden_scores[d_str] = max(0, min(score, 100))
            golden_scores_breakdown[d_str] = {
                "s_base": 25, "s_rt": s_rt, "s_tot": s_tot, 
                "s_pair": s_pair, "s_cont": s_cont, "s_upper": s_upper, "s_warn": s_warn
            }
    except Exception as e:
        print(f"Chart Golden Score Calc Error: {e}")

    # 상단 막대그래프 (매수/매도/방향미상)
    buy_df = merged_df[merged_df['side'] == '매수']
    sell_df = merged_df[merged_df['side'] == '매도']
    unknown_df = merged_df[merged_df['side'] == '방향미상']

    # 🏆 [골든스코어 호버 트레이스 인가] (주말/휴장일은 깔끔하게 휴장일 표출, 평일 거래일은 정밀 점수 표출!)
    score_y = [golden_scores.get(d) if golden_scores.get(d) is not None else 0 for d in buy_df['date_str']]
    score_text = [f"<b>{golden_scores.get(d)}점</b>" if golden_scores.get(d) is not None else "휴장일" for d in buy_df['date_str']]

    fig_bar.add_trace(go.Scatter(
        x=buy_df['date_str'], y=score_y,
        name="🏆 골든스코어",
        mode="markers",
        marker=dict(size=0, color="#FFD700"),
        text=score_text,
        hovertemplate="%{text}<extra></extra>"
    ), row=1, col=1)
    
    fig_bar.add_trace(go.Bar(
        x=buy_df['date_str'], y=buy_df['amount_krw_100m'],
        name="매수", marker_color='#ff4b4b',
        text=buy_df['amount_krw_100m'].apply(lambda x: f"{x:,.0f}억" if x > 0 else ""),
        textposition='outside', textfont=dict(size=11)
    ), row=1, col=1)
    
    fig_bar.add_trace(go.Bar(
        x=sell_df['date_str'], y=sell_df['amount_krw_100m'],
        name="매도", marker_color='#4B89B5',
        text=sell_df['amount_krw_100m'].apply(lambda x: f"{x:,.0f}억" if x > 0 else ""),
        textposition='outside', textfont=dict(size=11)
    ), row=1, col=1)

    fig_bar.add_trace(go.Bar(
        x=unknown_df['date_str'], y=unknown_df['amount_krw_100m'],
        name="방향미상", marker_color='#888888', opacity=0.7,
        text=unknown_df['amount_krw_100m'].apply(lambda x: f"{x:,.0f}억" if x > 0 else ""),
        textposition='outside', textfont=dict(size=11, color='#aaaaaa')
    ), row=1, col=1)
    
    # 2번째: 시장 전체 거래대금
    if 'kis_df' in locals() and not kis_df.empty:
        fig_bar.add_trace(go.Bar(
            x=kis_df['date_str'], y=kis_df['amount_100m'],
            name="전체 거래대금", marker_color='#888888', opacity=0.6,
            text=kis_df['amount_100m'].apply(lambda x: f"{x:,.0f}억" if x > 0 else ""),
            textposition='outside', textfont=dict(size=10, color='#888888'),
            showlegend=False
        ), row=2, col=1)
    
    # 3번째: 외국인/기관 상세 수급 (순매수로 변경)
    if not investor_df.empty:
        # 외국인 순매수
        fig_bar.add_trace(go.Bar(
            x=investor_df['date_str'], y=investor_df['frgn_net_100m'],
            name="외국인 순매수", marker_color='#FFB000', opacity=0.9,
            offset=-0.2, width=0.4,
            text=investor_df['frgn_net_100m'].apply(lambda x: f"{x:,.0f}억" if x != 0 else ""),
            textposition='auto', textfont=dict(size=10, color='white')
        ), row=3, col=1)
        
        # 기관 순매수
        fig_bar.add_trace(go.Bar(
            x=investor_df['date_str'], y=investor_df['orgn_net_100m'],
            name="기관 순매수", marker_color='#00FA9A', opacity=0.9,
            offset=0.2, width=0.4,
            text=investor_df['orgn_net_100m'].apply(lambda x: f"{x:,.0f}억" if x != 0 else ""),
            textposition='auto', textfont=dict(size=10, color='black')
        ), row=3, col=1)

    # 하단 캔들스틱 차트 (주가)
    if 'kis_df' in locals() and not kis_df.empty:
        fig_bar.add_trace(go.Candlestick(
            x=kis_df['date_str'],
            open=kis_df['Open'], high=kis_df['High'],
            low=kis_df['Low'], close=kis_df['Close'],
            name="주가",
            increasing_line_color='#ff4b4b', decreasing_line_color='#4B89B5',
            showlegend=False
        ), row=4, col=1)
        
        # 🚀 상한가 로켓 아이콘 추가
        upper_dates_res = supabase.table("upper_limit_stocks").select("recorded_date").eq("name", target_name).gte("recorded_date", thirty_days_ago.strftime('%Y-%m-%d')).execute()
        if upper_dates_res.data:
            upper_dates_md = [pd.to_datetime(item['recorded_date']).strftime('%m-%d') for item in upper_dates_res.data]
            for d in upper_dates_md:
                if d in kis_df['date_str'].values:
                    high_price = kis_df[kis_df['date_str'] == d]['High'].max()
                    fig_bar.add_annotation(
                        x=d,
                        y=high_price,
                        text="🚀",
                        showarrow=False,
                        yshift=15,
                        font=dict(size=18),
                        row=4, col=1
                    )
    
    # 5. 차트 영점 조절
    fig_bar.update_layout(
        template='plotly_dark',
        plot_bgcolor='#11111b', paper_bgcolor='#11111b',
        barmode='group', # 다시 group으로 복구 (각 row가 독립적인 막대 너비를 가짐)
        bargap=0.2,
        hovermode='x unified', # 🎯 4개 차트를 관통하는 수직 호버 가이드라인 & 통합 박스!
        legend=dict(title="", orientation="h", yanchor="bottom", y=1.05, xanchor="left", x=0.0),
        height=850, margin=dict(l=20, r=20, t=60, b=40),
        xaxis_rangeslider_visible=False,
        xaxis2_rangeslider_visible=False,
        xaxis3_rangeslider_visible=False,
        xaxis4_rangeslider_visible=False
    )
    
    # 🚨 [날짜 경계 구분선 튜닝]: 격자선을 막대 중앙이 아닌 '날짜와 날짜 사이(경계선)'로 이동 (tickson='boundaries')
    grid_style = dict(
        showgrid=True, 
        gridcolor='rgba(255, 255, 255, 0.20)', # 눈에 편안한 은은한 구분선
        griddash='dot',                        # 점선 (Dot) 스타일
        gridwidth=1,
        tickson='boundaries',                  # 🎯 막대 중앙 관통 방지! '날짜 간 경계선' 위치로 세로선 이동
        showspikes=True,
        spikemode='across',
        spikesnap='cursor',
        spikecolor='#ff4b4b',
        spikethickness=1.5
    )
    
    # 축 설정
    fig_bar.update_xaxes(title_text="날짜", type='category', categoryorder='category descending', tickangle=45, rangeslider=dict(visible=False), row=4, col=1, **grid_style)
    fig_bar.update_xaxes(type='category', categoryorder='category descending', showticklabels=False, row=1, col=1, **grid_style)
    fig_bar.update_xaxes(type='category', categoryorder='category descending', showticklabels=False, row=2, col=1, **grid_style)
    fig_bar.update_xaxes(type='category', categoryorder='category descending', showticklabels=False, row=3, col=1, **grid_style)
    
    # 🔧 [수정 2026-07-30] 호버(마우스오버) 툴팁 숫자도 1000단위 콤마가 보이도록 hoverformat 명시 추가
    fig_bar.update_yaxes(title_text="고래 수급 (억원)", gridcolor='rgba(255, 255, 255, 0.12)', tickformat=",.0f", hoverformat=",.0f", row=1, col=1)
    fig_bar.update_yaxes(title_text="전체 대금 (억원)", gridcolor='rgba(255, 255, 255, 0.12)', tickformat=",.0f", hoverformat=",.0f", row=2, col=1)
    fig_bar.update_yaxes(title_text="외인/기관 (억원)", gridcolor='rgba(255, 255, 255, 0.12)', tickformat=",.0f", hoverformat=",.0f", row=3, col=1)
    fig_bar.update_yaxes(title_text="주가 (원)", gridcolor='rgba(255, 255, 255, 0.12)', tickformat=",.0f", hoverformat=",.0f", row=4, col=1)
    
    # 🔍 줌(확대) 기능 추가
    zoom_key = f'zoom_{target_code}'
    if zoom_key not in st.session_state:
        st.session_state[zoom_key] = 0
        
    col_btn, col_chart = st.columns([0.06, 0.94])
    
    with col_btn:
        st.write("")
        st.write("")
        st.write("")
        st.write("")
        st.write("")
        zoom_step = st.session_state[zoom_key]
        btn_label = f"🔍 x{2**zoom_step}" if zoom_step > 0 else "🔍"
        if st.button(btn_label, key=f"btn_zoom_{target_code}", help="고래 수급 차트 Y축 확대 (아웃라이어 제외용)"):
            st.session_state[zoom_key] = (st.session_state[zoom_key] + 1) % 5
            st.rerun()

        # 🌟 [신규 2026-07-30] 돋보기(줌) 버튼 바로 아래에 관심종목 등록 버튼 추가
        # 🔧 [수정 2026-07-30] 위 돋보기 버튼과 크기가 달라 보인다는 피드백 → 크기는 그대로 두고 색만 입히는 -icon 클래스로 교체
        st.markdown('<div class="btn-style-green-icon"></div>', unsafe_allow_html=True)
        if st.button("⭐", key=f"btn_watch_add_chart_{target_code}", help="관심종목 등록"):
            if not st.session_state.get('authenticated', False):
                st.warning("🚫 정회원만 이용할 수 있습니다.")
            else:
                try:
                    supabase.table("user_watchlist").upsert({
                        "username": st.session_state.get('username', ''),
                        "stock_code": str(target_code).strip().zfill(6),
                        "stock_name": target_name,
                    }, on_conflict="username,stock_code").execute()
                    st.toast(f"⭐ '{target_name}' 관심종목에 추가되었습니다.")
                except Exception as e:
                    st.error(f"추가 실패: {e}")

    with col_chart:
        max_val = merged_df['amount_krw_100m'].max() if not merged_df.empty else 0
        if zoom_step > 0 and max_val > 0:
            adjusted_max = max_val / (2 ** zoom_step)
            # 10% 여백 추가
            fig_bar.update_yaxes(range=[0, adjusted_max * 1.1], row=1, col=1)
            
        st.plotly_chart(fig_bar, use_container_width=True)

    # 📊 [과거의 증명] 백테스트 리포트 UI 렌더링 (막대그래프 하단)
    backtest_results = calculate_backtest_yield(chart_df)
    if backtest_results:
        st.markdown("#### 📊 [놀빅 자체 검증] 과거 매수 폭주 시 주가 변화 (수일 내)")
        b_cols = st.columns(len(backtest_results))
        for idx, b_res in enumerate(backtest_results):
            with b_cols[idx]:
                y_pct = b_res['yield_pct']
                color = "#ff4b4b" if y_pct > 0 else "#4b8bff" if y_pct < 0 else "#a0a0a0"
                bg_color = "rgba(255, 75, 75, 0.1)" if y_pct > 0 else "rgba(75, 139, 255, 0.1)" if y_pct < 0 else "rgba(160, 160, 160, 0.1)"
                icon = "🚀" if y_pct > 0 else "❄️" if y_pct < 0 else "➖"
                sign = "+" if y_pct > 0 else ""
                
                st.markdown(f"""
                <div style="background: {bg_color}; border: 1px solid {color}; border-radius: 8px; padding: 15px; text-align: center; margin-bottom: 20px;">
                    <div style="font-size: 14px; color: #e0e0e0; margin-bottom: 5px;">🔥 <b>{b_res['t_date']}</b> (순매수: {int(b_res['net_buy']//100000000):,}억)</div>
                    <div style="font-size: 24px; font-weight: bold; color: {color}; margin: 10px 0;">{icon} {sign}{y_pct:.2f}%</div>
                    <div style="font-size: 12px; color: #a0a0a0;">
                        {b_res['t_date']} 종가: {int(b_res['t_price']):,}원<br>
                        ➔ {b_res['t3_date']} 종가: {int(b_res['t3_price']):,}원
                    </div>
                </div>
                """, unsafe_allow_html=True)



# ------------------------------------------------------------------
# 🎛️ 로그인 상태 제어반 (Session State 인터럽트 플래그)
# ------------------------------------------------------------------
if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False
if 'guest_id' not in st.session_state:
    import uuid
    st.session_state['guest_id'] = f"guest_{uuid.uuid4().hex[:8]}"

menu = ["🏠 홈화면"]
if st.session_state['authenticated']:
    menu.append("📝 내 정보 수정")
    if st.session_state.get('is_admin', False):
        menu.append("🛠️ 사용자 관리 사령탑")
    greeting = f"👑 {st.session_state['current_user']}님 환영합니다"
else:
    menu.append("🔐 로그인/가입")
    greeting = "👤 게스트님 환영합니다"

with st.sidebar:
    if 'force_menu_change' in st.session_state:
        st.session_state['control_center_menu'] = st.session_state.pop('force_menu_change')
    choice = st.radio(greeting, menu, key="control_center_menu")

if choice == "🔐 로그인/가입":
    # 🚧 게이트웨이 화면 렌더링
    
    # 대시보드를 통째로 가리고 무게감 있는 검은색 대문 페이지 구성
    st.subheader("🐳 진격의 놀빅 관리 센터")
    st.write("---")
    
    # 로그인 / 신규 신청 탭 분할 선택기
    mode = st.radio("[ "+"&nbsp;" * 0 + "사용 모드 선택 ]", ["🔐 기존 사용자 로그인", "📝 신규 가입 신청"])
    
    if mode == "🔐 기존 사용자 로그인":
        st.markdown("🔑 LOG IN")
        
        # 🎯 [크롬 연동용 폼 버퍼 개통] form 내부로 입력 소자들을 묶어줍니다.
        with st.form("login_form", clear_on_submit=False):
            login_id = st.text_input("아이디 (ID)", placeholder="아이디를 입력하세요.")
            login_pw = st.text_input("보안 패스워드", type="password", placeholder="비밀번호를 입력하세요.")
            
            # 🎯 일반 button 대신 반드시 form_submit_button을 써야 크롬이 팝업을 끕니다!
            submit_login = st.form_submit_button("로그인", use_container_width=True)
        
        if submit_login:
            if login_id and login_pw:
                res = supabase.table("users").select("*").eq("username", login_id).execute()
                if res.data:
                    user_info = res.data[0]
                    if user_info['password_hash'] == encrypt_password(login_pw):
                        if user_info['is_allowed']:
                            st.session_state['authenticated'] = True
                            st.session_state['current_user'] = user_info['name']
                            st.session_state['username'] = user_info['username']
                            st.session_state['auto_refresh_enabled'] = user_info.get('auto_refresh_enabled', True)
                            #st.success("🎯 보안 게이트 개방! 시스템을 동기화합니다.")
                            st.session_state['is_admin'] = user_info.get('is_admin', False) # 👈 관리자 핀 저장
                            st.rerun()
                        else:
                            st.error("🛑 [승인 대기] 계정은 등록되었으나, 최고 관리자의 승인이 대기 중입니다.")
                    else:
                        st.error("❌ 비밀번호가 일치하지 않습니다.")
                else:
                    st.error("❌ 등록되지 않은 아이디 (ID)입니다.")
            else:
                st.warning("⚠️ ID와 비밀번호를 모두 입력해 주십시오.")

    elif mode == "📝 신규 가입 신청":
        st.markdown("🛰️ 신규 가입 신청서 작성")
        
        # 🎯 회원가입 구역도 크롬이 감지할 수 있게 form으로 묶어줍니다.
        with st.form("register_form"):
            # 💡 크롬 자동완성 방지용 미끼(Dummy) 필드 (display:none은 크롬이 무시하므로 화면 밖으로 숨김)
            st.html('<div style="position: absolute; opacity: 0; top: -9999px; left: -9999px;"><input type="text" autocomplete="username" tabindex="-1"><input type="password" autocomplete="current-password" tabindex="-1"></div>')
            
            new_name = st.text_input("닉네임", autocomplete="off")
            new_id = st.text_input("아이디 (ID)", autocomplete="off")
            new_phone = st.text_input("비상 연락처 (전화번호)", placeholder="010-XXXX-XXXX", autocomplete="off")
            new_pw = st.text_input("비밀번호 설정", help="간편하게 5자 이상 문자, 숫자, [!, #, &]를 사용해 입력하세요!", autocomplete="off")
            
            submit_register = st.form_submit_button("권한 신청서 제출", use_container_width=True)
        
        if submit_register:
            if new_name and new_id and new_phone and new_pw:
                # 🛑 [규칙 단순화] 복잡한 정규식 다 떼어버리고 오직 '5글자 제한' 센서만 남깁니다!
                if len(new_pw) < 5:
                    st.error("❌ 패스워드는 최소 5자 이상으로 설계하십시오.")
                else:
                    hashed_pw = encrypt_password(new_pw)
                    encoded_phone = encode_phone(new_phone)
                    
                    # 닉네임 중복 체크
                    name_check = supabase.table("users").select("id").eq("name", new_name).execute()
                    if name_check.data:
                        st.error(f"❌ '{new_name}' 닉네임(호출명)은 이미 사용 중입니다. 다른 이름을 입력해 주십시오.")
                    else:
                        try:
                            supabase.table("users").insert({
                                "username": new_id,
                                "name": new_name,
                                "password_hash": hashed_pw,
                                "phone_encoded": encoded_phone,
                                "is_allowed": False
                            }).execute()
                            
                            st.success(f"🎉 신청 완료! 최고 관리자에게 '{new_id}' 승인을 요청하십시오.")
                        except Exception as e:
                            # 🎯 [디버깅 프로브 인가] 검은색 파이썬 터미널 창에 날것의 에러를 출력합니다!
                            print(f"\n🚨 [보안 게이트 에러 계측]: {e}\n")
                            # 웹 화면 경고창에도 진짜 에러 내용을 띄워버립니다.
                            st.error(f"❌ 등록 실패 (실제 에러 사유): {e}")

            else:
                st.warning("⚠️ 모든 서류 항목을 공백 없이 작성해 주십시오.")

    # 로그인 중일 때는 하부 대시보드 코드로 전류가 흐르지 않게 바리케이드를 칩니다.
    st.stop()

# ------------------------------------------------------------------
# 3. ⚡ 멀티플렉서(화면 스위칭) 회로 가동

if choice == "🏠 홈화면":

    # ------------------------------------------------------------------
    # 🌊 [여기서부터 기존 진짜 대시보드 코드 가동] 
    # ------------------------------------------------------------------

    # 디지털 시계 및 대시보드 본체 시작.
    
    # 전역 화면 스타일 설정 (모든 하위 화면에서 메인 컨테이너 상단 여백 제거)
    st.html("<style>.block-container { padding-top: 1rem !important; max-width: 95% !important; }</style>")

    # ⏱️ 60초(60000ms)마다 화면 전체를 자동으로 새로고침 (초지능형 조건식 가동)
    scrn_select = st.session_state.get('scrn_select_radio', '체결 로그')
    search_kw = st.session_state.get('search_input_val', '')
    user_refresh_opt = st.session_state.get('auto_refresh_enabled', True)
    
    # 1) 정규장 시간 2) 사용자 옵션 켜짐 3) 체결 로그(목록/상한가) 탭 4) 검색어 없음(막대그래프 상태 아님)
    if is_market_open_now() and user_refresh_opt and scrn_select == "체결 로그" and not search_kw.strip():
        st_autorefresh(interval=60000, key="whale_refresh")

    with st.sidebar:
        
        # 🎯 [신규 배선] Supabase 휴장일 테이블에서 명단 로드
        holidays_list = get_market_holidays()
        holidays_js_array = str(holidays_list) # 파이썬 리스트 형태를 그대로 문자열로 치환하면 JS 배열 형태가 됨

        components.html(
            f"""
            <div style="
                background: linear-gradient(135deg, #1e1e2e 0%, #11111b 100%);
                border: 1px solid #313244;
                border-radius: 10px;
                padding: 10px;
                text-align: center;
                box-shadow: inset 0 0 10px rgba(0,0,0,0.5);
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            ">
                <div style="color: #7f849c; font-size: 11px; font-weight: bold; letter-spacing: 2px; margin-bottom: 5px;">
                    SYSTEM TIME
                </div>
                <div id="live-digital-clock" style="
                    color: #ff4b4b; 
                    font-size: 28px; 
                    font-family: 'Courier New', Courier, monospace; 
                    font-weight: bold;
                    letter-spacing: 1px;
                    text-shadow: 0 0 12px rgba(255, 75, 75, 0.4);
                ">
                    00:00:00
                </div>
            </div>

            <script>
                const holidaysList = {holidays_js_array};
                
                function updateDashboardClock() {{
                    const now = new Date();
                    const year = now.getFullYear();
                    const month = String(now.getMonth() + 1).padStart(2, '0');
                    const date = String(now.getDate()).padStart(2, '0');
                    const todayStr = year + '-' + month + '-' + date;
                    const dayOfWeek = now.getDay(); // 0(일) ~ 6(토)
                    
                    const hours = now.getHours();
                    const minutes = now.getMinutes();
                    const seconds = now.getSeconds();
                    
                    const strHours = String(hours).padStart(2, '0');
                    const strMinutes = String(minutes).padStart(2, '0');
                    const strSeconds = String(seconds).padStart(2, '0');
                    
                    const clockTarget = document.getElementById('live-digital-clock');
                    if (clockTarget) {{
                        clockTarget.textContent = strHours + ':' + strMinutes + ':' + strSeconds;
                        
                        // 정규 시간 (08:30 ~ 15:30) 체크
                        const timeValue = hours * 60 + minutes;
                        const marketStart = 8 * 60 + 30; // 08:30
                        const marketEnd = 15 * 60 + 30;  // 15:30
                        
                        const isWeekend = (dayOfWeek === 0 || dayOfWeek === 6);
                        const isHoliday = holidaysList.includes(todayStr);
                        
                        if (!isWeekend && !isHoliday && timeValue >= marketStart && timeValue < marketEnd) {{
                            // 정규장 시간이고 휴일이 아님: 녹색(Green)
                            clockTarget.style.color = '#00E676';
                            clockTarget.style.textShadow = '0 0 12px rgba(0, 230, 118, 0.4)';
                        }} else {{
                            // 장 마감/시작 전 또는 휴일/주말: 기존 빨간색(Red)
                            clockTarget.style.color = '#ff4b4b';
                            clockTarget.style.textShadow = '0 0 12px rgba(255, 75, 75, 0.4)';
                        }}
                    }}
                }}
                // 1초(1000ms)마다 인터럽트를 걸어 시계를 동기화합니다.
                setInterval(updateDashboardClock, 1000);
                updateDashboardClock(); // 최초 기동 시 즉시 표기
            </script>
            """,
            height=90  # 사이드바 공간을 가치 있게 쓰기 위한 정밀 높이 세팅
        )

    # Streamlit Secrets를 통해 안전하게 키를 불러옵니다.
    # (상단에서 이미 init_supabase_client()로 캐싱 처리됨)
    # supabase = init_supabase_client()

    # ==========================================
    # 🚨 혁신적인 Two-Track 데이터 로딩 엔진 (캐시 분리)
    # ==========================================

    def _fetch_from_supabase(query, max_rows):
        all_data = []
        page_size = 1000
        start = 0
        while start < max_rows:
            res = query.order("date", desc=True).order("time", desc=True).range(start, start + page_size - 1).execute()
            data = res.data
            all_data.extend(data)
            if len(data) < page_size:
                break
            start += page_size
        
        df = pd.DataFrame(all_data)
        if not df.empty:
            df['datetime'] = pd.to_datetime(df['date'] + ' ' + df['time'], format='mixed')
            
            # 🔥 PyArrow 충돌(Oh no) 방지용 엄격한 타입 캐스팅 🔥
            for col in ['id', 'price', 'volume', 'amount_krw']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            for col in ['code', 'name', 'side', 'asset_type', 'market_type']:
                if col in df.columns:
                    df[col] = df[col].astype(str)
        else:
            df = pd.DataFrame(columns=['id', 'date', 'time', 'code', 'name', 'side', 'amount_krw', 'price', 'volume', 'asset_type', 'market_type', 'datetime'])
        return df

    def _apply_common_filters(query, asset_type, market_type, show_closing_auction):
        if asset_type == "개별 주식만 보기 🏢":
            query = query.eq('asset_type', '개별주식')
        elif asset_type == "ETF만 보기 🌐":
            query = query.eq('asset_type', 'ETF')
            
        if market_type == "KOSPI 🏢":
            query = query.eq('market_type', 'KOSPI')
        elif market_type == "KOSDAQ 🚀":
            query = query.eq('market_type', 'KOSDAQ')
            
        if not show_closing_auction:
            query = query.lt('time', '15:20:00')
        return query

    # 1. 과거 데이터 엔진 (35일 전 ~ 어제) -> 캐시 24시간 (자정 지나면 cache_date 변경으로 자동 갱신)
    @st.cache_data(ttl=86400, max_entries=1, show_spinner="⏳ 클라우드에서 대규모 과거 데이터를 불러오는 중입니다...")
    def load_historical_data(asset_type="전체 다 보기 📊", market_type="전체 시장 🌍", show_closing_auction=True, cache_date=""):
        latest_date = get_latest_market_open_date()
        target_start = latest_date - timedelta(days=35)
        yesterday = latest_date - timedelta(days=1)
        
        # OOM(Out of Memory) 방지를 위해 꼭 필요한 컬럼만 명시적으로 가져옵니다! (단, 스키마 일치를 위해 id 포함)
        query = supabase.table("whale_log").select("id, date, time, code, name, side, amount_krw, price, volume, asset_type, market_type")
        query = _apply_common_filters(query, asset_type, market_type, show_closing_auction)
        
        query = query.gte("date", target_start.strftime('%Y-%m-%d')).lte("date", yesterday.strftime('%Y-%m-%d'))
        
        # 최대 15만 건으로 제한하여 Streamlit Cloud 서버가 뻗지 않도록 방어합니다. (기존 50만 건은 1GB RAM 초과 위험)
        return _fetch_from_supabase(query, 150000)

    # 2. 당일 데이터 엔진 (오늘만) -> 1분 캐시 적용하여 전체 데이터(최대 15만건) 로드
    @st.cache_data(ttl=60, max_entries=1, show_spinner=False)
    def load_today_data(asset_type="전체 다 보기 📊", market_type="전체 시장 🌍", show_closing_auction=True):
        # 🇰🇷 한국 시간(KST) 기준으로 강제 설정 후 가장 최근 영업일로 매핑 (함수 내부에 구현됨)
        today_str = get_latest_market_open_date().strftime('%Y-%m-%d')
        
        # 중복 제거를 위해 id 컬럼 추가
        query = supabase.table("whale_log").select("id, date, time, code, name, side, amount_krw, price, volume, asset_type, market_type")
        query = _apply_common_filters(query, asset_type, market_type, show_closing_auction)
        query = query.eq("date", today_str)
            
        # 🚀 [서버 뻗음 방지 해결] 1분 단위 캐시를 적용하여 오늘 하루치 전체 데이터를 가볍게 가져옵니다.
        df = _fetch_from_supabase(query, 150000)
        
        # 💡 만약 오늘(KST 기준) 데이터가 아직 한 건도 없다면 (새벽 시간이거나 주말/휴일인 경우)
        if df.empty:
            # 가장 최근 7일 중 데이터가 존재하는 '마지막 날짜'를 찾아서 대체 로드!
            # (클라우드는 UTC라 우연히 어제 날짜로 작동했지만, 로컬 PC는 KST라 비어있었던 것)
            fallback_query = supabase.table("whale_log").select("date").order("date", desc=True).limit(1)
            fallback_res = fallback_query.execute()
            if fallback_res.data and len(fallback_res.data) > 0:
                latest_date_str = fallback_res.data[0]['date']
                query_fallback = supabase.table("whale_log").select("id, date, time, code, name, side, amount_krw, price, volume, asset_type, market_type")
                query_fallback = _apply_common_filters(query_fallback, asset_type, market_type, show_closing_auction)
                query_fallback = query_fallback.eq("date", latest_date_str)
                df = _fetch_from_supabase(query_fallback, 5000)

        st.session_state['today_df'] = df
        return df

    # 3. 검색 엔진 (검색어 전용) -> 캐시 1분
    @st.cache_data(ttl=60, max_entries=1, show_spinner="대규모 체결 데이터를 분석하고 있습니다...")
    def load_search_data(search_kw, exact=False, start_date=None, limit=None, asset_type="전체 다 보기 📊", market_type="전체 시장 🌍", show_closing_auction=True):
        # OOM 방지를 위해 필요한 컬럼만 추출 (단, 스키마 일치를 위해 id 포함)
        query = supabase.table("whale_log").select("id, date, time, code, name, side, amount_krw, price, volume, asset_type, market_type")
        query = _apply_common_filters(query, asset_type, market_type, show_closing_auction)
        
        if exact:
            query = query.or_(f"name.eq.{search_kw},code.eq.{search_kw}")
        else:
            query = query.or_(f"name.ilike.%{search_kw}%,code.ilike.%{search_kw}%")
            
        if start_date:
            query = query.gte("date", start_date.strftime('%Y-%m-%d'))
            
        max_rows = limit if limit else 50000
        return _fetch_from_supabase(query, max_rows)

    # 4. 상한가 전용 엔진 (DB 측에서 종목 필터링) -> 캐시 1분
    @st.cache_data(ttl=60, max_entries=1, show_spinner="상한가 종목의 체결 데이터를 불러오고 있습니다...")
    def load_upper_limit_logs(upper_stock_names_tuple, start_date_str, asset_type="전체 다 보기 📊", market_type="전체 시장 🌍", show_closing_auction=True):
        if not upper_stock_names_tuple:
            return pd.DataFrame()
            
        query = supabase.table("whale_log").select("id, date, time, code, name, side, amount_krw, price, volume, asset_type, market_type")
        query = _apply_common_filters(query, asset_type, market_type, show_closing_auction)
        query = query.gte("date", start_date_str)
        query = query.in_("name", upper_stock_names_tuple)
        
        return _fetch_from_supabase(query, 50000)

    # -------------------------------------------------------------
    # 메인 로직 시작
    # -------------------------------------------------------------
    
    # 🔍 종목 검색창을 데이터 로딩 '위쪽'으로 끌어올립니다. (검색어를 먼저 알아야 DB에서 낚아채니까요!)
    if 'pending_search' in st.session_state:
        st.session_state['search_input_val'] = st.session_state.pop('pending_search')
    # 🌟 [ 사이드바 검색 입력 및 더보기 상태 관리 ]
    if 'search_input_val' not in st.session_state:
        st.session_state['search_input_val'] = ""
    if 'log_fetch_limit' not in st.session_state:
        st.session_state['log_fetch_limit'] = 500

    search_hdr_col, clear_btn_col = st.sidebar.columns([2, 1])
    with search_hdr_col:
        st.markdown("<div style='margin-top: 7px;'><b>🔍 종목명 검색</b></div>", unsafe_allow_html=True)
    with clear_btn_col:
        st.markdown('<div class="btn-style-clear"></div>', unsafe_allow_html=True)
        # 검색어 비우기 버튼 (클릭 시 session_state 초기화 후 rerun)
        if st.button("🗑", key="clear_search_btn", help="검색어 비우기", use_container_width=True):
            st.session_state['search_input_val'] = ""
            st.session_state['ignore_next_selection'] = True
            st.rerun()
    
    # CSS 스타일링을 컬럼 외부로 빼서 레이아웃(세로 높이)이 틀어지는 현상을 방지합니다.
    st.markdown("""<style>
        /* 데이터프레임 체크박스 헤더에 '그래프' 글자 오버레이 */
        div[data-testid="stDataFrame"] {
            position: relative;
        }
        div[data-testid="stDataFrame"]::after {
            content: "📊";
            position: absolute;
            top: 9px;
            left: 10px;
            font-size: 16px;
            color: rgba(250, 250, 250, 0.6);
            z-index: 10;
            pointer-events: none;
        }

        /* 차트 점프 버튼 컨테이너 (막대그래프 하단 좌측 정렬용) */
        div.element-container:has(.jump-btn-wrapper) { display: none; }
        div.element-container:has(.jump-btn-wrapper) + div.element-container {
            margin-left: 65px !important; /* Y축 라인에 맞춤 */
            margin-top: -15px !important; /* 그래프 아래 여백 보정 */
            width: fit-content !important;
        }
        div.element-container:has(.jump-btn-wrapper) + div.element-container button {
            background-color: transparent !important;
            border: 1px solid #4B89B5 !important;
            padding: 2px 10px !important;
            min-height: 32px !important;
        }
        div.element-container:has(.jump-btn-wrapper) + div.element-container button p {
            font-size: 13px !important; 
            color: #4B89B5 !important;
            font-weight: bold !important;
        }
        div.element-container:has(.jump-btn-wrapper) + div.element-container button:hover {
            border: 1px solid #ffffff !important;
            background-color: transparent !important;
        }
        div.element-container:has(.jump-btn-wrapper) + div.element-container button:hover p {
            color: #ffffff !important;
        }

        /* 막대그래프 점프 버튼 컨테이너 (차트 화면 상단 좌측 정렬용) */
        div.element-container:has(.jump-btn-wrapper-chart) { display: none; }
        div.element-container:has(.jump-btn-wrapper-chart) + div.element-container {
            margin-top: 26px !important; /* 타임라인 설정과 높이 맞춤 */
            margin-left: 5px !important;
            width: fit-content !important;
        }
        div.element-container:has(.jump-btn-wrapper-chart) + div.element-container button {
            background-color: transparent !important;
            border: 1px solid #ff4b4b !important;
            padding: 2px 10px !important;
            min-height: 32px !important;
        }
        div.element-container:has(.jump-btn-wrapper-chart) + div.element-container button p {
            font-size: 13px !important; 
            color: #ff4b4b !important;
            font-weight: bold !important;
        }
        div.element-container:has(.jump-btn-wrapper-chart) + div.element-container button:hover {
            border: 1px solid #ffffff !important;
            background-color: transparent !important;
        }
        div.element-container:has(.jump-btn-wrapper-chart) + div.element-container button:hover p {
            color: #ffffff !important;
        }

        /* 엔터 버튼 (기존 색상 및 높이 유지) */
        div.element-container:has(.btn-style-darkblue) { display: none; }
        div.element-container:has(.btn-style-darkblue) + div.element-container button { 
            background-color: #2D4B7A !important;
            border: 1px solid #1F3A60 !important;
            padding-left: 4px !important; 
            padding-right: 4px !important; 
        }
        div.element-container:has(.btn-style-darkblue) + div.element-container button p { 
            font-size: 13px !important; 
            color: #FFFFFF !important;
            font-weight: bold !important;
        }
        div.element-container:has(.btn-style-darkblue) + div.element-container button:hover {
            background-color: #1F3A60 !important;
        }
        div.element-container:has(.btn-style-darkblue) + div.element-container button:hover p {
            color: #FFD700 !important;
        }

        /* 3버튼 공통 높이 축소 스타일 (패딩/최소높이 조절) */
        /* 목록보기 버튼 (작은 높이) */
        div.element-container:has(.btn-style-darkblue-sm) { display: none; }
        div.element-container:has(.btn-style-darkblue-sm) + div.element-container button { 
            background-color: #2D4B7A !important;
            border: 1px solid #1F3A60 !important;
            padding-left: 4px !important; 
            padding-right: 4px !important; 
            padding-top: 2px !important;
            padding-bottom: 2px !important;
            min-height: 32px !important;
        }
        div.element-container:has(.btn-style-darkblue-sm) + div.element-container button p { 
            font-size: 13px !important; 
            color: #FFFFFF !important;
            font-weight: bold !important;
            line-height: 1 !important;
        }
        div.element-container:has(.btn-style-darkblue-sm) + div.element-container button:hover {
            background-color: #1F3A60 !important;
        }
        div.element-container:has(.btn-style-darkblue-sm) + div.element-container button:hover p {
            color: #FFD700 !important; 
        }

        /* 빨간색 TOP10 버튼 스타일 */
        div.element-container:has(.btn-style-red) { display: none; }
        div.element-container:has(.btn-style-red) + div.element-container button { 
            background-color: #E24C4C !important;
            border: 1px solid #CC3333 !important;
            padding-left: 4px !important; 
            padding-right: 4px !important; 
            padding-top: 2px !important;
            padding-bottom: 2px !important;
            min-height: 32px !important;
        }
        div.element-container:has(.btn-style-red) + div.element-container button p { 
            font-size: 13px !important; 
            color: #FFFFFF !important;
            font-weight: bold !important;
            line-height: 1 !important;
        }
        div.element-container:has(.btn-style-red) + div.element-container button:hover {
            background-color: #CC3333 !important;
        }

        /* 파란색 TOP10 버튼 스타일 */
        div.element-container:has(.btn-style-blue) { display: none; }
        div.element-container:has(.btn-style-blue) + div.element-container button { 
            background-color: #4A86B7 !important;
            border: 1px solid #3873A3 !important;
            padding-left: 4px !important; 
            padding-right: 4px !important; 
            padding-top: 2px !important;
            padding-bottom: 2px !important;
            min-height: 32px !important;
        }
        div.element-container:has(.btn-style-blue) + div.element-container button p { 
            font-size: 13px !important; 
            color: #FFFFFF !important;
            font-weight: bold !important;
            line-height: 1 !important;
        }
        div.element-container:has(.btn-style-blue) + div.element-container button:hover {
            background-color: #3873A3 !important;
        }

        /* ------------------------------------------ */
        /* 활성화된 버튼 스타일 (테두리 + 진오렌지색 글자) */
        /* ------------------------------------------ */
        div.element-container:has(.btn-style-darkblue-sm-active) { display: none; }
        div.element-container:has(.btn-style-darkblue-sm-active) + div.element-container button { 
            background-color: transparent !important;
            border: 2px solid #FF8C00 !important;
            padding-left: 4px !important; 
            padding-right: 4px !important; 
            padding-top: 2px !important;
            padding-bottom: 2px !important;
            min-height: 32px !important;
        }
        div.element-container:has(.btn-style-darkblue-sm-active) + div.element-container button p { 
            font-size: 13px !important; 
            color: #FF8C00 !important;
            font-weight: bold !important;
            line-height: 1 !important;
        }

        div.element-container:has(.btn-style-red-active) { display: none; }
        div.element-container:has(.btn-style-red-active) + div.element-container button { 
            background-color: transparent !important;
            border: 2px solid #FF8C00 !important;
            padding-left: 4px !important; 
            padding-right: 4px !important; 
            padding-top: 2px !important;
            padding-bottom: 2px !important;
            min-height: 32px !important;
        }
        div.element-container:has(.btn-style-red-active) + div.element-container button p { 
            font-size: 13px !important; 
            color: #FF8C00 !important;
            font-weight: bold !important;
            line-height: 1 !important;
        }

        div.element-container:has(.btn-style-blue-active) { display: none; }
        div.element-container:has(.btn-style-blue-active) + div.element-container button { 
            background-color: transparent !important;
            border: 2px solid #FF8C00 !important;
            padding-left: 4px !important; 
            padding-right: 4px !important; 
            padding-top: 2px !important;
            padding-bottom: 2px !important;
            min-height: 32px !important;
        }
        div.element-container:has(.btn-style-blue-active) + div.element-container button p { 
            font-size: 13px !important; 
            color: #FF8C00 !important;
            font-weight: bold !important;
            line-height: 1 !important;
        }

        /* 보라색 수익율 버튼 스타일 */
        div.element-container:has(.btn-style-purple) { display: none; }
        div.element-container:has(.btn-style-purple) + div.element-container button { 
            background-color: #8A2BE2 !important; /* BlueViolet */
            border: 1px solid #7B68EE !important;
            padding-left: 4px !important; 
            padding-right: 4px !important; 
            padding-top: 2px !important;
            padding-bottom: 2px !important;
            min-height: 32px !important;
        }
        div.element-container:has(.btn-style-purple) + div.element-container button p { 
            font-size: 13px !important; 
            color: #FFFFFF !important;
            font-weight: bold !important;
            line-height: 1 !important;
        }
        div.element-container:has(.btn-style-purple) + div.element-container button:hover {
            background-color: #7B68EE !important;
        }

        div.element-container:has(.btn-style-purple-active) { display: none; }
        div.element-container:has(.btn-style-purple-active) + div.element-container button { 
            background-color: transparent !important;
            border: 2px solid #FF8C00 !important;
            padding-left: 4px !important; 
            padding-right: 4px !important; 
            padding-top: 2px !important;
            padding-bottom: 2px !important;
            min-height: 32px !important;
        }
        div.element-container:has(.btn-style-purple-active) + div.element-container button p { 
            font-size: 13px !important; 
            color: #FF8C00 !important;
            font-weight: bold !important;
            line-height: 1 !important;
        }

        /* 오렌지색 상선고 버튼 스타일 */
        div.element-container:has(.btn-style-orange) { display: none; }
        div.element-container:has(.btn-style-orange) + div.element-container button { 
            background-color: #FF8C00 !important; 
            border: 1px solid #E67E22 !important;
            padding-left: 4px !important; 
            padding-right: 4px !important; 
            padding-top: 2px !important;
            padding-bottom: 2px !important;
            min-height: 32px !important;
        }
        div.element-container:has(.btn-style-orange) + div.element-container button p { 
            font-size: 13px !important; 
            color: #FFFFFF !important;
            font-weight: bold !important;
            line-height: 1 !important;
        }
        div.element-container:has(.btn-style-orange) + div.element-container button:hover {
            background-color: #E67E22 !important;
        }

        div.element-container:has(.btn-style-orange-active) { display: none; }
        div.element-container:has(.btn-style-orange-active) + div.element-container button { 
            background-color: transparent !important;
            border: 2px solid #FFD700 !important;
            padding-left: 4px !important; 
            padding-right: 4px !important; 
            padding-top: 2px !important;
            padding-bottom: 2px !important;
            min-height: 32px !important;
        }
        div.element-container:has(.btn-style-orange-active) + div.element-container button p { 
            font-size: 13px !important; 
            color: #FFD700 !important;
            font-weight: bold !important;
            line-height: 1 !important;
        }

        /* 회색 예비 버튼 스타일 */
        div.element-container:has(.btn-style-gray) { display: none; }
        div.element-container:has(.btn-style-gray) + div.element-container button { 
            background-color: #555555 !important; 
            border: 1px solid #444444 !important;
            padding-left: 4px !important; 
            padding-right: 4px !important; 
            padding-top: 2px !important;
            padding-bottom: 2px !important;
            min-height: 32px !important;
        }
        div.element-container:has(.btn-style-gray) + div.element-container button p { 
            font-size: 13px !important; 
            color: #AAAAAA !important;
            font-weight: bold !important;
            line-height: 1 !important;
        }
        
        /* 기폭주 버튼 (붉은색) 스타일 */
        div.element-container:has(.btn-style-red) { display: none; }
        div.element-container:has(.btn-style-red) + div.element-container button { 
            background-color: #ff4b4b !important; 
            border: 1px solid #cc3c3c !important;
            padding-left: 4px !important; 
            padding-right: 4px !important; 
            padding-top: 2px !important;
            padding-bottom: 2px !important;
            min-height: 32px !important;
        }
        div.element-container:has(.btn-style-red) + div.element-container button p { 
            font-size: 13px !important; 
            color: #ffffff !important;
            font-weight: bold !important;
            line-height: 1 !important;
        }
        
        /* 기폭주 버튼 활성화 상태 */
        div.element-container:has(.btn-style-red-active) { display: none; }
        div.element-container:has(.btn-style-red-active) + div.element-container button { 
            background-color: transparent !important;
            border: 2px solid #ff4b4b !important;
            padding-left: 4px !important; 
            padding-right: 4px !important; 
            padding-top: 2px !important;
            padding-bottom: 2px !important;
            min-height: 32px !important;
        }
        div.element-container:has(.btn-style-red-active) + div.element-container button p {
            font-size: 13px !important;
            color: #ff4b4b !important;
            font-weight: bold !important;
            line-height: 1 !important;
        }

        /* 🔧 [수정 2026-07-30] "외/기" 버튼 전용 진한 빨간색 (TOP10/기폭주의 #ff4b4b와 구분되는 톤) */
        div.element-container:has(.btn-style-darkred) { display: none; }
        div.element-container:has(.btn-style-darkred) + div.element-container button {
            background-color: #B22222 !important;
            border: 1px solid #8B0000 !important;
            padding-left: 4px !important;
            padding-right: 4px !important;
            padding-top: 2px !important;
            padding-bottom: 2px !important;
            min-height: 32px !important;
        }
        div.element-container:has(.btn-style-darkred) + div.element-container button p {
            font-size: 13px !important;
            color: #ffffff !important;
            font-weight: bold !important;
            line-height: 1 !important;
        }
        div.element-container:has(.btn-style-darkred) + div.element-container button:hover {
            background-color: #8B0000 !important;
        }

        div.element-container:has(.btn-style-darkred-active) { display: none; }
        div.element-container:has(.btn-style-darkred-active) + div.element-container button {
            background-color: transparent !important;
            border: 2px solid #B22222 !important;
            padding-left: 4px !important;
            padding-right: 4px !important;
            padding-top: 2px !important;
            padding-bottom: 2px !important;
            min-height: 32px !important;
        }
        div.element-container:has(.btn-style-darkred-active) + div.element-container button p {
            font-size: 13px !important;
            color: #B22222 !important;
            font-weight: bold !important;
            line-height: 1 !important;
        }

        /* 🌟 [신규 2026-07-30] "내관심" 버튼 전용 녹색 */
        div.element-container:has(.btn-style-green) { display: none; }
        div.element-container:has(.btn-style-green) + div.element-container button {
            background-color: #2E8B57 !important;
            border: 1px solid #1F5C3D !important;
            padding-left: 4px !important;
            padding-right: 4px !important;
            padding-top: 2px !important;
            padding-bottom: 2px !important;
            min-height: 32px !important;
        }
        div.element-container:has(.btn-style-green) + div.element-container button p {
            font-size: 13px !important;
            color: #ffffff !important;
            font-weight: bold !important;
            line-height: 1 !important;
        }
        div.element-container:has(.btn-style-green) + div.element-container button:hover {
            background-color: #1F5C3D !important;
        }

        div.element-container:has(.btn-style-green-active) { display: none; }
        div.element-container:has(.btn-style-green-active) + div.element-container button {
            background-color: transparent !important;
            border: 2px solid #2E8B57 !important;
            padding-left: 4px !important;
            padding-right: 4px !important;
            padding-top: 2px !important;
            padding-bottom: 2px !important;
            min-height: 32px !important;
        }
        div.element-container:has(.btn-style-green-active) + div.element-container button p {
            font-size: 13px !important;
            color: #2E8B57 !important;
            font-weight: bold !important;
            line-height: 1 !important;
        }

        /* 🔧 [수정 2026-07-30] 차트 화면의 "⭐ 관심종목 등록" 아이콘 버튼 전용 —
           바로 위 돋보기(줌) 버튼과 크기를 맞추기 위해 padding/min-height는 건드리지 않고 색상만 입힘 */
        div.element-container:has(.btn-style-green-icon) { display: none; }
        div.element-container:has(.btn-style-green-icon) + div.element-container button {
            background-color: #2E8B57 !important;
            border: 1px solid #1F5C3D !important;
        }
        div.element-container:has(.btn-style-green-icon) + div.element-container button p {
            color: #ffffff !important;
            font-weight: bold !important;
        }
        div.element-container:has(.btn-style-green-icon) + div.element-container button:hover {
            background-color: #1F5C3D !important;
        }

        /* 🔧 [수정 2026-07-30] "내 관심종목" 화면의 "+ 추가" 버튼이 옆 입력창보다 2~3px 아래로 처져 보여
           좌측 입력창과 중심을 맞추기 위해 살짝 위로 당김 (색상/크기는 그대로 유지) */
        div.element-container:has(.btn-style-align-up) { display: none; }
        div.element-container:has(.btn-style-align-up) + div.element-container button {
            position: relative !important;
            top: -4px !important;
        }

        /* 🔧 [수정 2026-07-30] 특정 데이터프레임에서 좌상단 "📊" 오버레이 아이콘이 첫 컬럼(예: "종목명")
           헤더 글자를 가리는 문제 → 마커 div 바로 다음 데이터프레임에서만 이 아이콘을 숨김 */
        div.element-container:has(.no-header-icon) { display: none; }
        div.element-container:has(.no-header-icon) + div.element-container div[data-testid="stDataFrame"]::after {
            content: none !important;
        }

        /* 🌟 [신규 2026-07-30] "테마킹" 버튼 전용 찐노랑 (배경이 밝아서 글자는 어둡게) */
        div.element-container:has(.btn-style-yellow) { display: none; }
        div.element-container:has(.btn-style-yellow) + div.element-container button {
            background-color: #FFD400 !important;
            border: 1px solid #C9A600 !important;
            padding-left: 4px !important;
            padding-right: 4px !important;
            padding-top: 2px !important;
            padding-bottom: 2px !important;
            min-height: 32px !important;
        }
        div.element-container:has(.btn-style-yellow) + div.element-container button p {
            font-size: 13px !important;
            color: #1a1a1a !important;
            font-weight: bold !important;
            line-height: 1 !important;
        }
        div.element-container:has(.btn-style-yellow) + div.element-container button:hover {
            background-color: #E6BE00 !important;
        }

        div.element-container:has(.btn-style-yellow-active) { display: none; }
        div.element-container:has(.btn-style-yellow-active) + div.element-container button {
            background-color: transparent !important;
            border: 2px solid #FFD400 !important;
            padding-left: 4px !important;
            padding-right: 4px !important;
            padding-top: 2px !important;
            padding-bottom: 2px !important;
            min-height: 32px !important;
        }
        div.element-container:has(.btn-style-yellow-active) + div.element-container button p {
            font-size: 13px !important;
            color: #FFD400 !important;
            font-weight: bold !important;
            line-height: 1 !important;
        }


        /* 검색 초기화(휴지통) 버튼 스타일 */
        div.element-container:has(.btn-style-clear) { display: none; }
        div.element-container:has(.btn-style-clear) + div.element-container button { 
            background-color: #3B8C56 !important; /* 녹색 채도 낮춘 색 */
            border: 1px solid #29663D !important;
            padding-left: 0px !important; 
            padding-right: 0px !important; 
            padding-top: 2px !important;
            padding-bottom: 2px !important;
            min-height: 32px !important;
        }
        div.element-container:has(.btn-style-clear) + div.element-container button p { 
            font-size: 24px !important; /* 아이콘 50% 확대 */
            color: #FFA500 !important; /* 주황색 */
            font-weight: bold !important;
            line-height: 1 !important;
            display: flex;
            align-items: center;
            justify-content: center;
            margin-bottom: 0px !important;
            padding-bottom: 2px !important;
        }
        div.element-container:has(.btn-style-clear) + div.element-container button:hover {
            background-color: #29663D !important;
        }
        div.element-container:has(.btn-style-clear) + div.element-container button:hover p {
            color: #FF8C00 !important; 
        }

        /* 로그아웃 버튼용 하단 푸셔(Pusher) 및 스타일 */
        div.element-container:has(.spacer-logout) {
            margin-top: auto !important; /* 플렉스 박스에서 하단으로 밀어냄 */
        }
        div.element-container:has(.btn-style-logout) { display: none; }
        div.element-container:has(.btn-style-logout) + div.element-container button { 
            background-color: transparent !important;
            border: 1px solid #4a4a4a !important;
            padding-left: 10px !important; 
            padding-right: 10px !important; 
            padding-top: 2px !important;
            padding-bottom: 2px !important;
            min-height: 32px !important; /* 휴지통과 동일한 높이 */
            margin-bottom: 20px !important; /* 모서리 여백 */
        }
        div.element-container:has(.btn-style-logout) + div.element-container button p { 
            font-size: 13px !important; 
            color: #b0b0b0 !important;
            line-height: 1 !important;
            margin-bottom: 0px !important;
            padding-bottom: 2px !important;
        }
        div.element-container:has(.btn-style-logout) + div.element-container button:hover {
            border-color: #ff4b4b !important;
            background-color: transparent !important;
        }
        div.element-container:has(.btn-style-logout) + div.element-container button:hover p {
            color: #ff4b4b !important;
        }

        /* 자랑 게시판 버튼용 스타일 */
        div.element-container:has(.btn-style-brag) { display: none; }
        div.element-container:has(.btn-style-brag) + div.element-container button { 
            background-color: transparent !important;
            border: 1px solid #FF69B4 !important;
            padding-left: 10px !important; 
            padding-right: 10px !important; 
            padding-top: 2px !important;
            padding-bottom: 2px !important;
            min-height: 32px !important; 
            margin-bottom: 5px !important; 
        }
        div.element-container:has(.btn-style-brag) + div.element-container button p { 
            font-size: 14px !important; 
            color: #FF69B4 !important;
            font-weight: bold !important;
            line-height: 1 !important;
            margin-bottom: 0px !important;
            padding-bottom: 2px !important;
        }
        div.element-container:has(.btn-style-brag) + div.element-container button:hover {
            border-color: #FF1493 !important;
            background-color: rgba(255, 105, 180, 0.1) !important;
        }
        div.element-container:has(.btn-style-brag) + div.element-container button:hover p {
            color: #FF1493 !important;
        }

        /* 외기 탑백 버튼용 스타일 */
        div.element-container:has(.btn-style-top100) { display: none; }
        div.element-container:has(.btn-style-top100) + div.element-container button { 
            background-color: transparent !important;
            border: 1px solid rgba(212, 0, 0, 1) !important;
            padding-left: 10px !important; 
            padding-right: 10px !important;
            padding-top: 2px !important;
            padding-bottom: 2px !important;
            min-height: 32px !important; 
            margin-bottom: 5px !important; 
        }
        div.element-container:has(.btn-style-top100) + div.element-container button p { 
            font-size: 14px !important; 
            color: rgba(212, 0, 0, 1) !important;
            font-weight: bold !important;
            line-height: 1 !important;
            margin-bottom: 0px !important;
            padding-bottom: 2px !important;
        }
        div.element-container:has(.btn-style-top100) + div.element-container button:hover {
            border-color: #FF0000 !important;
            background-color: rgba(212, 0, 0, 0.1) !important;
        }
        div.element-container:has(.btn-style-top100) + div.element-container button:hover p {
            color: #FF0000 !important;
        }
    </style>""", unsafe_allow_html=True)
    
    guest_msg = st.sidebar.empty()

    search_col1, search_col2 = st.sidebar.columns([2, 1])
    with search_col1:
        raw_search_keyword = st.text_input("종목명 검색", label_visibility="collapsed", placeholder="입력 후 엔터", key="search_input_val")
        if raw_search_keyword:
            if not st.session_state.get('authenticated', False):
                guest_msg.error("🚫 정회원만 이용할 수 있습니다.")
                import time
                time.sleep(1.5)
                guest_msg.empty()
                search_keyword = ""
                st.session_state['last_search_keyword'] = ""
            else:
                sk = raw_search_keyword.replace(" 👑", "").replace(" 🔥", "").replace(" 💥", "").replace(" ✨", "").replace(" 🌱", "")
                search_keyword = sk.replace("👑", "").replace("🔥", "").replace("💥", "").replace("✨", "").replace("🌱", "").strip()
                
                # 검색어가 새롭게 입력된 경우 무조건 시계열 화면으로 강제 이동
                if st.session_state.get('last_search_keyword') != search_keyword:
                    st.session_state['last_search_keyword'] = search_keyword
                    st.session_state['scrn_select_radio'] = "체결 로그"
                    st.rerun()
        else:
            search_keyword = ""
            st.session_state['last_search_keyword'] = ""
            
    with search_col2:
        st.markdown('<div class="btn-style-darkblue"></div>', unsafe_allow_html=True)
        if st.button("🔍 엔터", use_container_width=True):
            if not st.session_state.get('authenticated', False):
                guest_msg.error("🚫 정회원만 이용할 수 있습니다.")
                import time
                time.sleep(1.5)
                guest_msg.empty()
            else:
                if search_keyword:
                    st.session_state['scrn_select_radio'] = "체결 로그"
                    st.rerun()
            
    # 현재 어떤 버튼이 활성화되어 있는지 상태 확인
    current_scrn = st.session_state.get('scrn_select_radio', "체결 로그")
    is_list_active = (current_scrn == "체결 로그" and not st.session_state.get('upper_limit_filter', False))
    is_upper_active = (current_scrn == "체결 로그" and st.session_state.get('upper_limit_filter', False))
    is_top10_active = (current_scrn == "TOP 10 화면")
    is_return_active = (current_scrn == "수익율 화면")

    btn_col1, btn_col2, btn_col3, btn_col4 = st.sidebar.columns([1, 1, 1, 1])
    with btn_col1:
        cls_list = "btn-style-darkblue-sm-active" if is_list_active else "btn-style-darkblue-sm"
        st.markdown(f'<div class="{cls_list}"></div>', unsafe_allow_html=True)
        if st.button("실시간", key="btn_list_view", use_container_width=True):
            if st.session_state.get('scrn_select_radio') != "체결 로그" or st.session_state.get('upper_limit_filter', False) != False or st.session_state.get('search_input_val', "") != "":
                st.session_state['last_search_keyword'] = ""
                st.session_state['pending_search'] = ""
                st.session_state['scrn_select_radio'] = "체결 로그"
                st.session_state['log_fetch_limit'] = 500 # 더보기 초기화
                st.session_state['upper_limit_filter'] = False
                st.session_state['ignore_next_selection'] = True
                st.session_state['ignore_next_selection'] = True
                
                # 강제 테이블 선택 초기화 (키 변경 방식)
                st.session_state['df_reset_counter'] = st.session_state.get('df_reset_counter', 0) + 1
                        
                import time
                st.session_state['realtime_mount_id'] = time.time()
                st.rerun()
    with btn_col2:
        cls_upper = "btn-style-blue-active" if is_upper_active else "btn-style-blue"
        st.markdown(f'<div class="{cls_upper}"></div>', unsafe_allow_html=True)
        if st.button("상한가", key="btn_top10_blue", use_container_width=True):
            if not st.session_state.get('authenticated', False):
                guest_msg.error("🚫 정회원만 이용할 수 있습니다.")
                import time
                time.sleep(1.5)
                guest_msg.empty()
            else:
                if st.session_state.get('scrn_select_radio') != "체결 로그" or st.session_state.get('upper_limit_filter', False) != True or st.session_state.get('search_input_val', "") != "":
                    st.session_state['last_search_keyword'] = ""
                    st.session_state['pending_search'] = ""
                    st.session_state['scrn_select_radio'] = "체결 로그"
                    st.session_state['log_fetch_limit'] = 500
                    st.session_state['upper_limit_filter'] = True
                    st.session_state['ignore_next_selection'] = True
                    st.session_state['ignore_next_selection'] = True
                    
                    # 강제 테이블 선택 초기화 (키 변경 방식)
                    st.session_state['df_reset_counter'] = st.session_state.get('df_reset_counter', 0) + 1
                            
                    import time
                    st.session_state['realtime_mount_id'] = time.time()
                    st.rerun()
    with btn_col3:
        cls_return = "btn-style-purple-active" if is_return_active else "btn-style-purple"
        st.markdown(f'<div class="{cls_return}"></div>', unsafe_allow_html=True)
        if st.button("수익율", key="btn_return_purple", use_container_width=True):
            if not st.session_state.get('authenticated', False):
                guest_msg.error("🚫 정회원만 이용할 수 있습니다.")
                import time
                time.sleep(1.5)
                guest_msg.empty()
            else:
                if st.session_state.get('scrn_select_radio') != "수익율 화면":
                    st.session_state['scrn_select_radio'] = "수익율 화면"
                    st.rerun()
    with btn_col4:
        cls_top10 = "btn-style-red-active" if is_top10_active else "btn-style-red"
        st.markdown(f'<div class="{cls_top10}"></div>', unsafe_allow_html=True)
        if st.button("TOP10", key="btn_top10_red", use_container_width=True):
            if not st.session_state.get('authenticated', False):
                guest_msg.error("🚫 정회원만 이용할 수 있습니다.")
                import time
                time.sleep(1.5)
                guest_msg.empty()
            else:
                if st.session_state.get('scrn_select_radio') != "TOP 10 화면":
                    st.session_state['scrn_select_radio'] = "TOP 10 화면"
                    st.rerun()

    is_radar_active = (current_scrn == "상선고 화면")
    is_golden_active = (current_scrn == "고래 골든픽")

    # 🌟 [버튼 재배치 2026-07-30] 2번째 줄 신설 — 1번째 줄과 동일하게 게스트/일반/관리자 모두에게 보이되,
    # 실제 사용은 정회원(authenticated)/관리자만 가능. "골든픽"을 여기로 이전하고, 기존 "외/기 탑100"도 이전(라벨은 "외/기"로 축약).
    btn_col5, btn_col6, btn_col7, btn_col8 = st.sidebar.columns([1, 1, 1, 1])
    with btn_col5:
        cls_golden = "btn-style-purple-active" if is_golden_active else "btn-style-purple"
        st.markdown(f'<div class="{cls_golden}"></div>', unsafe_allow_html=True)
        if st.button("골든픽", key="btn_golden_pick", use_container_width=True):
            if not st.session_state.get('authenticated', False):
                guest_msg.error("🚫 정회원만 이용할 수 있습니다.")
                import time
                time.sleep(1.5)
                guest_msg.empty()
            else:
                if st.session_state.get('scrn_select_radio') != "고래 골든픽":
                    st.session_state['scrn_select_radio'] = "고래 골든픽"
                    st.rerun()
    with btn_col6:
        # 🔧 [수정 2026-07-30] 다른 버튼들과 동일한 동작(평상시 빨간 배경+흰 글씨 / 활성 시 굵은 빨간 테두리+빨간 글씨)로 통일
        is_iogi_active = (current_scrn == "외기 TOP 100 화면")
        cls_iogi = "btn-style-darkred-active" if is_iogi_active else "btn-style-darkred"
        st.markdown(f'<div class="{cls_iogi}"></div>', unsafe_allow_html=True)
        if st.button("외/기", key="btn_iogi", use_container_width=True):
            if not st.session_state.get('authenticated', False):
                guest_msg.error("🚫 정회원만 이용할 수 있습니다.")
                import time
                time.sleep(1.5)
                guest_msg.empty()
            else:
                if st.session_state.get('scrn_select_radio') != "외기 TOP 100 화면":
                    st.session_state['scrn_select_radio'] = "외기 TOP 100 화면"
                    st.rerun()
    with btn_col7:
        # 🌟 [신규 2026-07-30] "내관심" — 관심종목(즐겨찾기) 화면. 골든픽/외기와 동일한 접근 규칙(정회원 이상).
        is_watch_active = (current_scrn == "내 관심종목")
        cls_watch = "btn-style-green-active" if is_watch_active else "btn-style-green"
        st.markdown(f'<div class="{cls_watch}"></div>', unsafe_allow_html=True)
        if st.button("내관심", key="btn_watchlist", use_container_width=True):
            if not st.session_state.get('authenticated', False):
                guest_msg.error("🚫 정회원만 이용할 수 있습니다.")
                import time
                time.sleep(1.5)
                guest_msg.empty()
            else:
                if st.session_state.get('scrn_select_radio') != "내 관심종목":
                    st.session_state['scrn_select_radio'] = "내 관심종목"
                    st.rerun()
    with btn_col8:
        # 🌟 [신규 2026-07-30] "테마킹" — 테마주 랭킹(섹터 모멘텀) 화면. 골든픽/외기와 동일한 접근 규칙(정회원 이상).
        is_themeking_active = (current_scrn == "테마 랭킹")
        cls_themeking = "btn-style-yellow-active" if is_themeking_active else "btn-style-yellow"
        st.markdown(f'<div class="{cls_themeking}"></div>', unsafe_allow_html=True)
        if st.button("테마킹", key="btn_themeking", use_container_width=True):
            if not st.session_state.get('authenticated', False):
                guest_msg.error("🚫 정회원만 이용할 수 있습니다.")
                import time
                time.sleep(1.5)
                guest_msg.empty()
            else:
                if st.session_state.get('scrn_select_radio') != "테마 랭킹":
                    st.session_state['scrn_select_radio'] = "테마 랭킹"
                    st.rerun()

    # 🌟 [버튼 재배치 2026-07-30] 3번째 줄 (구 2번째 줄) — 관리자에게만 보이고 관리자만 사용 가능 (기존 규칙 그대로)
    if st.session_state.get('is_admin', False):
        btn_col9, btn_col10, btn_col11, btn_col12 = st.sidebar.columns([1, 1, 1, 1])
        with btn_col9:
            cls_radar = "btn-style-orange-active" if is_radar_active else "btn-style-orange"
            st.markdown(f'<div class="{cls_radar}"></div>', unsafe_allow_html=True)
            if st.button("상선고", key="btn_radar_orange", use_container_width=True):
                if st.session_state.get('scrn_select_radio') != "상선고 화면":
                    st.session_state['scrn_select_radio'] = "상선고 화면"
                    st.rerun()
        with btn_col10:
            cls_res1 = "btn-style-red-active" if scrn_select == "기간 누적 폭주" else "btn-style-red"
            st.markdown(f'<div class="{cls_res1}"></div>', unsafe_allow_html=True)
            if st.button("기폭주", key="btn_res1", use_container_width=True):
                if st.session_state.get('scrn_select_radio') != "기간 누적 폭주":
                    st.session_state['scrn_select_radio'] = "기간 누적 폭주"
                    st.rerun()
        with btn_col11:
            st.markdown('<div class="btn-style-gray"></div>', unsafe_allow_html=True)
            if st.button("예비3", key="btn_res3", use_container_width=True): pass
        with btn_col12:
            st.markdown('<div class="btn-style-gray"></div>', unsafe_allow_html=True)
            if st.button("예비4", key="btn_reserve_4", use_container_width=True): pass


    exact_match = st.sidebar.toggle("🎯 검색어 완전 일치 (Exact Match)", value=True)
    
    # 🌟 [ 전체 요약 기간 스위치 ]를 데이터 쿼리 이전에 배치하여 DB 검색 범위 최적화!
    global_period = st.sidebar.radio(
        "📊 전체 요약 및 TOP 10 기간 선택",
        ["당일 데이터만", "최근 1주일 누적", "최근 1개월 누적"],
        index=2
    )
    
    # 날짜 연산을 위한 기준점 설정
    today = get_latest_market_open_date()
    if global_period == "당일 데이터만":
        start_date = today
    elif global_period == "최근 1주일 누적":
        start_date = today - timedelta(days=7)
    else:
        start_date = today - timedelta(days=30)
    
    # 🌟 [ 화면 선택 상태 사전 로드 ]
    if 'scrn_select_radio' not in st.session_state:
        st.session_state['scrn_select_radio'] = "체결 로그"
    scrn_select = st.session_state['scrn_select_radio']


    # 🌟 [ 전략적 펌핑 로직 ]
    # 체결 로그(목록보기) 상태이고 검색어가 없을 때는 세션에 저장된 limit 만큼 가져옵니다.
    if scrn_select == "체결 로그" and not search_keyword.strip():
        fetch_limit = st.session_state['log_fetch_limit']
    elif scrn_select in ["TOP 10 화면", "수익율 화면"]:
        fetch_limit = 0 # 개별 화면은 전역 글로벌 데이터가 필요 없음
    else:
        fetch_limit = None

    # 🎛️ 필터 상태 선행 판독 (DB 쿼리에 바로 쏘기 위함)
    show_closing_auction = st.sidebar.toggle("장마감 동시호가/장후 거래 포함", value=True)
    show_only_upper_limit = st.session_state.get('upper_limit_filter', False)

    if 'asset_type_val' not in st.session_state:
        st.session_state['asset_type_val'] = "개별 주식만 보기 🏢"
    if 'market_type_val' not in st.session_state:
        st.session_state['market_type_val'] = "전체 시장 🌍"

    def sync_ts_filters():
        st.session_state['asset_type_val'] = st.session_state['asset_type_ts']
        st.session_state['market_type_val'] = st.session_state['market_type_ts']
        
    def sync_log_filters():
        st.session_state['asset_type_val'] = st.session_state['asset_type_log']
        st.session_state['market_type_val'] = st.session_state['market_type_log']

    asset_type = st.session_state['asset_type_val']
    market_type = st.session_state['market_type_val']

    # 지능형 펌프 가동! (검색어 조건과 선택된 기간에 맞춰서 데이터를 퍼옵니다)
    if fetch_limit == 0 or scrn_select in ["수익율 자랑", "상선고 화면", "고래 골든픽"]:
        df = pd.DataFrame(columns=['id', 'date', 'time', 'code', 'name', 'side', 'amount_krw', 'price', 'volume', 'asset_type', 'market_type', 'datetime', 'date_parsed'])
    else:
        if not search_keyword.strip():
            if show_only_upper_limit:
                # 🚀 [DB 오프로딩 최적화] 상한가 종목을 먼저 찾고, DB에 해당 종목 데이터만 요청합니다!
                sys_set = supabase.table("system_settings").select("value").eq("key", "prev_upper_limit_window_days").execute()
                upper_window_days = int(sys_set.data[0]['value']) if sys_set.data else 3
                upper_start_date = today - timedelta(days=upper_window_days)
                
                upper_res = supabase.table("upper_limit_stocks").select("name").gte("recorded_date", upper_start_date.strftime('%Y-%m-%d')).execute()
                if upper_res.data:
                    upper_stock_names = list(set([item['name'] for item in upper_res.data]))
                    if upper_stock_names:
                        # 튜플로 변환하여 캐시 함수의 인자로 넘김
                        upper_stock_tuple = tuple(upper_stock_names)
                        df = load_upper_limit_logs(upper_stock_tuple, upper_start_date.strftime('%Y-%m-%d'), asset_type=asset_type, market_type=market_type, show_closing_auction=show_closing_auction)
                    else:
                        df = pd.DataFrame(columns=['id', 'date', 'time', 'code', 'name', 'side', 'amount_krw', 'price', 'volume', 'asset_type', 'market_type'])
                else:
                    df = pd.DataFrame(columns=['id', 'date', 'time', 'code', 'name', 'side', 'amount_krw', 'price', 'volume', 'asset_type', 'market_type'])
            else:
                # 🎯 [Two-Track 캐시 최적화] 검색어가 없고 상한가 필터도 없으면 기존 엔진 가동!
                today_df = load_today_data(asset_type=asset_type, market_type=market_type, show_closing_auction=show_closing_auction)
                
                is_realtime_log = (scrn_select == "체결 로그")
                if is_realtime_log or (global_period == "당일 데이터만"):
                    df = today_df
                else:
                    _cache_date = get_latest_market_open_date().strftime('%Y-%m-%d')
                    historical_df = load_historical_data(asset_type=asset_type, market_type=market_type, show_closing_auction=show_closing_auction, cache_date=_cache_date)
                    df = pd.concat([historical_df, today_df], ignore_index=True)
        else:
            # 검색어가 있으면 검색 전용 1분 캐시 엔진 가동
            df = load_search_data(
                search_keyword.strip(), exact_match, start_date, limit=fetch_limit,
                asset_type=asset_type, market_type=market_type,
                show_closing_auction=show_closing_auction
            )

    # --- [ SideBar: Personal Selectors ] ---
    st.sidebar.markdown('<div class="spacer-logout"></div>', unsafe_allow_html=True)
    
    # 🌟 [버튼 재배치 2026-07-30] "외/기 탑100" 버튼은 2번째 줄로 이전됨 — 이 자리는 "수익율 자랑" 버튼이 통째로 차지 (긴 버튼)
    st.sidebar.markdown('<div class="btn-style-brag"></div>', unsafe_allow_html=True)
    if st.sidebar.button("💖 수익율 자랑", use_container_width=True):
        st.session_state['scrn_select_radio'] = "수익율 자랑"
        st.session_state["brag_view_mode"] = "list"
        st.session_state["brag_selected_post"] = None
        st.session_state["show_brag_form"] = False
        st.rerun()

    if st.session_state.get('authenticated', False):
        st.sidebar.markdown('<div class="btn-style-logout"></div>', unsafe_allow_html=True)
        if st.sidebar.button("로그아웃 🔌"):
            st.session_state['authenticated'] = False
            st.session_state['is_admin'] = False
            st.session_state['current_user'] = ""
            st.rerun()

    # 🔧 [추가 2026-07-30] 투자 유의 문구 위 구분선
    st.sidebar.markdown('<hr style="margin:10px 0 6px 0; border:none; border-top:1px solid #333333;">', unsafe_allow_html=True)

    # 🔧 [추가 2026-07-30] 투자 유의 문구 (사이드바 맨 하단, 로그아웃 버튼 색상보다 살짝 밝게)
    st.sidebar.markdown(
        """
        <div style="font-family:'굴림체','GulimChe','Gulim',sans-serif; font-size:8pt; color:#c8c8c8; line-height:1.4; margin-top:6px;">
        본 사이트에서 제공하는 모든 정보는 투자 판단의 자료이며, 수익을 절대 보장하지 않습니다.<br>
        원금 손실이 발생할 수 있으며, 그 손실은 투자자 본인에게 책임이 있습니다.
        </div>
        """,
        unsafe_allow_html=True
    )

    # 🌟 [신규 2026-07-30] 골든스코어 / 뉴스감성 산출 방식 FAQ (사용자 문의 대응용, 문구 바로 아래 배치)
    with st.sidebar.expander("ℹ️ 골든스코어는 어떻게 계산되나요?"):
        st.markdown(
            """
            <div style="font-size:8.5pt; color:#dddddd; line-height:1.5;">
            골든스코어는 아래와 같은 시장 수급 데이터를 종합해 산출하는 참고 점수입니다 (0~100점).<br><br>
            • 외국인·기관의 동반 순매수 여부와 규모<br>
            • 최근 며칠간 이 흐름이 지속되고 있는지 (하루성 vs 지속적 관심)<br>
            • 실시간 대량 매수(고래) 활동 정도<br>
            • 최근 상한가 이력<br>
            • 관리종목·거래정지 등 위험 신호 유무<br><br>
            이 점수는 과거~현재의 수급 데이터를 정리해 보여드리는 참고 지표이며, 특정 종목의 매수/매도를 추천하거나 향후 수익을 보장하는 것이 아닙니다. 점수 산출 기준은 서비스 품질 개선을 위해 예고 없이 조정될 수 있습니다. 모든 투자 판단과 그에 따른 손익은 투자자 본인의 책임입니다.
            </div>
            """,
            unsafe_allow_html=True
        )

    with st.sidebar.expander("ℹ️ 📰 뉴스감성 점수는 무엇인가요?"):
        st.markdown(
            """
            <div style="font-size:8.5pt; color:#dddddd; line-height:1.5;">
            📰 뉴스감성은 해당 종목의 최근 뉴스 제목들을 AI가 읽고, 시장 심리가 긍정적인지 부정적인지를 -5(매우 부정적) ~ +5(매우 긍정적) 사이의 숫자로 정리해 보여드리는 실험적 참고 지표입니다.<br><br>
            매일 자동으로 갱신되며, 아직 해당 종목의 뉴스가 수집되지 않았거나 분석 전이라면 빈칸으로 표시됩니다.<br><br>
            이 점수는 AI가 뉴스 제목만으로 판단한 참고용 감성 지표이며, 실제 기업 가치나 향후 주가를 보장하지 않습니다. 뉴스 해석은 AI마다 다를 수 있으니 참고 자료로만 활용해 주세요.
            </div>
            """,
            unsafe_allow_html=True
        )

    if df.empty and scrn_select not in ["TOP 10 화면", "수익율 화면", "상선고 화면", "수익율 자랑", "기간 누적 폭주", "고래 골든픽"]:
        st.warning("⚠️ 해당 조건의 고래 데이터가 없거나, 아직 수집 전입니다!")
    else:
        # 메인 차트용 데이터 필터링
        if not df.empty:
            main_df = df[df['date'] >= start_date.strftime('%Y-%m-%d')]
        else:
            main_df = pd.DataFrame(columns=['id', 'date', 'time', 'code', 'name', 'side', 'amount_krw', 'price', 'volume', 'asset_type', 'market_type', 'datetime', 'date_parsed'])

        # UI용 변수 (df가 비어있어도 TOP 10 화면 등에서 사용됨)
        if market_type == "KOSPI 🏢":
            display_market = "KOSPI"
        elif market_type == "KOSDAQ 🚀":
            display_market = "KOSDAQ"
        else:
            display_market = "종합"

        # --- [상단 레이아웃 표출] ---
        if (scrn_select == "TOP 10 화면"):
            # RPC 파라미터 맵핑
            if asset_type == "개별 주식만 보기 🏢":
                p_asset_type = '개별주식'
            elif asset_type == "ETF만 보기 🌐":
                p_asset_type = 'ETF'
            else:
                p_asset_type = '전체'
                
            if market_type == "KOSPI 🏢":
                p_market_type = 'KOSPI'
            elif market_type == "KOSDAQ 🚀":
                p_market_type = 'KOSDAQ'
            else:
                p_market_type = '전체'

            left_col, gap_col, right_col = st.columns([7.7, 0.1, 2.2])
            with left_col:
                # 상단 헤더와 새로고침 버튼을 동일선상(Y축)에, 버튼을 차트 우측 끝단(X축)에 정렬
                title_col, btn_col = st.columns([8.5, 1.5])
                with title_col:
                    st.subheader(f"&nbsp;🏆&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; 오늘의 {display_market} TOP 10 ({global_period})")
                with btn_col:
                    # 서브헤더와 Y축 시각적 정렬을 위해 마진 추가
                    st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
                    if st.button("새로고침 🔄", use_container_width=True):
                        st.rerun()
                st.write("")
                col_chart, col_data = st.columns(2)
                with col_chart:
                    chart_type = st.radio("차트 모드 전환", ["막대 그래프 📊", "파이 차트 🍩"], horizontal=True)
                with col_data:
                    data_type = st.radio("데이터 구분", ["매수", "매도", "합산"], horizontal=True, index=2)
                
                # RPC 호출: TOP 10
                rpc_res = supabase.rpc('get_top10_whales', {
                    'p_start_date': start_date.strftime('%Y-%m-%d'),
                    'p_asset_type': p_asset_type,
                    'p_market_type': p_market_type,
                    'p_side': data_type
                }).execute()
                
                top10_df = pd.DataFrame(rpc_res.data)
                
                if not top10_df.empty:
                    # 🏷️ 테마 정보 결합
                    stock_names_list = top10_df['name'].tolist()
                    themes_dict = get_themes_for_stocks(stock_names_list)
                    
                    def format_name_with_theme(row):
                        name = row['name']
                        theme = themes_dict.get(name, "")
                        if theme:
                            # 콤마로 구분된 여러 테마를 줄바꿈(<br>)하여 세로로 배치
                            theme_list = [t.strip() for t in theme.split(',') if t.strip()]
                            formatted_themes = ""
                            for i, t in enumerate(theme_list):
                                # 최대 3개까지만 보여주고 나머지는 생략
                                if i >= 3:
                                    formatted_themes += f"<br><span style='font-size:11px;color:#a0a0a0;'>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;...</span>"
                                    break
                                
                                if i == 0:
                                    # 첫 번째 테마에만 🏷️ 아이콘 표시
                                    formatted_themes += f"<br><span style='font-size:11px;color:#a0a0a0;'>🏷️ {t}</span>"
                                else:
                                    # 두 번째 테마부터는 아이콘 크기만큼 들여쓰기 공간 확보
                                    formatted_themes += f"<br><span style='font-size:11px;color:#a0a0a0;'>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;{t}</span>"
                                    
                            return f"{name}{formatted_themes}"
                        return name
                        
                    top10_df['display_name'] = top10_df.apply(format_name_with_theme, axis=1)

                    color = '#00E676' if data_type == "합산" else ('#ff4b4b' if data_type == "매수" else '#4B89B5')

                    if chart_type == "막대 그래프 📊":
                        # 억 단위 환산
                        top10_df['amount_krw_100m'] = top10_df['amount_krw'] / 100000000
                        
                        fig = px.bar(top10_df, x='display_name', y='amount_krw_100m', 
                                    text=top10_df['amount_krw_100m'].apply(lambda x: f"{x:,.0f}억"),
                                    labels={'display_name': '종목명', 'amount_krw_100m': '누적 금액(억원)'})
                        fig.update_traces(marker_color=color, textposition='outside')
                        fig.update_layout(
                            yaxis=dict(tickformat=",.0f", ticksuffix="억"),
                            xaxis=dict(tickangle=0) # X축 라벨이 삐딱해지지 않도록 가로로 강제 고정
                        )
                        st.plotly_chart(fig, width='stretch')
                    else:
                        fig = px.pie(top10_df, values='amount_krw', names='display_name', hole=0.3)
                        fig.update_traces(textposition='inside', textinfo='percent+label')
                        st.plotly_chart(fig, width='stretch')
                else:
                    st.info(f"선택하신 조건에 포착된 '{data_type}' 데이터가 없습니다.")

            with right_col:
                # 1. 수급 온도계 (Market Sentiment) - TOP 10 매수/매도 합산 기반으로 정확한 시장 분위기 추산
                buy_res = supabase.rpc('get_top10_whales', {'p_start_date': start_date.strftime('%Y-%m-%d'), 'p_asset_type': p_asset_type, 'p_market_type': p_market_type, 'p_side': '매수'}).execute()
                sell_res = supabase.rpc('get_top10_whales', {'p_start_date': start_date.strftime('%Y-%m-%d'), 'p_asset_type': p_asset_type, 'p_market_type': p_market_type, 'p_side': '매도'}).execute()
                
                buy_df_tmp = pd.DataFrame(buy_res.data)
                sell_df_tmp = pd.DataFrame(sell_res.data)
                
                top_buy_sum = buy_df_tmp['amount_krw'].sum() if not buy_df_tmp.empty else 0
                top_sell_sum = sell_df_tmp['amount_krw'].sum() if not sell_df_tmp.empty else 0
                total_vol = top_buy_sum + top_sell_sum
                
                if total_vol > 0:
                    buy_ratio = (top_buy_sum / total_vol) * 100
                    sell_ratio = (top_sell_sum / total_vol) * 100
                else:
                    buy_ratio, sell_ratio = 50, 50
                
                # 2. 고래 자금 블랙홀 (Concentration) - 현재 보고 있는 TOP 10 내에서의 쏠림도!
                if not top10_df.empty:
                    top10_total_amount = top10_df['amount_krw'].sum()
                    if top10_total_amount > 0:
                        top3_amount = top10_df.head(3)['amount_krw'].sum()
                        concentration = (top3_amount / top10_total_amount) * 100
                        top3_names = ", ".join(top10_df.head(2)['name'].tolist())
                        desc = f"{top3_names} 등 최상위 종목에 집중 중" if concentration > 50 else "자금이 고르게 분산되어 있습니다."
                    else:
                        concentration = 0
                        desc = "데이터가 부족합니다."
                else:
                    concentration = 0
                    desc = "데이터가 부족합니다."

                # 차트 하단과 위치를 맞추기 위해 상단 여백 크게 부여
                st.markdown("<div style='margin-top: 220px;'></div>", unsafe_allow_html=True)
                st.markdown("<h5 style='color:#ffffff; border-left: 4px solid #FFA500; padding-left: 10px; margin-bottom: 20px;'>💡 놀빅 투자 인사이트</h5>", unsafe_allow_html=True)
                
                # 수급 온도계 UI
                st.markdown(f"""
                <div style="background-color: #1a1a24; padding: 15px; border-radius: 8px; margin-bottom: 15px;">
                    <div style="font-size: 14px; color: #b0b0b0; margin-bottom: 5px;">🌡️ 시장 수급 온도계 (매수 vs 매도)</div>
                    <div style="display: flex; height: 10px; border-radius: 5px; overflow: hidden; margin-bottom: 5px;">
                        <div style="width: {buy_ratio}%; background-color: #ff4b4b;"></div>
                        <div style="width: {sell_ratio}%; background-color: #4B89B5;"></div>
                    </div>
                    <div style="display: flex; justify-content: space-between; font-size: 12px; font-weight: bold;">
                        <span style="color: #ff4b4b;">매수 {buy_ratio:.1f}%</span>
                        <span style="color: #4B89B5;">매도 {sell_ratio:.1f}%</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                # 고래 자금 블랙홀 UI
                warn_color = "#ff4b4b" if concentration > 30 else "#00E676"
                warn_icon = "🚨" if concentration > 30 else "✅"
                st.markdown(f"""
                <div style="background-color: #1a1a24; padding: 15px; border-radius: 8px; margin-bottom: 15px;">
                    <div style="font-size: 14px; color: #b0b0b0; margin-bottom: 5px;">🕳️ 고래 자금 쏠림도 (TOP 3 기준)</div>
                    <div style="font-size: 18px; font-weight: bold; color: {warn_color};">{warn_icon} 점유율: {concentration:.1f}%</div>
                    <div style="font-size: 12px; color: #888888; margin-top: 5px;">{desc}</div>
                </div>
                """, unsafe_allow_html=True)

            # --- [오늘의 씬스틸러 (가로형 와이드 카드, 차트 아래 배치)] ---
            scene_stealer_name = "-"
            scene_stealer_netbuy = 0
            try:
                date_res = supabase.table('whale_log').select('date').order('date', desc=True).limit(1).execute()
                if date_res.data:
                    latest_date_str = date_res.data[0]['date']
                    today_res = supabase.table('whale_log').select('name, side, amount_krw').eq('date', latest_date_str).limit(10000).execute()
                    today_df = pd.DataFrame(today_res.data)
                    if not today_df.empty:
                        today_df['signed_amount'] = today_df.apply(lambda r: r['amount_krw'] if r['side'] == '매수' else -r['amount_krw'], axis=1)
                        net_buy_df = today_df.groupby('name')['signed_amount'].sum().sort_values(ascending=False)
                        if not net_buy_df.empty and net_buy_df.iloc[0] > 0:
                            scene_stealer_name = net_buy_df.index[0]
                            scene_stealer_netbuy = net_buy_df.iloc[0] / 100000000
            except Exception as e:
                pass

            st.markdown("<h5 style='color:#ffffff; border-left: 4px solid #ff4b4b; padding-left: 10px; margin-top: 5px; margin-bottom: 10px;'>💥 오늘의 씬스틸러 (최근 개장일 기준)</h5>", unsafe_allow_html=True)
            st.markdown(f"""
            <div style="background: linear-gradient(90deg, #2b1a1a, #11111b); border: 1px solid #ff4b4b; padding: 12px 20px; border-radius: 8px; display: flex; align-items: center; justify-content: space-between;">
                <div>
                    <div style="font-size: 13px; color: #b0b0b0; margin-bottom: 2px;">오늘 하루 동안 고래 자금이 가장 강하게 꽂힌 종목입니다.</div>
                    <div style="font-size: 22px; font-weight: bold; color: #ffffff;">{scene_stealer_name}</div>
                </div>
                <div style="text-align: right;">
                    <div style="font-size: 13px; color: #ff4b4b; margin-bottom: 2px;">당일 순매수 금액</div>
                    <div style="font-size: 22px; font-weight: bold; color: #ff4b4b;">+{int(scene_stealer_netbuy):,} 억</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            st.divider()

        elif scrn_select == "수익율 화면":
            st.markdown("<h4 style='color:#8A2BE2; border-left: 4px solid #8A2BE2; padding-left: 10px; margin-top: 0;'>📈 고래 매수 종목 수익율 TOP 20</h4>", unsafe_allow_html=True)
            
            # UI: 월, 주차, 기준금액 드롭다운
            ret_col1, ret_col2, ret_col3, ret_col4, ret_col_btn = st.columns([1.5, 0.8, 1.5, 1.5, 1.4])
            
            # 1. 월 생성 (최근 12개월)
            today_date = datetime.utcnow() + timedelta(hours=9)
            month_options = []
            for i in range(12):
                m_date = today_date.replace(day=1) - timedelta(days=28 * i)
                m_date = m_date.replace(day=1)
                month_options.append(m_date.strftime("%Y년 %m월"))
                
            with ret_col1:
                sel_month = st.selectbox("📅 월 선택", month_options, key="ret_month")
                
            with ret_col2:
                # 선택된 월의 순수 문자열 추출 (아이콘 제거용 - 현재는 불필요하지만 로직상 유지)
                pure_month = sel_month
                sel_week = st.selectbox("📆 주차 선택", ["월 전체", "1주차", "2주차", "3주차", "4주차", "5주차"], key="ret_week")
                
            with ret_col3:
                sel_amt = st.selectbox("💰 기준 금액", ["1천만원 이상", "3천만원 이상", "5천만원 이상", "1억 이상", "3억 이상", "5억 이상", "10억 이상", "50억 이상"], key="ret_amt")
            with ret_col4:
                sel_filter = st.selectbox("🎯 종목 필터", ["순수 개별종목 (우선주/ETF 제외)", "전체 종목 포함"], key="ret_filter")
                
            # 금액 파싱
            if "천만원" in sel_amt:
                min_krw = int(sel_amt.split("천만원")[0]) * 10000000
            else:
                min_krw = int(sel_amt.split("억")[0]) * 100000000

            # -------------------------------------------------------------
            # [캐시 유효성 판단 공통 로직] (버튼 UI와 실제 조회 로직에서 동일하게 사용)
            # -------------------------------------------------------------
            yyyy = int(pure_month[:4])
            mm = int(pure_month[6:8])
            
            first_day = datetime(yyyy, mm, 1)
            if mm == 12: last_day = datetime(yyyy + 1, 1, 1) - timedelta(days=1)
            else: last_day = datetime(yyyy, mm + 1, 1) - timedelta(days=1)
            
            if sel_week == "월 전체":
                start_dt = first_day
                end_dt = last_day
            else:
                week_num = int(sel_week[0])
                first_weekday = first_day.weekday()
                if first_weekday <= 4: w1_monday = first_day - timedelta(days=first_weekday)
                else: w1_monday = first_day + timedelta(days=(7 - first_weekday))
                start_dt = w1_monday + timedelta(weeks=week_num - 1)
                end_dt = start_dt + timedelta(days=4)
                
            now_kst = datetime.utcnow() + timedelta(hours=9)
            today_kr = now_kst.date()
            if end_dt.date() > today_kr: end_dt = now_kst
            
            is_currently_cached = False
            is_cache_stale = False
            cached_data_pre = []
            try:
                check_combo = supabase.table('return_rate_cache').select('*').eq('period_month', pure_month).eq('period_week', sel_week).eq('min_amount', min_krw).execute()
                if check_combo.data:
                    is_currently_cached = True
                    cached_data_pre = check_combo.data
                    # 만료 검사 (관리자의 업데이트 용도)
                    if start_dt.date() <= today_kr <= end_dt.date():
                        cache_dt_kr = datetime.fromisoformat(check_combo.data[0]['updated_at'].replace('Z', '+00:00')) + timedelta(hours=9)
                        if cache_dt_kr.date() == today_kr:
                            market_close_time = datetime.combine(today_kr, datetime.strptime("15:30", "%H:%M").time())
                            if cache_dt_kr < market_close_time and now_kst >= market_close_time:
                                is_cache_stale = True
                        else:
                            is_cache_stale = True
            except Exception:
                pass
            # -------------------------------------------------------------
            
            is_admin_view = st.session_state.get('is_admin', False)
            actual_use_cache = False
            
            with ret_col_btn:
                if is_currently_cached:
                    st.html("""
                    <div class='search-btn-wrapper' style='display:none;'></div>
                    <style>
                        div.element-container:has(.search-btn-wrapper) { display: none !important; }
                        div.element-container:has(.search-btn-wrapper) + div.element-container { margin-top: 28px !important; }
                        div.element-container:has(.search-btn-wrapper) + div.element-container button {
                            background-color: #198754 !important; color: white !important; border-color: #198754 !important;
                        }
                    </style>""")
                    search_ret = st.button("🚀 바로 조회 (캐시됨)", use_container_width=True)
                    actual_use_cache = True
                else:
                    st.html("""
                    <div class='search-btn-wrapper' style='display:none;'></div>
                    <style>
                        div.element-container:has(.search-btn-wrapper) { display: none !important; }
                        div.element-container:has(.search-btn-wrapper) + div.element-container { margin-top: 28px !important; }
                        div.element-container:has(.search-btn-wrapper) + div.element-container button {
                            background-color: #fd7e14 !important; color: white !important; border-color: #fd7e14 !important;
                        }
                    </style>""")
                    search_ret = st.button("🚀 신규 계산 (대기중)", use_container_width=True)
                    actual_use_cache = False
            
            if st.session_state.get('force_recalc_ret', False):
                st.session_state['force_recalc_ret'] = False
                actual_use_cache = False
                search_ret = True
            
            if search_ret or st.session_state.get('force_show_graph', False):
                st.session_state['force_show_graph'] = False
                
                if start_dt.date() > (datetime.utcnow() + timedelta(hours=9)).date():
                    st.warning("선택하신 기간은 아직 도래하지 않았습니다.")
                else:
                    if end_dt.date() > (datetime.utcnow() + timedelta(hours=9)).date():
                        end_dt = datetime.utcnow() + timedelta(hours=9)
                        
                    str_start = start_dt.strftime('%Y-%m-%d')
                    str_end = end_dt.strftime('%Y-%m-%d')
                    
                    st.markdown(f"<div style='background-color: rgba(23, 42, 69, 0.7); color: #64d2ff; padding: 8px 15px; border-radius: 5px; font-size: 13px; margin-bottom: 5px;'><span style='margin-right: 5px;'>🔎</span> 조회 기간: {str_start} ~ {str_end} | 기준금액: {sel_amt}</div>", unsafe_allow_html=True)
                    
                    # 이미 위에서 검증한 공통 로직 결과 재사용
                    use_cache = actual_use_cache
                    if st.session_state.get('force_show_graph', False):
                        use_cache = is_currently_cached # 하단 표에서 클릭 시 강제 캐시 조회
                        
                    cached_data = cached_data_pre
                    
                    res_df = pd.DataFrame()
                    
                    if use_cache and cached_data:
                        is_admin = st.session_state.get('is_admin', False)
                        if is_admin:
                            col_msg, col_btn = st.columns([7, 3])
                            with col_msg:
                                st.markdown("<div style='background-color: rgba(15, 61, 31, 0.7); color: #5bc27b; padding: 8px 15px; border-radius: 5px; font-size: 13px; margin-bottom: 5px;'><span style='margin-right: 5px;'>💾</span> DB에서 고속으로 캐시 데이터를 가져왔습니다!</div>", unsafe_allow_html=True)
                            with col_btn:
                                if st.button("🔄 캐시 강제 업데이트 실행", use_container_width=True):
                                    st.session_state['force_recalc_ret'] = True
                                    st.rerun()
                        else:
                            st.markdown("<div style='background-color: rgba(15, 61, 31, 0.7); color: #5bc27b; padding: 8px 15px; border-radius: 5px; font-size: 13px; margin-bottom: 5px;'><span style='margin-right: 5px;'>💾</span> DB에서 고속으로 캐시 데이터를 가져왔습니다!</div>", unsafe_allow_html=True)
                            
                        res_df = pd.DataFrame(cached_data)
                    else:
                        is_admin = st.session_state.get('is_admin', False)
                        if not is_admin:
                            st.warning("아직 계산되지 않은 자료입니다. 자료 준비를 관리자에게 요청하십시요.")
                            df_all = pd.DataFrame() # 빈 데이터프레임으로 하위 로직 패스
                        else:
                            with st.spinner("캐시가 없거나 만료되었습니다. 주가를 실시간 계산 중입니다... 🐳"):
                                if global_period != "당일 데이터만":
                                    _cache_date = get_latest_market_open_date().strftime('%Y-%m-%d')
                                    historical_df = load_historical_data(asset_type='전체 주식/ETF 🌍', market_type='전체 시장 🌍', show_closing_auction=True, cache_date=_cache_date)
                                    today_df = load_today_data(asset_type='전체 주식/ETF 🌍', market_type='전체 시장 🌍', show_closing_auction=True)
                                    df_all = pd.concat([historical_df, today_df], ignore_index=True)
                                else:
                                    today_df = load_today_data(asset_type='전체 주식/ETF 🌍', market_type='전체 시장 🌍', show_closing_auction=True)
                                    df_all = today_df

                        if df_all.empty:
                            if is_admin:
                                st.warning("수집된 데이터가 없습니다.")
                        else:
                            df_period = df_all[(df_all['date'] >= start_dt.strftime('%Y-%m-%d')) & (df_all['date'] <= end_dt.strftime('%Y-%m-%d'))]
                            df_buy = df_period[(df_period['side'] == '매수') & (df_period['amount_krw'] >= min_krw)]
                            
                            # 🚀 타임아웃/OOM 방어: 전체 종목을 조회하면 API 차단 및 Streamlit 제한시간(60초)에 걸려 뻗으므로,
                            # 해당 기간 누적 매수금액 기준 상위 200개 종목만 엄선하여 수익율을 계산합니다. (TOP 20 추출에는 200개면 충분함)
                            top_codes = df_buy.groupby(['code', 'name'])['amount_krw'].sum().reset_index().sort_values('amount_krw', ascending=False).head(200)
                            unique_stocks = top_codes[['code', 'name']]
                            results = []
                            total_stocks = len(unique_stocks)
                            if total_stocks == 0:
                                st.warning("해당 기간/조건에 포착된 고래 매수 종목이 없습니다.")
                            else:
                                progress_bar = st.progress(0)
                                progress_text = st.empty()
                                    
                                for idx, row in enumerate(unique_stocks.itertuples()):
                                    code = row.code
                                    name = row.name
                                    
                                    progress_bar.progress((idx + 1) / total_stocks)
                                    progress_text.text(f"주가 데이터 조회 중: {name} ({idx+1}/{total_stocks})")
                                    
                                    try:
                                        price_df = fdr.DataReader(code, str_start, str_end)
                                        if not price_df.empty and len(price_df) > 0:
                                            start_price = price_df.iloc[0]['Open']
                                            end_price = price_df.iloc[-1]['Close']
                                                
                                            if start_price > 0:
                                                ret_rate = ((end_price - start_price) / start_price) * 100
                                                diff_amt = end_price - start_price
                                                results.append({
                                                    'period_month': pure_month,
                                                    'period_week': sel_week,
                                                    'min_amount': min_krw,
                                                    'stock_code': code,
                                                    'stock_name': name,
                                                    'start_price': int(start_price),
                                                    'end_price': int(end_price),
                                                    'ret_rate': ret_rate,
                                                    'updated_at': datetime.utcnow().isoformat()
                                                })
                                    except Exception as e:
                                        pass
                                        
                                progress_text.empty()
                                progress_bar.empty()
                                
                                if results:
                                    res_df = pd.DataFrame(results)
                                    res_df['diff_amt'] = res_df['end_price'] - res_df['start_price']
                                    
                                    import re
                                    def is_pure_stock(name):
                                        if pd.isna(name): return False
                                        if re.search(r'우$|우B$|우\([A-Za-z0-9]+\)$|우[A-Z]$', name): return False
                                        if re.search(r'KODEX|TIGER|KINDEX|KBSTAR|ARIRANG|KOSEF|HANARO|ACE|SOL|TIMEFOLIO|히어로즈|스팩|ETN|제\d+호', name, re.IGNORECASE): return False
                                        return True
                                        
                                    res_df['is_pure'] = res_df['stock_name'].apply(is_pure_stock)
                                    pure_df = res_df[res_df['is_pure'] == True]
                                    
                                    # 🟢 최적화: 전체를 저장하지 않고 수익율 TOP 20, 상승폭 TOP 20만 병합(전체 + 개별종목)하여 캐싱
                                    top_rate_all = res_df.sort_values('ret_rate', ascending=False).head(20)
                                    top_amt_all = res_df.sort_values('diff_amt', ascending=False).head(20)
                                    top_rate_pure = pure_df.sort_values('ret_rate', ascending=False).head(20) if not pure_df.empty else pd.DataFrame()
                                    top_amt_pure = pure_df.sort_values('diff_amt', ascending=False).head(20) if not pure_df.empty else pd.DataFrame()
                                    
                                    final_cache_df = pd.concat([top_rate_all, top_amt_all, top_rate_pure, top_amt_pure]).drop_duplicates(subset=['stock_code'])
                                    cache_records = final_cache_df.drop(columns=['diff_amt', 'is_pure']).to_dict('records')
                                    
                                    # DB에 캐시 저장 (조건에 맞는 기존 캐시 삭제 후 인서트하여 중복 키 에러 방지)
                                    try:
                                        supabase.table('return_rate_cache').delete().eq('period_month', pure_month).eq('period_week', sel_week).eq('min_amount', min_krw).execute()
                                        supabase.table('return_rate_cache').upsert(cache_records).execute()
                                        
                                        # 요약본(이정표) 생성 및 system_settings 에 저장
                                        summary_key = f"cache_summary_{pure_month}_{sel_week}_{min_krw}"
                                        summary_val = {
                                            'month': pure_month,
                                            'week': sel_week,
                                            'amt': min_krw,
                                            'count': len(final_cache_df),
                                            'updated_at': datetime.utcnow().isoformat()
                                        }
                                        supabase.table('system_settings').upsert({
                                            'key': summary_key,
                                            'value': json.dumps(summary_val, ensure_ascii=False)
                                        }).execute()
                                        
                                        st.session_state['force_show_graph'] = True
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"캐시 저장 실패: {e}")
                                else:
                                    st.warning("수익율을 계산할 수 있는 종목이 없습니다.")

                    if not res_df.empty:
                        if 'name' not in res_df.columns and 'stock_name' in res_df.columns:
                            res_df['name'] = res_df['stock_name']
                            
                        # 절대 금액 상승폭 컬럼 생성
                        res_df['diff_amt'] = res_df['end_price'] - res_df['start_price']
                        
                        # 🟢 종목 필터 적용
                        if sel_filter == "순수 개별종목 (우선주/ETF 제외)":
                            pure_codes_set = get_pure_stock_codes()
                            if pure_codes_set is not None:
                                res_df = res_df[res_df['stock_code'].isin(pure_codes_set)]
                            else:
                                # FDR 로딩 실패 시 기존 정규식 방식 폴백 (Fallback)
                                import re
                                def is_pure_stock(name):
                                    if pd.isna(name): return False
                                    if re.search(r'우$|우B$|우\([A-Za-z0-9]+\)$|우[A-Z]$', name): return False
                                    if re.search(r'KODEX|TIGER|KINDEX|KBSTAR|ARIRANG|KOSEF|HANARO|ACE|SOL|TIMEFOLIO|히어로즈|스팩|ETN|제\d+호|PLUS|RISE|WON|1Q|KIWOOM|TRUE|QV|선물|콜|풋|옵션', name, re.IGNORECASE): return False
                                    return True
                                res_df = res_df[res_df['name'].apply(is_pure_stock)]
                        
                        # 1. 수익률 기준 TOP 20
                        ret_df = res_df.sort_values('ret_rate', ascending=False).head(20).reset_index(drop=True)
                        # 2. 상승폭 기준 TOP 20
                        amt_df = res_df.sort_values('diff_amt', ascending=False).head(20).reset_index(drop=True)
                        
                        # 데이터가 20개가 안될 수도 있으므로 최대 길이 구하기
                        max_len = max(len(ret_df), len(amt_df))
                        
                        x_labels = []
                        ret_rates = []
                        ret_hovers = []
                        ret_names = []
                        
                        amt_diffs = []
                        amt_hovers = []
                        amt_names = []
                        
                        for i in range(max_len):
                            # 퍼센트 랭커
                            if i < len(ret_df):
                                r_name = ret_df.iloc[i]['name']
                                r_rate = ret_df.iloc[i]['ret_rate']
                                r_start = ret_df.iloc[i]['start_price']
                                r_end = ret_df.iloc[i]['end_price']
                                ret_rates.append(r_rate)
                                ret_names.append(r_name)
                                ret_hovers.append(f"<b>{r_name}</b><br>시작가: {int(r_start):,}원<br>종료가: {int(r_end):,}원<br>수익율: {r_rate:.1f}%")
                            else:
                                r_name = "-"
                                ret_rates.append(0)
                                ret_names.append("-")
                                ret_hovers.append("-")
                                
                            # 절대금액 랭커
                            if i < len(amt_df):
                                a_name = amt_df.iloc[i]['name']
                                a_start = amt_df.iloc[i]['start_price']
                                a_end = amt_df.iloc[i]['end_price']
                                a_diff = amt_df.iloc[i]['diff_amt']
                                amt_diffs.append(a_diff)
                                amt_names.append(a_name)
                                amt_hovers.append(f"<b>{a_name}</b><br>시작가: {int(a_start):,}원<br>종료가: {int(a_end):,}원<br>상승폭: {int(a_diff):+,}원")
                            else:
                                a_name = "-"
                                amt_diffs.append(0)
                                amt_names.append("-")
                                amt_hovers.append("-")
                                
                            # X축 라벨 조합 (위: 주황색 금액 랭커, 아래: 보라색 수익율 랭커 - 기울기 시 막대 위치와 시각적 일치)
                            x_labels.append(f"<span style='color:#ffb74d;'>{i+1}위: {a_name}</span><br><span style='color:#b57edd;'>{i+1}위: {r_name}</span>")
                            
                        # Plotly 듀얼 차트 렌더링
                        from plotly.subplots import make_subplots
                        import plotly.graph_objects as go
                        fig = make_subplots(specs=[[{"secondary_y": True}]])
                        
                        # 보라색 막대 (수익율)
                        fig.add_trace(
                            go.Bar(
                                x=x_labels, 
                                y=ret_rates,
                                name='수익율 랭커 (%)',
                                marker_color='#8A2BE2',
                                text=[f"{val:.1f}%" if val != 0 else "" for val in ret_rates],
                                textposition='outside',
                                customdata=ret_hovers,
                                hovertemplate='%{customdata}<extra></extra>',
                                offsetgroup='1'
                            ),
                            secondary_y=False
                        )
                        
                        # 주황색 막대 (상승폭)
                        fig.add_trace(
                            go.Bar(
                                x=x_labels,
                                y=amt_diffs,
                                name='상승폭 랭커 (원)',
                                marker_color='#FFA500',
                                text=[f"{int(val):+,}원" if val != 0 else "" for val in amt_diffs],
                                textposition='outside',
                                customdata=amt_hovers,
                                hovertemplate='%{customdata}<extra></extra>',
                                offsetgroup='2'
                            ),
                            secondary_y=True
                        )
                        
                        fig.update_layout(
                            barmode='group',
                            xaxis=dict(
                                tickangle=45,
                                tickfont=dict(size=12)
                            ),
                            yaxis=dict(
                                title=dict(text="수익율 (%)", font=dict(color="#8A2BE2")),
                                tickformat=".1f", 
                                ticksuffix="%",
                                tickfont=dict(color="#8A2BE2"),
                                side='left'
                            ),
                            yaxis2=dict(
                                title=dict(text="상승폭 (원)", font=dict(color="#FFA500")),
                                tickformat=",", 
                                tickfont=dict(color="#FFA500"),
                                side='right',
                                overlaying='y'
                            ),
                            legend=dict(
                                orientation="h",
                                yanchor="bottom",
                                y=1.05,
                                xanchor="center",
                                x=0.5
                            ),
                            margin=dict(t=50, b=100),
                            height=520
                        )
                        
                        st.plotly_chart(fig, width='stretch')
                        
            # --- [데이터 추출 요청 게시판] ---
            st.divider()
            st.markdown("<div style='font-size: 18px; font-weight: bold; margin-bottom: 15px;'>📝 데이터 추출 요청 게시판</div>", unsafe_allow_html=True)
            st.markdown("새로운 조건의 데이터 추출은 서버 부하 방지를 위해 관리자만 실행할 수 있습니다. 필요하신 자료를 아래에서 요청해 주세요.")
            
            is_admin_view = st.session_state.get('is_admin', False)
            current_user = st.session_state.get('user_id', 'unknown')
            if 'username' in st.session_state and current_user == 'unknown':
                current_user = st.session_state['username']
                
            # 신규 요청 처리
            if not is_admin_view:
                req_col1, req_col2 = st.columns([4, 1])
                with req_col1:
                    st.info(f"현재 선택된 조건: **{pure_month}**, **{sel_week}**, **{sel_amt}**")
                with req_col2:
                    check_res = supabase.table('return_rate_cache').select('period_month').eq('period_month', pure_month).eq('period_week', sel_week).eq('min_amount', min_krw).limit(1).execute()
                    is_cached = len(check_res.data) > 0
                    if is_cached:
                        st.button("이미 산출된 조건입니다", disabled=True, use_container_width=True, key="req_btn")
                    else:
                        if st.button("이 조건 추출 요청하기", use_container_width=True, key="req_btn"):
                            req_id = str(uuid.uuid4())
                            req_data = {
                                "user": current_user,
                                "month": pure_month,
                                "week": sel_week,
                                "amt": sel_amt,
                                "status": "대기 중",
                                "reply": "",
                                "req_time": datetime.utcnow().isoformat()
                            }
                            try:
                                supabase.table("system_settings").insert({
                                    "key": f"yield_req_{req_id}",
                                    "value": json.dumps(req_data, ensure_ascii=False)
                                }).execute()
                                st.success("요청이 완료되었습니다!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"요청 실패: {e}")
                            
            # 요청 목록 및 캐시된 목록 불러오기
            try:
                req_res = supabase.table("system_settings").select("*").like("key", "yield_req_%").execute()
                req_list = []
                for row in req_res.data:
                    try:
                        val = json.loads(row['value'])
                        val['db_key'] = row['key']
                        req_list.append(val)
                    except Exception:
                        pass
                
                def set_req_conditions(month, week, amt):
                    st.session_state['ret_month'] = month
                    st.session_state['ret_week'] = week
                    st.session_state['ret_amt'] = amt
                    
                if is_admin_view:
                    admin_tab = st.segmented_control(
                        "관리자 메뉴 선택",
                        options=["⚙️ 데이터 추출 요청 관리 (관리자용)", "⚡ 분석 완료된 수익율 차트 목록 (일반용)"],
                        default="⚙️ 데이터 추출 요청 관리 (관리자용)",
                        key="admin_req_tab",
                        label_visibility="collapsed"
                    )
                    
                    if admin_tab == "⚙️ 데이터 추출 요청 관리 (관리자용)":
                        if req_list:
                            req_list.sort(key=lambda x: x.get('req_time', ''), reverse=True)
                            st.markdown("#### 전체 요청 내역 (관리자용)")
                            
                            st.html("""
                            <style>
                                div.element-container:has(.req-flex-marker) { display: none !important; }
                                div:has(> div.element-container .req-flex-marker) { display: flex !important; flex-direction: row !important; align-items: center !important; gap: 50px !important; }
                                div:has(> div.element-container .req-flex-marker) > div.element-container { width: auto !important; flex: 0 0 auto !important; }
                                div:has(> div.element-container .req-flex-marker) p { margin: 0 !important; }
                                div:has(> div.element-container .req-flex-marker) button { min-height: 32px !important; height: 32px !important; padding-top: 0 !important; padding-bottom: 0 !important; margin-top: 4px !important; }
                                div:has(> div.element-container .req-flex-marker) button p { line-height: 1 !important; font-size: 14px !important; }
                            </style>
                            """)
                            
                            for r in req_list:
                                with st.container():
                                    status_color = "#FFA500" if r.get('status') == "대기 중" else "#5bc27b"
                                    req_row = st.container()
                                    with req_row:
                                        st.html("<div class='req-flex-marker' style='display:none;'></div>")
                                        st.markdown(f"**요청자:** {r.get('user')} | **조건:** {r.get('month')} / {r.get('week')} / {r.get('amt')} | **상태:** <span style='color:{status_color}; font-weight:bold;'>{r.get('status')}</span>", unsafe_allow_html=True)
                                        st.button("✔ 설정", key=f"set_{r['db_key']}", on_click=set_req_conditions, args=(r.get('month'), r.get('week'), r.get('amt')), help="이 조건으로 상단 메뉴를 자동 설정합니다")
                                    
                                    if r.get('reply'):
                                        st.markdown(f"<div style='background-color:rgba(255,255,255,0.05); padding:10px; border-left:3px solid #8A2BE2; margin-top:5px; margin-bottom:10px;'>↳ <b>관리자 답변:</b> {r.get('reply')}</div>", unsafe_allow_html=True)
                                        
                                    if r.get('status') == "대기 중":
                                        req_month = r.get('month')
                                        req_week = r.get('week')
                                        req_amt_str = r.get('amt')
                                        if "천만원" in req_amt_str:
                                            req_min_krw = int(req_amt_str.split("천만원")[0]) * 10000000
                                        else:
                                            req_min_krw = int(req_amt_str.split("억")[0]) * 100000000
                                            
                                        check_res = supabase.table('return_rate_cache').select('period_month').eq('period_month', req_month).eq('period_week', req_week).eq('min_amount', req_min_krw).limit(1).execute()
                                        is_req_cached = len(check_res.data) > 0
                                        
                                        with st.form(key=f"form_{r['db_key']}"):
                                            reply_text = st.text_input("답변 내용 (추출 완료 후 작성해주세요)", key=f"reply_{r['db_key']}")
                                            col_btn1, col_btn2 = st.columns([1, 4])
                                            with col_btn1:
                                                submit_btn = st.form_submit_button("완료 처리")
                                            if submit_btn:
                                                if not is_req_cached:
                                                    st.error("❌ 먼저 상단 메뉴에서 해당 조건의 데이터를 추출(캐싱)해주세요.")
                                                else:
                                                    r['reply'] = reply_text
                                                    r['status'] = "완료됨"
                                                    db_key = r.pop('db_key')
                                                    try:
                                                        supabase.table("system_settings").upsert({"key": db_key, "value": json.dumps(r, ensure_ascii=False)}).execute()
                                                        st.success("✅ 처리 완료!")
                                                        import time
                                                        time.sleep(0.5)
                                                        st.rerun()
                                                    except Exception as e:
                                                        st.error(f"업데이트 실패: {e}")
                                    st.markdown("---")

                def render_user_cache_list():
                    with st.expander("⚡ 분석 완료된 수익율 차트 목록 (클릭하여 열람/닫기)", expanded=True):
                        st.markdown("아래 목록은 서버에서 이미 분석이 완료된 데이터입니다. 원하시는 종목 필터를 체크한 뒤 **⚙️ 옵션 세팅하기**를 누르시고, **화면 상단으로 이동하여 조회 버튼을 클릭**해주세요.")
                        
                        cached_combos = []
                        try:
                            # 캐시 요약(이정표) 테이블에서만 가볍게 읽어오기
                            c_res = supabase.table('system_settings').select('*').like('key', 'cache_summary_%').execute()
                            if c_res.data:
                                summary_list = []
                                for row in c_res.data:
                                    try:
                                        val = json.loads(row['value'])
                                        summary_list.append(val)
                                    except:
                                        pass
                                
                                if summary_list:
                                    cdf = pd.DataFrame(summary_list)
                                    cdf = cdf.sort_values(by=['month', 'week', 'amt'], ascending=[False, False, False])
                                    for _, row in cdf.iterrows():
                                        amt_str = f"{int(row['amt'])//10000000}천만원 이상" if row['amt'] < 100000000 else f"{int(row['amt'])//100000000}억 이상"
                                        cached_combos.append({
                                            'month': row['month'],
                                            'week': row['week'],
                                            'amt': amt_str
                                        })
                        except Exception as e:
                            st.error(f"캐시 목록 로드 실패: {e}")
                        
                        if cached_combos:
                            st.html("""
                            <style>
                                .cache-table { width: 100%; border-collapse: collapse; margin-top: 10px; color: white; text-align: center; }
                                .cache-table th { background-color: #262730; padding: 6px; border-bottom: 2px solid #8A2BE2; font-size: 14px; }
                            </style>
                            """)
                            
                            st.markdown("""
                            <table class="cache-table">
                                <thead>
                                    <tr>
                                        <th>분석 월</th>
                                        <th>주차</th>
                                        <th>기준 금액</th>
                                        <th>종목 필터</th>
                                        <th style="width: 140px;">차트 보기</th>
                                    </tr>
                                </thead>
                                <tbody>
                            """, unsafe_allow_html=True)
                            
                            def set_req_combo(idx, m, w, a):
                                st.session_state['ret_month'] = m
                                st.session_state['ret_week'] = w
                                st.session_state['ret_amt'] = a
                                is_pure = st.session_state.get(f"chk_{idx}", True)
                                st.session_state['ret_filter'] = "순수 개별종목 (우선주/ETF 제외)" if is_pure else "전체 종목 포함"
                                st.toast("✅ 옵션 설정 완료! 화면 상단으로 스크롤하여 [🚀 바로 조회] 버튼을 눌러주세요.", icon="⬆️")
                            
                            for i, combo in enumerate(cached_combos):
                                col1, col2, col3, col4, col5 = st.columns([1.2, 1.2, 1.5, 2.0, 1.5])
                                with col1:
                                    st.markdown(f"<div style='text-align:center; padding: 5px 0; font-size: 13px;'>{combo['month']}</div>", unsafe_allow_html=True)
                                with col2:
                                    st.markdown(f"<div style='text-align:center; padding: 5px 0; font-size: 13px;'>{combo['week']}</div>", unsafe_allow_html=True)
                                with col3:
                                    st.markdown(f"<div style='text-align:center; padding: 5px 0; font-size: 13px;'>{combo['amt']}</div>", unsafe_allow_html=True)
                                with col4:
                                    st.checkbox("순수 개별종목 한정", value=True, key=f"chk_{i}")
                                with col5:
                                    st.button("⚙️ 옵션 세팅하기", key=f"btn_cache_tbl_{i}", use_container_width=True, on_click=set_req_combo, args=(i, combo['month'], combo['week'], combo['amt']))
                                st.html("<hr style='margin:2px 0; border:0; border-bottom:1px solid #333;'>")
                                
                            st.markdown("</tbody></table>", unsafe_allow_html=True)
                            
                        else:
                            st.info("현재 분석이 완료되어 서버에 저장된 캐시 데이터가 없습니다.")

                if is_admin_view:
                    if admin_tab == "⚡ 분석 완료된 수익율 차트 목록 (일반용)":
                        render_user_cache_list()
                else:
                    render_user_cache_list()

            except Exception as e:
                st.error(f"요청 게시판 처리 중 오류 발생: {e}")
        elif scrn_select == "고래 골든픽":
            col_gold_left, col_gold_right = st.columns([1.8, 1])
            
            with col_gold_left:
                st.markdown("<h4 style='color:#E040FB; border-left: 4px solid #E040FB; padding-left: 10px; margin-top: 0;'>🏆 고래 골든픽 TOP 20</h4>", unsafe_allow_html=True)
                st.caption("시장 세력 수급, 외인/기관 쌍끌이, 상한가 족보, 실시간 고래 활동 및 위험 배지를 입체 종합 분석하여 산출된 1~20위 최정예 종목입니다. 🚀")
                st.write("")


            with col_gold_right:
                # 📅 골든픽 전용 커스텀 HTML 달력 연동
                now_kst = datetime.utcnow() + timedelta(hours=9)
                if now_kst.time() < datetime.strptime("16:00", "%H:%M").time():
                    target_dt = now_kst - timedelta(days=1)
                else:
                    target_dt = now_kst
                target_dt = target_dt.replace(hour=12, minute=0, second=0, microsecond=0)
                today_kor = get_latest_market_open_date(target_dt)
                min_date = today_kor - timedelta(days=90)
                
                import calendar
                from st_click_detector import click_detector
                
                if 'golden_cal_year' not in st.session_state:
                    st.session_state.golden_cal_year = today_kor.year
                    st.session_state.golden_cal_month = today_kor.month
                    st.session_state.golden_selected_date = today_kor
                    st.session_state.golden_cal_reset = 0
                
                cal_year = st.session_state.golden_cal_year
                cal_month = st.session_state.golden_cal_month
                selected_date = st.session_state.golden_selected_date
                
                html_cal = f"""
                <div style="max-width: 230px; margin-left: auto; background: #1a1c24; padding: 10px; border-radius: 10px; font-family: 'Inter', sans-serif; box-shadow: 0 4px 6px rgba(0,0,0,0.3);">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; color: white;">
                        <a href='#' id='gcal_prev' style='color: #888; text-decoration: none; padding: 3px 8px; background: #2a2d3a; border-radius: 4px; font-weight: bold; font-size: 12px;'>&lt;</a>
                        <strong style="font-size: 14px;">{cal_year}년 {cal_month}월</strong>
                        <a href='#' id='gcal_next' style='color: #888; text-decoration: none; padding: 3px 8px; background: #2a2d3a; border-radius: 4px; font-weight: bold; font-size: 12px;'>&gt;</a>
                    </div>
                    <div style="display: grid; grid-template-columns: repeat(7, 1fr); text-align: center; gap: 3px; font-size: 11px; font-weight: bold; margin-bottom: 5px;">
                        <div style="color: #ff4b4b;">일</div>
                        <div style="color: #aaa;">월</div>
                        <div style="color: #aaa;">화</div>
                        <div style="color: #aaa;">수</div>
                        <div style="color: #aaa;">목</div>
                        <div style="color: #aaa;">금</div>
                        <div style="color: #4B89B5;">토</div>
                    </div>
                    <div style="display: grid; grid-template-columns: repeat(7, 1fr); text-align: center; gap: 3px; font-size: 11px;">
                """
                
                c = calendar.Calendar(firstweekday=6)
                for week in c.monthdatescalendar(cal_year, cal_month):
                    for day in week:
                        if day.month == cal_month:
                            bg_color = "transparent"
                            color = "white"
                            border = "1px solid transparent"
                            
                            if day == selected_date:
                                bg_color = "#FFD700"
                                color = "#111"
                            elif day.weekday() == 6:
                                color = "#ff4b4b"
                            elif day.weekday() == 5:
                                color = "#4B89B5"
                                
                            if day == today_kor and day != selected_date:
                                border = "1px solid #FFD700"
                                
                            if day > today_kor or day < min_date:
                                html_cal += f"<div style='padding: 4px; color: #444; border: {border}; border-radius: 4px;'>{day.day}</div>"
                            else:
                                html_cal += f"<a href='#' id='gcal_date_{day.strftime('%Y-%m-%d')}' style='padding: 4px; background: {bg_color}; color: {color}; border: {border}; text-decoration: none; border-radius: 4px; display: block; font-weight: bold;'>{day.day}</a>"
                        else:
                            html_cal += "<div></div>"
                            
                html_cal += "</div></div>"
                
                g_clicked = click_detector(html_cal, key=f"golden_cal_ui_{st.session_state.golden_cal_reset}")
            
            if g_clicked:
                if g_clicked == 'gcal_prev':
                    if st.session_state.golden_cal_month == 1:
                        st.session_state.golden_cal_month = 12
                        st.session_state.golden_cal_year -= 1
                    else:
                        st.session_state.golden_cal_month -= 1
                    st.session_state.golden_cal_reset += 1
                    st.rerun()
                elif g_clicked == 'gcal_next':
                    if st.session_state.golden_cal_month == 12:
                        st.session_state.golden_cal_month = 1
                        st.session_state.golden_cal_year += 1
                    else:
                        st.session_state.golden_cal_month += 1
                    st.session_state.golden_cal_reset += 1
                    st.rerun()
                elif g_clicked.startswith('gcal_date_'):
                    date_str = g_clicked.split('gcal_date_')[1]
                    st.session_state.golden_selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                    st.session_state.golden_cal_reset += 1
                    st.rerun()

            st.write("---")

            global_meta = get_global_stock_metadata()

            # 선택된 날짜 기준 최근 10일 수급 데이터 로딩
            sel_date_dt = datetime.combine(selected_date, datetime.min.time())
            start_date_str = (sel_date_dt - timedelta(days=14)).strftime("%Y-%m-%d")
            sel_date_str = selected_date.strftime("%Y-%m-%d")

            # 🔧 [수정 2026-07-30] 아래 네 개 쿼리(daily_whale_top200 x2, upper_limit_stocks, whale_log 페이지네이션)는
            # 선택 날짜(sel_date_str)가 안 바뀌면 결과가 똑같으므로 st.cache_data로 하루 캐싱된 함수를 통해 가져옴 —
            # 화면 안에서 AI 요약 보기/차트 이동 등 다른 버튼을 눌러도 이 무거운 조회가 매번 반복되지 않도록 함.
            # (캘린더에서 날짜를 바꾸면 sel_date_str/start_date_str이 달라지므로 자동으로 새로 조회됨.)
            with st.spinner(f"🚀 {selected_date.strftime('%Y년 %m월 %d일')} 기준 최정예 골든 픽 종목을 종합 분석 중입니다..."):
                base_data_gp = _fetch_golden_pick_base_data(sel_date_str, start_date_str)
                top_data_gp = base_data_gp["top_data"]

                if not top_data_gp:
                    st.warning("⚠️ 해당 날짜의 수급 데이터가 준비되지 않았습니다.")
                else:
                    df_latest_gp = pd.DataFrame(top_data_gp)
                    hist_data_gp = base_data_gp["hist_data"]
                    if hist_data_gp:
                        df_hist = pd.DataFrame(hist_data_gp)
                        all_dates = sorted(df_hist['trade_date'].unique(), reverse=True)
                        total_trading_days = len(all_dates) if all_dates else 1
                        appear_counts = df_hist.groupby('stock_code')['trade_date'].nunique().to_dict()
                    else:
                        total_trading_days = 1
                        appear_counts = {}

                    upper_names = set([r['name'] for r in base_data_gp["upper_data"]]) if base_data_gp["upper_data"] else set()

                    whale_realtime = {}

                    # 1. 14일치 DB 고래 수급 데이터 (캐시된 조회 결과 사용, 항상 반영하여 과거 14일 이내 고래 포착 여부 누적 반영)
                    try:
                        all_w_data = base_data_gp["whale_log_data"]
                        if all_w_data:
                            df_w_db = pd.DataFrame(all_w_data)
                            for code_val, group_val in df_w_db.groupby('code'):
                                c_code = str(code_val).strip().zfill(6)
                                b_sum = group_val[group_val['side'] == '매수']['amount_krw'].sum() / 1_000_000
                                s_sum = group_val[group_val['side'] == '매도']['amount_krw'].sum() / 1_000_000
                                whale_realtime[c_code] = (b_sum, s_sum)
                    except Exception:
                        pass

                    # 2. 당일 실시간 데이터(df)가 있으면 기존 DB 합산값에 누적 (당일 포착분 추가) — 이 부분은 캐시하지 않고
                    #    매번 그대로 반영해서, 캐시된 하루치 기준값 위에 "지금 이 순간"의 실시간 틱을 얹어줌.
                    if not df.empty and 'side' in df.columns and 'code' in df.columns:
                        for code_val, group_val in df.groupby('code'):
                            c_code = str(code_val).strip().zfill(6)
                            b_sum = group_val[group_val['side'] == '매수']['amount_krw'].sum() / 1_000_000
                            s_sum = group_val[group_val['side'] == '매도']['amount_krw'].sum() / 1_000_000
                            existing_b, existing_s = whale_realtime.get(c_code, (0, 0))
                            whale_realtime[c_code] = (existing_b + b_sum, existing_s + s_sum)

                    candidates = []
                    for _, r_val in df_latest_gp.iterrows():
                        name_str = r_val['stock_name']
                        clean_n = name_str.replace("🚀","").replace("👑","").replace("🔥","").replace("💥","").replace("✨","").replace("🌱","").strip()
                        code_str = r_val['stock_code']
                        market_str = r_val['market']
                        frgn_net = (r_val['frgn_buy'] - r_val['frgn_sell'])
                        orgn_net = (r_val['orgn_buy'] - r_val['orgn_sell'])
                        total_net = frgn_net + orgn_net

                        warning_text = get_warning_text(name_str, global_meta)
                        app_count = appear_counts.get(code_str, 0)

                        score = 25
                        reasons = []

                        # 🔧 [버그 수정 2026-07-29]: 이름(clean_n/name_str) 대신 종목코드로 조회 (whale_realtime도 code 기준으로 통일됨)
                        rt_buy, rt_sell = whale_realtime.get(str(code_str).strip().zfill(6), (0, 0))
                        # 🔧 [튜닝 2026-07-29] whale_realtime은 14일 구간 "합계"라서 그대로 쓰면 거래일이 쌓일수록
                        # 점수가 계속 부풀려짐. 실제 거래일수(total_trading_days)로 나눈 "일평균 고래매수"로 통일 (차트와 동일 기준).
                        rt_buy = rt_buy / total_trading_days
                        # 🔧 [튜닝 2026-07-29] 강세장에서 여러 종목이 동시에 100점 상한에 몰려 변별력이 사라지는 문제 수정.
                        # 기존 만점 총합(25+25+25+15+15+10+5=120, 100점 클리핑)을 실질 상한 82점대로 압축 (약 0.6배율, 차트와 동일하게 전 항목 적용).
                        # 🔧 [버그 수정 2026-07-29]: rt_buy는 "백만원" 단위라 "억원" 표시는 /100이 맞는데 /1000으로 10배 작게 표시되던 버그도 같이 수정.
                        if rt_buy >= 1000:
                            score += 15
                            reasons.append(f"🐋 고래매수 일평균 대량({rt_buy/100:.1f}억)")
                        elif rt_buy >= 100:
                            score += 9
                            reasons.append(f"🐋 고래매수 일평균 포착({rt_buy/100:.1f}억)")
                        elif rt_buy > 0:
                            score += 5
                            reasons.append("🐋 고래 소액 체결 포착")
                        else:
                            score -= 9
                            reasons.append("⚠️ 실시간 고래 포착 미흡")

                        if total_net >= 300:
                            score += 15
                        elif total_net >= 100:
                            score += 12
                        elif total_net >= 50:
                            score += 9
                        elif total_net >= 20:
                            score += 6
                        elif total_net > 0:
                            score += 2

                        if frgn_net > 0 and orgn_net > 0:
                            score += 9
                            reasons.append("🔥 외/기 동시 쌍끌이")
                        elif frgn_net < -100 or orgn_net < -100:
                            score -= 12
                            reasons.append("⚠️ 외인/기관 한쪽 대량 덤핑(-100억 이상)")

                        # 🔧 [버그 수정 2026-07-29]: DB 쿼리가 일시적으로 비어있으면(네트워크 지연 등) app_count=0,
                        # total_trading_days=1로 폴백되는데, "0 >= 1-1(=0)"이 참이 되어 실제로는 단 하루도
                        # TOP200에 출현하지 않은 종목에게 "수급 지속성 우수" 보너스가 잘못 부여되는 함정이 있었음
                        # (차트와 골든픽 화면이 같은 종목/같은 날짜인데도 점수가 다르게 나오던 원인 중 하나로 추정).
                        # app_count>0(실제로 최소 1일은 출현) 조건을 추가해 이 오탐을 차단 (차트 로직과 동일하게 통일).
                        if app_count >= total_trading_days:
                            score += 9
                            reasons.append(f"👑 {total_trading_days}일 연속 수급 장악")
                        elif app_count > 0 and app_count >= total_trading_days - 1:
                            score += 5
                            reasons.append("✨ 수급 지속성 우수")

                        if clean_n in upper_names or name_str in upper_names:
                            if app_count > 0 and app_count >= total_trading_days - 1:
                                score += 6
                                reasons.append("🚀 상한가 후 수급 유지")
                            else:
                                score -= 18
                                reasons.append("⚠️ 상한가 후 수급 이탈 이력")

                        if not warning_text:
                            score += 3
                        else:
                            score -= 9
                            reasons.append(f"🚨 {warning_text}")

                        if not reasons:
                            reasons.append("수급 순매수 우상향")

                        candidates.append({
                            "code": code_str,
                            "name": name_str,
                            "market": market_str,
                            "score": max(0, min(score, 100)),
                            "total_net": total_net,
                            "frgn_net": frgn_net,
                            "orgn_net": orgn_net,
                            "warning": warning_text if warning_text else "정상",
                            "rt_buy": round(rt_buy, 1),
                            "reason": " | ".join(reasons)
                        })

                    df_cand = pd.DataFrame(candidates)
                    if not df_cand.empty:
                        df_cand = df_cand.sort_values(by=["score", "total_net"], ascending=[False, False]).reset_index(drop=True)
                        top20_gp = df_cand.head(20).copy()
                        top20_gp.insert(0, "순위", range(1, len(top20_gp) + 1))

                        # 🌟 [신규 2026-07-30] 뉴스 감성점수 조인 (scripts/fetch_news_sentiment.py 배치가 채워주는 news_sentiment_daily)
                        # 아직 실험 단계 기능이라 실패해도 골든픽 화면 자체는 항상 정상 표출되도록 예외를 넓게 잡음
                        try:
                            codes_gp = top20_gp['code'].tolist()
                            sent_res = supabase.table("news_sentiment_daily").select("stock_code, trade_date, sentiment_score").in_("stock_code", codes_gp).order("trade_date", desc=True).execute()
                            sent_map = {}
                            if sent_res.data:
                                for r in sent_res.data:
                                    # 최신순 정렬이므로 종목당 가장 먼저 나오는 값(=가장 최근 날짜)만 채택
                                    if r['stock_code'] not in sent_map:
                                        sent_map[r['stock_code']] = r['sentiment_score']
                            top20_gp['news_sentiment'] = top20_gp['code'].map(sent_map)
                        except Exception:
                            top20_gp['news_sentiment'] = None

                        st.markdown("<h5 style='color:#FFD700; margin-top:15px;'>🥇 오늘의 TOP 3 골든 픽 명예의 전당</h5>", unsafe_allow_html=True)
                        c1_gp, c2_gp, c3_gp = st.columns(3)
                        medals = ["🥇 1위", "🥈 2위", "🥉 3위"]
                        colors = ["#FFD700", "#C0C0C0", "#CD7F32"]
                        cols_gp = [c1_gp, c2_gp, c3_gp]

                        for i in range(min(3, len(top20_gp))):
                            row_gp = top20_gp.iloc[i]
                            with cols_gp[i]:
                                st.markdown(f"""
                                <div style="background:#1a1c24; border: 2px solid {colors[i]}; border-radius:12px; padding:15px; box-shadow: 0 4px 10px rgba(0,0,0,0.5);">
                                    <div style="color:{colors[i]}; font-weight:bold; font-size:16px; margin-bottom:5px;">{medals[i]} {row_gp['name']}</div>
                                    <div style="font-size:24px; font-weight:900; color:#00E676; margin-bottom:8px;">{row_gp['score']}점 <span style="font-size:12px; color:#aaa;">/ 100점</span></div>
                                    <div style="font-size:13px; color:#ddd; margin-bottom:4px;">🏛️ 외/기 합산: <b>{row_gp['total_net']:,.0f}억 원</b></div>
                                    <div style="font-size:12px; color:#ff9800; margin-bottom:8px;">(외인 {row_gp['frgn_net']:,.0f}억 / 기관 {row_gp['orgn_net']:,.0f}억)</div>
                                    <div style="font-size:11px; color:#64B5F6; background:#12131c; padding:6px; border-radius:6px; min-height:38px;">💡 {row_gp['reason']}</div>
                                </div>
                                """, unsafe_allow_html=True)

                        st.markdown("<div style='margin-top: 25px;'></div>", unsafe_allow_html=True)
                        st.markdown("<h5 style='color:#FFFFFF;'>📋 골든 픽 TOP 20 전체 순위 전광판</h5>", unsafe_allow_html=True)
                        st.write("")
                        click_action_gp = st.radio(
                            "👇 표에서 종목(행)을 클릭했을 때 동작을 선택하세요:", 
                            ["📊 시계열 추적 (차트 이동)", "💬 AI 요약 보기 (팝업)"], 
                            horizontal=True,
                            key="gp_click_action_radio"
                        )

                        top20_key_gp = f"golden_pick_table_{st.session_state.get('gp_reset_counter', 0)}"

                        display_gp = top20_gp[['순위', 'name', 'market', 'score', 'warning', 'total_net', 'frgn_net', 'orgn_net', 'rt_buy', 'news_sentiment', 'reason']].copy()
                        display_gp = display_gp.rename(columns={
                            'name': '종목명', 'market': '시장', 'score': '황금점수',
                            'warning': '특이사항', 'total_net': '🟣외/기 순매수(억)',
                            'frgn_net': '🟣외국인 순매수(억)', 'orgn_net': '🟡기관 순매수(억)',
                            'rt_buy': '🐋고래매수 일평균(백만)', 'news_sentiment': '📰 뉴스감성',
                            'reason': '핵심 추천 포인트'
                        })

                        # 🌟 [신규 2026-07-30] 뉴스감성 점수 색상(호재=빨강/악재=파랑/중립=회색, 이 앱의 매수·매도 색 관례와 통일)
                        # 🔧 [수정 2026-07-30] font-size 시도는 반영이 안 되는 것으로 확인되어 제거.
                        #    대신 "🟡기관 순매수(억)" 컬럼처럼 Styler를 아예 안 씌운(스타일 없는 기본) 컬럼과 폰트가
                        #    똑같아 보이도록 color만 남기고 font-weight/font-size는 모두 제거함(컬러 로직은 그대로 유지).
                        def _get_sentiment_color(val):
                            if pd.isna(val):
                                return 'color: #777777;'
                            if val > 0:
                                return 'color: #ff4b4b;'
                            elif val < 0:
                                return 'color: #4B89B5;'
                            return 'color: #aaaaaa;'

                        styled_gp = display_gp.style.applymap(_get_sentiment_color, subset=['📰 뉴스감성'])

                        event_gp = st.dataframe(
                            styled_gp,
                            use_container_width=True,
                            hide_index=True,
                            height=580,
                            on_select="rerun",
                            selection_mode="single-row",
                            key=top20_key_gp,
                            column_config={
                                # 🔧 [수정 2026-07-30] 숫자 가독성을 위해 1000단위 콤마(,) 포맷 전면 적용
                                "순위": st.column_config.NumberColumn("순위", format="%,d위"),
                                "황금점수": st.column_config.NumberColumn("황금점수", format="%,d점"),
                                "🟣외/기 순매수(억)": st.column_config.NumberColumn(format="%,.0f억"),
                                "🟣외국인 순매수(억)": st.column_config.NumberColumn(format="%,.0f억"),
                                "🟡기관 순매수(억)": st.column_config.NumberColumn(format="%,.0f억"),
                                "🐋고래매수 일평균(백만)": st.column_config.NumberColumn(format="%,.0f백만"),
                                "📰 뉴스감성": st.column_config.NumberColumn(format="%+d", help="배치 스크립트(fetch_news_sentiment.py)가 매일 채워주는 실험적 뉴스 감성 점수 (-5~+5). 아직 데이터 없으면 빈칸."),
                            }
                        )

                        if event_gp and "selection" in event_gp:
                            rows_gp = event_gp["selection"]["rows"]
                            if rows_gp and rows_gp[0] < len(top20_gp):
                                selected_stock_gp = top20_gp.iloc[rows_gp[0]]['name']
                                clean_stock_gp = selected_stock_gp.replace(" 🚀", "").replace(" 👑", "").replace(" 🔥", "").replace(" 💥", "").replace(" ✨", "").replace(" 🌱", "").strip()
                                row_stock_code_gp = top20_gp.iloc[rows_gp[0]]['code']

                                if click_action_gp == "💬 AI 요약 보기 (팝업)":
                                    trigger_gp = st.session_state.get('dialog_trigger_id', 0) + 1
                                    st.session_state['dialog_trigger_id'] = trigger_gp
                                    st.session_state['show_summary_dialog'] = {
                                        "stock": clean_stock_gp,
                                        "code": row_stock_code_gp,
                                        "trigger_id": trigger_gp
                                    }
                                    st.session_state['gp_reset_counter'] = st.session_state.get('gp_reset_counter', 0) + 1
                                    st.rerun()
                                else:
                                    st.session_state['pending_search'] = clean_stock_gp
                                    st.session_state['last_search_keyword'] = ""
                                    st.session_state['df_reset_counter'] = st.session_state.get('df_reset_counter', 0) + 1
                                    st.session_state['scrn_select_radio'] = "체결 로그"
                                    st.rerun()

        elif scrn_select == "내 관심종목":
            st.markdown("<h4 style='color:#2E8B57; border-left: 4px solid #2E8B57; padding-left: 10px;'>⭐ 내 관심종목</h4>", unsafe_allow_html=True)
            st.caption("관심 있는 종목을 등록해두면 오늘자 골든점수·외/기 수급·뉴스감성을 한눈에 모아볼 수 있습니다.")

            watch_username = st.session_state.get('username', '')

            if 'watch_input_reset_counter' not in st.session_state:
                st.session_state['watch_input_reset_counter'] = 0

            add_col1, add_col2 = st.columns([3, 1])
            with add_col1:
                new_watch_input = st.text_input(
                    "종목명 또는 종목코드 입력 후 추가",
                    key=f"watch_add_input_{st.session_state['watch_input_reset_counter']}",
                    placeholder="예: 삼성전자 또는 005930"
                )
            with add_col2:
                st.write("")
                st.write("")
                st.markdown('<div class="btn-style-align-up"></div>', unsafe_allow_html=True)
                add_watch_clicked = st.button("➕ 추가", key="watch_add_btn", use_container_width=True)

            if add_watch_clicked:
                if not new_watch_input.strip():
                    st.warning("⚠️ 종목명 또는 종목코드를 입력해주세요.")
                else:
                    try:
                        krx_df_w = get_cached_krx_listing()
                        query_str_w = new_watch_input.strip()
                        match_w = krx_df_w[krx_df_w['Code'] == query_str_w.zfill(6)]
                        if match_w.empty:
                            match_w = krx_df_w[krx_df_w['Name'] == query_str_w]
                        if match_w.empty:
                            match_w = krx_df_w[krx_df_w['Name'].str.contains(query_str_w, case=False, na=False)]

                        if match_w.empty:
                            st.warning(f"⚠️ '{query_str_w}'에 해당하는 종목을 찾을 수 없습니다.")
                        else:
                            if len(match_w) > 1:
                                st.info(f"🔍 '{query_str_w}'로 검색된 종목이 여러 개라 첫 번째 결과({match_w.iloc[0]['Name']})를 추가합니다. 정확한 종목명으로 다시 검색해보시면 원하는 종목을 콕 집어 추가할 수 있어요.")
                            row_match_w = match_w.iloc[0]
                            match_code_w = str(row_match_w['Code']).strip().zfill(6)
                            match_name_w = str(row_match_w['Name']).strip()

                            supabase.table("user_watchlist").upsert({
                                "username": watch_username,
                                "stock_code": match_code_w,
                                "stock_name": match_name_w,
                            }, on_conflict="username,stock_code").execute()
                            st.success(f"✅ '{match_name_w}' 관심종목에 추가되었습니다.")
                            st.session_state['watch_input_reset_counter'] += 1
                            st.rerun()
                    except Exception as e:
                        st.error(f"추가 중 오류가 발생했습니다: {e}")

            st.write("---")

            try:
                watch_res = supabase.table("user_watchlist").select("*").eq("username", watch_username).order("created_at", desc=True).execute()
                watch_list = watch_res.data if watch_res.data else []
            except Exception:
                watch_list = []

            if not watch_list:
                st.info("아직 등록된 관심종목이 없습니다. 위에서 종목을 추가해보세요.")
            else:
                watch_codes = [w['stock_code'] for w in watch_list]
                watch_names = [w['stock_name'] for w in watch_list]

                today_watch = get_latest_market_open_date()
                today_watch_str = today_watch.strftime("%Y-%m-%d")
                start_watch_str = (today_watch - timedelta(days=14)).strftime("%Y-%m-%d")

                with st.spinner("⭐ 관심종목의 오늘자 골든점수를 계산하는 중입니다..."):
                    # 🔧 [신규 2026-07-30] 아래 골든점수 계산은 "고래 골든픽" 화면(~4260줄 부근)의 배점 공식을
                    # 관심종목(임의의 종목 리스트)에 맞게 그대로 옮겨온 것 — 세 번째 복제본이라는 점을 인지하고 있음.
                    # ⚠️ 향후 배점 공식을 조정할 때는 차트(draw_whale_bar_chart)/골든픽 화면/이 화면 3곳을 모두 맞춰야 함
                    # (공용 함수로 합치는 리팩터링은 추후 과제로 남겨둠 — 기존 화면들을 건드리는 리스크를 피하기 위함).
                    global_meta_w = get_global_stock_metadata()

                    try:
                        today_res_w = supabase.table("daily_whale_top200").select("*").eq("trade_date", today_watch_str).in_("stock_code", watch_codes).execute()
                        today_map_w = {r['stock_code']: r for r in today_res_w.data} if today_res_w.data else {}
                    except Exception:
                        today_map_w = {}

                    try:
                        hist_res_w = supabase.table("daily_whale_top200").select("trade_date").gte("trade_date", start_watch_str).lte("trade_date", today_watch_str).execute()
                        all_dates_w = sorted(set(r['trade_date'] for r in hist_res_w.data)) if hist_res_w.data else []
                        total_trading_days_w = len(all_dates_w) if all_dates_w else 1
                    except Exception:
                        total_trading_days_w = 1

                    try:
                        appear_res_w = supabase.table("daily_whale_top200").select("stock_code, trade_date").gte("trade_date", start_watch_str).lte("trade_date", today_watch_str).in_("stock_code", watch_codes).execute()
                        appear_counts_w = {}
                        if appear_res_w.data:
                            df_appear_w = pd.DataFrame(appear_res_w.data)
                            appear_counts_w = df_appear_w.groupby('stock_code')['trade_date'].nunique().to_dict()
                    except Exception:
                        appear_counts_w = {}

                    try:
                        upper_res_w = supabase.table("upper_limit_stocks").select("name").gte("recorded_date", start_watch_str).lte("recorded_date", today_watch_str).in_("name", watch_names).execute()
                        upper_names_w = set(r['name'] for r in upper_res_w.data) if upper_res_w.data else set()
                    except Exception:
                        upper_names_w = set()

                    whale_realtime_w = {}
                    try:
                        w_res_w = supabase.table("whale_log").select("code, side, amount_krw").gte("date", start_watch_str).lte("date", today_watch_str).in_("code", watch_codes).execute()
                        if w_res_w.data:
                            df_w_watch = pd.DataFrame(w_res_w.data)
                            for code_val_w, group_val_w in df_w_watch.groupby('code'):
                                c_code_w = str(code_val_w).strip().zfill(6)
                                whale_realtime_w[c_code_w] = group_val_w[group_val_w['side'] == '매수']['amount_krw'].sum() / 1_000_000
                    except Exception:
                        pass

                    try:
                        sent_res_w = supabase.table("news_sentiment_daily").select("stock_code, trade_date, sentiment_score").in_("stock_code", watch_codes).order("trade_date", desc=True).execute()
                        sent_map_w = {}
                        if sent_res_w.data:
                            for r in sent_res_w.data:
                                if r['stock_code'] not in sent_map_w:
                                    sent_map_w[r['stock_code']] = r['sentiment_score']
                    except Exception:
                        sent_map_w = {}

                rows_watch = []
                for w in watch_list:
                    code_w = w['stock_code']
                    name_w = w['stock_name']
                    td_w = today_map_w.get(code_w)
                    in_top200_today = td_w is not None

                    if td_w:
                        frgn_net_w = td_w['frgn_buy'] - td_w['frgn_sell']
                        orgn_net_w = td_w['orgn_buy'] - td_w['orgn_sell']
                    else:
                        frgn_net_w = 0.0
                        orgn_net_w = 0.0
                    total_net_w = frgn_net_w + orgn_net_w

                    rt_buy_w = whale_realtime_w.get(code_w, 0.0) / total_trading_days_w
                    app_count_w = appear_counts_w.get(code_w, 0)
                    warning_text_w = get_warning_text(name_w, global_meta_w)

                    score_w = 25
                    reasons_w = []

                    if rt_buy_w >= 1000:
                        score_w += 15
                        reasons_w.append(f"🐋 고래매수 일평균 대량({rt_buy_w/100:.1f}억)")
                    elif rt_buy_w >= 100:
                        score_w += 9
                        reasons_w.append(f"🐋 고래매수 일평균 포착({rt_buy_w/100:.1f}억)")
                    elif rt_buy_w > 0:
                        score_w += 5
                        reasons_w.append("🐋 고래 소액 체결 포착")
                    else:
                        score_w -= 9
                        reasons_w.append("⚠️ 실시간 고래 포착 미흡")

                    if total_net_w >= 300:
                        score_w += 15
                    elif total_net_w >= 100:
                        score_w += 12
                    elif total_net_w >= 50:
                        score_w += 9
                    elif total_net_w >= 20:
                        score_w += 6
                    elif total_net_w > 0:
                        score_w += 2

                    if frgn_net_w > 0 and orgn_net_w > 0:
                        score_w += 9
                        reasons_w.append("🔥 외/기 동시 쌍끌이")
                    elif frgn_net_w < -100 or orgn_net_w < -100:
                        score_w -= 12
                        reasons_w.append("⚠️ 외인/기관 한쪽 대량 덤핑(-100억 이상)")

                    if app_count_w >= total_trading_days_w:
                        score_w += 9
                        reasons_w.append(f"👑 {total_trading_days_w}일 연속 수급 장악")
                    elif app_count_w > 0 and app_count_w >= total_trading_days_w - 1:
                        score_w += 5
                        reasons_w.append("✨ 수급 지속성 우수")

                    if name_w in upper_names_w:
                        if app_count_w > 0 and app_count_w >= total_trading_days_w - 1:
                            score_w += 6
                            reasons_w.append("🚀 상한가 후 수급 유지")
                        else:
                            score_w -= 18
                            reasons_w.append("⚠️ 상한가 후 수급 이탈 이력")

                    if not warning_text_w:
                        score_w += 3
                    else:
                        score_w -= 9
                        reasons_w.append(f"🚨 {warning_text_w}")

                    if not reasons_w:
                        reasons_w.append("수급 순매수 우상향")

                    score_w = max(0, min(score_w, 100))

                    rows_watch.append({
                        "종목명": name_w,
                        "코드": code_w,
                        "골든점수": score_w,
                        "오늘 TOP200": "✅" if in_top200_today else "❌",
                        "🟣외/기 순매수(억)": total_net_w,
                        "🟣외국인 순매수(억)": frgn_net_w,
                        "🟡기관 순매수(억)": orgn_net_w,
                        "📰 뉴스감성": sent_map_w.get(code_w),
                        "핵심 포인트": " | ".join(reasons_w),
                    })

                df_watch = pd.DataFrame(rows_watch).sort_values(by="골든점수", ascending=False).reset_index(drop=True)
                st.caption("⚠️ '오늘 TOP200'이 ❌인 종목은 외국인/기관 순매수 TOP 100(코스피)+TOP 100(코스닥)에 들지 못해 외/기 수급이 0으로 처리된 상태입니다 (골든점수가 실제보다 낮게 나올 수 있음).")

                # 🌟 [신규 2026-07-30] "고래 골든픽" 화면과 동일하게 뉴스감성 점수에 색상 적용
                # (호재=빨강/악재=파랑/중립=회색). 골든픽 화면의 _get_sentiment_color와 동일 로직이지만
                # 서로 다른 elif 분기(화면)라 세션 내에서 공유되지 않아 이 화면에도 동일 함수를 둠.
                def _get_sentiment_color_watch(val):
                    if pd.isna(val):
                        return 'color: #777777;'
                    if val > 0:
                        return 'color: #ff4b4b;'
                    elif val < 0:
                        return 'color: #4B89B5;'
                    return 'color: #aaaaaa;'

                styled_watch = df_watch.style.applymap(_get_sentiment_color_watch, subset=['📰 뉴스감성'])

                st.markdown('<div class="no-header-icon"></div>', unsafe_allow_html=True)
                st.dataframe(
                    styled_watch,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "골든점수": st.column_config.NumberColumn("골든점수", format="%,d점"),
                        "🟣외/기 순매수(억)": st.column_config.NumberColumn(format="%,.0f억"),
                        "🟣외국인 순매수(억)": st.column_config.NumberColumn(format="%,.0f억"),
                        "🟡기관 순매수(억)": st.column_config.NumberColumn(format="%,.0f억"),
                        "📰 뉴스감성": st.column_config.NumberColumn(format="%+d"),
                    }
                )

                st.write("---")
                st.markdown("<div style='font-size:13px; color:#aaa; margin-bottom:6px;'>🗑️ 관심종목 삭제</div>", unsafe_allow_html=True)
                del_cols = st.columns(4)
                for idx_w, w in enumerate(watch_list):
                    with del_cols[idx_w % 4]:
                        if st.button(f"❌ {w['stock_name']}", key=f"watch_del_{w['stock_code']}", use_container_width=True):
                            try:
                                supabase.table("user_watchlist").delete().eq("username", watch_username).eq("stock_code", w['stock_code']).execute()
                                st.rerun()
                            except Exception as e:
                                st.error(f"삭제 실패: {e}")

        elif scrn_select == "테마 랭킹":
            st.markdown("<h4 style='color:#FFD400; border-left: 4px solid #FFD400; padding-left: 10px;'>👑 테마킹 - 오늘의 테마 모멘텀 랭킹</h4>", unsafe_allow_html=True)
            st.caption("오늘 외국인/기관 순매수 TOP 100(코스피)+TOP 100(코스닥)에 오른 종목들을 테마별로 묶어, 어떤 테마에 수급이 몰리고 있는지 보여줍니다.")
            st.caption("⚠️ 테마 매핑 데이터가 현재 약 100개 종목에 한해 등록되어 있어, 테마 매핑이 없는 종목은 집계에서 빠질 수 있습니다.")

            today_theme = get_latest_market_open_date()
            today_theme_str = today_theme.strftime("%Y-%m-%d")

            with st.spinner("🏷️ 오늘의 테마 모멘텀을 집계하는 중입니다..."):
                try:
                    theme_top_res = supabase.table("daily_whale_top200").select("*").eq("trade_date", today_theme_str).execute()
                    df_theme_top = pd.DataFrame(theme_top_res.data) if theme_top_res.data else pd.DataFrame()
                except Exception:
                    df_theme_top = pd.DataFrame()

            if df_theme_top.empty:
                st.warning("⚠️ 오늘자 수급 데이터가 아직 준비되지 않았습니다.")
            else:
                df_theme_top['frgn_net'] = df_theme_top['frgn_buy'] - df_theme_top['frgn_sell']
                df_theme_top['orgn_net'] = df_theme_top['orgn_buy'] - df_theme_top['orgn_sell']
                df_theme_top['total_net'] = df_theme_top['frgn_net'] + df_theme_top['orgn_net']

                theme_map_today = get_themes_for_stocks(df_theme_top['stock_name'].tolist())

                theme_agg = {}
                for _, r_t in df_theme_top.iterrows():
                    theme_str_t = theme_map_today.get(r_t['stock_name'], "")
                    if not theme_str_t:
                        continue
                    for t_name in [t.strip() for t in theme_str_t.split(',') if t.strip()]:
                        if t_name not in theme_agg:
                            theme_agg[t_name] = {"total_net": 0.0, "stocks": []}
                        theme_agg[t_name]["total_net"] += r_t['total_net']
                        theme_agg[t_name]["stocks"].append((r_t['stock_name'], r_t['total_net']))

                if not theme_agg:
                    st.info("오늘 TOP 200 종목 중 테마 매핑이 확인된 종목이 없습니다.")
                else:
                    theme_rows = []
                    for t_name, info_t in theme_agg.items():
                        top_stocks_t = sorted(info_t["stocks"], key=lambda x: x[1], reverse=True)[:3]
                        top_stocks_str_t = ", ".join([f"{n}({v:,.0f}억)" for n, v in top_stocks_t])
                        theme_rows.append({
                            "테마명": t_name,
                            "종목수": len(info_t["stocks"]),
                            "합산 외/기 순매수(억)": info_t["total_net"],
                            "대표 종목": top_stocks_str_t,
                        })

                    df_theme_rank = pd.DataFrame(theme_rows).sort_values(by="합산 외/기 순매수(억)", ascending=False).reset_index(drop=True)
                    df_theme_rank.insert(0, "순위", df_theme_rank.index + 1)

                    st.dataframe(
                        df_theme_rank,
                        use_container_width=True,
                        hide_index=True,
                        height=600,
                        column_config={
                            "순위": st.column_config.NumberColumn("순위", format="%,d위"),
                            "합산 외/기 순매수(억)": st.column_config.NumberColumn(format="%,.0f억"),
                        }
                    )

        elif scrn_select == "상선고 화면":
            st.markdown("<h4 style='color:#FF8C00; border-left: 4px solid #FF8C00; padding-left: 10px;'>📡 상한가 선행 고래 포착 레이더 (상선고)</h4>", unsafe_allow_html=True)
            
            today_date = datetime.utcnow() + timedelta(hours=9)
            month_options = []
            for i in range(12):
                m_date = today_date.replace(day=1) - timedelta(days=28 * i)
                m_date = m_date.replace(day=1)
                month_options.append(m_date.strftime("%Y년 %m월"))
                
            radar_col1, radar_col2, radar_col3, radar_col4, radar_col_btn = st.columns([1.5, 1.3, 2.0, 1.5, 1.2])
            with radar_col1:
                radar_month = st.selectbox("📅 조회할 월 선택", month_options, key="radar_month")
            with radar_col2:
                radar_week = st.selectbox("📆 주차 선택", ["월 전체", "이전 30일", "1주차", "2주차", "3주차", "4주차", "5주차"], index=1, key="radar_week")
            with radar_col3:
                radar_filter = st.selectbox("🎯 종목 필터", ["순수 개별종목 (우선주/ETF 제외)", "전체 종목 포함"], key="radar_filter")
            with radar_col4:
                radar_cell_format = st.selectbox("🔠 셀 표시형식", ["크기와 금액", "금액"], index=1, key="radar_cell_format")
            
            with radar_col_btn:
                st.html("""
                <div class="radar-search-btn" style="display:none;"></div>
                <style>
                    div.element-container:has(.radar-search-btn) {
                        display: none !important;
                        margin: 0 !important;
                        padding: 0 !important;
                    }
                    div.element-container:has(.radar-search-btn) + div.element-container {
                        margin-top: 28px !important;
                    }
                    div.element-container:has(.radar-search-btn) + div.element-container button {
                        background-color: #FF8C00 !important; 
                        color: white !important; 
                        border-color: #E67E22 !important;
                    }
                </style>
                """)
                do_radar = st.button("🚀 레이더 가동", use_container_width=True)

            if do_radar:
                st.session_state['radar_active'] = True
                # last_mock_clicked 초기화 삭제 (새로고침/재가동 시 무한 팝업 버그 방지)

            if st.session_state.get('radar_active'):
                with st.spinner("🚀 상한가 선행 고래 데이터를 분석 중입니다..."):
                    yyyy = int(radar_month[:4])
                    mm = int(radar_month[6:8])
                    first_day = datetime(yyyy, mm, 1)
                    if mm == 12:
                        last_day = datetime(yyyy + 1, 1, 1) - timedelta(days=1)
                    else:
                        last_day = datetime(yyyy, mm + 1, 1) - timedelta(days=1)
                        
                    if radar_week == "월 전체":
                        start_dt = first_day
                        end_dt = last_day
                    elif radar_week == "이전 30일":
                        today = datetime.utcnow() + timedelta(hours=9)
                        start_dt = (today - timedelta(days=29)).replace(hour=0, minute=0, second=0, microsecond=0)
                        end_dt = today.replace(hour=23, minute=59, second=59, microsecond=999999)
                    else:
                        week_num = int(radar_week[0])
                        first_weekday = first_day.weekday()
                        if first_weekday <= 4:
                            w1_monday = first_day - timedelta(days=first_weekday)
                        else:
                            w1_monday = first_day + timedelta(days=(7 - first_weekday))
                            
                        target_monday = w1_monday + timedelta(weeks=week_num - 1)
                        target_friday = target_monday + timedelta(days=4)
                        
                        start_dt = target_monday
                        end_dt = target_friday
                        
                    latest_date = get_latest_market_open_date()
                    if start_dt.date() > latest_date:
                        st.warning("선택하신 기간은 아직 도래하지 않았습니다.")
                        st.stop()
                        
                    if end_dt.date() > latest_date:
                        end_dt = datetime.combine(latest_date, datetime.max.time())
                        
                    str_start = start_dt.strftime('%Y-%m-%d')
                    str_end = end_dt.strftime('%Y-%m-%d')
                    
                    # 1. 영업일 목록 생성 (휴장일 제외)
                    all_days = pd.bdate_range(start=str_start, end=str_end).strftime('%Y-%m-%d').tolist()
                    holidays = get_market_holidays()
                    trading_days = [d for d in all_days if d not in holidays]
                    
                    # 2. 해당 월의 상한가 종목 쿼리
                    upper_res = supabase.table("upper_limit_stocks").select("*").gte("recorded_date", str_start).lte("recorded_date", str_end).execute()
                    
                    if not upper_res.data:
                        st.warning("선택하신 월에 상한가 종목 데이터가 없습니다.")
                    else:
                        upper_df = pd.DataFrame(upper_res.data)
                        
                        if radar_filter == "순수 개별종목 (우선주/ETF 제외)":
                            pure_codes_set = get_pure_stock_codes()
                            if pure_codes_set is not None:
                                upper_df = upper_df[upper_df['code'].isin(pure_codes_set)]
                            else:
                                import re
                                def is_pure_stock(name):
                                    if pd.isna(name): return False
                                    if re.search(r'우$|우B$|우\([A-Za-z0-9]+\)$|우[A-Z]$', name): return False
                                    if re.search(r'KODEX|TIGER|KINDEX|KBSTAR|ARIRANG|KOSEF|HANARO|ACE|SOL|TIMEFOLIO|히어로즈|스팩|ETN|제\d+호|PLUS|RISE|WON|1Q|KIWOOM|TRUE|QV|선물|콜|풋|옵션', name, re.IGNORECASE): return False
                                    return True
                                upper_df['is_pure'] = upper_df['name'].apply(is_pure_stock)
                                upper_df = upper_df[upper_df['is_pure'] == True]

                        if upper_df.empty:
                            st.warning("조건에 맞는 상한가 종목이 없습니다 (필터링됨).")
                            stock_names = []
                        else:
                            # 종목별로 상한가 날짜들을 모두 리스트로 수집 (중복 상한가 허용)
                            upper_grouped = upper_df.groupby('name')['recorded_date'].apply(list).reset_index()
                            # 상한가 횟수 기준으로 내림차순 정렬 추가
                            upper_grouped['upper_cnt'] = upper_grouped['recorded_date'].apply(len)
                            upper_grouped = upper_grouped.sort_values(by='upper_cnt', ascending=False).reset_index(drop=True)
                            
                            stock_names = upper_grouped['name'].tolist()
                        
                        # 3. 고래 체결 내역 쿼리 (페이징 & 청크 처리)
                        all_whale = []
                        chunk_size = 30
                        for i in range(0, len(stock_names), chunk_size):
                            chunk = stock_names[i:i + chunk_size]
                            page_size = 1000
                            start_idx = 0
                            while True:
                                res = supabase.table("whale_log").select("date, time, name, side, amount_krw").gte("date", str_start).lte("date", str_end).in_("name", chunk).range(start_idx, start_idx + page_size - 1).execute()
                                data = res.data
                                all_whale.extend(data)
                                if len(data) < page_size:
                                    break
                                start_idx += page_size
                        whale_df = pd.DataFrame(all_whale)
                        daily_whale = {}
                        if not whale_df.empty:
                            whale_df = whale_df[whale_df['side'] == '매수'].copy()
                            whale_df['amount_krw'] = pd.to_numeric(whale_df['amount_krw'], errors='coerce').fillna(0)
                            grouped = whale_df.groupby(['name', 'date']).agg(
                                amount_krw=('amount_krw', 'sum'),
                                cnt=('amount_krw', 'count')
                            ).reset_index()
                            for _, row in grouped.iterrows():
                                if row['name'] not in daily_whale:
                                    daily_whale[row['name']] = {}
                                daily_whale[row['name']][row['date']] = {'amt': row['amount_krw'], 'cnt': row['cnt']}
                        
                        # 5. HTML/SVG 표 렌더링 준비
                        html_parts = []
                        html_parts.append(f"""
                        <div style="overflow-x: auto; margin-top: 20px; background-color: #1E1E1E; padding: 15px; border-radius: 10px;">
                            <table style="width: 100%; border-collapse: collapse; color: white; text-align: center; font-size: 13px; table-layout: fixed;">
                                <thead>
                                    <tr>
                                        <th style="width: 120px; border-bottom: 2px solid #555; padding: 5px;">종목명 (상한가일)</th>
                        """)
                        # 헤더 생성
                        for d in trading_days:
                            day_str = d[-2:] # "01", "15" 등
                            html_parts.append(f'<th style="width: 40px; border-bottom: 2px solid #555; padding: 5px;">{day_str}일</th>')
                        html_parts.append("""
                                    </tr>
                                </thead>
                                <tbody>
                        """)
                        
                        # 종목별 행 생성
                        import math
                        for _, row in upper_grouped.iterrows():
                            stock = row['name']
                            u_dates = row['recorded_date']
                            
                            # (절대 금액 5단계 평가를 위해 max_amt 계산은 제거)
                                
                            # 여러 번 상한가를 간 경우 표시 방법 변경
                            u_dates_sorted = sorted(u_dates)
                            if len(u_dates_sorted) > 1:
                                badge = f"({len(u_dates_sorted)}회)"
                            else:
                                badge = f"({u_dates_sorted[0][-5:]})"
                                
                            # 고유 렌더링 ID 생성 (반복 클릭 감지용, 매번 바뀌면 전체가 깜빡이므로 클릭 시에만 변경)
                            render_id = str(st.session_state.get('sangseongo_reset', 0))
                            
                            html_parts.append(f"""
                                    <tr>
                                        <td style="border-bottom: 1px solid #333; padding: 8px; font-weight: normal; font-size: 15px; text-align: left; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="{stock}">
                                            <a href="javascript:void(0);" id="goto___{stock}___{render_id}" style="text-decoration: none; margin-right: 6px; font-size: 16px; color: #888;" title="{stock} 시계열 추적 화면으로 이동">☐</a>
                                            <a href="javascript:void(0);" id="summary___{stock}___{render_id}" style="text-decoration: none; margin-right: 6px; font-size: 16px; color: #4b8bff;" title="{stock} 기업 요약(AI) 보기">💬</a>
                                            {stock} <span style="color:#FF4B4B; font-size:12px;">{badge}</span>
                                        </td>
                            """)
                            
                            for d in trading_days:
                                cell_bg = "rgba(230, 30, 30, 0.45)" if d in u_dates else "transparent"
                                border_style = "border-bottom: 1px solid #333; border-right: 1px solid #333;"
                                
                                amt = 0
                                cnt = 0
                                if stock in daily_whale and d in daily_whale[stock]:
                                    amt = daily_whale[stock][d]['amt']
                                    cnt = daily_whale[stock][d]['cnt']
                                    
                                inner_html = ""
                                if d in u_dates:
                                    img_b64 = "iVBORw0KGgoAAAANSUhEUgAAADAAAAAwCAYAAABXAvmHAAAIKUlEQVR42u2Zf2yVVxnHP885772UH6Ut7b39AaZkbqBrxCjGP5wRYUOIOMBM6h/LtjDYWJhODdk/M/O2RE0Ws0TjVigwui10SJERgUwdiUUlWWKsClJMYMggDii0FChtoe/7nsc/7g9uaXvpLZ0S5UlO7s1933vOeZ7n+/w43wN35a78f4uM52QKQgKhBqEd4cupBweAGpR2VOpxd5wVtAWrCbxRv5/A0wTmv+4BbcFKLeGg37ZVVOPcLJAZIMWEGmK1yw/c6YjIcVl54VyWIoYa5OY5PnIFNIGhDhVBAbQp9oAz5nEjsoSITMcAAwoBCghRwBPwgdAdB36Fc82y8sLfAFQxcGO+j1SBbKtrU3w5nqlnsplDj7sM+g6OdwnDQ6g5g4R99KpQRCFhZAZGPoPoIoRFTDITXb/7o/HDF2VV5+9H8ui4KqAJPKkn0FeKqymeuJGpZjHdwd9Rfoh27JGVXBvVPFtKC7HmEYz5PlPtvVwNmznf/5ysu3IxXyUk781vjD/IVLsb1SjXda082bE12zu0I9Th2ISFuUAblKQyTztCDZrxIAivlz9L1Pwc9EOu+Mvlma4/p9cavyyTyjDaGHtEd1WpNpe36YaimSn8irZgNR9jKKIJvPR/tKF0tr5V2a47KkPdGH8wY4zxSpEAuiG+UN+uUm0u368JJgFo69DUqZrclN8UX67bK7+j2yse0y0V1dnPBr2fmkOfLy3U5oqDuqMy1A3TPj9aJcwts80KnG6pqKbYvk1f+FfOdSyVevq0BSvzh3FzXXKTntgXmGJ/SqH3JtZ9I1XQhmxI5hNoC1Z+0tXDGV1EoEcpmrBPGyvLaEdvVS9yF5M6EEGx+iao7e8cWC7r6B9doMklelzAVRcQci5TkYd7s5ZQW7DyfEcv5/sfxlBERF+Tehw1uaFpcqZLwelr5bXEvC9xJfjWpO92n9ZWvNFlCbUIXnKYW0JBagm1FU++d/kDLoXfJmaXalNscVq5/D2wAqcJPDx5iU7/qKzp3DoibEaR6BSEs4gyeAx6dX7KE8+c38TF8DiYlxWE9pELnMlhfWVm7CFK7EycW59Jg2MRgwoo3Tgh+T09blJVM2sEbj0l9n42lX1R6nEjeeEWDZVZxaXwKn5kbyomwrx60/SnU09b53l8tTqirfM8bZ3naePciCbmecPEXXKNiOymJ+zDs6tzGc8M1xJLLaE2EgFZhO/elTVn+zJeyQc6RuCahlj5MaeOtSMDhzh1rN2dOtZOwdnDzD52RDeXzc3qhxBBtQUrj3f04uvvgCXagpV6guFqzVAPJFIvRUs/TqEUYtivIMTGBh8XApNtBSV2VnqYEjuLIvMJpnmzA0s5ADuz5o+l40N+yxRbSk+8etDesmSoC9Npy3n3YkRRPSygeiH/ThEFExWhN/gNVzmKiEFVnYIRo0TAs5Ej6aSR+d+FZHyoCQ9jrSJ6H/DP4VLqUAXSWBOZjq+CDpxL/T4mBYiK4ZrbIqsv7MoJuGx4ptcKoh2ECGqqRoqDoRBKHwPVTSFQ6Pf7bvecGYqZqq142kSBtuINGpoLmn3XcArWTB60t5weuBGDAUYgWuDB7elgkVDmE2gCZGUedSQaiWAE0IGRKvlQDxzIQmJUIGLL0m3F2CXPE2Ma674pxQIu6Bx9IatJ4c/I+wgg8smUAuZ2fJCXZLAus5MJRU8O2ltOCKWzQRD8g6sS4FgIbB9Cn7RiR2jOjCZwCKlCK2DUpM4UniZG2HQ94c2VGWE+V0OfqD02JFONpIAIqooR6eoJt1YcxMoybSFKLf6gkn+Lnkib1EdMsvSErid1whod/uuTjR2n9GuEelCePN+bKqTh6II4CRdnxG2hNLKNzvhi4fwebZwbkTVtvm6OlzNBfoDDQ1CGZBIHcD++OkTBk7Xh6+VfSamjWRZOukj1OpGChDx6ulsbibCGgBOxBcS9Mi76W3O1Et6IFgBhwO6mO+wCqQP2ZJ5HpJqSyFrCHKfqfpeKXYHCyALjyYJh64Qk+wguXW8EumEuQpuqtQkuh5cwsju9p1ErIKT6kdqzfcHm2It2+oQG3RxbKU+1NakibA4vcVHex2FA1SFiJGl3c+NsaTPqDUhIVqFymdBAU7HiIwM9qohIm6+b4l8nbr/AWX+drD7fm+uQLzl5TkWoA+6peI8J8imuuBp5uuOkJjBUYbk2PvQgBTjOEEo9ThsmxymZetT5rtMUdMyhnSCbRMufgQN0Q9l9+ovKPm2uPKSJ2JTsZ+NCHKRiSBNEdVvFH3RnlerG0s+NCzuRYSVeLVuiu6erbis/oC+VFiZpFiKqQ09Zox6KJNt20JeZqNsq9um+6aqNsSfGl1pJ80Kby76pu6pU36o8rA2lswexzZoHL0SKS0pbviF+jzaX/0n3Tld9LfZs9prjz8w1THuI4uhOVIrw3XOc7GhIc/4ZZg4cdTdhNkm3mGxmLlkvylcRlVcR8ej1H5WnOnfkw8yNjRv92bQZlERfodgu43J4AtUfMRD8UlZ39YxqniYK8MqXgrxAif003cF79Aw8LWu7j+RLK94mO122BGvXU2g/S4/rB/bh9NeE7i8UeB9y7mwvH5sB3eFkJroKVOeAWYiwjCJbwuXwAzSskycuvPEfYaczp84Epg7IQKcp9gDWPAbyMFGpQoABIHA+ihAxHtFkn0K/u+LQ/UaCN9jb9Y7sTBkjgRnL9dNt39CwApedo7WpaCYSnQUyE5VinDOIvYJx/0KC40y8eEJqGch1y3Pn35G1YPNltO+YW8oxV9W7clfuyv+m/Bs2lfaVP2FA8QAAAABJRU5ErkJggg=="
                                    inner_html += f'<div style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); opacity: 1.0; pointer-events: none; z-index: 1;"><img src="data:image/png;base64,{img_b64}" width="35" height="35" /></div>'
                                    
                                if amt >= 10_000_000:
                                    # 1천만원(0.1억) 이상일 경우 표시
                                    if amt >= 1_000_000_000:
                                        level = 5
                                    elif amt >= 500_000_000:
                                        level = 4
                                    elif amt >= 200_000_000:
                                        level = 3
                                    elif amt >= 100_000_000:
                                        level = 2
                                    else:
                                        level = 1
                                        
                                    if amt >= 100_000_000_000:
                                        amt_str = f"{amt / 100_000_000_000:.1f}천억"
                                    elif amt >= 10_000_000_000:
                                        amt_str = f"{amt / 10_000_000_000:.1f}백억"
                                    else:
                                        amt_str = f"{amt / 100_000_000:.1f}억"
                                        
                                    amt_억 = amt / 100_000_000
                                    
                                    if d in u_dates:
                                        # 상한가 날(빨간 배경)에서는 글씨를 더 찐하게(테두리 강조) 처리
                                        if radar_cell_format == "금액":
                                            text_style = "color: #FFD700; font-size: 13px; font-weight: 900; line-height: 1; letter-spacing: -0.5px; text-shadow: -1px -1px 0 #000, 1px -1px 0 #000, -1px 1px 0 #000, 1px 1px 0 #000, 2px 2px 2px #000;"
                                        else:
                                            text_style = "color: #FFD700; font-size: 10.5px; font-weight: 900; line-height: 1; letter-spacing: -0.5px; text-shadow: -1px -1px 0 #000, 1px -1px 0 #000, -1px 1px 0 #000, 1px 1px 0 #000, 2px 2px 2px #000;"
                                    else:
                                        # 일반 날짜
                                        if radar_cell_format == "금액":
                                            text_style = "color: #FFA500; font-size: 13px; font-weight: bold; line-height: 1; letter-spacing: -0.5px; text-shadow: 1px 1px 2px #000;"
                                        else:
                                            text_style = "color: #FFA500; font-size: 10.5px; font-weight: bold; line-height: 1; letter-spacing: -0.5px; text-shadow: 1px 1px 2px #000;"
                                        
                                    if radar_cell_format == "금액":
                                        inner_html += f"""
                                        <div style="width:100%; height:40px; position:absolute; top:0; left:0; pointer-events: none; z-index: 2; display: flex; align-items: center; justify-content: center;" title="{amt_억:.1f}억 (Lv.{level})">
                                            <div style="{text_style}">{amt_str}</div>
                                        </div>
                                        """
                                    else:
                                        inner_html += f"""
                                        <div style="width:100%; height:40px; position:absolute; top:0; left:0; pointer-events: none; z-index: 2;" title="{amt_억:.1f}억 (Lv.{level})">
                                            <div style="width: 25%; height: {level * 20}%; background-color: rgba(255,165,0,0.9); clip-path: polygon(50% 0%, 0% 100%, 100% 100%); position: absolute; bottom: 0; left: 0;"></div>
                                            <div style="position: absolute; bottom: 1px; left: 26%; {text_style}">{amt_str}</div>
                                        </div>
                                        """
                                    
                                html_parts.append(f"""
                                        <td style="{border_style} background-color: {cell_bg}; height: 40px; padding: 0; position: relative; vertical-align: bottom;">
                                            <a href="javascript:void(0);" id="{stock}___{d}___{render_id}" style="display: block; width: 100%; height: 100%; text-decoration: none; color: inherit; min-height: 40px; cursor: pointer; position: relative;" title="{d} (고래 체결: {cnt}건)">
                                                {inner_html}
                                            </a>
                                        </td>
                                """)
                            html_parts.append("</tr>")
                            
                        html_parts.append("""
                                </tbody>
                            </table>
                        </div>
                        """)
                        
                        from st_click_detector import click_detector
                        html_content = "".join(html_parts)
                        clicked = click_detector(html_content, key="sangseongo_click_detector")
                        
                        if clicked and st.session_state.get("last_mock_clicked") != clicked:
                            st.session_state["last_mock_clicked"] = clicked
                            
                            if clicked.startswith("goto___"):
                                stock = clicked.split("___")[1]
                                st.session_state['pending_search'] = stock
                                st.session_state['scrn_select_radio'] = "체결 로그"
                                st.session_state['sangseongo_reset'] = st.session_state.get('sangseongo_reset', 0) + 1
                                st.rerun()
                            elif clicked.startswith("summary___"):
                                stock = clicked.split("___")[1]
                                trigger = st.session_state.get('dialog_trigger_id', 0) + 1
                                st.session_state['dialog_trigger_id'] = trigger
                                st.session_state['show_summary_dialog'] = {
                                    "stock": stock,
                                    "code": "",
                                    "trigger_id": trigger
                                }
                                st.session_state['sangseongo_reset'] = st.session_state.get('sangseongo_reset', 0) + 1
                                st.rerun()
                            else:
                                stock, date_str = clicked.split("___")
                                st.session_state['show_mock_dialog'] = {
                                    "stock": stock,
                                    "date": date_str
                                }
                                st.rerun()

                
        elif scrn_select == "외기 TOP 100 화면":
            # 일반 사용자 이상 접근 가능
            if not st.session_state.get('authenticated', False):
                st.markdown("<h4 style='color:#FFD700; border-left: 4px solid #FFD700; padding-left: 10px;'>📊 일별 외국인/기관 TOP 100</h4>", unsafe_allow_html=True)
                st.warning("⚠️ 정회원 이상만 접근 가능한 고급 수급 분석 화면입니다. 가입 및 등업 후 이용해 주세요.")
            else:
                col_left, col_right = st.columns([1.8, 1])
                
                with col_left:
                    st.markdown("<h4 style='color:#00BFFF; border-left: 4px solid #00BFFF; padding-left: 10px; margin-top: 0;'>📊 일별 외국인/기관 순매수 TOP 100</h4>", unsafe_allow_html=True)
                    st.write("시장 주도 세력(외국인/기관)의 일일 순매수 상위 핵심 종목을 확인합니다.")
                    
                    st.write("") # 약간의 여백
                    
                    # 🔘 행 클릭 시 동작 모드 선택 라디오 버튼 (왼쪽 배치)
                    click_action = st.radio(
                        "👇 표에서 종목(행)을 클릭했을 때 동작을 선택하세요:", 
                        ["📊 시계열 추적 (차트 이동)", "💬 AI 요약 보기 (팝업)"], 
                        horizontal=True,
                        key="top100_click_action"
                    )
                
                with col_right:
                    # 달력 선택기 (오늘 ~ 3개월 전)
                    # 탑백 데이터는 매일 오후 4시에 수집되므로, 4시 이전에는 전날 데이터를 기본으로 보여주도록 설정합니다.
                    now_kst = datetime.utcnow() + timedelta(hours=9)
                    if now_kst.time() < datetime.strptime("16:00", "%H:%M").time():
                        # 오후 4시 이전이면 전날 기준
                        target_dt = now_kst - timedelta(days=1)
                    else:
                        target_dt = now_kst
                        
                    # get_latest_market_open_date 내부의 '오전 9시 이전이면 하루 빼기' 로직을 회피하기 위해 시간을 정오로 고정합니다.
                    target_dt = target_dt.replace(hour=12, minute=0, second=0, microsecond=0)
                        
                    # 휴일/주말을 건너뛰고 가장 최근 유효한 장 마감일을 가져옵니다.
                    today_kor = get_latest_market_open_date(target_dt)
                    min_date = today_kor - timedelta(days=90)
                    
                    import calendar
                    from st_click_detector import click_detector
                    
                    if 'top100_cal_year' not in st.session_state:
                        st.session_state.top100_cal_year = today_kor.year
                        st.session_state.top100_cal_month = today_kor.month
                        st.session_state.top100_selected_date = today_kor
                        st.session_state.top100_cal_reset = 0
                    
                    cal_year = st.session_state.top100_cal_year
                    cal_month = st.session_state.top100_cal_month
                    selected_date = st.session_state.top100_selected_date
                    
                    # 캘린더 상단 (이전/다음 달 이동) - 크기 30% 축소
                    html_cal = f"""
                    <div style="max-width: 230px; margin-left: auto; background: #1a1c24; padding: 10px; border-radius: 10px; font-family: 'Inter', sans-serif; box-shadow: 0 4px 6px rgba(0,0,0,0.3);">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; color: white;">
                            <a href='#' id='cal_prev' style='color: #888; text-decoration: none; padding: 3px 8px; background: #2a2d3a; border-radius: 4px; font-weight: bold; font-size: 12px;'>&lt;</a>
                            <strong style="font-size: 14px;">{cal_year}년 {cal_month}월</strong>
                            <a href='#' id='cal_next' style='color: #888; text-decoration: none; padding: 3px 8px; background: #2a2d3a; border-radius: 4px; font-weight: bold; font-size: 12px;'>&gt;</a>
                        </div>
                        <div style="display: grid; grid-template-columns: repeat(7, 1fr); text-align: center; gap: 3px; font-size: 11px; font-weight: bold; margin-bottom: 5px;">
                            <div style="color: #ff4b4b;">일</div>
                            <div style="color: #aaa;">월</div>
                            <div style="color: #aaa;">화</div>
                            <div style="color: #aaa;">수</div>
                            <div style="color: #aaa;">목</div>
                            <div style="color: #aaa;">금</div>
                            <div style="color: #4B89B5;">토</div>
                        </div>
                        <div style="display: grid; grid-template-columns: repeat(7, 1fr); text-align: center; gap: 3px; font-size: 11px;">
                    """
                    
                    c = calendar.Calendar(firstweekday=6) # 일요일부터 시작
                    for week in c.monthdatescalendar(cal_year, cal_month):
                        for day in week:
                            if day.month == cal_month:
                                bg_color = "transparent"
                                color = "white"
                                border = "1px solid transparent"
                                
                                if day == selected_date:
                                    bg_color = "#00BFFF"
                                    color = "white"
                                elif day.weekday() == 6: # 일요일
                                    color = "#ff4b4b"
                                elif day.weekday() == 5: # 토요일
                                    color = "#4B89B5"
                                    
                                if day == today_kor and day != selected_date:
                                    border = "1px solid #555" # 오늘 날짜 테두리
                                    
                                if day > today_kor or day < min_date:
                                    # 미래 날짜 또는 90일 이전 날짜는 비활성화
                                    html_cal += f"<div style='padding: 4px; color: #444; border: {border}; border-radius: 4px;'>{day.day}</div>"
                                else:
                                    html_cal += f"<a href='#' id='cal_date_{day.strftime('%Y-%m-%d')}' style='padding: 4px; background: {bg_color}; color: {color}; border: {border}; text-decoration: none; border-radius: 4px; display: block; transition: 0.2s;'>{day.day}</a>"
                            else:
                                html_cal += "<div></div>"
                                
                    html_cal += "</div></div>"
                    
                    clicked = click_detector(html_cal, key=f"top100_cal_ui_{st.session_state.top100_cal_reset}")
                
                if clicked:
                    if clicked == 'cal_prev':
                        if st.session_state.top100_cal_month == 1:
                            st.session_state.top100_cal_month = 12
                            st.session_state.top100_cal_year -= 1
                        else:
                            st.session_state.top100_cal_month -= 1
                        st.session_state.top100_cal_reset += 1
                        st.rerun()
                    elif clicked == 'cal_next':
                        if st.session_state.top100_cal_month == 12:
                            st.session_state.top100_cal_month = 1
                            st.session_state.top100_cal_year += 1
                        else:
                            st.session_state.top100_cal_month += 1
                        st.session_state.top100_cal_reset += 1
                        st.rerun()
                    elif clicked.startswith('cal_date_'):
                        date_str = clicked.split('cal_date_')[1]
                        st.session_state.top100_selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                        st.session_state.top100_cal_reset += 1
                        st.rerun()
                
                # 해당 날짜 데이터 가져오기
                import time
                t0 = time.time()
                with st.spinner("수급 데이터를 불러오고 있습니다..."):
                    res = supabase.table("daily_whale_top200").select("*").eq("trade_date", selected_date.strftime("%Y-%m-%d")).execute()
                    t1 = time.time()
                    if res.data:
                        df_top = pd.DataFrame(res.data)
                        
                        # 합산 필드 만들어서 정렬 (합산 순매수 기준)
                        df_top['외/기 합산 순매수(억)'] = (df_top["frgn_buy"] - df_top["frgn_sell"]) + (df_top["orgn_buy"] - df_top["orgn_sell"])
                        df_top['🟣외국인 매수세(억)'] = df_top["frgn_buy"] - df_top["frgn_sell"]
                        df_top['🟡기관 매수세(억)'] = df_top["orgn_buy"] - df_top["orgn_sell"]
                        df_top = df_top.sort_values(by="외/기 합산 순매수(억)", ascending=False)

                        
                        # 컬럼명 예쁘게 매핑
                        df_top = df_top.rename(columns={
                            "trade_date": "날짜",
                            "market": "시장",
                            "stock_name": "종목명",
                            "frgn_buy": "🔴외국인 매수(억)",
                            "frgn_sell": "🔵외국인 매도(억)",
                            "orgn_buy": "🟠기관 매수(억)",
                            "orgn_sell": "🟢기관 매도(억)"
                        })
                        
                        # 합산 필드 이름도 이모지 추가
                        df_top.rename(columns={"외/기 합산 순매수(억)": "🟣외/기 합산(억)"}, inplace=True)

                        display_cols = ["날짜", "시장", "종목명", "🔴외국인 매수(억)", "🔵외국인 매도(억)", "🟣외국인 매수세(억)", "🟠기관 매수(억)", "🟢기관 매도(억)", "🟡기관 매수세(억)", "🟣외/기 합산(억)"]
                        display_df = df_top[display_cols]
                        
                        top100_key = f"top100_dataframe_{st.session_state.get('top100_reset_counter', 0)}"
                        t2 = time.time()
                        
                        # 형님이 원하셨던 '글자 색상' 스크립트 복원!
                        def get_col_color(col_name):
                            if col_name == "🔴외국인 매수(억)": return "color: #ff4b4b;"       # 빨강
                            elif col_name == "🔵외국인 매도(억)": return "color: #1e90ff;"     # 파랑
                            elif col_name == "🟣외국인 매수세(억)": return "color: #b388ff;"   # 밝은 보라
                            elif col_name == "🟠기관 매수(억)": return "color: #ff7f50;"       # 주홍
                            elif col_name == "🟢기관 매도(억)": return "color: #2e8b57;"       # 진녹
                            elif col_name == "🟡기관 매수세(억)": return "color: #ffd54f;"     # 노랑
                            elif col_name == "🟣외/기 합산(억)": return "color: #d8bfd8;"       # 옅은 보라
                            return ""
                            
                        styled_df = display_df.style.apply(
                            lambda col: [get_col_color(col.name)] * len(col), axis=0
                        )
                        
                        st.caption(f"⏱️ DB조회: {t1-t0:.2f}초 | Pandas가공: {t2-t1:.2f}초 | (색상 렌더링 복구 완료!)")
                        
                        event = st.dataframe(
                            styled_df,
                            use_container_width=True,
                            hide_index=True,
                            height=650,
                            on_select="rerun",
                            selection_mode="single-row",
                            key=top100_key,
                            column_config={
                                # 🔧 [수정 2026-07-30] 숫자 가독성을 위해 1000단위 콤마(,) 포맷 전면 적용
                                "🔴외국인 매수(억)": st.column_config.NumberColumn(format="%,.2f"),
                                "🔵외국인 매도(억)": st.column_config.NumberColumn(format="%,.2f"),
                                "🟣외국인 매수세(억)": st.column_config.NumberColumn(format="%,.2f"),
                                "🟠기관 매수(억)": st.column_config.NumberColumn(format="%,.2f"),
                                "🟢기관 매도(억)": st.column_config.NumberColumn(format="%,.2f"),
                                "🟡기관 매수세(억)": st.column_config.NumberColumn(format="%,.2f"),
                                "🟣외/기 합산(억)": st.column_config.NumberColumn(format="%,.2f")
                            }
                        )
                        
                        if event and "selection" in event:
                            rows = event["selection"]["rows"]
                            if rows and rows[0] < len(df_top):
                                selected_stock = df_top.iloc[rows[0]]['종목명']
                                ss = selected_stock.replace(" 🚀", "").replace(" 👑", "").replace(" 🔥", "").replace(" 💥", "").replace(" ✨", "").replace(" 🌱", "")
                                clean_stock = ss.replace("🚀", "").replace("👑", "").replace("🔥", "").replace("💥", "").replace("✨", "").replace("🌱", "").strip()
                                
                                # Retrieve stock code if available
                                row_stock_code = df_top.iloc[rows[0]]['stock_code'] if 'stock_code' in df_top.columns else ""
                                
                                if click_action == "💬 AI 요약 보기 (팝업)":
                                    trigger = st.session_state.get('dialog_trigger_id', 0) + 1
                                    st.session_state['dialog_trigger_id'] = trigger
                                    st.session_state['show_summary_dialog'] = {
                                        "stock": clean_stock,
                                        "code": row_stock_code,
                                        "trigger_id": trigger
                                    }
                                    st.session_state['top100_reset_counter'] = st.session_state.get('top100_reset_counter', 0) + 1
                                    st.rerun()
                                else:
                                    st.session_state['pending_search'] = clean_stock
                                    st.session_state['last_search_keyword'] = clean_stock
                                    st.session_state['scrn_select_radio'] = "체결 로그"
                                    st.session_state['top100_reset_counter'] = st.session_state.get('top100_reset_counter', 0) + 1
                                    st.rerun()
                        else:
                            st.session_state.pop('last_summary_stock_top100', None)
                    else:
                        st.info("해당 날짜의 수급 데이터가 아직 수집되지 않았거나 휴장일입니다. (또는 너무 오래된 과거입니다)")

        elif scrn_select == "수익율 자랑":
            is_admin_view = st.session_state.get('is_admin', False)
            st.markdown("<h4 style='color:#FF69B4; border-left: 4px solid #FF69B4; padding-left: 10px;'>💖 수익율 자랑</h4>", unsafe_allow_html=True)
            st.write("수익을 얻으셨다면 마음껏 자랑해 주세요! 인증샷을 올리시면 함께 축하해 드립니다. 🚀")
            
            # --- 라우팅 및 뷰 모드 ---
            if "brag_view_mode" not in st.session_state:
                st.session_state["brag_view_mode"] = "list"
            if "brag_selected_post" not in st.session_state:
                st.session_state["brag_selected_post"] = None

            # --- 글쓰기 폼 ---
            if "brag_text_input" not in st.session_state:
                st.session_state["brag_text_input"] = ""
            if "brag_title_input" not in st.session_state:
                st.session_state["brag_title_input"] = ""
                
            if st.session_state.get("brag_clear_trigger", False):
                st.session_state["brag_text_input"] = ""
                st.session_state["brag_title_input"] = ""
                st.session_state["brag_clear_trigger"] = False

            if "show_brag_form" not in st.session_state:
                st.session_state["show_brag_form"] = False

            # 🚨 [신규 튜닝]: expander 대신 명시적인 버튼을 사용하여 사용자 혼동 방지
            btn_label = "글쓰기 창 닫기 ❌" if st.session_state["show_brag_form"] else "📝 글 쓰기"
            is_auth = st.session_state.get("authenticated", False)
            
            if "brag_layout_mode_radio" not in st.session_state:
                st.session_state["brag_layout_mode_radio"] = "바둑판형"
                
            col_btn, col_view = st.columns([1.5, 8.5])
            with col_btn:
                if st.button(btn_label, use_container_width=True, disabled=not is_auth, help="로그인 후 자랑글을 작성할 수 있습니다." if not is_auth else None):
                    st.session_state["show_brag_form"] = not st.session_state["show_brag_form"]
                    if st.session_state["show_brag_form"]:
                        import time
                        st.session_state["brag_mount_id"] = time.time()
                    st.rerun()
            with col_view:
                st.radio("보기 형태", ["목록형", "바둑판형"], horizontal=True, label_visibility="collapsed", key="brag_layout_mode_radio")

            if st.session_state["show_brag_form"]:
                st.html("""
                <style>
                    /* 입력창 배경을 살짝 밝게 하고, 눈에 띄는 테두리 추가 */
                    div[data-baseweb="input"] > div,
                    div[data-baseweb="textarea"] > div {
                        background-color: #262630 !important;
                        border: 1px solid #4B4B5A !important;
                        border-radius: 6px !important;
                    }
                    /* 포커스(입력 중)일 때 테두리를 주황색으로 강조 */
                    div[data-baseweb="input"] > div:focus-within, 
                    div[data-baseweb="textarea"] > div:focus-within {
                        border: 1px solid #FF8C00 !important;
                        box-shadow: 0 0 5px rgba(255, 140, 0, 0.5) !important;
                    }
                </style>
                """)
                brag_title = st.text_input("제목", key="brag_title_input")
                brag_text = st.text_area("자랑하고 싶은 내용", key="brag_text_input", height=100)
                
                class DummyPasteResult:
                    image_data = None
                paste_result = DummyPasteResult()
                
                if st.session_state.get('user_role') == 'admin':
                    col1, col2 = st.columns([1, 1])
                    with col1:
                        brag_image_file = st.file_uploader("📂 인증샷 첨부 (파일 선택)", type=["png", "jpg", "jpeg"])
                    with col2:
                        st.write("또는 캡처 후 아래 버튼을 누르세요")
                        paste_result = paste_image_button(
                            label="📋 클립보드 붙여넣기",
                            text_color="#ffffff",
                            background_color="#FF69B4",
                            hover_background_color="#FF1493",
                            key=f"paste_image_btn_{st.session_state.get('brag_mount_id', 0)}"
                        )
                else:
                    brag_image_file = st.file_uploader("📂 인증샷 첨부 (파일 선택)", type=["png", "jpg", "jpeg"])
                    
                if paste_result.image_data is not None:
                    st.session_state["pasted_image"] = paste_result.image_data
                    st.success("✅ 클립보드 이미지 임시 저장 완료! (등록하기를 눌러주세요)")

                submit_brag = st.button("등록하기 🚀", type="primary")
                
                if submit_brag:
                    if not st.session_state["brag_title_input"].strip():
                        st.warning("제목을 입력해 주세요!")
                    elif not st.session_state["brag_text_input"].strip():
                        st.warning("내용을 입력해 주세요!")
                    else:
                        base64_str = None
                        target_image = None
                        
                        if "pasted_image" in st.session_state and st.session_state["pasted_image"] is not None:
                            target_image = st.session_state["pasted_image"]
                        elif brag_image_file:
                            target_image = Image.open(brag_image_file)
                            
                        if target_image:
                            try:
                                target_image.thumbnail((800, 800))
                                if target_image.mode in ("RGBA", "P"):
                                    target_image = target_image.convert("RGB")
                                buffer = io.BytesIO()
                                target_image.save(buffer, format="JPEG", quality=80)
                                base64_str = base64.b64encode(buffer.getvalue()).decode("utf-8")
                            except Exception as e:
                                st.error(f"이미지 압축 실패: {e}")
                                
                        try:
                            supabase.table("brag_board").insert({
                                "author": st.session_state.get('current_user', 'Guest'),
                                "title": st.session_state["brag_title_input"].strip(),
                                "content": st.session_state["brag_text_input"].strip(),
                                "image_base64": base64_str
                            }).execute()
                            
                            st.session_state["brag_clear_trigger"] = True
                            st.session_state.pop("pasted_image", None)
                            st.session_state["show_brag_form"] = False # 글 등록 성공 시 폼 닫기
                            st.success("글이 등록되었습니다!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"등록 실패: {e}")
            
            st.markdown("<br>", unsafe_allow_html=True) # divider 대신 약간의 여백만 부여
            
            def cb_toggle_like(post_id, current_likes, liked_users, current_user, has_liked):
                new_likes = current_likes
                new_users = liked_users.copy()
                if has_liked:
                    new_likes -= 1
                    new_users.remove(current_user)
                else:
                    new_likes += 1
                    new_users.append(current_user)
                supabase.table("brag_board").update({
                    "likes_count": new_likes,
                    "liked_users": new_users
                }).eq("id", post_id).execute()

            def cb_toggle_edit(edit_key, text_key, content):
                st.session_state[edit_key] = True
                st.session_state[text_key] = content

            def cb_save_edit(post_id, edit_key, text_key):
                supabase.table("brag_board").update({"content": st.session_state.get(text_key, "")}).eq("id", post_id).execute()
                st.session_state[edit_key] = False

            def cb_cancel_edit(edit_key):
                st.session_state[edit_key] = False

            # --- 피드 표시 ---
            @st.fragment
            def render_post(post_id):
                try:
                    # 렌더링 시점에 DB에서 최신 상태를 가져옵니다.
                    fresh_res = supabase.table("brag_board").select("*").eq("id", post_id).execute()
                    if not fresh_res.data:
                        return
                    post = fresh_res.data[0]
                    
                    is_hidden = post.get('is_hidden', False)
                    
                    if is_hidden and not is_admin_view:
                        return
                        
                    with st.container():
                        p_time_utc = pd.to_datetime(post['created_at'])
                        if p_time_utc.tzinfo is None:
                            p_time_utc = p_time_utc.tz_localize('UTC')
                        p_time = p_time_utc.tz_convert('Asia/Seoul').strftime('%Y-%m-%d %H:%M')
                        
                        opacity = 0.4 if is_hidden else 1.0
                        st.markdown(f"<div style='opacity: {opacity};'>", unsafe_allow_html=True)
                        
                        if is_hidden:
                            st.markdown("<span style='color:red; font-weight:bold; font-size:12px;'>🚨 [관리자에 의해 숨김 처리된 게시물입니다]</span>", unsafe_allow_html=True)
                            
                        title_str = post.get('title') or "제목 없음"
                        st.markdown(f"<div style='font-size: 18px; font-weight: bold; margin-bottom: 5px;'>{title_str}</div>", unsafe_allow_html=True)
                        st.markdown(f"**👤 {post['author']}** <span style='color:gray; font-size:12px; margin-left:10px;'>{p_time}</span>", unsafe_allow_html=True)
                        
                        # 텍스트 및 수정 모드
                        edit_key = f"edit_mode_{post['id']}"
                        if edit_key not in st.session_state:
                            st.session_state[edit_key] = False
                            
                        is_editing = st.session_state[edit_key]
                        
                        if is_editing:
                            edit_text_key = f"edit_text_{post['id']}"
                            if edit_text_key not in st.session_state:
                                st.session_state[edit_text_key] = post.get('content', '')
                            
                            st.text_area("내용 수정", key=edit_text_key, height=100)
                            
                            col_s, col_c, _ = st.columns([1.5, 1.5, 7])
                            with col_s:
                                st.button("💾 저장", key=f"save_{post['id']}", use_container_width=True, on_click=cb_save_edit, args=(post['id'], edit_key, edit_text_key))
                            with col_c:
                                st.button("❌ 취소", key=f"cancel_{post['id']}", use_container_width=True, on_click=cb_cancel_edit, args=(edit_key,))
                        else:
                            if post.get('content'):
                                st.markdown(f"<div style='margin-top: 5px; margin-bottom: 15px; font-size: 15px; white-space: pre-wrap;'>{post['content']}</div>", unsafe_allow_html=True)
                            
                        # 이미지
                        if post.get('image_base64'):
                            img_b64 = post['image_base64']
                            st.html(f"<img src='data:image/jpeg;base64,{img_b64}' style='max-width: 100%; height: auto; border-radius: 8px; margin: 10px 0;'>")
                            
                        st.markdown("</div>", unsafe_allow_html=True)
                            
                        # 하단 버튼부 (좋아요 & 액션 & 목록)
                        cols = st.columns([1.5, 1.5, 1.5, 1.5, 4.0])
                        
                        likes = post.get('likes_count') or 0
                        liked_users = post.get('liked_users') or []
                        curr_user = st.session_state.get('current_user', st.session_state.get('guest_id', 'Guest'))
                        is_auth = st.session_state.get('authenticated', False)
                        has_liked = (curr_user in liked_users)
                        
                        like_btn_text = f"❤️ {likes}" if has_liked else f"🤍 {likes}"
                        
                        with cols[0]:
                            st.button(like_btn_text, key=f"like_{post['id']}", use_container_width=True, on_click=cb_toggle_like, args=(post['id'], likes, liked_users, curr_user, has_liked))
                                
                        idx = 1
                        if is_auth and curr_user == post.get('author', ''):
                            if not is_editing:
                                with cols[idx]:
                                    st.button("✏️ 수정", key=f"edit_{post['id']}", use_container_width=True, on_click=cb_toggle_edit, args=(edit_key, f"edit_text_{post['id']}", post.get('content', '')))
                                idx += 1
                                with cols[idx]:
                                    if st.button("🗑️ 삭제", key=f"del_{post['id']}", use_container_width=True):
                                        supabase.table("brag_board").delete().eq("id", post['id']).execute()
                                        st.success("게시글이 삭제되었습니다.")
                                        st.rerun()
                                idx += 1
                        elif is_admin_view:
                            if not is_hidden:
                                with cols[idx]:
                                    if st.button("🙈 숨기기", key=f"hide_{post['id']}", use_container_width=True):
                                        supabase.table("brag_board").update({"is_hidden": True}).eq("id", post['id']).execute()
                                        st.success("숨김 처리되었습니다.")
                                        st.rerun()
                                idx += 1
                                with cols[idx]:
                                    if st.button("🗑️ 삭제", key=f"del_admin_{post['id']}", use_container_width=True):
                                        supabase.table("brag_board").delete().eq("id", post['id']).execute()
                                        st.success("게시글이 삭제되었습니다.")
                                        st.rerun()
                                idx += 1
                            else:
                                with cols[idx]:
                                    if st.button("👀 숨김 해제", key=f"unhide_{post['id']}", use_container_width=True):
                                        supabase.table("brag_board").update({"is_hidden": False}).eq("id", post['id']).execute()
                                        st.success("숨김 해제되었습니다.")
                                        st.rerun()
                                idx += 1
                                with cols[idx]:
                                    if st.button("🗑️ 완전 삭제", key=f"fulldel_{post['id']}", use_container_width=True):
                                        supabase.table("brag_board").delete().eq("id", post['id']).execute()
                                        st.success("영구 삭제되었습니다.")
                                        st.rerun()
                                idx += 1
                                
                        with cols[idx]:
                            if st.button("⬅️ 목록", key=f"back_btm_{post['id']}", use_container_width=True):
                                st.session_state["brag_view_mode"] = "list"
                                st.rerun()
                                        
                        st.markdown("<hr style='margin-top: 10px; margin-bottom: 20px; border-color: rgba(255,255,255,0.1);'>", unsafe_allow_html=True)
                except Exception as e:
                    st.error(f"포스트 렌더링 에러: {e}")

            try:
                if st.session_state["brag_view_mode"] == "detail" and st.session_state["brag_selected_post"]:
                    def back_to_list():
                        st.session_state["brag_view_mode"] = "list"
                    st.button("⬅️ 목록으로", type="primary", on_click=back_to_list)
                    render_post(st.session_state["brag_selected_post"])
                else:
                    view_mode = st.session_state.get("brag_layout_mode_radio", "바둑판형")
                    
                    if view_mode == "목록형":
                        brag_res = supabase.table("brag_board").select("id, title, author, created_at, likes_count, views_count, is_hidden").order("created_at", desc=True).limit(100).execute()
                    else:
                        brag_res = supabase.table("brag_board").select("id, title, author, created_at, likes_count, views_count, is_hidden, image_base64").order("created_at", desc=True).limit(100).execute()
                    
                    if not brag_res.data:
                        st.info("아직 자랑글이 없습니다. 첫 번째로 자랑해 보세요!")
                    else:
                        st.markdown(f"<div style='font-size: 14px; color: gray; margin-bottom: 10px;'>총 {len(brag_res.data)}개의 자랑글이 있습니다.</div>", unsafe_allow_html=True)
                        
                        if view_mode == "목록형":
                        
                        # --- 행 간격 극강 압축 및 헤더 스타일을 위한 CSS ---
                            st.html("""
                            <style>
                                /* my-table-start 마커 이후의 모든 element-container (행) 위쪽 여백 제거하여 간격 완벽 밀착 */
                                div.element-container:has(.my-table-start) ~ div.element-container {
                                    margin-top: -16px !important;
                                }
                            
                                /* 테이블 행(가로 블록) 일괄 스타일링 */
                                div.element-container:has(.my-table-start) ~ div.element-container div[data-testid="stHorizontalBlock"] {
                                    border-bottom: 1px solid rgba(255,255,255,0.1) !important;
                                    padding-top: 4px !important;
                                    padding-bottom: 4px !important;
                                    align-items: center !important;
                                }
                            
                                /* 헤더 행 스타일 (고유 ID 사용해서 정확히 타겟팅) */
                                div[data-testid="stHorizontalBlock"]:has(#brag-board-header) {
                                    border-top: none !important;
                                    border-bottom: 1px solid rgba(255,255,255,0.1) !important;
                                    background-color: rgba(255,255,255,0.03) !important;
                                    padding-top: 8px !important;
                                    padding-bottom: 8px !important;
                                    border-radius: 4px 4px 0 0;
                                }
                            
                                /* 버튼 높이 완벽 통일 */
                                .stButton button[kind="tertiary"] {
                                    min-height: 24px !important;
                                    padding: 0px !important;
                                    margin: 0px !important;
                                }
                            </style>
                            """)
                        
                            # --- 테이블 마커 ---
                            st.html("<div class='my-table-start'></div>")
                        
                            # --- 테이블 헤더 ---
                            show_views_res = supabase.table("system_settings").select("value").eq("key", "brag_board_show_views").execute()
                            show_views_public = True
                            if show_views_res.data and show_views_res.data[0]['value'] == "False":
                                show_views_public = False
                        
                            can_see_views = is_admin_view or show_views_public

                            col1, col2, col3, col4, col5 = st.columns([5, 2, 2, 1.5, 1.5])
                            with col1: st.html("<div id='brag-board-header' style='font-weight:bold; text-align:center;'>제목</div>")
                            with col2: st.html("<div style='font-weight:bold; text-align:center;'>작성자</div>")
                            with col3: st.html("<div style='font-weight:bold; text-align:center;'>작성일시</div>")
                            with col4: 
                                header_text = "조회수" if can_see_views else ""
                                st.html(f"<div style='font-weight:bold; text-align:center;'>{header_text}</div>")
                            with col5: st.html("<div style='font-weight:bold; text-align:center;'>좋아요</div>")
                        
                            now_seoul = pd.Timestamp.now(tz='Asia/Seoul')
                        
                            for p in brag_res.data:
                                if p.get('is_hidden') and not is_admin_view:
                                    continue
                                
                                p_time_utc = pd.to_datetime(p['created_at'])
                                if p_time_utc.tzinfo is None:
                                    p_time_utc = p_time_utc.tz_localize('UTC')
                                p_time_seoul = p_time_utc.tz_convert('Asia/Seoul')
                            
                                if p_time_seoul.date() == now_seoul.date():
                                    p_time = p_time_seoul.strftime('%H:%M')
                                else:
                                    p_time = p_time_seoul.strftime('%y.%m.%d')
                            
                                title_text = p.get('title') or "제목 없음"
                            
                                if p.get('is_hidden'):
                                    title_text = f"🚨[숨김] {title_text}"
                                
                                likes = p.get('likes_count') or 0
                                views = p.get('views_count') or 0
                            
                                c1, c2, c3, c4, c5 = st.columns([5, 2, 2, 1.5, 1.5])
                                with c1:
                                    def view_detail_cb(post_id=p['id'], current_views=views):
                                        st.session_state["brag_view_mode"] = "detail"
                                        st.session_state["brag_selected_post"] = post_id
                                        # 조회수 1 증가 (DB 직빵 업데이트)
                                        supabase.table("brag_board").update({"views_count": current_views + 1}).eq("id", post_id).execute()
                                        
                                    st.button(title_text, key=f"list_btn_{p['id']}", on_click=view_detail_cb, type="tertiary")
                                with c2:
                                    st.html(f"<div style='text-align:center; font-size:14px; margin-top:4px;'>{p['author']}</div>")
                                with c3:
                                    st.html(f"<div style='text-align:center; font-size:14px; color:gray; margin-top:4px;'>{p_time}</div>")
                                with c4:
                                    view_text = str(views) if can_see_views else "-"
                                    st.html(f"<div style='text-align:center; font-size:14px; color:#A0C4FF; margin-top:4px;'>{view_text}</div>")
                                with c5:
                                    st.html(f"<div style='text-align:center; font-size:14px; color:#FFB4B4; margin-top:4px;'>{likes}</div>")
                        
                        elif view_mode == "바둑판형":
                            show_views_res = supabase.table("system_settings").select("value").eq("key", "brag_board_show_views").execute()
                            show_views_public = True
                            if show_views_res.data and show_views_res.data[0]['value'] == "False":
                                show_views_public = False
                            can_see_views = is_admin_view or show_views_public
                            now_seoul = pd.Timestamp.now(tz='Asia/Seoul')
                            
                            display_posts = [p for p in brag_res.data if not (p.get('is_hidden') and not is_admin_view)]
                            
                            num_cols = 4
                            for i in range(0, len(display_posts), num_cols):
                                cols = st.columns(num_cols)
                                for j in range(num_cols):
                                    if i + j < len(display_posts):
                                        p = display_posts[i + j]
                                        with cols[j]:
                                            with st.container(border=True):
                                                title_text = p.get('title') or "제목 없음"
                                                if p.get('is_hidden'):
                                                    title_text = f"🚨[숨김] {title_text}"
                                                    
                                                def view_detail_cb_grid(post_id=p['id'], current_views=p.get('views_count') or 0):
                                                    st.session_state["brag_view_mode"] = "detail"
                                                    st.session_state["brag_selected_post"] = post_id
                                                    supabase.table("brag_board").update({"views_count": current_views + 1}).eq("id", post_id).execute()
                                                
                                                # 버튼의 라벨 길이를 자르거나 할 수 있지만 여기선 그대로 렌더링
                                                st.button(title_text, key=f"grid_btn_{p['id']}", on_click=view_detail_cb_grid, use_container_width=True)
                                                
                                                if p.get('image_base64'):
                                                    img_b64 = p['image_base64']
                                                    st.html(f"<div style='height: 120px; width: 100%; display: flex; justify-content: center; align-items: center; overflow: hidden; border-radius: 4px; margin-bottom: 8px; margin-top: 4px;'><img src='data:image/jpeg;base64,{img_b64}' style='min-width: 100%; min-height: 100%; object-fit: cover;'></div>")
                                                else:
                                                    st.html("<div style='height: 120px; width: 100%; display: flex; justify-content: center; align-items: center; background-color: rgba(255,255,255,0.05); border-radius: 4px; margin-bottom: 8px; margin-top: 4px; color: gray; font-size: 12px;'>이미지 없음</div>")
                                                
                                                p_time_utc = pd.to_datetime(p['created_at'])
                                                if p_time_utc.tzinfo is None:
                                                    p_time_utc = p_time_utc.tz_localize('UTC')
                                                p_time_seoul = p_time_utc.tz_convert('Asia/Seoul')
                                                if p_time_seoul.date() == now_seoul.date():
                                                    p_time = p_time_seoul.strftime('%H:%M')
                                                else:
                                                    p_time = p_time_seoul.strftime('%y.%m.%d')
                                                    
                                                st.markdown(f"<div style='font-size: 12px; color: #aaa; margin-top: 4px; text-align: left;'>👤 {p['author']}</div>", unsafe_allow_html=True)
                                                info_str = f"🕒 {p_time} &nbsp;|&nbsp; ❤️ {p.get('likes_count') or 0}"
                                                if can_see_views:
                                                    info_str += f" &nbsp;|&nbsp; 👁️ {p.get('views_count') or 0}"
                                                st.markdown(f"<div style='font-size: 11px; color: #888; margin-top: 2px; text-align: left;'>{info_str}</div>", unsafe_allow_html=True)
            except Exception as e:
                st.error(f"게시글 로딩 에러: {e}")

        elif scrn_select == "기간 누적 폭주":
            st.markdown(f"<h4 style='color:#FF9900; border-left: 4px solid #FF9900; padding-left: 10px;'>📊 기간 누적 매수 폭주 종목 ({global_period})</h4>", unsafe_allow_html=True)
            st.write(f"선택하신 기간 동안 세력들이 가장 강력하게 매집한 Top 10 종목입니다.")
            st.write("---")
            
            with st.spinner("🚀 기간 누적 폭주 종목을 분석하고 있습니다... 잠시만 기다려주세요 (최대 1~2분 소요)"):
                # 검색어에 의해 main_df가 1개 종목으로 필터링되어 있을 수 있으므로, 원본 전체 데이터를 강제로 불러옵니다.
                today_df_full = load_today_data(asset_type=asset_type, market_type=market_type, show_closing_auction=show_closing_auction)
                if global_period == "당일 데이터만":
                    full_df = today_df_full
                else:
                    _cache_date = get_latest_market_open_date().strftime('%Y-%m-%d')
                    historical_df_full = load_historical_data(asset_type=asset_type, market_type=market_type, show_closing_auction=show_closing_auction, cache_date=_cache_date)
                    full_df = pd.concat([historical_df_full, today_df_full], ignore_index=True) if not historical_df_full.empty else today_df_full
                
                target_df = full_df[full_df['date'] >= start_date.strftime('%Y-%m-%d')] if not full_df.empty else full_df
                hot_signals = get_accumulated_hot_signals(target_df)
            
            if not hot_signals:
                st.info(f"해당 기간({global_period}) 내에 폭주 종목이 없습니다.")
            else:
                # 2줄, 5칸 씩 출력 (총 10개)
                for row_idx in range(2):
                    cols = st.columns(5)
                    for col_idx in range(5):
                        idx = row_idx * 5 + col_idx
                        with cols[col_idx]:
                            if idx < len(hot_signals):
                                signal = hot_signals[idx]
                                score = signal['score']
                                if score >= 95:
                                    bg_grad, border_col, text_col, shadow_col = "linear-gradient(135deg, #332700 0%, #1a1400 100%)", "#FFD700", "#FFD700", "rgba(255, 215, 0, 0.4)"
                                elif score >= 90:
                                    bg_grad, border_col, text_col, shadow_col = "linear-gradient(135deg, #2b1111 0%, #1a0a0a 100%)", "#ff4b4b", "#ff4b4b", "rgba(255, 75, 75, 0.3)"
                                elif score >= 70:
                                    bg_grad, border_col, text_col, shadow_col = "linear-gradient(135deg, #2b1d11 0%, #1a110a 100%)", "#ff9900", "#ff9900", "rgba(255, 153, 0, 0.3)"
                                else:
                                    bg_grad, border_col, text_col, shadow_col = "linear-gradient(135deg, #261f18 0%, #1a1510 100%)", "#c28e5c", "#c28e5c", "rgba(194, 142, 92, 0.2)"
                                
                                st.markdown(f"""
                                <div style="background: {bg_grad}; border: 1px solid {border_col}; border-radius: 8px; padding: 10px; text-align: center; box-shadow: 0 0 10px {shadow_col}; margin-bottom: 15px; height: 110px; display: flex; flex-direction: column; justify-content: center;">
                                    <div style="font-size: 15px; font-weight: bold; color: #ffffff; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">{idx+1}. {signal['name']}</div>
                                    <div style="font-size: 13px; color: {text_col}; font-weight: bold; margin-top: 6px;">{signal['icon']} 파워: {score:.1f}점</div>
                                    <div style="font-size: 11px; color: #a0a0a0; margin-top: 4px;">{int(signal['net_buy'] // 1000000):,}백만 ({int(signal['buy_count'])}회)</div>
                                </div>
                                """, unsafe_allow_html=True)
                            else:
                                # 빈 슬롯
                                st.markdown(f"""
                                <div style="background: linear-gradient(135deg, #151515 0%, #0a0a0a 100%); border: 1px dashed #333; border-radius: 8px; padding: 10px; text-align: center; margin-bottom: 15px; height: 110px; display: flex; flex-direction: column; justify-content: center; opacity: 0.5;">
                                    <div style="font-size: 15px; font-weight: bold; color: #555;">-</div>
                                </div>
                                """, unsafe_allow_html=True)

        elif (scrn_select == "체결 로그"):
            # --- [하단 패널: 실시간 로그] ---
            filtered_df = main_df.copy()

            if search_keyword:
                if exact_match:
                    # 🟢 판다스 데이터프레임에서 이름이 칼같이 일치하는 행만 추출!
                    filtered_df = filtered_df[filtered_df['name'].str.strip() == search_keyword.strip()]
                else:
                    # 🔵 포함된 녀석들 전부 서치
                    filtered_df = filtered_df[filtered_df['name'].str.contains(search_keyword, case=False, na=False)]

                if filtered_df.empty:
                    st.warning(f"⚠️ '{search_keyword}' 종목에는 고래가 없었다.")
                else:
                    target_code = filtered_df.iloc[0]['code']
                    target_name = filtered_df.iloc[0]['name']
                    draw_whale_bar_chart(target_code, target_name, main_df)

            # 정렬 (상한가 탭은 최신 시간순, 일반 목록은 금액 큰 순)
            if not search_keyword:
                if show_only_upper_limit:
                    filtered_df = filtered_df.sort_values(by=['date', 'time'], ascending=[False, False])
                else:
                    filtered_df = filtered_df.sort_values(by='amount_krw', ascending=False)
            if not search_keyword:
                log_col1, log_empty, log_col2, log_col3 = st.columns([3.0, 1.0, 1.4, 1.1])
                with log_col1:
                    if show_only_upper_limit:
                        st.subheader(f"📋 놀빅 상한가 종목 고래 체결 목록")
                    else:
                        st.subheader(f"📋 실시간 놀빅 고래 체결 상황")
                        st.info("💡 당일 실시간 500 거래를 분석자료로 표시합니다.")
                with log_col2:
                    st.radio(
                        "🗂️ 자산 유형 필터",
                        ["개별 주식만 보기 🏢", "ETF만 보기 🌐", "전체 다 보기 📊"],
                        index=["개별 주식만 보기 🏢", "ETF만 보기 🌐", "전체 다 보기 📊"].index(asset_type),
                        key="asset_type_log",
                        horizontal=False,
                        label_visibility="collapsed",
                        on_change=sync_log_filters
                    )
                with log_col3:
                    st.radio(
                        "🗂️ 시장 유형 필터",
                        ["전체 시장 🌍", "KOSPI 🏢", "KOSDAQ 🚀"],
                        index=["전체 시장 🌍", "KOSPI 🏢", "KOSDAQ 🚀"].index(market_type),
                        key="market_type_log",
                        horizontal=False,
                        label_visibility="collapsed",
                        on_change=sync_log_filters
                    )
                
                st.write("") # 간격 띄우기
                
                # 🚨 [놀빅 AI 탐지] 실시간 매수 폭주 종목 렌더링
                hot_signals = get_hot_signals(main_df)
                
                st.markdown("#### 🚨 [놀빅 AI 탐지] 실시간 매수 폭주 종목 (Top 3)")
                hot_cols = st.columns(3) # 항상 3자리를 고정으로 유지
                
                for idx in range(3):
                    with hot_cols[idx]:
                        if idx < len(hot_signals):
                            signal = hot_signals[idx]
                            score = signal['score']
                            if score >= 95:
                                bg_grad, border_col, text_col, shadow_col = "linear-gradient(135deg, #332700 0%, #1a1400 100%)", "#FFD700", "#FFD700", "rgba(255, 215, 0, 0.4)"
                            elif score >= 90:
                                bg_grad, border_col, text_col, shadow_col = "linear-gradient(135deg, #2b1111 0%, #1a0a0a 100%)", "#ff4b4b", "#ff4b4b", "rgba(255, 75, 75, 0.3)"
                            elif score >= 70:
                                bg_grad, border_col, text_col, shadow_col = "linear-gradient(135deg, #2b1d11 0%, #1a110a 100%)", "#ff9900", "#ff9900", "rgba(255, 153, 0, 0.3)"
                            else: # 30 이상 (30 미만은 이미 위에서 필터링됨)
                                bg_grad, border_col, text_col, shadow_col = "linear-gradient(135deg, #261f18 0%, #1a1510 100%)", "#c28e5c", "#c28e5c", "rgba(194, 142, 92, 0.2)"

                            st.markdown(f"""
                            <div style="background: {bg_grad}; border: 1px solid {border_col}; border-radius: 8px; padding: 15px; text-align: center; box-shadow: 0 0 15px {shadow_col};">
                                <div style="font-size: 18px; font-weight: bold; color: #ffffff;">{signal['name']}</div>
                                <div style="font-size: 15px; color: {text_col}; font-weight: bold; margin-top: 8px;">{signal['icon']} 파워 스코어: {score:.1f}점</div>
                                <div style="font-size: 13px; color: #a0a0a0; margin-top: 5px;">순매수 강도: {int(signal['net_buy'] // 1000000):,}백만원 ({int(signal['buy_count'])}회 고래 매집)</div>
                            </div>
                            """, unsafe_allow_html=True)
                        else:
                            # 30점 이상 종목이 부족할 때 보여주는 채도 낮은 녹색 빈 슬롯 (자존심 유지용)
                            st.markdown(f"""
                            <div style="background: linear-gradient(135deg, #0a150e 0%, #050a06 100%); border: 1px dashed #2a4a35; border-radius: 8px; padding: 15px; text-align: center; box-shadow: none; opacity: 0.8;">
                                <div style="font-size: 18px; font-weight: bold; color: #5a8a6a;">탐지 대기 중...</div>
                                <div style="font-size: 15px; color: #2a4a35; font-weight: bold; margin-top: 8px;">🌱 파워 스코어: - </div>
                                <div style="font-size: 13px; color: #4a5a4a; margin-top: 5px;">현재 폭주 종목 없음</div>
                            </div>
                            """, unsafe_allow_html=True)
                st.write("---")

            if len(filtered_df) > 0:
                    # 🔌 [신호 복제 및 전처리 행렬 탄생]
                    # 🚀 [치명적 OOM 방지] 1개월치(15만건)를 표에 모두 그리면 Pandas Styler가 즉시 메모리를 폭파시킵니다!
                    # 지정된 fetch_limit 만큼만 렌더링하도록 브레이크를 겁니다.
                    if fetch_limit is not None:
                        display_df = filtered_df.head(fetch_limit).copy()
                    else:
                        display_df = filtered_df.copy()
                    
                    # 🚀 [상한가 직관성 패치] 찐 상한가 당일 체결 로그에만 로켓 뱃지 부여!
                    if show_only_upper_limit:
                        try:
                            upper_query_res = supabase.table("upper_limit_stocks").select("name, recorded_date").gte("recorded_date", start_date.strftime('%Y-%m-%d')).execute()
                            if upper_query_res.data:
                                upper_hits = set((item['name'], item['recorded_date']) for item in upper_query_res.data)
                                display_df['name'] = display_df.apply(
                                    lambda r: r['name'] + " 🚀" if (r['name'], r['date']) in upper_hits else r['name'], axis=1
                                )
                        except Exception as e:
                            pass
                            
                    # 🔥 [데이터프레임 시각화 강화] 핫 시그널 종목에 등급별 뱃지 부여
                    if 'hot_signals' in locals() and hot_signals:
                        hot_dict = {s['name']: s['icon'] for s in hot_signals}
                        # 이름에 이미 🚀가 붙어있을 수 있으므로 기존 이름 기준으로 맵핑
                        display_df['name'] = display_df['name'].apply(lambda x: x + f" {hot_dict[x.replace(' 🚀', '')]}" if x.replace(' 🚀', '') in hot_dict else x)
                    
                    # ⚡ [안전 퓨즈] 혹시나 테이블 데이터에 'side' 컬럼 신호가 비어있다면 에러 방지용 기본값 주입
                    if 'side' not in display_df.columns:
                        display_df['side'] = '매수'

                    # 1️⃣ 체결금액 단위를 '원' -> '백만원' 단위로 전압 다운 및 분기
                    display_df['buy_amount'] = display_df.apply(
                        lambda r: r['amount_krw'] / 1_000_000 if r['side'] == '매수' else 0, axis=1
                    ).fillna(0).astype(int)
                    
                    display_df['sell_amount'] = display_df.apply(
                        lambda r: r['amount_krw'] / 1_000_000 if r['side'] == '매도' else 0, axis=1
                    ).fillna(0).astype(int)
                    
                    display_df['unknown_amount'] = display_df.apply(
                        lambda r: r['amount_krw'] / 1_000_000 if r['side'] == '방향미상' else 0, axis=1
                    ).fillna(0).astype(int)

                    # 🔥 PyArrow 에러 방지용: 화면에 그리지 않는 날짜 컬럼 제거 🔥
                    if 'datetime' in display_df.columns:
                        display_df.drop(columns=['datetime'], inplace=True)

                    # 🎨 [피드백 3] 동시호가 틱 시간표시 붉은 백라이트 + 핵고래 색상 통합 칩셋
                    def style_rows(row):
                        styles = [''] * len(row)
                        
                        # ⏰ [광대역 필터] 15:20:00 포함, 그 이후에 들어오는 모든 장마감/장후 틱 처리
                        if row['time'] >= '15:20:00': 
                            styles[row.index.get_loc('time')] = 'background-color: #5c1d1d; color: #ff9999; font-weight: bold;'

                        # 🐋 매수/매도 레일별 고래 LED 하이라이트
                        total_amt_raw = row['amount_krw']
                        if total_amt_raw >= 1_000_000_000: # 10억 이상 레드 LED
                            if row['side'] == '매수':
                                styles[row.index.get_loc('buy_amount')] = 'background-color: #801a1a; color: white; font-weight: bold;'
                            elif row['side'] == '매도':
                                styles[row.index.get_loc('sell_amount')] = 'background-color: #2B4980; color: white; font-weight: bold;'
                            else:
                                styles[row.index.get_loc('unknown_amount')] = 'background-color: #666666; color: white; font-weight: bold;'
                        elif total_amt_raw >= 100_000_000: # 5억 이상 오렌지 LED
                            if row['side'] == '매수':
                                styles[row.index.get_loc('buy_amount')] = 'background-color: #c35b00; color: white; font-weight: bold;'
                            elif row['side'] == '매도':
                                styles[row.index.get_loc('sell_amount')] = 'background-color: #4B89b5; color: white; font-weight: bold;'
                            else:
                                styles[row.index.get_loc('unknown_amount')] = 'background-color: #555555; color: white; font-weight: bold;'
                        else:
                            if row['side'] == '매수':
                                styles[row.index.get_loc('buy_amount')] = 'background-color: #ff7b00; color: white; font-weight: bold;'
                            elif row['side'] == '매도':
                                styles[row.index.get_loc('sell_amount')] = 'background-color: #7B99e5; color: white; font-weight: bold;'
                            else:
                                styles[row.index.get_loc('unknown_amount')] = 'background-color: #444444; color: white; font-weight: bold;'
                                
                        return styles
                    
                    # 🔢 좌측 순번(No.) 컬럼 추가 (1번부터 시작)
                    display_df.insert(0, 'No.', range(1, len(display_df) + 1))
                    
                    # 🛠️ [교정 1 & 2] 스타일러 대상을 display_df로 바꾸고, 신형 style_rows 칩을 장착합니다!
                    styled_df = display_df.style \
                        .apply(style_rows, axis=1)
                    
                    # 🔘 행 클릭 시 동작 모드 선택 라디오 버튼
                    click_action = st.radio(
                        "👇 표에서 종목(행)을 클릭했을 때 동작을 선택하세요:", 
                        ["📊 시계열 추적 (차트 이동)", "💬 AI 요약 보기 (팝업)"], 
                        horizontal=True
                    )
                    
                    # 📊 최종 전광판 디스플레이 표출
                    grid_key = f"whale_log_board_main_{st.session_state.get('upper_limit_filter', False)}_{search_keyword}_{st.session_state.get('df_reset_counter', 0)}"
                    event = st.dataframe(
                        styled_df, 
                        # 🛠️ [교정 3] 출력 전광판 순서에서 amount_krw를 폐기하고, 신형 듀얼 레일을 배치합니다!
                        column_order=["No.", "date", "time", "name", "price", "volume", "buy_amount", "sell_amount", "unknown_amount", "market_type"],
                        
                        column_config={
                            "No.": st.column_config.NumberColumn("순번", format="%,d"),
                            "date": "체결일자",
                            "time": "체결시간",
                            "name": "종목명",
                            "price": st.column_config.NumberColumn(("\u00A0" * 16) + "체결가 (원)", format="%,d"),
                            "volume": st.column_config.NumberColumn(("\u00A0" * 16) + "체결량 (주)", format="%,d"),
                            "buy_amount": st.column_config.NumberColumn("매수금액 (백만)", format="%,d"), 
                            "sell_amount": st.column_config.NumberColumn("매도금액 (백만)", format="%,d"), 
                            "unknown_amount": st.column_config.NumberColumn("방미금액 (백만)", format="%,d"),
                            "market_type": "시장구분"
                        },
                        hide_index=True,  
                        height=620,       
                        use_container_width=False,
                        on_select="rerun",
                        selection_mode="single-row",
                        key=grid_key
                    )
                    
                    # 🎯 "더 보기" 버튼: 검색어가 없을 때, 가져온 데이터가 limit 이상이라면(더 있을 가능성이 높다면) 표출
                    if not search_keyword.strip() and len(df) >= fetch_limit:
                        st.markdown("<div style='margin-top: 5px;'></div>", unsafe_allow_html=True)
                        
                        col_btn, col_space = st.columns([3.5, 6.5])
                        with col_btn:
                            if st.button("⬇️ 다음 500건 더 가져오기...", use_container_width=True):
                                st.session_state['log_fetch_limit'] += 500
                                st.session_state['ignore_next_selection'] = True
                                st.rerun()

                    # ✅ 테이블 행 선택 이벤트 감지
                    if event and "selection" in event:
                        rows = event["selection"]["rows"]
                        if rows:
                            # 💡 [Ghost Selection 버그 방어] 버튼 클릭으로 인한 데이터 길이 변경 시 발생하는 가짜 선택 이벤트 무시
                            if st.session_state.get('ignore_next_selection', False):
                                st.session_state['ignore_next_selection'] = False
                            else:
                                selected_idx = rows[0]
                                # 💡 [IndexError 방지] 데이터 변경(필터/리로드) 시 이전 선택 인덱스가 남아있어 Out of bounds 발생하는 버그 방어
                                if selected_idx < len(display_df):
                                    raw_selected_stock = display_df.iloc[selected_idx]['name']
                                    ss = raw_selected_stock.replace(" 🚀", "").replace(" 👑", "").replace(" 🔥", "").replace(" 💥", "").replace(" ✨", "").replace(" 🌱", "")
                                    selected_stock = ss.replace("🚀", "").replace("👑", "").replace("🔥", "").replace("💥", "").replace("✨", "").replace("🌱", "").strip()
                                    
                                    needs_rerun = False
                                    
                                    if click_action == "💬 AI 요약 보기 (팝업)":
                                        row_code = display_df.iloc[selected_idx]['code'] if 'code' in display_df.columns else ""
                                        trigger = st.session_state.get('dialog_trigger_id', 0) + 1
                                        st.session_state['dialog_trigger_id'] = trigger
                                        st.session_state['show_summary_dialog'] = {
                                            "stock": selected_stock,
                                            "code": row_code,
                                            "trigger_id": trigger
                                        }
                                        st.session_state['df_reset_counter'] = st.session_state.get('df_reset_counter', 0) + 1
                                        needs_rerun = True
                                    else:
                                        st.session_state['pending_search'] = selected_stock
                                        st.session_state['last_search_keyword'] = selected_stock
                                        st.session_state['df_reset_counter'] = st.session_state.get('df_reset_counter', 0) + 1
                                        needs_rerun = True
                                        
                                    if needs_rerun:
                                        st.rerun()
                        else:
                            # 선택이 해제되거나 비어있을 때 플래그 리셋 (정상 렌더링 확인)
                            st.session_state.pop('last_summary_stock', None)
                            if st.session_state.get('ignore_next_selection', False):
                                st.session_state['ignore_next_selection'] = False
            else:
                st.info("포착된 고래 거래가 없습니다.")

elif choice == "📝 내 정보 수정":
    current_id = st.session_state['username']
    user_res = supabase.table("users").select("*").eq("username", current_id).execute()
    if user_res.data:
        user_data = user_res.data[0]
        try:
            db_phone = base64.b64decode(user_data['phone_encoded']).decode('utf-8')
        except:
            db_phone = ""
    
        render_profile_edit_panel(user_data, current_id, db_phone)

elif choice == "🛠️ 사용자 관리 사령탑":
    # 👑 최고 관리자 전용 제어반 함수 호출
    render_admin_panel()

# ------------------------------------------------------------------
# 🗺️ [내비게이션 동기화] 브라우저 뒤로가기(Query Params) 지원 (하단: State -> URL)
# ------------------------------------------------------------------
def update_query_params():
    current_page = st.session_state.get('scrn_select_radio', "체결 로그")
    if current_page != st.session_state.get("last_page"):
        st.query_params["page"] = current_page
        st.session_state["last_page"] = current_page
        
    current_upper = "true" if st.session_state.get('upper_limit_filter', False) else "false"
    if current_upper != st.session_state.get("last_upper"):
        st.query_params["upper"] = current_upper
        st.session_state["last_upper"] = current_upper

    if current_page == "수익율 자랑":
        current_view = st.session_state.get('brag_view_mode', "list")
        if current_view != st.session_state.get("last_view"):
            st.query_params["view"] = current_view
            st.session_state["last_view"] = current_view
            
        current_post_id = st.session_state.get('brag_selected_post')
        last_post_id = st.session_state.get("last_post_id")
        current_post_id_str = str(current_post_id) if current_post_id is not None else None
        
        if current_post_id_str != last_post_id:
            if current_post_id_str is not None:
                st.query_params["post_id"] = current_post_id_str
            else:
                if "post_id" in st.query_params:
                    del st.query_params["post_id"]
            st.session_state["last_post_id"] = current_post_id_str
    else:
        # 타 페이지 이동 시 자랑게시판 파라미터 삭제
        if "view" in st.query_params:
            del st.query_params["view"]
        if "post_id" in st.query_params:
            del st.query_params["post_id"]
        st.session_state["last_view"] = None
        st.session_state["last_post_id"] = None
        st.session_state['brag_selected_post'] = None 

update_query_params()