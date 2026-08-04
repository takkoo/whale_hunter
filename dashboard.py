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
import math  # 🌟 [신규 2026-08-01] 골든점수 로그 스케일 계산용(get_market_force_score/get_pair_buy_score)
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

# ------------------------------------------------------------------
# 🌟 [신규 2026-07-31] "테마킹" 화면 — 테마별 AI 요약 기능
# 개별 종목 AI요약(get_gemini/chatgpt_company_summary)과 동일한 패턴이지만,
# 하나의 종목이 아니라 "테마에 속한 대표 종목 몇 개"의 뉴스를 한꺼번에 모아서
# "왜 이 테마 전체가 오늘 강세/약세인지"를 분석하도록 프롬프트만 테마용으로 교체.
# 캐싱도 동일한 gemini_summaries 테이블을 재사용하되, stock_name 컬럼에
# "[THEME]테마명" / "[GPT-THEME]테마명" 같은 접두어를 붙여 종목 요약과 겹치지 않게 함.
# ------------------------------------------------------------------
def _fetch_theme_news_headlines(theme_name, rep_stocks, max_stocks=5, max_news_per_stock=3):
    """
    테마 대표 종목(rep_stocks: [{'name':.., 'code':.., 'net':..}, ...] 순매수 큰 순 정렬)
    상위 max_stocks개에 대해 네이버 금융 뉴스 제목을 긁어와 하나의 텍스트로 합쳐줌.
    반환: (합산 뉴스 원문 텍스트(AI 프롬프트용), 합산 뉴스 마크다운(화면 표시용))
    """
    combined_raw_parts = []
    combined_md_parts = []
    for stock_info in rep_stocks[:max_stocks]:
        s_name = stock_info.get('name', '')
        s_code = stock_info.get('code', '')
        if not s_code:
            continue
        try:
            _, news_md_one, news_raw_one, _ = get_naver_company_summary(s_code)
        except Exception:
            continue
        if news_raw_one and news_raw_one != "최근 관련 뉴스가 없습니다.":
            # 뉴스 개수 제한 (종목당 최대 max_news_per_stock개)
            raw_lines = news_raw_one.split("\n")[:max_news_per_stock]
            combined_raw_parts.append(f"[{s_name}]\n" + "\n".join(raw_lines))
            md_lines = news_md_one.split("\n")[:max_news_per_stock]
            combined_md_parts.append(f"**{s_name}**\n" + "\n".join(md_lines))

    combined_raw = "\n\n".join(combined_raw_parts) if combined_raw_parts else "최근 관련 뉴스가 없습니다."
    combined_md = "\n\n".join(combined_md_parts) if combined_md_parts else "최근 관련 뉴스가 없습니다."
    return combined_raw, combined_md

def get_gemini_theme_summary(theme_name, news_text=""):
    import google.generativeai as genai

    api_key = st.secrets.get("gemini", {}).get("api_key", None)
    if not api_key:
        raise ValueError("API_KEY_MISSING")

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-flash-latest')

    prompt = f"""한국 주식 시장의 '{theme_name}' 테마(업종/섹터)에 대해 다음 두 가지 항목으로 나누어 분석해줘.
주의: 답변 내용에 '(1~2줄)', '(3~4줄)' 같은 분량 지시어는 절대 출력하지 마.

**1. 테마 개요**
이 테마가 최근 시장에서 왜 주목받고 있는지 핵심 배경을 1~2줄로 요약해줘.

**2. 대표 종목 동향 및 평가**
아래는 이 테마의 대표 종목들에 대한 최근 뉴스 제목들이야. 이를 바탕으로 이 테마 전체의 호재, 악재, 전망을 서술식 말고 보기 좋게 한 줄씩 나열식(Bullet points)으로 명확하게 요약해 줘.
(반드시 아래 예시 포맷을 지켜서 작성할 것)
- [호재] ~~~
- [악재] ~~~
- [전망] ~~~

※ 주의사항: 요약할 때 기사에 언급된 특정 기업명, 기관명, 고유명사 등을 뭉뚱그리지 말고 구체적인 명칭을 반드시 그대로 명시할 것.

뉴스 제목이 없다면 일반적인 최근 시장에서의 이 테마 평가를 위 포맷으로 적어줘.

[대표 종목별 최근 뉴스 제목]
{news_text}
"""
    response = model.generate_content(
        prompt,
        request_options={"timeout": 60.0, "retry": None}
    )
    summary = response.text

    try:
        theme_key = f"[THEME]{theme_name}"
        supabase.table("gemini_summaries").delete().eq("stock_name", theme_key).execute()
        supabase.table("gemini_summaries").insert({
            "stock_name": theme_key,
            "news_text": news_text,
            "summary": summary
        }).execute()
    except Exception:
        pass

    return summary

def get_chatgpt_theme_summary(theme_name, news_text=""):
    api_key = st.secrets.get("openai", {}).get("api_key", None)
    if not api_key:
        raise ValueError("OPENAI_API_KEY_MISSING")

    client = openai.OpenAI(api_key=api_key)

    prompt = f"""한국 주식 시장의 '{theme_name}' 테마(업종/섹터)에 대해 다음 두 가지 항목으로 나누어 분석해줘.
주의: 답변 내용에 '(1~2줄)', '(3~4줄)' 같은 분량 지시어는 절대 출력하지 마.

**1. 테마 개요**
이 테마가 최근 시장에서 왜 주목받고 있는지 핵심 배경을 1~2줄로 요약해줘.

**2. 대표 종목 동향 및 평가**
아래는 이 테마의 대표 종목들에 대한 최근 뉴스 제목들이야. 이를 바탕으로 이 테마 전체의 호재, 악재, 전망을 서술식 말고 보기 좋게 한 줄씩 나열식(Bullet points)으로 명확하게 요약해 줘.
(반드시 아래 예시 포맷을 지켜서 작성할 것)
- [호재] ~~~
- [악재] ~~~
- [전망] ~~~

※ 주의사항: 요약할 때 기사에 언급된 특정 기업명, 기관명, 고유명사 등을 뭉뚱그리지 말고 구체적인 명칭을 반드시 그대로 명시할 것.

뉴스 제목이 없다면 일반적인 최근 시장에서의 이 테마 평가를 위 포맷으로 적어줘.

[대표 종목별 최근 뉴스 제목]
{news_text}
"""
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "당신은 증권가 최고의 주식 애널리스트입니다."},
            {"role": "user", "content": prompt}
        ],
        timeout=30.0
    )
    summary = response.choices[0].message.content

    try:
        theme_key = f"[GPT-THEME]{theme_name}"
        supabase.table("gemini_summaries").delete().eq("stock_name", theme_key).execute()
        supabase.table("gemini_summaries").insert({
            "stock_name": theme_key,
            "news_text": news_text,
            "summary": summary
        }).execute()
    except Exception as e:
        return f"ChatGPT 테마 요약 저장 중 오류 발생: {e}"

    return summary

# ------------------------------------------------------------------
# 🌟 [신규 2026-08-01] "실시간" 화면 — 국내/미국/일본/중국 "증시 시황" AI 요약 버튼
# 사용자 요청: 4개 버튼(국내/미국/일본/중국)을 누르면 팝업으로 "그 나라 증시 최근 상황"을
# 간단히 요약해서 보여줌. 개별 종목/테마 AI요약과 달리 여기서는 특정 종목 뉴스가 아니라
# "지수 자체의 등락"이 핵심 재료라서, 이미 프로젝트에서 쓰고 있는 FinanceDataReader(fdr)로
# 코스피/코스닥/다우/나스닥/S&P500/니케이225/상해종합 등 지수 시세를 직접 가져와 그 숫자를
# 근거로 Gemini에게 요약을 맡김. (네이버 "국내증시/해외증시" 뉴스 목록 페이지를 스크래핑하는
# 방법도 검토했으나, 이번 세션은 네트워크 제약으로 그 페이지의 실제 HTML 구조를 라이브로
# 검증할 수 없어 셀렉터가 정확한지 확신할 수 없었음 — 반면 지수 시세는 이미 이 파일 다른 곳
# 에서도 안정적으로 쓰고 있는 fdr 라이브러리로 가져오므로 신뢰도가 더 높다고 판단해 이 방식을
# 택함. 미국은 이미 수집 중인 us_theme_performance(테마별 등락률) 데이터도 곁들여
# "어떤 섹터가 강세/약세였는지"까지 반영함.)
#
# 캐싱: 기존 종목/테마 AI요약과 동일하게 gemini_summaries 테이블을 재사용(신규 테이블 생성 없음),
# stock_name 컬럼에 "[MARKET]국내" 같은 접두어를 붙여 종목/테마 요약과 겹치지 않게 함. 다만
# 캐시 유효기간은 종목요약(30일)과 다르게 "최소 10분"으로 짧게 잡아(사용자 확정), 여러 번 눌러도
# 10분 안에는 같은 요약을 재사용해 API를 다시 호출하지 않음(크레딧 절약). 나중에 비용이 감당할
# 만하면 _MARKET_CACHE_MINUTES 값만 줄이면 더 자주 갱신되게 조정 가능. 모델은 비용 절감을 위해
# Gemini 단일 모델만 사용(종목/테마 요약과 달리 ChatGPT 탭 없음 — 사용자가 직접 선택).
# ------------------------------------------------------------------
_MARKET_CACHE_MINUTES = 10

_MARKET_INDEX_SYMBOLS = {
    "국내": [("코스피", "KS11"), ("코스닥", "KQ11")],
    "미국": [("다우존스", "DJI"), ("나스닥", "IXIC"), ("S&P500", "US500")],
    "일본": [("니케이225", "JP225")],
    "중국": [("상해종합", "SSEC")],
}

def _fetch_market_index_snapshot(market_type):
    """market_type("국내"/"미국"/"일본"/"중국")에 해당하는 지수들의 최근 시세를 fdr로 가져와
    (LLM 프롬프트용 원문 텍스트, 화면 표시용 마크다운, 최신 기준일 문자열) 튜플로 반환.
    일부 지수 조회가 실패해도 나머지는 계속 진행(부분 실패 허용) — 휴장일 등으로 데이터가
    비어있을 수도 있으므로 그런 경우엔 아예 실패 표시를 반환함."""
    symbols = _MARKET_INDEX_SYMBOLS.get(market_type, [])
    raw_lines = []
    md_lines = []
    latest_date_str = ""
    end_dt = datetime.utcnow()
    start_dt = end_dt - timedelta(days=12)

    for label, code in symbols:
        try:
            df_idx = fdr.DataReader(code, start_dt.strftime("%Y-%m-%d"), end_dt.strftime("%Y-%m-%d"))
            if df_idx is None or df_idx.empty:
                continue
            df_idx = df_idx.tail(5)  # 최근 5거래일만
            last_row = df_idx.iloc[-1]
            last_close = last_row['Close']
            last_date = df_idx.index[-1].strftime("%Y-%m-%d")
            if not latest_date_str or last_date > latest_date_str:
                latest_date_str = last_date

            if 'Change' in df_idx.columns and pd.notna(last_row.get('Change')):
                chg_pct = last_row['Change'] * 100
            elif len(df_idx) >= 2:
                prev_close = df_idx.iloc[-2]['Close']
                chg_pct = ((last_close - prev_close) / prev_close) * 100 if prev_close else 0.0
            else:
                chg_pct = 0.0

            trend_str = ", ".join([f"{d.strftime('%m-%d')}:{r['Close']:,.2f}" for d, r in df_idx.iterrows()])
            raw_lines.append(f"[{label}({code})] {last_date} 종가 {last_close:,.2f} (전일대비 {chg_pct:+.2f}%) / 최근5일 추이: {trend_str}")
            arrow = "▲" if chg_pct >= 0 else "▼"
            md_lines.append(f"- **{label}**: {last_close:,.2f} ({arrow} {chg_pct:+.2f}%) — {last_date} 종가 기준")
        except Exception:
            continue

    # 🇺🇸 미국은 이미 수집돼 있는 테마별 등락률(us_theme_performance)도 곁들여 섹터 색깔을 더함
    if market_type == "미국":
        try:
            us_date, us_left, us_right = get_us_theme_top_movers(left_count=5)
            if us_date:
                theme_parts = [f"{it['theme_name']} {it['pct_change']:+.2f}%" for it in (us_left + us_right)]
                raw_lines.append(f"[미국 테마별 등락률({us_date} 마감 기준)] " + ", ".join(theme_parts))
        except Exception:
            pass

    raw_text = "\n".join(raw_lines) if raw_lines else "지수 데이터를 가져오지 못했습니다."
    md_text = "\n".join(md_lines) if md_lines else "지수 데이터를 가져오지 못했습니다 (휴장일이거나 일시적 오류일 수 있습니다)."
    return raw_text, md_text, latest_date_str


def get_gemini_market_briefing(market_type, index_data_text, latest_date_str=""):
    import google.generativeai as genai

    api_key = st.secrets.get("gemini", {}).get("api_key", None)
    if not api_key:
        raise ValueError("API_KEY_MISSING")

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-flash-latest')

    # 🔧 [수정 2026-08-01] 사용자 요청: "1. 지수 동향" 제목에 그 자료가 몇일자 기준인지 표시해줘야
    # 휴일에 화면을 봐도(전 거래일 자료가 표시되는 상황) 헷갈리지 않음. AI가 날짜를 직접 계산/추출하게
    # 맡기면 틀릴 수 있어서, _fetch_market_index_snapshot이 이미 계산해둔 최신 기준일(latest_date_str,
    # "YYYY-MM-DD")을 파이썬에서 "N월 N일" 형식으로 미리 변환해 프롬프트에 못박아 넣음.
    date_label = ""
    if latest_date_str:
        try:
            # 🔧 [주의] strftime의 "%-m"/"%-d"(0 안 채운 월/일)는 리눅스 전용 확장이라 배포
            # 환경(OS)에 따라 깨질 수 있어, 이식성 안전한 방식으로 직접 "N월 N일" 조립.
            _d = datetime.strptime(latest_date_str, "%Y-%m-%d")
            date_label = f"{_d.month}월 {_d.day}일"
        except Exception:
            date_label = latest_date_str

    date_instruction = (
        f"'1. 지수 동향' 소제목 뒤에 반드시 ' - {date_label} 기준'을 그대로 덧붙여서 "
        f"'1. 지수 동향 - {date_label} 기준'처럼 출력해줘(자료 기준일을 사용자가 한눈에 알 수 있게)."
        if date_label else
        "자료에 명확한 기준일이 없으면 '1. 지수 동향' 제목은 그대로 두고, 본문에서 데이터가 비어있거나 오래됐을 가능성을 언급해줘."
    )

    prompt = f"""아래는 '{market_type}' 증시의 최근 주요 지수 시세 데이터야. 이 데이터를 바탕으로 '{market_type}' 증시의 최근 시황을 간단하게 요약해줘.
주의: 답변 내용에 '(1~2줄)' 같은 분량 지시어는 절대 출력하지 마.
만약 데이터가 비어있거나 부족하면, 휴장일이거나 데이터 수집에 문제가 있었을 가능성을 언급해줘.

**1. 지수 동향**
주요 지수들의 최근 종가와 등락률을 서술식 말고 보기 좋게 한 줄씩 나열식(Bullet points)으로 정리해줘.
- [지수명] ~~~
{date_instruction}

**2. 특이사항 및 시사점**
데이터에서 눈에 띄는 특징(강세/약세 업종, 변동성, 추세 등)을 서술식 말고 나열식으로 짧게 짚어줘.
- [특징] ~~~

[최근 지수 시세 데이터]
{index_data_text}
"""
    response = model.generate_content(
        prompt,
        request_options={"timeout": 60.0, "retry": None}
    )
    summary = response.text

    try:
        market_key = f"[MARKET]{market_type}"
        # 같은 시장의 예전 요약본(또는 만료된 캐시)을 깔끔하게 지웁니다
        supabase.table("gemini_summaries").delete().eq("stock_name", market_key).execute()
        supabase.table("gemini_summaries").insert({
            "stock_name": market_key,
            "news_text": index_data_text,
            "summary": summary
        }).execute()
    except Exception:
        pass  # 저장 실패 시에도 정상적으로 요약본 반환

    return summary


@st.dialog("🌏 증시 시황 요약", dismissible=False)
def show_market_briefing_dialog(market_type, trigger_id=0):
    # 🔧 [수정 2026-08-03] 예전엔 CSS로 X 버튼을 숨겼는데(`button[aria-label="Close"]` 셀렉터),
    # Streamlit이 이후 버전에서 st.dialog에 공식 `dismissible` 파라미터를 추가하면서 다이얼로그
    # 내부 DOM 구조가 바뀌어 그 CSS 셀렉터가 더 이상 안 먹혀서 X 버튼이 다시 보이는 문제가 있었음
    # (사용자가 스크린샷으로 재확인). CSS 땜빵 대신 공식 파라미터 `dismissible=False`로 교체 —
    # 이러면 X 버튼 자체가 없어지고, 바깥 클릭/ESC로도 안 닫혀서 "닫기 (확인)" 버튼으로만 닫힘.

    st.markdown(f"<h3 style='margin: 0; padding: 0; margin-bottom: 4px;'>🌏 {market_type} 증시 시황</h3>", unsafe_allow_html=True)

    market_key = f"[MARKET]{market_type}"
    cached_summary = None
    try:
        ten_min_ago = (datetime.utcnow() - timedelta(minutes=_MARKET_CACHE_MINUTES)).isoformat()
        cache_res = supabase.table("gemini_summaries").select("summary").eq("stock_name", market_key).gte("created_at", ten_min_ago).order("created_at", desc=True).limit(1).execute()
        if cache_res.data:
            cached_summary = cache_res.data[0]['summary']
    except Exception:
        pass

    if cached_summary:
        # 🔧 [수정 2026-08-01, 2번째] 사용자 요청: "캐시 — API 재호출 없음" 안내 캡션이 화면을
        # 지저분하게 만든다고 판단해 제거. 캐시 여부는 이제 화면에 노출하지 않고 내부적으로만 사용.
        render_ai_summary_box(cached_summary)
    else:
        # 🔧 [수정 2026-08-01] 사용자 요청: 캐시가 없을 때 "AI 요약 생성" 버튼을 한 번 더 누르게
        # 하지 말고, 팝업이 뜨자마자 원클릭으로 바로 생성해서 보여줌. 대신 st.spinner로 "진행 중"임을
        # 명확히 표시(사용자가 이 스피너 표시를 전제 조건으로 확인함) — 버튼 클릭이라는 안전장치가
        # 빠지는 대신, 이 다이얼로그 자체가 사용자의 명시적 클릭(4개 버튼 중 하나)으로만 열리고
        # 10분 캐시가 여전히 재호출을 막아주므로 크레딧 남용 위험은 낮음.
        with st.spinner(f"{market_type} 증시 지수 시세를 가져오는 중..."):
            index_raw, index_md, latest_date = _fetch_market_index_snapshot(market_type)

        st.markdown("##### 📊 참고 지수 시세")
        st.info(index_md)

        with st.spinner(f"Gemini AI가 {market_type} 증시 지수 데이터를 바탕으로 시황을 요약하는 중입니다..."):
            try:
                briefing_summary = get_gemini_market_briefing(market_type, index_raw, latest_date)
                render_ai_summary_box(briefing_summary)
            except Exception as e:
                err_msg = str(e)
                if "API_KEY_MISSING" in err_msg:
                    st.warning("⚠️ `.streamlit/secrets.toml` 파일에 Gemini API Key가 설정되지 않았습니다.")
                elif "429" in err_msg or "quota" in err_msg.lower():
                    st.warning("⚠️ **Gemini AI 무료 제공량 초과 (Rate Limit)** — 잠시 후 다시 시도하거나 내일 다시 시도해주세요.")
                elif "504" in err_msg or "deadline" in err_msg.lower():
                    st.error("⚠️ **구글 AI 서버 응답 지연 (504 Timeout)** — 잠시 후 창을 닫고 버튼을 다시 눌러주세요.")
                elif "503" in err_msg or "high demand" in err_msg.lower():
                    st.warning("⚠️ **구글 AI 서버 과부하 (503)** — 1~2분 후 다시 시도해 주세요.")
                else:
                    st.error(f"Gemini AI 호출 중 오류가 발생했습니다: {e}")

    if st.button("닫기 (확인)", use_container_width=True, key=f"market_dlg_close_{market_type}_{trigger_id}"):
        st.session_state.pop('show_market_briefing_dialog', None)
        st.rerun()

# 🔧 [주의 2026-08-01] 이 다이얼로그의 세션스테이트 트리거 체크(if 'show_market_briefing_dialog' in
# st.session_state: ...)는 일부러 여기(함수 정의 바로 아래)에 두지 않음! show_market_briefing_dialog가
# 내부적으로 호출하는 render_ai_summary_box()와 get_us_theme_top_movers()가 이 지점보다 훨씬 아래에서
# 정의되는데, 이 스크립트는 매 상호작용마다 위→아래로 전체 재실행되므로, 트리거 체크가 그 함수들의
# def문보다 먼저 실행되면 "아직 정의 안 됨" NameError가 남(위 get_themes_for_stocks 이동 사례와 동일한
# 함정). 그래서 트리거 체크는 실제 버튼이 있는 "실시간" 화면 섹션(하단, 두 함수 정의 이후 지점)에 배치함.

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

    # 3.5 🌟 [신규 2026-08-01] "증시 시황 요약"(get_gemini_market_briefing) 전용 배색 —
    # "1. 지수 동향" 섹션의 [지수명] 태그는 빨간색, "2. 특이사항 및 시사점" 섹션의 [특징] 태그는
    # 진갈색/찐청색을 번갈아 적용(사용자가 참고 이미지로 요청한 배색 그대로). 이 함수는 종목/테마
    # 요약에도 재사용되는 공용 함수라, "지수 동향" 문구가 있을 때(=시장 시황 요약일 때)만 이 로직을
    # 타도록 조건을 걸어서 위 2)/3)번 색칠(종목/테마용 [호재]/[악재]/[전망])과 절대 안 겹치게 함.
    if "지수 동향" in html_text:
        market_red_style = "color: #ff4b4b; font-weight: bold;"
        # 🔧 [수정 2026-08-03] 사용자가 "[기술주 중심 상승]" 태그가 어두운 초록 배경에 묻혀서 잘
        # 안 보인다고 지적 — 첫 번째 색(진갈색 #8B4513)을 RGB 채널별로 약 30% 밝게 조정
        # (139,69,19 → 181,90,25 = #B55A19). 두 번째 색(찐청색 #1565C0)은 지적 없었으니 그대로 유지.
        market_alt_colors = ["#B55A19", "#1565C0"]  # 밝은 갈색(수정됨), 찐청색 순서로 번갈아 적용

        split_match = re.search(r'2\.\s*특이사항\s*및\s*시사점', html_text)
        if split_match:
            part1, part2 = html_text[:split_match.start()], html_text[split_match.start():]
        else:
            part1, part2 = html_text, ""

        part1 = re.sub(r'(\[[^\[\]]+\])', rf'<span style="{market_red_style}">\1</span>', part1)

        _alt_counter = [0]
        def _market_alt_repl(m):
            color = market_alt_colors[_alt_counter[0] % 2]
            _alt_counter[0] += 1
            return f'<span style="color:{color}; font-weight: bold;">{m.group(1)}</span>'
        part2 = re.sub(r'(\[[^\[\]]+\])', _market_alt_repl, part2)

        html_text = part1 + part2

    # 4. 시인성 높은 다크 그린 배경 컨테이너 렌더링
    container_html = f"""
    <div style="background-color: rgba(30, 50, 35, 0.45); border: 1px solid rgba(46, 125, 50, 0.5); border-radius: 8px; padding: 16px; font-size: 0.95em; line-height: 1.7; color: #e0e0e0; margin-bottom: 12px;">
        {html_text}
    </div>
    """
    st.markdown(container_html, unsafe_allow_html=True)

# 🔧 [위치 이동 2026-07-31] 원래는 이 아래 TOP10 화면 쪽에 정의되어 있었는데,
# show_summary_dialog()가 종목 테마 표시를 위해 이 함수를 호출하게 되면서 문제가 생김:
# 이 스크립트는 위에서 아래로 한 번에 실행되는데, 만약 이 dialog가 (아래 세션스테이트 트리거 블록에서)
# 이 함수의 원래 정의 위치보다 앞에서 먼저 호출되면 "get_themes_for_stocks가 아직 정의 안 됨" 에러가 남.
# 그래서 호출부(show_summary_dialog, 그 아래 트리거 블록)보다 앞으로 정의를 옮김. supabase 클라이언트만
# 있으면 되는 함수라 위치를 옮겨도 동작은 완전히 동일함.
def get_themes_for_stocks(stock_names):
    if not stock_names:
        return {}
    try:
        res = supabase.table('stock_themes').select('stock_name, theme_names').in_('stock_name', stock_names).execute()
        return {row['stock_name']: row['theme_names'] for row in res.data}
    except Exception as e:
        return {}

# 🔧 [수정 2026-07-31, 3번째] table 레이아웃으로 바꾼 뒤에도 다이얼로그 기본 폭이 좁아서
# 그 안에서 텍스트가 원치 않게 줄바꿈되는 문제(종목코드가 이름 아래로, 52주고저/현재가가
# 2줄로 분리)가 있어 사용자가 지적함 → 처음엔 width="large"로 시도했으나 사용자가 "너무 넓어졌다,
# 이상해 보인다"고 피드백 → width="large"(large/small 이분법이라 세밀 조절 불가)는 제거하고,
# 원래 기본(small) 폭 그대로 두되 CSS로 다이얼로그 컨테이너 자체의 폭만 20% 정도 더 넓힘
# ([수정 2026-07-31, 4번째] 아래 CSS 참고) + metrics_html의 이름/코드, PER정보 두 줄 각각에
# white-space: nowrap을 줘서 웬만하면 줄바꿈 자체가 안 일어나게 함.
@st.dialog("🏢 기업 요약 및 AI 분석", dismissible=False)
def show_summary_dialog(stock_name, stock_code="", trigger_id=0):
    import FinanceDataReader as fdr

    # 🔧 [수정 2026-07-30] 우측 상단 기본 X 닫기 버튼 제거.
    # X로 닫으면 Streamlit이 스크립트 rerun을 트리거하지 않아서(Streamlit 공식 이슈 #8507) 우리 쪽
    # session_state['show_summary_dialog'] 정리 코드가 아예 실행이 안 되고, 그래서 다음 자동새로고침 때
    # 창이 또 뜨는 버그가 있었음. "닫기 (확인)"/"관심종목 추가" 버튼만 쓰도록 X를 아예 숨김.
    #
    # 🔧 [수정 2026-08-03] 위 X 숨기기를 CSS 셀렉터(`button[aria-label="Close"]`)로 해뒀었는데,
    # Streamlit이 이후 버전에서 st.dialog에 공식 `dismissible` 파라미터를 추가하면서 다이얼로그
    # 내부 DOM 구조가 바뀌어 이 셀렉터가 더 이상 안 먹히고 X 버튼이 다시 보이는 문제가 있었음
    # (사용자가 스크린샷으로 재확인). CSS 땜빵 대신 위 데코레이터에 공식 파라미터 `dismissible=False`를
    # 줘서 교체 — X 버튼 자체가 사라지고 바깥 클릭/ESC로도 안 닫힘. 폭 조정용 CSS는 계속 유지.
    #
    # 🔧 [수정 2026-07-31, 4번째] width="large" 파라미터가 너무 큰 폭 점프(작음↔큼 이분법)라
    # 사용자가 "이상해 보인다"고 피드백함 → 대신 기본(small) 다이얼로그에 CSS로 직접
    # width/max-width를 지정해서 기존 대비 약 20%만 넓힘(기본 small 폭이 대략 500px대라고
    # 알려져 있어 20% 증가분인 ~620px로 설정 — 정확한 기본값은 Streamlit 버전마다 조금씩 다를 수
    # 있어서 근사치임. 더 좁게/넓게 보이면 이 px 값만 조정하면 됨).
    st.markdown(
        '<style>'
        'div[aria-label="dialog"] { width: 620px !important; max-width: 620px !important; }'
        '</style>',
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

    # 🌟 [신규 2026-07-31] 사용자 요청: 종목명 바로 아래에 이 종목이 속한 테마명을 표시.
    # stock_themes 테이블(100개 종목만 매핑)을 기존 get_themes_for_stocks()로 조회 —
    # 2개 이상의 테마에 속해도 최대 2개까지만, 각각 한 줄씩 보여줌. 매핑이 없으면 아예 표시 안 함.
    theme_line_html = ""
    try:
        theme_map_dlg = get_themes_for_stocks([stock_name])
        theme_str_dlg = theme_map_dlg.get(stock_name, "")
        if theme_str_dlg:
            theme_names_dlg = [t.strip() for t in theme_str_dlg.split(',') if t.strip()][:2]
            if theme_names_dlg:
                theme_line_html = (
                    "<div style='font-size: 0.85em; color: #e0e0e0; line-height: 1.4; font-weight: normal; margin: 2px 0 8px 0;'>"
                    + "<br>".join([f"🏷️ {t}" for t in theme_names_dlg])
                    + "</div>"
                )
    except Exception:
        theme_line_html = ""

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

        # 🔧 [수정 2026-07-31, 재수정] 처음엔 종목명→테마→PER 순으로 전부 세로로 쌓았는데, 사용자가
        # "PER 등의 표시는 원래 그대로(옆 빈공간에 두려고 일부러 그렇게 만든 것) 두고, 테마 태그만
        # 지금처럼(이름 바로 아래, 왼쪽정렬) 추가해달라"고 정정함 — 즉 세로 스택 길이가 늘어나는 걸
        # 최소화하고 싶다는 의도. 그래서 원래의 가로 배치(flex row) 레이아웃은 그대로 복원하되,
        # "종목명 + 테마"만 한 세로 컬럼으로 묶어서 그 컬럼 전체를 PER 정보 옆(오른쪽 빈 공간)에 배치함.
        # → 종목명 바로 아래에 테마가 오면서도(왼쪽정렬 유지), PER 정보는 예전처럼 옆에 그대로 남음.
        #
        # 🐛 [버그 수정 2026-07-31] 삼성전기(테마 매핑 없는 종목, theme_line_html="")에서 팝업이
        # HTML 태그가 그대로 텍스트로 노출되는 코드블록처럼 깨져 보이는 문제 발견(삼성전자는 정상).
        # 원인: 위 템플릿을 여러 줄 들여쓰기된 f-string(""" ... """)으로 작성했는데, theme_line_html이
        # 빈 문자열이면 그 줄이 "공백만 있는 빈 줄"이 되고, Markdown은 "빈 줄 다음에 오는 4칸 이상
        # 들여쓰기된 텍스트"를 코드블록으로 해석하는 규칙이 있어서, 이후의 모든 HTML이 그대로
        # 문자로 노출돼버림(테마가 있는 종목은 그 줄이 비지 않아서 우연히 문제가 안 드러났던 것).
        # 해결: 줄바꿈/들여쓰기가 전혀 없는 한 줄짜리 문자열로 합쳐서 Markdown의 블록 파싱 규칙에
        # 애초에 걸리지 않도록 함 — 빈 테마든 아니든 항상 안전하게 렌더링됨.
        #
        # 🐛 [버그 수정 2026-07-31, 2번째] SK하이닉스(테마 1개, "AI 반도체")에서 PER/PBR/ROE 정보
        # 전체가 이름 옆이 아니라 그 아래 새 줄로 뚝 떨어져서 다시 세로로 쌓이는 문제 발견.
        # 원인: 위 flex 컨테이너에 flex-wrap: wrap이 걸려 있었는데, "종목명+테마" 컬럼에 테마 줄이
        # 추가되면서 그 컬럼의 고유 너비(자기 내용 중 가장 넓은 줄 기준)가 넓어졌고, 그 결과 "이름+테마"
        # 칸 + "PER정보" 칸의 합산 너비가 팝업 폭을 넘어서면서 flex-wrap이 PER정보 칸을 다음 줄로
        # 밀어버린 것(테마가 없는 종목은 왼쪽 칸이 좁아서 안 걸렸던 것뿐). 즉 flex-wrap 자체가
        # "옆 공간에 계속 붙어있어야 한다"는 요구사항과 상충함.
        # 해결: flex 대신 CSS table 레이아웃(display: table/table-row/table-cell)으로 교체.
        # table-cell은 내용이 넘치면 그 칸 안에서 줄바꿈될 뿐, flex처럼 칸 전체가 다음 "행"으로
        # 떨어지는 일이 없어서 이름/테마 칸과 PER정보 칸이 항상 나란히 유지됨.
        metrics_html = (
            "<div style='display: table; width: 100%; margin-bottom: 10px;'>"
            "<div style='display: table-row;'>"
            "<div style='display: table-cell; vertical-align: top; padding-right: 16px; white-space: nowrap;'>"
            f"<h3 style='margin: 0; padding: 0; white-space: nowrap;'>{stock_name} {f'({stock_code})' if stock_code else ''}</h3>"
            f"{theme_line_html}"
            "</div>"
            "<div style='display: table-cell; vertical-align: top; font-size: 0.85em; color: #e0e0e0; line-height: 1.4; font-weight: normal; white-space: nowrap;'>"
            f"[ PER {per} / PBR {pbr} / ROE {roe_str} ]<br>"
            f"[ 52주고/저 {high52} / {low52} ] &nbsp;&nbsp;[ 현재가 {price} ]"
            "</div>"
            "</div>"
            "</div>"
        )
        st.markdown(metrics_html, unsafe_allow_html=True)
    else:
        st.markdown(f"<h3 style='margin: 0; padding: 0; margin-bottom: 4px;'>{stock_name} {f'({stock_code})' if stock_code else ''}</h3>", unsafe_allow_html=True)
        if theme_line_html:
            st.markdown(theme_line_html, unsafe_allow_html=True)

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
                st.info("💡 버튼을 눌러 최근 30일 내의 새로운 분석을 시작하세요.")
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

# ------------------------------------------------------------------
# 🌟 [신규 2026-07-31] "테마킹" 화면 — 테마별 AI 요약 팝업
# 개별 종목의 "🏢 기업 요약 및 AI 분석"(show_summary_dialog)과 동일한 UX(다이얼로그+탭)를
# 테마 단위로 재구성. 테마 대표 종목 상위 몇 개의 뉴스를 모아 Gemini/ChatGPT에 넘겨 분석받음.
# ------------------------------------------------------------------
@st.dialog("🏷️ 테마 요약 및 AI 분석", dismissible=False)
def show_theme_summary_dialog(theme_name, rep_stocks, trigger_id=0):
    # 🔧 [수정 2026-08-03] X 닫기 버튼 제거 방식을 CSS 셀렉터에서 공식 `dismissible=False`
    # 파라미터로 교체 (show_summary_dialog와 동일한 이유 — 기존 CSS가 Streamlit 버전업으로 깨짐).

    stock_names_str = ", ".join([s['name'] for s in rep_stocks[:5]])
    st.markdown(f"<h3 style='margin: 0; padding: 0; margin-bottom: 4px;'>🏷️ {theme_name}</h3>", unsafe_allow_html=True)
    st.caption(f"대표 종목: {stock_names_str}")

    with st.spinner("대표 종목들의 최근 뉴스를 모으는 중..."):
        theme_news_raw, theme_news_md = _fetch_theme_news_headlines(theme_name, rep_stocks)

    tab1_t, tab2_t, tab3_t = st.tabs(["📰 대표 종목 뉴스 모아보기", "🤖 Gemini AI 테마 분석", "💡 ChatGPT AI 테마 분석"])

    with tab1_t:
        st.markdown("##### 📰 대표 종목별 최근 뉴스")
        st.warning(theme_news_md if theme_news_md else "최근 뉴스가 없습니다.")

    with tab2_t:
        db_summary_t = None
        thirty_days_ago_t = (datetime.utcnow() - timedelta(days=30)).isoformat()
        theme_key_gemini = f"[THEME]{theme_name}"
        try:
            db_res_t = supabase.table("gemini_summaries").select("summary").eq("stock_name", theme_key_gemini).eq("news_text", theme_news_raw).gte("created_at", thirty_days_ago_t).limit(1).execute()
            if db_res_t.data:
                db_summary_t = db_res_t.data[0]['summary']
        except Exception:
            pass

        if db_summary_t:
            render_ai_summary_box(db_summary_t)
        else:
            st.info("💡 처음 조회하는 뉴스 조합이거나 기존 분석이 만료(30일 경과)되었습니다. 아래 버튼을 눌러 AI 분석을 갱신하세요.")
            if st.button("🤖 Gemini AI 테마 분석 시작", key=f"gemini_theme_btn_{theme_name}"):
                with st.spinner("Gemini AI가 테마 대표 종목 뉴스를 바탕으로 분석 중입니다..."):
                    try:
                        gemini_summary_t = get_gemini_theme_summary(theme_name, theme_news_raw)
                        render_ai_summary_box(gemini_summary_t)
                    except Exception as e:
                        err_msg = str(e)
                        if "API_KEY_MISSING" in err_msg:
                            st.warning("⚠️ `.streamlit/secrets.toml` 파일에 Gemini API Key가 설정되지 않았습니다.")
                        elif "429" in err_msg or "quota" in err_msg.lower():
                            st.warning("⚠️ **Gemini AI 무료 제공량 초과 (Rate Limit)** — 잠시 후 다시 시도하거나 내일 다시 시도해주세요.")
                        elif "504" in err_msg or "deadline" in err_msg.lower():
                            st.error("⚠️ **구글 AI 서버 응답 지연 (504 Timeout)** — 잠시 후 버튼을 다시 눌러주세요.")
                        elif "503" in err_msg or "high demand" in err_msg.lower():
                            st.warning("⚠️ **구글 AI 서버 과부하 (503)** — 1~2분 후 다시 시도해 주세요.")
                        else:
                            st.error(f"Gemini AI 호출 중 오류가 발생했습니다: {e}")

    with tab3_t:
        db_summary_gpt_t = None
        theme_key_gpt = f"[GPT-THEME]{theme_name}"
        thirty_days_ago_gpt_t = (datetime.utcnow() - timedelta(days=30)).isoformat()
        try:
            db_res_gpt_t = supabase.table("gemini_summaries").select("summary").eq("stock_name", theme_key_gpt).eq("news_text", theme_news_raw).gte("created_at", thirty_days_ago_gpt_t).limit(1).execute()
            if db_res_gpt_t.data:
                db_summary_gpt_t = db_res_gpt_t.data[0]['summary']
        except Exception:
            pass

        if db_summary_gpt_t:
            render_ai_summary_box(db_summary_gpt_t)
        else:
            st.info("💡 버튼을 눌러 최근 30일 내의 새로운 분석을 시작하세요.")
            if st.button("💡 ChatGPT AI 테마 분석 시작", key=f"chatgpt_theme_btn_{theme_name}"):
                with st.spinner("ChatGPT(gpt-4o-mini)가 테마 대표 종목 뉴스를 바탕으로 분석 중입니다..."):
                    try:
                        chatgpt_summary_t = get_chatgpt_theme_summary(theme_name, theme_news_raw)
                        render_ai_summary_box(chatgpt_summary_t)
                    except Exception as e:
                        err_msg = str(e)
                        if "OPENAI_API_KEY_MISSING" in err_msg:
                            st.warning("⚠️ `.streamlit/secrets.toml` 파일에 OpenAI API Key가 설정되지 않았습니다.")
                        elif "429" in err_msg or "quota" in err_msg.lower() or "insufficient_quota" in err_msg.lower():
                            st.warning("⚠️ **ChatGPT API 잔액 부족 또는 한도 초과**")
                        else:
                            st.error(f"ChatGPT API 호출 중 오류가 발생했습니다: {e}")

    if st.button("닫기 (확인)", use_container_width=True, key=f"theme_dlg_close_{theme_name}_{trigger_id}"):
        st.session_state.pop('show_theme_summary_dialog', None)
        st.rerun()

if 'show_theme_summary_dialog' in st.session_state:
    data_t = st.session_state['show_theme_summary_dialog']
    show_theme_summary_dialog(data_t['theme'], data_t.get('rep_stocks', []), data_t.get('trigger_id', 0))

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

# (get_themes_for_stocks 함수는 2026-07-31에 이 위치에서 파일 상단(show_summary_dialog 바로 위)으로
#  이동함 — 이유는 그 이동 지점의 주석 참고. 이 자리엔 더 이상 정의가 없음, 삭제된 것 아님.)

# 🌟 [신규 2026-08-01] 골든점수 계산 공통 헬퍼: "시장세력수급"(총 순매수 로그 스케일)과
# "쌍끌이/비쌍끌이"(외국인·기관 조합 로그 스케일) 점수 산출 로직을 한 곳에 모음.
# 이 두 항목의 계산식은 원래 골든픽 화면(~4900번대 줄)/차트 호버(~2260번대 줄)/관심종목 화면
# (~5250번대 줄) 이렇게 3곳에 완전히 동일하게 복제돼 있었는데, 이번 로그 스케일 전환을 계기로
# 아예 공통 함수로 뽑아내 앞으로는 여기 한 곳만 고치면 3곳 모두에 반영되게 함.
#
# 배경(2026-08-01, 사용자 지적): 기존 방식은 총 순매수 300억만 넘으면 무조건 만점(+15)을 줘서
# 300억짜리와 4만억짜리 종목이 똑같이 취급되는 변별력 문제가 있었음. 또한 "외/기 쌍끌이가
# 아니면 무조건 -12점" 룰은, 한쪽이 압도적으로 사고 다른 한쪽이 아주 조금만 팔아도(그 매도액이
# -100억만 넘으면) 그대로 -12점 처리해버려서, 실제로는 총액 기준으로 매우 강한 매수인 종목까지
# 부당하게 깎이는 문제가 있었음. 로그 스케일 기반으로 교체해 이 두 문제를 모두 해결.
#
# 사용자와 합의한 기준: 로그 스케일의 "만점 기준"(이 금액이면 최고점)은 50,000억원 — 최근
# SK하이닉스/삼성전자가 찍은 3~4만억대 최고 기록에 약간의 여유를 둔 값. 시장 거래 규모가
# 구조적으로 더 커지면(예: 몇 년 뒤 대형주 거래대금이 지금보다 훨씬 커지면) 이 상수 하나만
# 올려주면 전체 스케일이 같이 재조정됨.
_GOLDEN_SCORE_LOG_REF = 50000

def _golden_log_ratio(amount_eok):
    """amount_eok(억원, 0 이상)을 0~1 사이 로그 스케일 비율로 변환.
    _GOLDEN_SCORE_LOG_REF(50,000)억원이면 1.0(만점 비율)."""
    if amount_eok <= 0:
        return 0.0
    ratio = math.log10(1 + amount_eok) / math.log10(1 + _GOLDEN_SCORE_LOG_REF)
    return max(0.0, min(1.0, ratio))

def get_market_force_score(total_net):
    """'시장세력수급' 항목 점수(0~15). 총 순매수 금액(억원)의 로그 스케일.
    예전엔 300억만 넘으면 무조건 만점이라 변별력이 없었는데, 로그 스케일로 바꿔서
    수만억대 초대형 매수와 수백억대 매수를 구분함."""
    if total_net <= 0:
        return 0
    return round(15 * _golden_log_ratio(total_net))

def get_pair_buy_score(frgn_net, orgn_net):
    """'쌍끌이/비쌍끌이' 항목 점수와 사유 텍스트를 (score, reason) 튜플로 반환.
    - 외국인+기관 둘 다 순매수(진짜 쌍끌이): 총액 로그 스케일로 5단계(+1~+9, 만점은
      다른 항목들의 기존 만점과 동일하게 +9로 유지).
    - 한쪽이라도 순매도(쌍끌이 아님): 총 순매수액(부호 있음)의 로그 스케일로 10단계.
      총액이 여전히 플러스면(한쪽만 소폭 매도, 전체는 강한 매수) +1~+9까지 갈 수 있고,
      총액 자체가 마이너스면(둘 다 팔거나 매도 우위) 예전 덤핑 페널티와 같은 수준인
      최대 -12점까지 감점됨(사용자가 기존 -12 페널티 값을 그대로 유지하기로 확정)."""
    total_net = frgn_net + orgn_net
    ratio = _golden_log_ratio(abs(total_net))

    if frgn_net > 0 and orgn_net > 0:
        if ratio >= 0.8:
            return 9, "🔥 초대형 외/기 쌍끌이"
        elif ratio >= 0.6:
            return 7, "🔥 대형 외/기 쌍끌이"
        elif ratio >= 0.4:
            return 5, "🔥 외/기 쌍끌이"
        elif ratio >= 0.2:
            return 3, "🔥 외/기 소규모 쌍끌이"
        elif ratio > 0:
            return 1, ""
        else:
            return 0, ""
    elif total_net > 0:
        if ratio >= 0.8:
            return 9, "🔥 편측매도에도 총액 초강세"
        elif ratio >= 0.6:
            return 7, "🔥 편측매도에도 총액 강세"
        elif ratio >= 0.4:
            return 5, "편측매도 있으나 총액 우위"
        elif ratio >= 0.2:
            return 3, ""
        elif ratio > 0:
            return 1, ""
        else:
            return 0, ""
    elif total_net < 0:
        if ratio >= 0.8:
            return -12, "⚠️ 외인/기관 동반 대량 순매도"
        elif ratio >= 0.6:
            return -9, "⚠️ 외인/기관 대량 순매도"
        elif ratio >= 0.4:
            return -6, "⚠️ 외인/기관 순매도 우위"
        elif ratio >= 0.2:
            return -3, ""
        elif ratio > 0:
            return -1, ""
        else:
            return 0, ""
    else:
        return 0, ""

# 🌟 [신규 2026-08-03] 뉴스감성 등급 변환 공통 헬퍼 — 사용자 요청으로 기존 -5~+5 숫자 표시를
# 신용등급 스타일(AAA~F) 11단계 문자 등급으로 바꿈. "고래 골든픽"/"내 관심종목" 두 화면이
# 뉴스감성 컬럼 스타일링 로직을 중복 구현해둔 상태라, get_market_force_score/get_pair_buy_score와
# 같은 이유로 공통 함수 하나로 뽑아서 양쪽 다 이걸 재사용하게 함.
_SENTIMENT_GRADE_MAP = {
    5: "AAA", 4: "AA", 3: "A",
    2: "BBB", 1: "BB", 0: "B",
    -1: "CCC", -2: "CC", -3: "C",
    -4: "D", -5: "F",
}

def get_sentiment_grade(val):
    """뉴스감성 점수(-5~+5 정수, 없으면 NaN/None)를 등급 문자열로 변환. 데이터 없으면 None 반환(빈칸 유지)."""
    if pd.isna(val):
        return None
    try:
        v = int(round(float(val)))
    except (TypeError, ValueError):
        return None
    return _SENTIMENT_GRADE_MAP.get(v, None)

def get_sentiment_grade_color(grade):
    """등급 문자열에 대응하는 표시 색상. AAA/AA/A=빨강, BBB/BB/B=주황, CCC/CC/C=파랑, D=녹색, F=보라."""
    if grade in ("AAA", "AA", "A"):
        return "#ff4b4b"
    elif grade in ("BBB", "BB", "B"):
        return "#FFA500"
    elif grade in ("CCC", "CC", "C"):
        return "#4B89B5"
    elif grade == "D":
        return "#00E676"
    elif grade == "F":
        return "#BA68C8"
    return "#777777"

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
        # 🔧 [수정 2026-08-01] 사용자 요청으로 CSV 포맷을 "A열: 테마 / B열: 종목들(콤마구분)"에서
        # "A열: 번호(참고용, 미사용) / B열: 테마 / C열: 종목(1개)"로 변경. 한 종목이 여러 테마에
        # 속하면 그만큼 줄을 반복해서 적는 방식(예: 삼성전자가 AI 반도체 줄에도, 다른 테마 줄에도
        # 나올 수 있음). 사용자가 실제 겪은 문제: "AI 반도체"라는 '테마' 값이 통째로 하나의
        # 테마명으로 저장되어 트리맵/랭킹표에 "AI 반도체"라는 이상한 합성 테마 하나로 나타남 —
        # 원래 의도는 "AI"와 "반도체" 두 개의 서로 다른 테마에 속한다는 뜻이었음.
        # → '테마' 칸에 공백으로 여러 단어가 있으면 공백 기준으로 전부 별도 테마로 분리하도록 수정
        # (사용자가 명시적으로 확인한 규칙: "공백 기준으로 항상 전부 분리" — 예: "반도체 소부장"도
        # "반도체"+"소부장" 두 개의 테마로 분리됨. 예외 없이 일괄 적용).
        # ⚠️ 이 분리 규칙 덕분에 다운스트림(테마킹 화면의 theme_agg 집계, 트리맵 등)은 이미
        # theme_names를 콤마로 split해서 쓰고 있어 별도 수정이 필요 없음 — 여기서 "AI, 반도체"처럼
        # 콤마로 이어붙여 저장하기만 하면 자동으로 올바르게 두 테마로 인식됨.
        with st.expander("🚀 엑셀(CSV) 일괄 대량 업로드 (Bulk Upload)", expanded=False):
            st.info(
                "💡 CSV 작성법(2026-08-01 변경): A열에 [번호](참고용, 안 적어도 됨), B열에 [테마], "
                "C열에 [종목명] 하나씩, **종목 1개당 1줄**로 적어주세요. 같은 종목이 여러 테마에 속하면 "
                "그 종목을 여러 줄에 나눠 반복해서 적으면 됩니다.\n\n"
                "예시)\n번호,테마,종목\n1,AI 반도체,삼성전자\n2,AI 반도체,SK하이닉스\n11,반도체 소부장,원익IPS\n21,로봇,레인보우로보틱스\n\n"
                "⚠️ **'테마' 칸에 공백으로 여러 단어가 있으면(예: 'AI 반도체') 공백 기준으로 각각 별도의 "
                "테마로 자동 분리되어 저장됩니다** — 즉 'AI 반도체'는 'AI' 테마와 '반도체' 테마 둘 다에 "
                "속하는 것으로 처리됩니다('반도체 소부장'도 마찬가지로 '반도체'+'소부장' 2개로 분리되니 "
                "테마명을 지을 때 참고해 주세요).\n\n"
                "작성 후 **[파일 -> 다른 이름으로 저장]**에서 CSV 형식으로 저장해서 올려주세요 "
                "('CSV UTF-8(쉼표로 분리)'가 안 보이면 그냥 일반 'CSV(쉼표로 분리)'로 저장해도 됩니다 — "
                "업로드 시 자동으로 인코딩을 인식합니다)."
            )
            uploaded_file = st.file_uploader("CSV 파일 선택", type=['csv'], key="theme_bulk_csv_uploader")
            if uploaded_file is not None:
                # 🔧 [수정 2026-08-01, 2번째] 사용자 피드백: 엑셀 버전에 따라 "CSV UTF-8(쉼표로 분리)"
                # 저장 옵션 자체가 안 보이는 경우가 있음(엑셀 버전/OS별로 메뉴 구성이 다름). 일반
                # "CSV(쉼표로 분리)"로 저장하면 한글 윈도우 엑셀은 보통 시스템 기본 인코딩(CP949, 이른바
                # "EUC-KR 계열")으로 저장되어 encoding='utf-8' 고정으로는 UnicodeDecodeError가 남.
                # → utf-8만 강제하는 대신 여러 인코딩을 순서대로 시도해서, 사용자가 어떤 CSV
                # 저장 옵션을 쓰든(UTF-8이든 CP949든) 그대로 업로드할 수 있게 함.
                df_upload = None
                for _enc in ('utf-8-sig', 'utf-8', 'cp949', 'euc-kr'):
                    try:
                        uploaded_file.seek(0)
                        df_upload = pd.read_csv(uploaded_file, encoding=_enc, header=None)
                        break
                    except (UnicodeDecodeError, UnicodeError):
                        continue

                if df_upload is None:
                    st.error("❌ CSV 파일의 인코딩을 인식하지 못했습니다(UTF-8/CP949/EUC-KR 모두 실패). 엑셀에서 [파일 → 다른 이름으로 저장 → CSV(쉼표로 분리)]로 다시 저장해서 올려주세요.")
                else:
                    try:
                        if len(df_upload.columns) >= 3:
                            if st.button("파일 데이터 DB에 일괄 저장 🚀", key="theme_bulk_upload_btn"):
                                stock_to_themes = {}
                                now_str = datetime.now().isoformat()
                                skipped_rows = 0

                                for _, row in df_upload.iterrows():
                                    # col0(번호)은 참고용이라 무시, col1=테마, col2=종목
                                    theme_field = str(row.iloc[1]).strip()
                                    stock_name_field = str(row.iloc[2]).strip()

                                    # 사용자가 첫 줄에 제목(헤더)을 적었을 경우 스킵
                                    if theme_field in ['테마', '테마명', '테마이름', 'theme'] or stock_name_field in ['종목', '종목명', '종목이름', 'stock']:
                                        continue

                                    if not theme_field or theme_field == 'nan' or not stock_name_field or stock_name_field == 'nan':
                                        skipped_rows += 1
                                        continue

                                    # 공백 기준으로 전부 분리 → 독립된 테마 여러 개로 취급(사용자 확정 규칙).
                                    # str.split()은 공백이 몇 개든 구분자로 처리하고 빈 문자열은 자동으로 걸러줌.
                                    theme_tokens = theme_field.split()
                                    if not theme_tokens:
                                        skipped_rows += 1
                                        continue

                                    if stock_name_field not in stock_to_themes:
                                        stock_to_themes[stock_name_field] = []
                                    for tok in theme_tokens:
                                        # 중복 테마 방지(같은 종목이 여러 줄에 걸쳐 나와도 태그는 한 번만)
                                        if tok not in stock_to_themes[stock_name_field]:
                                            stock_to_themes[stock_name_field].append(tok)

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
                                    success_msg = f"✅ 총 {len(bulk_data)}개 종목의 테마 세팅이 완벽하게 업로드되었습니다!"
                                    if skipped_rows:
                                        success_msg += f" (형식이 맞지 않아 건너뛴 줄 {skipped_rows}개)"
                                    st.success(success_msg)
                                    st.rerun()
                                else:
                                    st.warning("유효한 데이터가 없습니다. 형식을 확인해 주세요.")
                        else:
                            st.error("CSV 파일에 최소 3개의 열(A열: 번호, B열: 테마, C열: 종목)이 필요합니다.")
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

                # 🌟 [신규 2026-08-01] 사용자가 "기존 테마 정보 다 지우고 다시 넣겠다"고 밝혀서,
                # 300개 가까운 종목을 하나씩 지우는 수고를 덜어주는 "전체 삭제" 버튼 추가.
                # 실수 클릭 방지를 위해 체크박스로 한 번 확인받은 뒤에만 버튼이 눌리게 함.
                with st.expander("⚠️ 전체 테마 데이터 초기화 (모든 종목 삭제)"):
                    st.warning(f"현재 등록된 테마 데이터 **{len(theme_df)}개 종목**을 전부 영구 삭제합니다. 새 CSV를 업로드하기 직전에만 사용하세요.")
                    confirm_wipe = st.checkbox("네, 전체 테마 데이터를 삭제하는 것이 맞습니다.", key="theme_wipe_confirm")
                    if st.button("🚨 전체 테마 데이터 영구 삭제", disabled=not confirm_wipe, key="theme_wipe_btn"):
                        # Supabase delete()는 조건절이 필요해서, stock_name(NOT NULL)이 빈 문자열이
                        # 아닌 모든 행을 지우는 조건으로 사실상 "전체 삭제"를 구현.
                        supabase.table("stock_themes").delete().neq("stock_name", "").execute()
                        st.success("🗑️ 전체 테마 데이터가 삭제되었습니다. 이제 새 CSV를 업로드해 주세요.")
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

# 🌟 [신규 2026-08-01] 사용자 요청: "실시간 놀빅 고래 체결 상황" 화면의 매수 폭주 Top3 카드
# 폭을 30%씩 줄이고, 남는 공간에 미국 테마별 등락률 위젯을 배치. us_theme_performance
# 테이블(FindingWhale.py의 독립 데몬 스레드가 매일 자동 수집)에서 최신 거래일 기준 상승/하락
# 테마 순위를 뽑아옴. 30분 캐시(ttl=1800) — 어차피 하루 1회만 갱신되는 데이터라 충분히 여유있음.
@st.cache_data(ttl=1800)
def get_us_theme_top_movers(left_count=8):
    try:
        res = supabase.table("us_theme_performance").select("trade_date, theme_name, pct_change").order("trade_date", desc=True).limit(200).execute()
        if not res.data:
            return None, [], []
        df_us = pd.DataFrame(res.data)
        latest_date = df_us['trade_date'].max()
        today_df = df_us[df_us['trade_date'] == latest_date].copy()
        today_df['pct_change'] = today_df['pct_change'].astype(float)
        # 🔧 [수정 2026-07-31, 4차] 이전에는 "상승 Top-N / 하락 Top-N"으로 나눠 뽑다 보니, 값
        # 크기 순위로 딱 중간권(예: 15개 중 8위)에 있는 테마가 양쪽 컷 어디에도 안 들어가고
        # 통째로 누락되는 문제가 있었음(사용자 발견: 반도체 +0.90%가 화면에 안 보임).
        # → 등락률이 아니라 "순위"로만 좌/우를 나눔: 전체 테마를 값이 큰 순서(내림차순)로 한 줄
        # 세운 뒤, 앞쪽 left_count개는 좌측 컬럼, 나머지는 전부 우측 컬럼에 배치 → 어떤 테마도
        # 빠지지 않고 전부 표시됨. 좌/우는 순위 배치일 뿐이고, 색상(빨강/파랑)은 화면 렌더링
        # 단계에서 각 항목의 실제 부호로 별도 판단(_us_row_html) — 좌/우 소속과 무관.
        sorted_records = today_df.sort_values('pct_change', ascending=False).to_dict('records')
        left_items = sorted_records[:left_count]
        right_items = sorted_records[left_count:]
        return latest_date, left_items, right_items
    except Exception as e:
        return None, [], []

# 🌟 [신규 2026-08-01] '미국 테마 등락률' 위젯 HTML 빌더 — 기존에는 '실시간' 화면에만 인라인으로
# 만들어져 있던 코드였는데, 사용자 요청으로 '테마킹' 화면 우측 상단에도 똑같이 배치하게 되어
# 코드 중복을 피하려고 공용 함수로 뽑아냄. get_us_theme_top_movers()의 반환값을 그대로 받아서
# 렌더링용 HTML 문자열만 만들어 돌려준다(st.markdown 호출은 각 호출부에서 각자 수행).
def render_us_theme_widget_html(us_latest_date, us_left_items, us_right_items):
    if not us_latest_date:
        return (
            "<div style='background: linear-gradient(135deg, #12151c 0%, #05070a 100%); border: 1px dashed #333a45; border-radius: 8px; padding: 12px; text-align:center; opacity:0.7; height: 100%;'>"
            "<div style='font-size:12px; color:#888888;'>미국 테마 데이터 대기 중...</div>"
            "</div>"
        )

    def _us_row_html(item):
        val = item['pct_change']
        if val >= 0:
            color, arrow = "#ff4b4b", "▲"
        else:
            color, arrow = "#4B89B5", "▼"
        return f"<div style='display:flex; justify-content:space-between; gap:6px; font-size:11px; color:{color}; padding:2px 0;'><span>{arrow} {item['theme_name']}</span><span>{val:+.2f}%</span></div>"

    us_left_html = "".join(_us_row_html(g) for g in us_left_items)
    us_right_html = "".join(_us_row_html(l) for l in us_right_items)
    return (
        "<div style='background: linear-gradient(135deg, #12151c 0%, #05070a 100%); border: 1px solid #333a45; border-radius: 8px; padding: 12px 12px 20px 12px; height: 100%;'>"
        "<div style='display:flex; justify-content:space-between; align-items:baseline; margin-bottom:6px;'>"
        "<div style='font-size:13px; font-weight:bold; color:#e0e0e0;'>미국 테마 등락률</div>"
        f"<div style='font-size:15px; color:#888888;'>{us_latest_date} 마감 기준</div>"
        "</div>"
        "<div style='display:flex; gap:10px;'>"
        f"<div style='flex:1; min-width:0;'>{us_left_html}</div>"
        f"<div style='flex:1; min-width:0; border-left:1px solid #333a45; padding-left:10px;'>{us_right_html}</div>"
        "</div>"
        "</div>"
    )

# 🌟 [신규 2026-08-01] "공매도·대차잔고 워치"(예비3) / "신용잔고·프로그램매매 추이"(예비4) 화면용
# 데이터 조회 함수 5종. get_us_theme_top_movers()와 동일한 스타일(try/except 안전망, @st.cache_data로
# 30분 캐싱, latest_date 기준으로 "가장 최근 거래일" 데이터만 추림). 데이터 원본은 scripts/fetch_market_risk_signals.py가
# 매일 장마감 이후 자동 수집하는 5개 Supabase 테이블.
@st.cache_data(ttl=1800)
def get_short_sale_ranking(limit=30, target_date=None):
    """공매도 상위종목 랭킹(target_date 지정 시 해당 거래일, 없으면 최신 거래일). 반환: (거래일, [행 dict, ...])
    🌟 [2026-08-02] "공대치" 화면에 달력 연동 추가하면서 target_date 파라미터 신규 도입 —
    지정 시 해당 날짜로 직접 eq 조회(과거 500건 윈도우에 안 걸리는 날짜도 조회 가능)."""
    try:
        if target_date:
            res = supabase.table("short_sale_ranking").select("*").eq("trade_date", target_date).order("rank").limit(limit).execute()
            return target_date, (res.data or [])
        res = supabase.table("short_sale_ranking").select("*").order("trade_date", desc=True).limit(500).execute()
        if not res.data:
            return None, []
        df = pd.DataFrame(res.data)
        latest_date = df['trade_date'].max()
        today_df = df[df['trade_date'] == latest_date].sort_values('rank').head(limit)
        return latest_date, today_df.to_dict('records')
    except Exception as e:
        return None, []


@st.cache_data(ttl=1800)
def get_stock_loan_balance_ranking(limit=30, target_date=None):
    """종목별 대차잔고 상위종목(target_date 지정 시 해당 거래일, 없으면 최신 거래일,
    daily_whale_top200 200종목 대상 자체 랭킹). 반환: (거래일, [행 dict, ...])
    🌟 [2026-08-02] "공대치" 화면 달력 연동용 target_date 파라미터 신규 도입."""
    try:
        if target_date:
            res = supabase.table("stock_loan_balance_ranking").select("*").eq("trade_date", target_date).order("rank").limit(limit).execute()
            return target_date, (res.data or [])
        res = supabase.table("stock_loan_balance_ranking").select("*").order("trade_date", desc=True).limit(500).execute()
        if not res.data:
            return None, []
        df = pd.DataFrame(res.data)
        latest_date = df['trade_date'].max()
        today_df = df[df['trade_date'] == latest_date].sort_values('rank').head(limit)
        return latest_date, today_df.to_dict('records')
    except Exception as e:
        return None, []


@st.cache_data(ttl=1800)
def get_credit_balance_ranking(limit=30, target_date=None):
    """신용잔고 상위종목 랭킹(target_date 지정 시 해당 거래일, 없으면 최신 거래일, 융자잔고 금액 상위).
    반환: (거래일, [행 dict, ...])
    🌟 [2026-08-02] "신프로" 화면 달력 연동용 target_date 파라미터 신규 도입."""
    try:
        if target_date:
            res = supabase.table("credit_balance_ranking").select("*").eq("trade_date", target_date).order("rank").limit(limit).execute()
            return target_date, (res.data or [])
        res = supabase.table("credit_balance_ranking").select("*").order("trade_date", desc=True).limit(500).execute()
        if not res.data:
            return None, []
        df = pd.DataFrame(res.data)
        latest_date = df['trade_date'].max()
        today_df = df[df['trade_date'] == latest_date].sort_values('rank').head(limit)
        return latest_date, today_df.to_dict('records')
    except Exception as e:
        return None, []


@st.cache_data(ttl=1800)
def get_market_loan_trans_trend(days=20):
    """시장 전체(KOSPI/KOSDAQ) 대차잔고 추이 — 최근 N거래일. 반환: DataFrame(빈 경우 empty)"""
    try:
        res = supabase.table("market_loan_trans_daily").select("*").order("trade_date", desc=True).limit(days * 2).execute()
        if not res.data:
            return pd.DataFrame()
        df = pd.DataFrame(res.data)
        return df.sort_values('trade_date')
    except Exception as e:
        return pd.DataFrame()


@st.cache_data(ttl=1800)
def get_program_trade_investor_today(target_date=None):
    """프로그램매매 투자자별 순매수 동향(target_date 지정 시 해당 거래일, 없으면 최신 거래일, KOSPI+KOSDAQ 합산).
    반환: (거래일, [행 dict, ...])
    ⚠️ 2026-08-02: KIS API가 시장 구분(MRKT_DIV_CLS_CODE) 파라미터를 필수로 요구해서 KOSPI/KOSDAQ를
    각각 별도 행(market 컬럼)으로 수집하도록 수집기가 바뀜 — 화면에서는 투자자별로 두 시장을 합산해 표시.
    🌟 [2026-08-02] "신프로" 화면 달력 연동용 target_date 파라미터 신규 도입."""
    try:
        if target_date:
            res = supabase.table("program_trade_investor_today").select("*").eq("trade_date", target_date).execute()
            if not res.data:
                return target_date, []
            df = pd.DataFrame(res.data)
            numeric_cols = ['sell_qty', 'sell_amount', 'buy_qty', 'buy_amount', 'net_qty', 'net_amount',
                            'arb_net_qty', 'arb_net_amount', 'non_arb_net_qty', 'non_arb_net_amount']
            grouped = df.groupby(['investor_code', 'investor_name'], as_index=False)[numeric_cols].sum()
            grouped = grouped.sort_values('net_amount', ascending=False)
            return target_date, grouped.to_dict('records')
        res = supabase.table("program_trade_investor_today").select("*").order("trade_date", desc=True).limit(100).execute()
        if not res.data:
            return None, []
        df = pd.DataFrame(res.data)
        latest_date = df['trade_date'].max()
        today_df = df[df['trade_date'] == latest_date]
        numeric_cols = ['sell_qty', 'sell_amount', 'buy_qty', 'buy_amount', 'net_qty', 'net_amount',
                         'arb_net_qty', 'arb_net_amount', 'non_arb_net_qty', 'non_arb_net_amount']
        grouped = today_df.groupby(['investor_code', 'investor_name'], as_index=False)[numeric_cols].sum()
        grouped = grouped.sort_values('net_amount', ascending=False)
        return latest_date, grouped.to_dict('records')
    except Exception as e:
        return None, []


@st.cache_data(ttl=1800)
def get_program_trade_market_trend(days=20):
    """시장 전체(KOSPI/KOSDAQ) 프로그램매매 순매수 추이 — 최근 N거래일. 반환: DataFrame(빈 경우 empty)"""
    try:
        res = supabase.table("program_trade_market_daily").select("*").order("trade_date", desc=True).limit(days * 2).execute()
        if not res.data:
            return pd.DataFrame()
        df = pd.DataFrame(res.data)
        return df.sort_values('trade_date')
    except Exception as e:
        return pd.DataFrame()


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

            # 🌟 [2026-08-01 로그 스케일 전환] 하드 임계값 티어 → get_market_force_score/get_pair_buy_score 공통 함수로 교체
            s_tot = get_market_force_score(total_net)
            score += s_tot

            s_pair, _pair_reason_hover = get_pair_buy_score(frgn_net, orgn_net)
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
            background-color: #3E4F69 !important;
            border: 1px solid #2E3C51 !important;
            padding-left: 4px !important;
            padding-right: 4px !important;
        }
        div.element-container:has(.btn-style-darkblue) + div.element-container button p {
            font-size: 13px !important;
            color: #FFFFFF !important;
            font-weight: bold !important;
        }
        div.element-container:has(.btn-style-darkblue) + div.element-container button:hover {
            background-color: #2E3C51 !important;
        }
        div.element-container:has(.btn-style-darkblue) + div.element-container button:hover p {
            color: #FFD700 !important;
        }

        /* 3버튼 공통 높이 축소 스타일 (패딩/최소높이 조절) */
        /* 목록보기 버튼 (작은 높이) */
        div.element-container:has(.btn-style-darkblue-sm) { display: none; }
        div.element-container:has(.btn-style-darkblue-sm) + div.element-container button {
            background-color: #3E4F69 !important;
            border: 1px solid #2E3C51 !important;
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
            background-color: #2E3C51 !important;
        }
        div.element-container:has(.btn-style-darkblue-sm) + div.element-container button:hover p {
            color: #FFD700 !important;
        }

        /* 빨간색 TOP10 버튼 스타일 (2026-08-01 채도 낮춤 — 아래 "기폭주" 재정의와 동일 색으로 통일) */
        div.element-container:has(.btn-style-red) { display: none; }
        div.element-container:has(.btn-style-red) + div.element-container button {
            background-color: #9E2E2E !important;
            border: 1px solid #663333 !important;
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
            background-color: #582C2C !important;
        }

        /* 파란색 TOP10 버튼 스타일 */
        div.element-container:has(.btn-style-blue) { display: none; }
        div.element-container:has(.btn-style-blue) + div.element-container button {
            background-color: #4E687E !important;
            border: 1px solid #384F61 !important;
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
            background-color: #304454 !important;
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

        /* 보라색 수익율 버튼 스타일 (2026-08-01 채도 낮춤) */
        div.element-container:has(.btn-style-purple) { display: none; }
        div.element-container:has(.btn-style-purple) + div.element-container button {
            background-color: #683B91 !important; /* BlueViolet, 채도 낮춘 톤 */
            border: 1px solid #342B6E !important;
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
            background-color: #2D255F !important;
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

        /* 오렌지색 상선고 버튼 스타일 (2026-08-01 채도 낮춤) */
        div.element-container:has(.btn-style-orange) { display: none; }
        div.element-container:has(.btn-style-orange) + div.element-container button {
            background-color: #9E6C2E !important;
            border: 1px solid #6E4A2B !important;
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
            background-color: #5F4125 !important;
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
            color: #FFFFFF !important;
            font-weight: bold !important;
            line-height: 1 !important;
        }

        /* 🌟 [신규 2026-08-01] "공대치"(공매도·대차잔고 워치, 구 예비3) 버튼 전용 틸(teal) — 다른 버튼과 동일하게 채도 낮춤 */
        div.element-container:has(.btn-style-teal) { display: none; }
        div.element-container:has(.btn-style-teal) + div.element-container button {
            background-color: #3C8181 !important;
            border: 1px solid #306969 !important;
            padding-left: 4px !important;
            padding-right: 4px !important;
            padding-top: 2px !important;
            padding-bottom: 2px !important;
            min-height: 32px !important;
        }
        div.element-container:has(.btn-style-teal) + div.element-container button p {
            font-size: 13px !important;
            color: #ffffff !important;
            font-weight: bold !important;
            line-height: 1 !important;
        }
        div.element-container:has(.btn-style-teal) + div.element-container button:hover {
            background-color: #2A5B5B !important;
        }

        div.element-container:has(.btn-style-teal-active) { display: none; }
        div.element-container:has(.btn-style-teal-active) + div.element-container button {
            background-color: transparent !important;
            border: 2px solid #3C8181 !important;
            padding-left: 4px !important;
            padding-right: 4px !important;
            padding-top: 2px !important;
            padding-bottom: 2px !important;
            min-height: 32px !important;
        }
        div.element-container:has(.btn-style-teal-active) + div.element-container button p {
            font-size: 13px !important;
            color: #3C8181 !important;
            font-weight: bold !important;
            line-height: 1 !important;
        }

        /* 🌟 [신규 2026-08-01] "신프로"(신용잔고·프로그램매매 추이, 구 예비4) 버튼 전용 인디고 — 수익율/골든픽의 보라색과 구분되는 톤 */
        div.element-container:has(.btn-style-indigo) { display: none; }
        div.element-container:has(.btn-style-indigo) + div.element-container button {
            background-color: #4C4686 !important;
            border: 1px solid #393465 !important;
            padding-left: 4px !important;
            padding-right: 4px !important;
            padding-top: 2px !important;
            padding-bottom: 2px !important;
            min-height: 32px !important;
        }
        div.element-container:has(.btn-style-indigo) + div.element-container button p {
            font-size: 13px !important;
            color: #ffffff !important;
            font-weight: bold !important;
            line-height: 1 !important;
        }
        div.element-container:has(.btn-style-indigo) + div.element-container button:hover {
            background-color: #312D57 !important;
        }

        div.element-container:has(.btn-style-indigo-active) { display: none; }
        div.element-container:has(.btn-style-indigo-active) + div.element-container button {
            background-color: transparent !important;
            border: 2px solid #4C4686 !important;
            padding-left: 4px !important;
            padding-right: 4px !important;
            padding-top: 2px !important;
            padding-bottom: 2px !important;
            min-height: 32px !important;
        }
        div.element-container:has(.btn-style-indigo-active) + div.element-container button p {
            font-size: 13px !important;
            color: #4C4686 !important;
            font-weight: bold !important;
            line-height: 1 !important;
        }

        /* 기폭주 버튼 (붉은색) 스타일 (2026-08-01 채도 낮춤 — 위 "btn-style-red" 첫 정의와 동일 색으로 통일) */
        div.element-container:has(.btn-style-red) { display: none; }
        div.element-container:has(.btn-style-red) + div.element-container button {
            background-color: #9E2E2E !important;
            border: 1px solid #663333 !important;
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
        /* 🔧 [수정 2026-08-01] 사이드바 버튼 전체 채도 낮춤 */
        div.element-container:has(.btn-style-darkred) { display: none; }
        div.element-container:has(.btn-style-darkred) + div.element-container button {
            background-color: #8C4040 !important;
            border: 1px solid #6C1F1F !important;
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
            background-color: #671E1E !important;
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
        /* 🔧 [수정 2026-08-01] 채도 낮춤 */
        div.element-container:has(.btn-style-green) { display: none; }
        div.element-container:has(.btn-style-green) + div.element-container button {
            background-color: #437659 !important;
            border: 1px solid #2D4E3D !important;
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
            background-color: #2D4E3D !important;
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

        /* 🌟 [신규 2026-07-30] "테마킹" 버튼 전용 찐노랑 */
        /* 🔧 [수정 2026-08-01] 채도 낮춤(어두운 겨자색 톤으로) + 다른 버튼과 동일하게 흰 글씨로 통일 */
        div.element-container:has(.btn-style-yellow) { display: none; }
        div.element-container:has(.btn-style-yellow) + div.element-container button {
            background-color: #9E8B2E !important;
            border: 1px solid #776822 !important;
            padding-left: 4px !important;
            padding-right: 4px !important;
            padding-top: 2px !important;
            padding-bottom: 2px !important;
            min-height: 32px !important;
        }
        div.element-container:has(.btn-style-yellow) + div.element-container button p {
            font-size: 13px !important;
            color: #ffffff !important;
            font-weight: bold !important;
            line-height: 1 !important;
        }
        div.element-container:has(.btn-style-yellow) + div.element-container button:hover {
            background-color: #675A1E !important;
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
            # 🌟 [신규 2026-08-01] "공매도·대차잔고 워치" — 골든스코어(매수세 쏠림)의 반대편,
            # 공매도/신용대차가 쏠리는 위험 신호를 보여주는 화면. 상선고/기폭주와 동일하게 관리자 전용 규칙.
            is_short_watch_active = (scrn_select == "공매도·대차잔고 워치")
            cls_short_watch = "btn-style-teal-active" if is_short_watch_active else "btn-style-teal"
            st.markdown(f'<div class="{cls_short_watch}"></div>', unsafe_allow_html=True)
            if st.button("공대차", key="btn_res3", use_container_width=True):
                if st.session_state.get('scrn_select_radio') != "공매도·대차잔고 워치":
                    st.session_state['scrn_select_radio'] = "공매도·대차잔고 워치"
                    st.rerun()
        with btn_col12:
            # 🌟 [신규 2026-08-01] "신용잔고·프로그램매매 추이" — 신용잔고 상위 + 프로그램매매 동향을
            # 함께 보여줘 "진짜 선행지표 찾기" 연구에도 데이터로 활용 가능.
            is_credit_prog_active = (scrn_select == "신용잔고·프로그램매매 추이")
            cls_credit_prog = "btn-style-indigo-active" if is_credit_prog_active else "btn-style-indigo"
            st.markdown(f'<div class="{cls_credit_prog}"></div>', unsafe_allow_html=True)
            if st.button("신프로", key="btn_reserve_4", use_container_width=True):
                if st.session_state.get('scrn_select_radio') != "신용잔고·프로그램매매 추이":
                    st.session_state['scrn_select_radio'] = "신용잔고·프로그램매매 추이"
                    st.rerun()


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

                        # 🌟 [2026-08-01 로그 스케일 전환] 하드 임계값 티어 → get_market_force_score/get_pair_buy_score 공통 함수로 교체
                        score += get_market_force_score(total_net)

                        pair_score, pair_reason = get_pair_buy_score(frgn_net, orgn_net)
                        score += pair_score
                        if pair_reason:
                            reasons.append(pair_reason)

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

                        # 🔧 [수정 2026-08-03] 사용자 요청: -5~+5 숫자 대신 신용등급 스타일(AAA~F) 문자 등급으로 표시.
                        # 데이터 없는 경우는 그대로 None(빈칸) 유지. 공통 헬퍼(get_sentiment_grade)는 위쪽
                        # get_market_force_score 근처에 정의됨.
                        display_gp['📰 뉴스감성'] = display_gp['📰 뉴스감성'].apply(get_sentiment_grade)

                        # 🌟 [신규 2026-07-30] 뉴스감성 등급 색상(빨강=AAA/AA/A, 주황=BBB/BB/B, 파랑=CCC/CC/C,
                        # 녹색=D, 보라=F, 없음=회색) — 🔧 [수정 2026-08-03] 등급 전환에 맞춰 get_sentiment_grade_color로 교체.
                        # 🔧 [수정 2026-07-30] font-size 시도는 반영이 안 되는 것으로 확인되어 제거.
                        #    대신 "🟡기관 순매수(억)" 컬럼처럼 Styler를 아예 안 씌운(스타일 없는 기본) 컬럼과 폰트가
                        #    똑같아 보이도록 color만 남기고 font-weight/font-size는 모두 제거함(컬러 로직은 그대로 유지).
                        def _get_sentiment_color(grade):
                            return f'color: {get_sentiment_grade_color(grade)};'

                        # 🔧 [수정 2026-08-03] 사용자 요청: "황금점수" 텍스트를 빨간색으로 표시.
                        def _get_golden_score_color(_val):
                            return 'color: #ff4b4b;'

                        # 🔧 [수정 2026-07-30] Streamlit Cloud 배포 시 최신 pandas(applymap 완전 제거)에서
                        # AttributeError 발생 확인 → pandas 2.1+에서 applymap의 대체 메서드인 Styler.map으로 교체
                        styled_gp = display_gp.style.map(_get_sentiment_color, subset=['📰 뉴스감성']) \
                                              .map(_get_golden_score_color, subset=['황금점수'])

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
                                # 🔧 [수정 2026-08-03] 숫자(%+d) → 등급 문자열 표시로 바뀌어 TextColumn으로 교체.
                                "📰 뉴스감성": st.column_config.TextColumn(help="배치 스크립트(fetch_news_sentiment.py)가 매일 채워주는 실험적 뉴스 감성 점수를 신용등급 스타일(AAA~F, 좋음→나쁨)로 표시. 아직 데이터 없으면 빈칸."),
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

                    # 🌟 [2026-08-01 로그 스케일 전환] 하드 임계값 티어 → get_market_force_score/get_pair_buy_score 공통 함수로 교체
                    score_w += get_market_force_score(total_net_w)

                    pair_score_w, pair_reason_w = get_pair_buy_score(frgn_net_w, orgn_net_w)
                    score_w += pair_score_w
                    if pair_reason_w:
                        reasons_w.append(pair_reason_w)

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

                # 🔧 [수정 2026-08-03] "고래 골든픽" 화면과 동일하게, -5~+5 숫자 대신 신용등급 스타일(AAA~F)
                # 문자 등급으로 표시(공통 헬퍼 get_sentiment_grade 재사용).
                df_watch['📰 뉴스감성'] = df_watch['📰 뉴스감성'].apply(get_sentiment_grade)

                # 🌟 [신규 2026-07-30] "고래 골든픽" 화면과 동일하게 뉴스감성 등급에 색상 적용
                # (빨강=AAA/AA/A, 주황=BBB/BB/B, 파랑=CCC/CC/C, 녹색=D, 보라=F, 없음=회색).
                # 🔧 [수정 2026-08-03] 등급 전환에 맞춰 공통 헬퍼 get_sentiment_grade_color로 교체.
                def _get_sentiment_color_watch(grade):
                    return f'color: {get_sentiment_grade_color(grade)};'

                # 🔧 [수정 2026-08-03] 사용자 요청: "골든점수" 텍스트를 빨간색으로 표시("고래 골든픽" 화면과 통일).
                def _get_golden_score_color_watch(_val):
                    return 'color: #ff4b4b;'

                # 🔧 [수정 2026-07-30] Streamlit Cloud 배포 시 최신 pandas(applymap 완전 제거)에서
                # AttributeError 발생 확인 → pandas 2.1+에서 applymap의 대체 메서드인 Styler.map으로 교체
                styled_watch = df_watch.style.map(_get_sentiment_color_watch, subset=['📰 뉴스감성']) \
                                        .map(_get_golden_score_color_watch, subset=['골든점수'])

                # 🌟 [신규 2026-07-31] "고래 골든픽" 화면과 동일하게 표에서 종목(행)을 클릭하면
                # 차트로 바로 이동하거나 AI 요약 팝업을 띄울 수 있도록 클릭 동작 라디오 + on_select 연결
                click_action_watch = st.radio(
                    "👇 표에서 종목(행)을 클릭했을 때 동작을 선택하세요:",
                    ["📊 시계열 추적 (차트 이동)", "💬 AI 요약 보기 (팝업)"],
                    horizontal=True,
                    key="watch_click_action_radio"
                )

                watch_table_key = f"watchlist_table_{st.session_state.get('watch_reset_counter', 0)}"

                st.markdown('<div class="no-header-icon"></div>', unsafe_allow_html=True)
                event_watch = st.dataframe(
                    styled_watch,
                    use_container_width=True,
                    hide_index=True,
                    on_select="rerun",
                    selection_mode="single-row",
                    key=watch_table_key,
                    column_config={
                        "골든점수": st.column_config.NumberColumn("골든점수", format="%,d점"),
                        "🟣외/기 순매수(억)": st.column_config.NumberColumn(format="%,.0f억"),
                        "🟣외국인 순매수(억)": st.column_config.NumberColumn(format="%,.0f억"),
                        "🟡기관 순매수(억)": st.column_config.NumberColumn(format="%,.0f억"),
                        # 🔧 [수정 2026-08-03] 숫자(%+d) → 등급 문자열 표시로 바뀌어 TextColumn으로 교체.
                        "📰 뉴스감성": st.column_config.TextColumn(help="뉴스 감성 점수를 신용등급 스타일(AAA~F, 좋음→나쁨)로 표시. 데이터 없으면 빈칸."),
                    }
                )

                if event_watch and "selection" in event_watch:
                    rows_watch_sel = event_watch["selection"]["rows"]
                    if rows_watch_sel and rows_watch_sel[0] < len(df_watch):
                        selected_stock_watch = df_watch.iloc[rows_watch_sel[0]]['종목명']
                        clean_stock_watch = selected_stock_watch.replace(" 🚀", "").replace(" 👑", "").replace(" 🔥", "").replace(" 💥", "").replace(" ✨", "").replace(" 🌱", "").strip()
                        row_stock_code_watch = df_watch.iloc[rows_watch_sel[0]]['코드']

                        if click_action_watch == "💬 AI 요약 보기 (팝업)":
                            trigger_watch = st.session_state.get('dialog_trigger_id', 0) + 1
                            st.session_state['dialog_trigger_id'] = trigger_watch
                            st.session_state['show_summary_dialog'] = {
                                "stock": clean_stock_watch,
                                "code": row_stock_code_watch,
                                "trigger_id": trigger_watch
                            }
                            st.session_state['watch_reset_counter'] = st.session_state.get('watch_reset_counter', 0) + 1
                            st.rerun()
                        else:
                            st.session_state['pending_search'] = clean_stock_watch
                            st.session_state['last_search_keyword'] = ""
                            st.session_state['df_reset_counter'] = st.session_state.get('df_reset_counter', 0) + 1
                            st.session_state['scrn_select_radio'] = "체결 로그"
                            st.rerun()

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
            # 🇺🇸 [신규 2026-08-01] 사용자 요청: '실시간' 화면의 '미국 테마 등락률' 위젯을
            # '테마킹' 화면 우측 상단에도 동일하게 배치. render_us_theme_widget_html() 공용 함수 재사용.
            themeking_header_cols = st.columns([2.3, 1])
            with themeking_header_cols[0]:
                st.markdown("<h4 style='color:#FFD400; border-left: 4px solid #FFD400; padding-left: 10px;'>👑 테마킹 - 오늘의 테마 모멘텀 랭킹</h4>", unsafe_allow_html=True)
                st.caption("오늘 외국인/기관 순매수 TOP 100(코스피)+TOP 100(코스닥)에 오른 종목 + 실시간 고래거래로 1억원 이상 체결이 있었던 종목을 테마별로 묶어, 어떤 테마에 수급이 몰리고 있는지 보여줍니다.")
                st.caption("⚠️ 테마 매핑 데이터가 현재 약 100개 종목에 한해 등록되어 있어, 테마 매핑이 없는 종목은 집계에서 빠질 수 있습니다.")
            with themeking_header_cols[1]:
                tk_us_latest_date, tk_us_left_items, tk_us_right_items = get_us_theme_top_movers(left_count=8)
                st.markdown(render_us_theme_widget_html(tk_us_latest_date, tk_us_left_items, tk_us_right_items), unsafe_allow_html=True)

            # 🔧 [수정 2026-08-04] 사용자 리포트: 오전 10시~오후 4시 사이에 "테마킹"에 오면
            # daily_whale_top200(장마감 후 16시에만 수집)에 "오늘자" 행이 아직 없어서
            # "오늘자 수급 데이터가 아직 준비되지 않았습니다"가 뜨는 버그 발견.
            # "고래 골든픽"/"외기 TOP100"/"공대차"/"신프로" 화면과 동일하게, 16시 이전이면
            # 어제 날짜(이미 수집 완료된 데이터)로 폴백하도록 통일.
            now_kst_theme = datetime.utcnow() + timedelta(hours=9)
            if now_kst_theme.time() < datetime.strptime("16:00", "%H:%M").time():
                target_dt_theme = now_kst_theme - timedelta(days=1)
            else:
                target_dt_theme = now_kst_theme
            target_dt_theme = target_dt_theme.replace(hour=12, minute=0, second=0, microsecond=0)
            today_theme = get_latest_market_open_date(target_dt_theme)
            today_theme_str = today_theme.strftime("%Y-%m-%d")
            st.caption(f"📅 {today_theme_str} 마감 기준 데이터입니다 (당일 16시 이전에는 전 거래일 자료가 표시됩니다).")

            with st.spinner("🏷️ 오늘의 테마 모멘텀을 집계하는 중입니다..."):
                try:
                    theme_top_res = supabase.table("daily_whale_top200").select("*").eq("trade_date", today_theme_str).execute()
                    df_theme_top = pd.DataFrame(theme_top_res.data) if theme_top_res.data else pd.DataFrame()
                except Exception:
                    df_theme_top = pd.DataFrame()

                # 🌟 [신규 2026-08-03] 사용자 피드백: 삼성전자/SK하이닉스처럼 그날 "순매수" TOP100+100
                # 밖(순매도였거나 순매수폭이 작았던 날)이면 테마 매핑이 있어도 테마 집계에서 통째로
                # 빠지는 문제 발견 → daily_whale_top200에 없는 종목이라도, 오늘 실시간 고래거래(whale_log)에서
                # 1억원 이상 단일 체결이 한 번이라도 있었다면 보완적으로 테마 집계에 포함시킴.
                # (whale_log는 대형 개별 체결만 모은 로그라 진짜 "하루 전체 순매수"는 아니지만, TOP100+100
                # 밖의 종목에 대해 우리가 가진 유일한 근사치라 이걸로 보완함.)
                try:
                    whale_theme_res = supabase.table("whale_log").select("name, code, side, amount_krw").eq("date", today_theme_str).execute()
                    df_whale_theme = pd.DataFrame(whale_theme_res.data) if whale_theme_res.data else pd.DataFrame()
                except Exception:
                    df_whale_theme = pd.DataFrame()

            if df_theme_top.empty and df_whale_theme.empty:
                st.warning("⚠️ 오늘자 수급 데이터가 아직 준비되지 않았습니다.")
            else:
                if not df_theme_top.empty:
                    df_theme_top['frgn_net'] = df_theme_top['frgn_buy'] - df_theme_top['frgn_sell']
                    df_theme_top['orgn_net'] = df_theme_top['orgn_buy'] - df_theme_top['orgn_sell']
                    df_theme_top['total_net'] = df_theme_top['frgn_net'] + df_theme_top['orgn_net']

                existing_names_theme = set(df_theme_top['stock_name'].tolist()) if not df_theme_top.empty else set()

                # 🌟 [신규 2026-08-03] whale_log 보완 후보 추출: 1억원 이상 단일 체결이 있었고,
                # 이미 daily_whale_top200에 있는 종목은 중복 방지로 제외.
                extra_names_theme = []
                extra_net_map = {}
                extra_code_map = {}
                if not df_whale_theme.empty:
                    df_whale_theme['signed_amt'] = df_whale_theme.apply(
                        lambda r: r['amount_krw'] if r['side'] == '매수' else -r['amount_krw'], axis=1
                    )
                    whale_grp_theme = df_whale_theme.groupby('name').agg(
                        max_amt=('amount_krw', 'max'),
                        net_amt=('signed_amt', 'sum'),
                        code=('code', 'first'),
                    ).reset_index()
                    whale_grp_theme = whale_grp_theme[whale_grp_theme['max_amt'] >= 100_000_000]
                    whale_grp_theme = whale_grp_theme[~whale_grp_theme['name'].isin(existing_names_theme)]
                    extra_names_theme = whale_grp_theme['name'].tolist()
                    extra_net_map = dict(zip(whale_grp_theme['name'], whale_grp_theme['net_amt'] / 100_000_000))
                    extra_code_map = dict(zip(whale_grp_theme['name'], whale_grp_theme['code']))

                theme_map_today = get_themes_for_stocks(
                    (df_theme_top['stock_name'].tolist() if not df_theme_top.empty else []) + extra_names_theme
                )

                theme_agg = {}
                for _, r_t in df_theme_top.iterrows():
                    theme_str_t = theme_map_today.get(r_t['stock_name'], "")
                    if not theme_str_t:
                        continue
                    stock_code_t = r_t.get('stock_code', '')
                    for t_name in [t.strip() for t in theme_str_t.split(',') if t.strip()]:
                        if t_name not in theme_agg:
                            theme_agg[t_name] = {"total_net": 0.0, "stocks": []}
                        theme_agg[t_name]["total_net"] += r_t['total_net']
                        # 🌟 [2026-07-31] 테마별 AI 요약 시 대표 종목 뉴스를 긁어오려면 종목코드가 필요해서 튜플에 코드 추가
                        theme_agg[t_name]["stocks"].append((r_t['stock_name'], r_t['total_net'], stock_code_t))

                # 🌟 [신규 2026-08-03] whale_log 보완 종목을 동일한 방식으로 theme_agg에 병합
                for name_e in extra_names_theme:
                    theme_str_e = theme_map_today.get(name_e, "")
                    if not theme_str_e:
                        continue
                    net_e = extra_net_map.get(name_e, 0.0)
                    code_e = extra_code_map.get(name_e, '')
                    for t_name in [t.strip() for t in theme_str_e.split(',') if t.strip()]:
                        if t_name not in theme_agg:
                            theme_agg[t_name] = {"total_net": 0.0, "stocks": []}
                        theme_agg[t_name]["total_net"] += net_e
                        theme_agg[t_name]["stocks"].append((name_e, net_e, code_e))

                if not theme_agg:
                    st.info("오늘 TOP 200 종목 중 테마 매핑이 확인된 종목이 없습니다.")
                else:
                    theme_rows = []
                    for t_name, info_t in theme_agg.items():
                        top_stocks_t = sorted(info_t["stocks"], key=lambda x: x[1], reverse=True)[:3]
                        # 🔧 [수정 2026-08-03] 사용자 요청: 트리맵 호버 메시지에서 종목 이름만 빨간색으로 강조
                        # (호버 텍스트도 차트 text와 동일한 pseudo-html 렌더러를 쓰므로 <span style> 사용 가능).
                        top_stocks_str_t = ", ".join([f"<span style='color:#FF4B4B; font-weight:bold;'>{n}</span>({v:,.0f}억)" for n, v, c in top_stocks_t])
                        theme_rows.append({
                            "테마명": t_name,
                            "종목수": len(info_t["stocks"]),
                            "합산 외/기 순매수(억)": info_t["total_net"],
                            "대표 종목": top_stocks_str_t,
                        })

                    df_theme_rank = pd.DataFrame(theme_rows).sort_values(by="합산 외/기 순매수(억)", ascending=False).reset_index(drop=True)
                    df_theme_rank.insert(0, "순위", df_theme_rank.index + 1)

                    # 🌟 [신규 2026-07-31] Plotly 트리맵 시각화 — 박스 크기: 테마 합산 외/기 순매수(억) 절대값,
                    # 박스 색상: 실제 순매수 방향/강도(빨강=매수 강세, 파랑=매도 강세). 사용자가 보여준 참고 이미지
                    # (다른 사이트의 테마 모멘텀 트리맵)와 유사한 형태를 이 프로젝트의 매수/매도 색 관례(빨강/파랑)로 구현.
                    st.markdown("<h5 style='color:#FFD400; margin-top:10px;'>🗺️ 테마 모멘텀 트리맵</h5>", unsafe_allow_html=True)
                    st.caption("박스 크기 = 테마 합산 외/기 순매수 규모(단, 어느 테마도 전체 면적의 25%는 넘지 않도록 보정), 색상 = 매수(🔴)·매도(🔵) 강도. 박스를 클릭하면 바로 AI 요약이 뜹니다(혹시 클릭이 안 먹으면 아래 '테마별 AI 요약 보기' 버튼을 이용해주세요).")

                    # 🌟 [신규 2026-07-31] 사용자 피드백: "AI 반도체"처럼 압도적으로 큰 테마 하나가
                    # 트리맵 전체 면적을 거의 다 차지해버려서(예: 72,829억 vs 나머지 800억대)
                    # 나머지 테마들이 화면 구석에 찌그러져 안 보이는 문제 발생 → "값이 아무리 커도
                    # 각 레벨에서 전체 면적의 50%를 넘지 않도록" 해달라는 요청에 따라 면적 캡핑 함수 추가.
                    # 🔧 [수정 2026-08-01] 50%로 캡핑해도 여전히 영역 활용이 비효율적이라는 피드백에 따라
                    # 상한을 25%로 더 낮춤(호출부의 max_share=0.25). 함수 자체는 그대로 범용 유지.
                    # 실제 순매수 금액(색상/텍스트 표시용 "합산 외/기 순매수(억)")은 전혀 건드리지 않고,
                    # 트리맵 "면적" 계산에만 쓰이는 별도 값("박스크기")만 이 함수로 보정함.
                    def _cap_treemap_share(values, max_share=0.5):
                        """
                        형제 노드들(같은 레벨의 테마 박스들) 중 어느 하나도 전체 면적의 max_share
                        비율을 넘지 않도록 값을 캡핑. 작은 값들은 서로 간의 상대 비율을 그대로 유지함.
                        수학적 근거: v_i <= max_share * sum(전체) ⟺ v_i <= (max_share/(1-max_share)) * sum(다른 값들)
                        → 가장 큰 값부터 이 조건을 만족할 때까지 반복적으로 깎아냄(유한 횟수 내 항상 수렴).
                        """
                        vals = list(values)
                        n = len(vals)
                        if n <= 1 or max_share >= 1:
                            return vals
                        factor = max_share / (1 - max_share)  # max_share=0.5 → factor=1.0
                        for _ in range(n + 2):
                            total = sum(vals)
                            changed = False
                            for i in range(n):
                                other_sum = total - vals[i]
                                allowed_max = factor * other_sum
                                if vals[i] > allowed_max + 1e-9:
                                    total = total - vals[i] + allowed_max
                                    vals[i] = allowed_max
                                    changed = True
                            if not changed:
                                break
                        return vals

                    df_treemap = df_theme_rank.copy()
                    raw_treemap_sizes = df_treemap["합산 외/기 순매수(억)"].abs().clip(lower=0.1).tolist()
                    df_treemap["박스크기"] = _cap_treemap_share(raw_treemap_sizes, max_share=0.25)

                    fig_treemap = px.treemap(
                        df_treemap,
                        path=[px.Constant("전체 테마"), "테마명"],
                        values="박스크기",
                        color="합산 외/기 순매수(억)",
                        color_continuous_scale=["#4B89B5", "#2b2f3a", "#ff4b4b"],
                        color_continuous_midpoint=0,
                        custom_data=["종목수", "대표 종목", "합산 외/기 순매수(억)"],
                        hover_data=None,
                    )

                    # ⚠️ [되돌림 2026-08-01, 3번째] 순위별로 textfont.size를 배열(리스트)로 지정하는
                    # 시도(1~7위 28px / 8위 이하 20px)를 했었는데, 실제 배포본에서 트리맵 전체가
                    # 빈 단색 박스로 깨지는 렌더링 실패가 발생함(사용자 스크린샷으로 확인). 이 샌드박스는
                    # plotly가 설치돼 있지 않고 네트워크 설치도 불가능해 사전에 직접 렌더링 검증을 하지
                    # 못한 채 반영했던 것이 원인으로 보임 → 즉시 마지막으로 확인됐던 안전한 상태
                    # (균일 28px, 사용자가 "아주 좋았어!"로 확인한 상태)로 되돌림. 순위별 차등 폰트는
                    # 추후 검증 가능한 방법을 찾을 때까지 보류.
                    fig_treemap.update_traces(
                        texttemplate="<b>%{label}</b><br>%{customdata[2]:,.0f}억",
                        hovertemplate="<b>%{label}</b><br>합산 외/기 순매수: %{customdata[2]:,.0f}억<br>종목수: %{customdata[0]}개<br>대표 종목: %{customdata[1]}<extra></extra>",
                        textposition="middle center",
                        textfont_size=28,
                        # 🔧 [수정 2026-08-03] 사용자 요청: 호버 메시지 글자 크기를 기존(플롯리 기본 13px) 대비
                        # 약 50% 확대(20px). 스칼라 값만 사용 — 위 "되돌림" 이력처럼 배열/리스트 지정은
                        # 렌더링 실패 사례가 있어 피함.
                        hoverlabel=dict(font_size=20),
                    )
                    fig_treemap.update_layout(
                        margin=dict(t=10, l=10, r=10, b=10),
                        height=480,
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)",
                        font_color="#e0e0e0",
                        coloraxis_showscale=False,
                    )
                    # 🌟 [신규 2026-07-31] 사용자 질문: "AI요약 버튼을 따로 만든 게 트리맵 셀 클릭이
                    # 안 돼서 그런 건가? 되면 셀 클릭으로 바로 AI요약이 뜨면 좋겠다" → Streamlit이
                    # st.dataframe처럼 st.plotly_chart에도 on_select="rerun"을 지원하므로 시도해봄.
                    # ⚠️ 다만 treemap/sunburst/icicle 같은 계층형 차트는 Plotly 자체의 기본 클릭 동작이
                    # "그 박스로 확대(drill-down)"라서, Streamlit의 on_select가 이 클릭을 selection으로
                    # 제대로 잡아주는지는 이 샌드박스(plotly 미설치, 브라우저 클릭 테스트 불가)에서 직접
                    # 검증하지 못했음 — 그래서 기존 "🤖 테마별 AI 요약 보기" 버튼 그리드는 그대로 남겨둠
                    # (혹시 클릭이 안 먹거나 확대만 되고 끝나면, 버튼으로 여전히 접근 가능하도록 하는 안전망).
                    theme_treemap_key = f"theme_treemap_chart_{st.session_state.get('theme_treemap_reset_counter', 0)}"
                    event_treemap = st.plotly_chart(
                        fig_treemap,
                        use_container_width=True,
                        on_select="rerun",
                        selection_mode="points",
                        key=theme_treemap_key,
                    )

                    if event_treemap and "selection" in event_treemap:
                        points_treemap = event_treemap["selection"].get("points", [])
                        if points_treemap:
                            clicked_theme_label = points_treemap[0].get("label", "")
                            # "전체 테마"(가상 루트 박스) 클릭은 무시 — theme_agg에 없는 키라 자동으로 걸러짐
                            if clicked_theme_label and clicked_theme_label in theme_agg:
                                rep_stocks_click = [
                                    {"name": n, "net": v, "code": c}
                                    for n, v, c in sorted(theme_agg[clicked_theme_label]["stocks"], key=lambda x: x[1], reverse=True)[:5]
                                ]
                                trigger_treemap = st.session_state.get('dialog_trigger_id', 0) + 1
                                st.session_state['dialog_trigger_id'] = trigger_treemap
                                st.session_state['show_theme_summary_dialog'] = {
                                    "theme": clicked_theme_label,
                                    "rep_stocks": rep_stocks_click,
                                    "trigger_id": trigger_treemap
                                }
                                # 골든픽/내관심 표와 동일한 패턴: key를 바꿔 선택 상태를 리셋해서
                                # 다이얼로그를 닫고 돌아왔을 때 같은 박스가 계속 "선택됨"으로 남아
                                # 무한 재트리거되는 것을 방지.
                                st.session_state['theme_treemap_reset_counter'] = st.session_state.get('theme_treemap_reset_counter', 0) + 1
                                st.rerun()

                    st.markdown("<h5 style='color:#FFFFFF; margin-top:20px;'>📋 테마 랭킹 표</h5>", unsafe_allow_html=True)
                    # 🔧 [수정 2026-08-01] 사용자 요청 5가지 반영:
                    # (1) st.dataframe 좌상단 📊 오버레이 아이콘이 첫 컬럼("순위") 헤더 글자를 가림,
                    # (2) "순위" 컬럼 폭이 불필요하게 넓음("10위" 글자만 들어갈 정도로),
                    # (3) 맨 오른쪽("대표 종목") 컬럼을 제외한 나머지 컬럼도 헤더/내용 텍스트 길이에 맞춰 좁힘,
                    # (4) "대표 종목" 안의 "(nn,nnn억)" 부분만 빨간색으로,
                    # (5) 대표 종목 표시 개수를 3개 → 5개로 확대.
                    # (4)는 st.dataframe/column_config로는 불가능함(Streamlit 데이터프레임은 셀 전체
                    # 단위 스타일링만 지원하고, 셀 안의 일부 텍스트만 색칠하는 건 지원 안 함) → 이 표는
                    # st.dataframe 대신 직접 만든 HTML 표로 교체(📊 아이콘 문제도 자동으로 해결됨).
                    # 컬럼 폭은 픽셀을 직접 추정하는 대신, "width:1%; white-space:nowrap"을 앞쪽
                    # 4개 컬럼에 줘서 브라우저 표 자동 레이아웃이 내용 길이에 맞게 최소화하고, 마지막
                    # "대표 종목" 컬럼만 폭 제약 없이 남은 공간을 전부 채우도록 하는 표준 CSS 기법 사용.
                    theme_rank_rows_html = []
                    for _, r_tk in df_theme_rank.iterrows():
                        theme_name_tk = r_tk["테마명"]
                        rep_list_tk = sorted(theme_agg[theme_name_tk]["stocks"], key=lambda x: x[1], reverse=True)[:5]
                        rep_html_tk = ", ".join(
                            f"{n}(<span style='color:#ff4b4b; font-weight:bold;'>{v:,.0f}억</span>)"
                            for n, v, c in rep_list_tk
                        )
                        theme_rank_rows_html.append(
                            "<tr style='border-bottom:1px solid #2a2d35;'>"
                            f"<td style='width:1%; white-space:nowrap; text-align:center; padding:6px 8px;'>{int(r_tk['순위'])}위</td>"
                            f"<td style='width:1%; white-space:nowrap; text-align:left; padding:6px 10px;'>{theme_name_tk}</td>"
                            f"<td style='width:1%; white-space:nowrap; text-align:center; padding:6px 8px;'>{int(r_tk['종목수'])}</td>"
                            f"<td style='width:1%; white-space:nowrap; text-align:right; padding:6px 10px;'>{r_tk['합산 외/기 순매수(억)']:,.0f}억</td>"
                            f"<td style='text-align:left; padding:6px 10px;'>{rep_html_tk}</td>"
                            "</tr>"
                        )
                    theme_rank_table_html = (
                        "<div style='max-height:400px; overflow-y:auto; border:1px solid #333a45; border-radius:6px;'>"
                        "<table style='width:100%; border-collapse:collapse; font-size:13px; color:#e0e0e0;'>"
                        "<thead><tr style='background:#1a1d24; border-bottom:2px solid #333a45; position:sticky; top:0;'>"
                        "<th style='width:1%; white-space:nowrap; text-align:center; padding:8px;'>순위</th>"
                        "<th style='width:1%; white-space:nowrap; text-align:left; padding:8px 10px;'>테마명</th>"
                        "<th style='width:1%; white-space:nowrap; text-align:center; padding:8px;'>종목수</th>"
                        "<th style='width:1%; white-space:nowrap; text-align:right; padding:8px 10px;'>합산 외/기 순매수(억)</th>"
                        "<th style='text-align:left; padding:8px 10px;'>대표 종목</th>"
                        "</tr></thead>"
                        f"<tbody>{''.join(theme_rank_rows_html)}</tbody>"
                        "</table>"
                        "</div>"
                    )
                    st.markdown(theme_rank_table_html, unsafe_allow_html=True)

                    # 🌟 [신규 2026-07-31] 테마별 AI 요약 진입점 — "내 관심종목" 삭제 버튼과 동일한
                    # 4열 그리드 버튼 패턴 재사용. 클릭하면 해당 테마의 대표 종목(순매수 상위 5개) 뉴스를
                    # 모아 AI 분석 팝업(show_theme_summary_dialog)을 띄움.
                    st.write("---")
                    st.markdown("<div style='font-size:13px; color:#aaa; margin-bottom:6px;'>🤖 테마별 AI 요약 보기</div>", unsafe_allow_html=True)
                    theme_ai_cols = st.columns(4)
                    for idx_theme, t_name_btn in enumerate(df_theme_rank["테마명"].tolist()):
                        with theme_ai_cols[idx_theme % 4]:
                            if st.button(f"🤖 {t_name_btn}", key=f"theme_ai_btn_{t_name_btn}", use_container_width=True):
                                rep_stocks_for_dialog = [
                                    {"name": n, "net": v, "code": c}
                                    for n, v, c in sorted(theme_agg[t_name_btn]["stocks"], key=lambda x: x[1], reverse=True)[:5]
                                ]
                                trigger_theme = st.session_state.get('dialog_trigger_id', 0) + 1
                                st.session_state['dialog_trigger_id'] = trigger_theme
                                st.session_state['show_theme_summary_dialog'] = {
                                    "theme": t_name_btn,
                                    "rep_stocks": rep_stocks_for_dialog,
                                    "trigger_id": trigger_theme
                                }
                                st.rerun()

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
                                # 🔧 [수정 2026-08-03] 반복 클릭 감지용 render_id가 셀 id에 추가되면서
                                # id가 "종목___날짜___render_id" 3파트가 됐는데, 여기서는 여전히 2개로
                                # 언패킹하려다 ValueError가 나서 셀 클릭이 먹통이 됐던 버그 수정 —
                                # goto___/summary___ 분기와 동일하게 앞 2개 파트만 사용.
                                parts = clicked.split("___")
                                stock, date_str = parts[0], parts[1]
                                st.session_state['show_mock_dialog'] = {
                                    "stock": stock,
                                    "date": date_str
                                }
                                # 🔧 [수정 2026-08-03] 사용자 재확인 버그: 가상 데이터 입력 → "가상 데이터
                                # 일괄 삭제"로 삭제 → 같은 셀을 다시 클릭하면 반응이 아예 없는 문제 발견.
                                # 원인: goto___/summary___ 분기는 처리 후 sangseongo_reset(render_id)을
                                # 올려서 다음 렌더의 셀 id가 바뀌는데, 이 mock 분기만 그걸 빼먹어서 같은 셀의
                                # DOM id가 계속 고정됨 — st_click_detector는 "값이 실제로 바뀔 때만" 새 이벤트를
                                # 파이썬에 알려주므로, 같은 셀을 연달아 클릭하면(=id가 그대로라 값이 안 바뀜)
                                # rerun 자체가 안 일어나 "완전 무반응"으로 보였음(다른 셀을 클릭해야만 그 사이에
                                # 껴서 풀리는 것도 이 때문). goto___/summary___와 동일하게 render_id를 올려서
                                # 다음 클릭부터는 같은 셀이라도 항상 새 id가 되도록 통일.
                                st.session_state['sangseongo_reset'] = st.session_state.get('sangseongo_reset', 0) + 1
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

        elif scrn_select == "공매도·대차잔고 워치":
            # 🌟 [신규 2026-08-01] 골든스코어가 "매수세가 몰리는 곳"을 보여준다면, 이 화면은 반대로
            # "공매도/대차가 몰리는 위험 신호"를 보여줌. 데이터 출처: scripts/fetch_market_risk_signals.py
            # (매일 장마감 15:45 이후 자동 수집). ⚠️ 이 화면은 실제 KIS API 응답으로 검증되지 못한 상태 —
            # 데이터가 비어 보이거나 이상하면 수집 스크립트를 먼저 확인해야 함.
            # 📅 [수정 2026-08-02] 날짜 계산/세션state 초기화를 컬럼 블록보다 앞으로 옮김 — 좌측 컬럼
            # 안에서도 "조회 날짜" 안내 캡션을 표시해서(우측 달력과 높이를 더 맞추기 위해) sw_selected_date/
            # sw_date_touched를 컬럼 진입 전에 미리 읽을 수 있어야 하기 때문.
            now_kst = datetime.utcnow() + timedelta(hours=9)
            if now_kst.time() < datetime.strptime("16:00", "%H:%M").time():
                target_dt = now_kst - timedelta(days=1)
            else:
                target_dt = now_kst
            target_dt = target_dt.replace(hour=12, minute=0, second=0, microsecond=0)
            sw_today_kor = get_latest_market_open_date(target_dt)
            sw_min_date = sw_today_kor - timedelta(days=90)

            import calendar
            from st_click_detector import click_detector

            if 'sw_cal_year' not in st.session_state:
                st.session_state.sw_cal_year = sw_today_kor.year
                st.session_state.sw_cal_month = sw_today_kor.month
                st.session_state.sw_selected_date = sw_today_kor
                st.session_state.sw_cal_reset = 0
                # 🔧 [수정 2026-08-02] 아래 "달력 미조작(터치 전)" 판단용 플래그. 각 데이터 소스(대차잔고/
                # 공매도/신용잔고/프로그램매매)의 실제 최신 수집일이 서로 다를 수 있어(수동 실행 시점이 제각각),
                # 달력이 계산해주는 "이론상 최신 거래일"과 실제 DB의 최신 날짜가 어긋나면 특정 위젯만 "데이터
                # 없음"으로 보이는 문제가 있었음 — 사용자가 실제로 날짜를 클릭하기 전까지는 target_date를
                # None으로 넘겨 각 함수가 기존처럼(달력 도입 전과 동일하게) 자기 테이블의 진짜 최신 날짜를
                # 알아서 찾도록 함.
                st.session_state.sw_date_touched = False

            col_sw_left, col_sw_right = st.columns([1.8, 1])
            with col_sw_left:
                st.markdown("<h4 style='color:#3C8181; border-left: 4px solid #3C8181; padding-left: 10px;'>📉 공매도·대차잔고 워치</h4>", unsafe_allow_html=True)
                st.caption("매수세가 아니라 공매도·대차잔고가 몰리는 종목을 보여주는 '위험 신호' 화면입니다. 골든스코어(매수 쏠림)와 반대 관점으로 함께 참고하세요.")
                # 🔧 [수정 2026-08-02] "외기 TOP100"/"신프로" 화면과 동일하게, 행 클릭 동작 선택 라디오를
                # 달력과 같은 줄(왼쪽 컬럼)에 배치 — 좌측 컬럼(제목+설명만)이 우측 달력보다 훨씬 짧아서
                # 달력 아래에 큰 빈 공간이 남아 보이던 문제를 줄이기 위함. 아래 대차잔고/공매도 상위종목
                # 표 2개가 이 하나의 라디오를 공유해서 사용함(원래 표마다 따로 있던 라디오를 통합).
                sw_click_action = st.radio(
                    "👇 아래 표에서 종목(행)을 클릭했을 때 동작을 선택하세요:",
                    ["📊 시계열 추적 (차트 이동)", "💬 AI 요약 보기 (팝업)"],
                    horizontal=True,
                    key="sw_click_action"
                )
                # 🔧 [수정 2026-08-02] 날짜 상태 안내 캡션도 좌측 컬럼 안으로 이동 — 예전에는 컬럼 블록이
                # 끝난 뒤 전체 폭에 따로 표시해서 좌측 컬럼 높이에 보탬이 안 됐음. 여기로 옮기면 좌측 컬럼
                # 높이가 실제로 늘어나 우측 달력과의 빈 공간이 더 줄어듦.
                if st.session_state.get('sw_date_touched', False):
                    st.caption(f"📅 조회 날짜: {st.session_state.sw_selected_date.strftime('%Y-%m-%d')}" + (" (최신 거래일)" if st.session_state.sw_selected_date == sw_today_kor else " (과거 조회)"))
                else:
                    st.caption("📅 각 항목의 최신 수집일 기준으로 표시 중입니다 (달력에서 과거 날짜를 선택할 수 있습니다)")

            with col_sw_right:
                # 📅 [신규 2026-08-02] "고래 골든픽"/"외기 TOP100" 화면과 동일한 커스텀 HTML 달력 연동.
                # 상위종목 표/당일 스냅샷 위젯을 선택한 과거 날짜 기준으로 조회. (아래 KOSPI/KOSDAQ
                # 대차잔고 line chart는 이미 여러 날짜를 보여주는 추세 차트라 달력 미연동 — 그대로 유지.)
                sw_cal_year = st.session_state.sw_cal_year
                sw_cal_month = st.session_state.sw_cal_month
                sw_selected_date = st.session_state.sw_selected_date

                # 🔧 [수정 2026-08-02] 사용자가 "달력 아래쪽 빈 공간을 좀 더 좁혀달라"고 재요청 —
                # 좌측 컬럼 높이(라디오+캡션)를 더 늘리는 대신, 달력 자체를 조금 더 컴팩트하게
                # 렌더링해서 우측 컬럼 높이를 줄이는 방향으로 접근(바깥 padding/줄간격/셀 padding/
                # 폰트 크기를 소폭 축소). 클릭 가능 영역/가독성에는 영향 없는 수준으로만 축소함.
                sw_html_cal = f"""
                <div style="max-width: 230px; margin-left: auto; background: #1a1c24; padding: 6px; border-radius: 10px; font-family: 'Inter', sans-serif; box-shadow: 0 4px 6px rgba(0,0,0,0.3);">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; color: white;">
                        <a href='#' id='sw_cal_prev' style='color: #888; text-decoration: none; padding: 2px 8px; background: #2a2d3a; border-radius: 4px; font-weight: bold; font-size: 12px;'>&lt;</a>
                        <strong style="font-size: 14px;">{sw_cal_year}년 {sw_cal_month}월</strong>
                        <a href='#' id='sw_cal_next' style='color: #888; text-decoration: none; padding: 2px 8px; background: #2a2d3a; border-radius: 4px; font-weight: bold; font-size: 12px;'>&gt;</a>
                    </div>
                    <div style="display: grid; grid-template-columns: repeat(7, 1fr); text-align: center; gap: 2px; font-size: 10px; font-weight: bold; margin-bottom: 3px; line-height: 1.2;">
                        <div style="color: #ff4b4b;">일</div>
                        <div style="color: #aaa;">월</div>
                        <div style="color: #aaa;">화</div>
                        <div style="color: #aaa;">수</div>
                        <div style="color: #aaa;">목</div>
                        <div style="color: #aaa;">금</div>
                        <div style="color: #4B89B5;">토</div>
                    </div>
                    <div style="display: grid; grid-template-columns: repeat(7, 1fr); text-align: center; gap: 2px; font-size: 10px; line-height: 1.2;">
                """

                sw_c = calendar.Calendar(firstweekday=6)
                for week in sw_c.monthdatescalendar(sw_cal_year, sw_cal_month):
                    for day in week:
                        if day.month == sw_cal_month:
                            bg_color = "transparent"
                            color = "white"
                            border = "1px solid transparent"

                            if day == sw_selected_date:
                                bg_color = "#3C8181"
                                color = "white"
                            elif day.weekday() == 6:
                                color = "#ff4b4b"
                            elif day.weekday() == 5:
                                color = "#4B89B5"

                            if day == sw_today_kor and day != sw_selected_date:
                                border = "1px solid #3C8181"

                            if day > sw_today_kor or day < sw_min_date:
                                sw_html_cal += f"<div style='padding: 3px; color: #444; border: {border}; border-radius: 4px;'>{day.day}</div>"
                            else:
                                sw_html_cal += f"<a href='#' id='sw_cal_date_{day.strftime('%Y-%m-%d')}' style='padding: 3px; background: {bg_color}; color: {color}; border: {border}; text-decoration: none; border-radius: 4px; display: block; font-weight: bold;'>{day.day}</a>"
                        else:
                            sw_html_cal += "<div></div>"

                sw_html_cal += "</div></div>"

                sw_clicked = click_detector(sw_html_cal, key=f"sw_cal_ui_{st.session_state.sw_cal_reset}")

            if sw_clicked:
                if sw_clicked == 'sw_cal_prev':
                    if st.session_state.sw_cal_month == 1:
                        st.session_state.sw_cal_month = 12
                        st.session_state.sw_cal_year -= 1
                    else:
                        st.session_state.sw_cal_month -= 1
                    st.session_state.sw_cal_reset += 1
                    st.rerun()
                elif sw_clicked == 'sw_cal_next':
                    if st.session_state.sw_cal_month == 12:
                        st.session_state.sw_cal_month = 1
                        st.session_state.sw_cal_year += 1
                    else:
                        st.session_state.sw_cal_month += 1
                    st.session_state.sw_cal_reset += 1
                    st.rerun()
                elif sw_clicked.startswith('sw_cal_date_'):
                    date_str = sw_clicked.split('sw_cal_date_')[1]
                    st.session_state.sw_selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                    st.session_state.sw_date_touched = True
                    st.session_state.sw_cal_reset += 1
                    st.rerun()

            sw_selected_date = st.session_state.sw_selected_date
            sw_sel_date_str = sw_selected_date.strftime("%Y-%m-%d")
            # 🔧 [수정 2026-08-02] 사용자가 달력을 아직 안 건드렸으면(sw_date_touched=False) 아래 데이터
            # 조회 함수들에 target_date=None을 넘겨(달력 도입 전과 동일하게) 각자 실제 최신 날짜를 스스로 찾게 함.
            # (날짜 상태 안내 캡션은 위쪽 헤더 좌측 컬럼으로 옮겨서 여기서는 더 이상 출력하지 않음.)
            sw_target_date_param = sw_sel_date_str if st.session_state.get('sw_date_touched', False) else None
            st.write("---")

            loan_trend_df = get_market_loan_trans_trend(days=20)
            if loan_trend_df.empty:
                st.info("💡 시장 전체 대차잔고 추이 데이터가 아직 없습니다. 수집 스크립트가 최소 1회 실행된 이후 표시됩니다.")
            else:
                trend_cols = st.columns(2)
                for i, mkt in enumerate(["KOSPI", "KOSDAQ"]):
                    mkt_df = loan_trend_df[loan_trend_df['market'] == mkt]
                    if mkt_df.empty:
                        continue
                    if sw_target_date_param:
                        date_match = mkt_df[mkt_df['trade_date'] == sw_target_date_param]
                        latest_row = date_match.iloc[-1] if not date_match.empty else mkt_df.iloc[-1]
                        is_fallback = date_match.empty
                    else:
                        latest_row = mkt_df.iloc[-1]
                        is_fallback = False
                    with trend_cols[i]:
                        st.markdown(f"**{mkt} 대차잔고**")
                        if is_fallback:
                            st.caption(f"⚠️ 선택한 {sw_target_date_param}는 이 지표의 최근 조회 범위(20거래일) 밖이라 가장 최근 데이터({latest_row['trade_date']})로 대체 표시합니다.")
                        # 🌟 [2026-08-02] 잔고금액(rmnd_amt)의 실제 단위는 KIS 문서에 명시돼 있지 않으나,
                        # 같은 응답의 잔고주수(rmnd_stcn)와 나눠보면 1주당 평균 단가가 KOSPI는 약 8만원,
                        # KOSDAQ은 약 1.7만원대로 나와(둘 다 실제 시세와 맞아떨어짐) — "백만원" 단위로 추정.
                        est_trillion = (latest_row['balance_amount'] or 0) / 1_000_000
                        st.metric(
                            label=f"{latest_row['trade_date']} 기준 잔고금액 (추정: 백만원 단위)",
                            value=f"약 {est_trillion:,.1f}조원",
                            delta=f"{latest_row['balance_change']:,.0f} 백만원"
                        )
                        st.caption(f"원본값 {latest_row['balance_amount']:,.0f} (백만원 추정 — 잔고주수 대비 역산, 공식 확인 전까지 참고용)")
                        # 🌟 [2026-08-02] st.line_chart는 x축 라벨 각도를 조절할 수 없어(세로 회전 고정),
                        # 다른 두 차트와 마찬가지로 plotly(plotly_dark 템플릿)로 교체해 라벨을 수평으로 표시.
                        chart_df = mkt_df.set_index('trade_date')[['balance_amount']]
                        # 🌟 [2026-08-02] 연도까지 표시하면 x축 자리를 많이 차지해서, "MM-DD"만 잘라서 표시
                        x_labels_loan = [d[5:] if isinstance(d, str) and len(d) == 10 else str(d) for d in chart_df.index]
                        # 🌟 [2026-08-02] Y축도 "억원" 단위로 통일(백만원 → 억원 = /100), k/M 자동축약 표기를
                        # 막기 위해 tickformat/hovertemplate을 명시적으로 콤마 정수 포맷으로 고정.
                        y_loan_eok = (chart_df['balance_amount'] / 100).tolist()
                        fig_loan = go.Figure(data=[go.Scatter(
                            x=x_labels_loan,
                            y=y_loan_eok,
                            mode='lines+markers',
                            name=f'{mkt} 잔고금액(억원)',
                            line=dict(color='#3C8181'),
                            hovertemplate='%{x}<br>%{y:,.0f}억원<extra></extra>',
                        )])
                        fig_loan.update_layout(
                            template='plotly_dark',
                            plot_bgcolor='#11111b', paper_bgcolor='#11111b',
                            font_color='#e0e0e0',
                            height=180,
                            margin=dict(l=20, r=20, t=10, b=20),
                            xaxis=dict(tickangle=0, type='category'),
                            yaxis=dict(title='억원', tickformat=',.0f'),
                            showlegend=False,
                        )
                        st.plotly_chart(fig_loan, use_container_width=True)

            st.write("---")
            st.markdown("<h5 style='color:#FFFFFF; margin-top:10px;'>📋 대차잔고 상위종목 (외/기 순매수 상위 200종목 대상)</h5>", unsafe_allow_html=True)
            st.caption("KIS API가 대차잔고는 '상위종목 랭킹'을 한 번에 주지 않아서, 이미 이 프로젝트가 관리 중인 daily_whale_top200(외국인/기관 순매수 상위 200종목)을 대상으로 종목별 잔고를 직접 조회해 자체 순위를 매긴 표입니다. 전체 시장이 아니라 이 200종목 안에서의 순위입니다.")
            lb_date, lb_rows = get_stock_loan_balance_ranking(limit=30, target_date=sw_target_date_param)
            if not lb_rows:
                if sw_target_date_param:
                    st.info(f"💡 {sw_target_date_param} 기준 종목별 대차잔고 데이터가 없습니다. 달력에서 다른 날짜를 선택해보세요.")
                else:
                    st.info("💡 종목별 대차잔고 데이터가 아직 없습니다. 수집 스크립트가 최소 1회 실행된 이후 표시됩니다.")
            else:
                st.caption(f"{lb_date} 마감 기준 · 대차잔고 금액 상위 {len(lb_rows)}종목 (200종목 내 순위)")
                # 🌟 [신규 2026-08-02] 다른 화면(외기 TOP100/체결 로그 등)과 동일한 "행 클릭 → 시계열 추적/AI 요약" 패턴 적용.
                # (행 클릭 동작 라디오는 위쪽 헤더 좌측 컬럼의 sw_click_action으로 공매도 표와 공유함)
                lb_click_action = sw_click_action
                lb_display_df = pd.DataFrame([{
                    "순위": int(r['rank']),
                    "종목명": r['stock_name'],
                    "stock_code": r.get('stock_code', ''),
                    "현재가": r['close_price'],
                    "등락률": r['change_rate'],
                    "잔고주수": r['balance_shares'],
                    "잔고금액": f"{(r.get('balance_amount') or 0) / 100:,.0f}억원",
                } for r in lb_rows])

                def _lb_style(row):
                    styles = [''] * len(row)
                    color = '#ff4b4b' if (row['등락률'] or 0) >= 0 else '#4B89B5'
                    styles[row.index.get_loc('등락률')] = f'color: {color};'
                    return styles

                lb_styled = lb_display_df.style.apply(_lb_style, axis=1)
                lb_reset_key = st.session_state.get('lb_reset_counter', 0)
                lb_event = st.dataframe(
                    lb_styled,
                    column_order=["순위", "종목명", "현재가", "등락률", "잔고주수", "잔고금액"],
                    column_config={
                        # 🔧 [수정 2026-08-02, 2차] "small"/"medium" 프리셋은 세밀 조절이 안 돼서(스크롤바에
                        # 마지막 컬럼이 가려지고 일부 컬럼 글자가 잘리는 문제) 픽셀 정수 폭으로 전환.
                        # 기존 small≈80px/medium≈200px 기준으로 순위·종목명은 40% 축소, 나머지는 25% 확대.
                        "순위": st.column_config.NumberColumn(format="%d", width=48),
                        "종목명": st.column_config.TextColumn(width=120),
                        "현재가": st.column_config.NumberColumn(format="%,.0f", width=100),
                        "등락률": st.column_config.NumberColumn(format="%+.2f%%", width=100),
                        "잔고주수": st.column_config.NumberColumn(format="%,.0f", width=100),
                        "잔고금액": st.column_config.TextColumn(width=100),
                    },
                    hide_index=True,
                    height=420,
                    use_container_width=False,
                    on_select="rerun",
                    selection_mode="single-row",
                    key=f"lb_dataframe_{lb_reset_key}"
                )
                if lb_event and "selection" in lb_event:
                    lb_rows_sel = lb_event["selection"]["rows"]
                    if lb_rows_sel and lb_rows_sel[0] < len(lb_display_df):
                        lb_sel_stock = lb_display_df.iloc[lb_rows_sel[0]]['종목명']
                        lb_sel_code = lb_display_df.iloc[lb_rows_sel[0]]['stock_code']
                        if lb_click_action == "💬 AI 요약 보기 (팝업)":
                            trigger = st.session_state.get('dialog_trigger_id', 0) + 1
                            st.session_state['dialog_trigger_id'] = trigger
                            st.session_state['show_summary_dialog'] = {"stock": lb_sel_stock, "code": lb_sel_code, "trigger_id": trigger}
                        else:
                            st.session_state['pending_search'] = lb_sel_stock
                            st.session_state['last_search_keyword'] = lb_sel_stock
                            st.session_state['scrn_select_radio'] = "체결 로그"
                        st.session_state['lb_reset_counter'] = lb_reset_key + 1
                        st.rerun()

            st.write("---")
            st.markdown("<h5 style='color:#FFFFFF; margin-top:10px;'>📋 공매도 상위종목</h5>", unsafe_allow_html=True)
            ss_date, ss_rows = get_short_sale_ranking(limit=30, target_date=sw_target_date_param)
            if not ss_rows:
                if sw_target_date_param:
                    st.info(f"💡 {sw_target_date_param} 기준 공매도 상위종목 데이터가 없습니다. 달력에서 다른 날짜를 선택해보세요.")
                else:
                    st.info("💡 공매도 상위종목 데이터가 아직 없습니다. 수집 스크립트가 최소 1회 실행된 이후 표시됩니다.")
            else:
                st.caption(f"{ss_date} 마감 기준 · 공매도 거래대금 상위 {len(ss_rows)}종목")
                # 🌟 [신규 2026-08-02] 대차잔고 표와 동일한 "행 클릭 → 시계열 추적/AI 요약" 패턴 적용.
                # 맨 오른쪽 '거래대금비중' 컬럼은 문자열(object dtype)로 저장해 왼쪽 정렬되도록 함.
                # (행 클릭 동작 라디오는 위쪽 헤더 좌측 컬럼의 sw_click_action으로 대차잔고 표와 공유함)
                ss_click_action = sw_click_action
                ss_display_df = pd.DataFrame([{
                    "순위": int(r['rank']),
                    "종목명": r['stock_name'],
                    "stock_code": r.get('stock_code', ''),
                    "현재가": r['close_price'],
                    "등락률": r['change_rate'],
                    "공매도체결량": r['short_sale_volume'],
                    "거래량비중": r['short_sale_volume_ratio'],
                    "공매도거래대금": r['short_sale_amount'],
                    "거래대금비중": f"({r['short_sale_amount_ratio']:.2f}%)",
                } for r in ss_rows])

                def _ss_style(row):
                    styles = [''] * len(row)
                    color = '#ff4b4b' if (row['등락률'] or 0) >= 0 else '#4B89B5'
                    styles[row.index.get_loc('등락률')] = f'color: {color};'
                    styles[row.index.get_loc('거래대금비중')] = 'color: #FFA500;'
                    return styles

                ss_styled = ss_display_df.style.apply(_ss_style, axis=1)
                ss_reset_key = st.session_state.get('ss_reset_counter', 0)
                ss_event = st.dataframe(
                    ss_styled,
                    column_order=["순위", "종목명", "현재가", "등락률", "공매도체결량", "거래량비중", "공매도거래대금", "거래대금비중"],
                    column_config={
                        # 🔧 [수정 2026-08-02, 3차] 헤더 라벨 글자 수가 5~7자로 긴 컬럼(공매도체결량/거래량비중/
                        # 공매도거래대금/거래대금비중)은 100px로는 헤더 텍스트 자체가 잘려서(...) 표시됨 —
                        # 헤더 길이에 맞춰 130~150px로 넉넉하게 재조정.
                        "순위": st.column_config.NumberColumn(format="%d", width=48),
                        "종목명": st.column_config.TextColumn(width=120),
                        "현재가": st.column_config.NumberColumn(format="%,.0f", width=100),
                        "등락률": st.column_config.NumberColumn(format="%+.2f%%", width=100),
                        "공매도체결량": st.column_config.NumberColumn(format="%,.0f주", width=140),
                        "거래량비중": st.column_config.NumberColumn(format="%.2f%%", width=130),
                        "공매도거래대금": st.column_config.NumberColumn(format="%,.0f", width=150),
                        "거래대금비중": st.column_config.TextColumn(width=140),
                    },
                    hide_index=True,
                    height=420,
                    use_container_width=False,
                    on_select="rerun",
                    selection_mode="single-row",
                    key=f"ss_dataframe_{ss_reset_key}"
                )
                if ss_event and "selection" in ss_event:
                    ss_rows_sel = ss_event["selection"]["rows"]
                    if ss_rows_sel and ss_rows_sel[0] < len(ss_display_df):
                        ss_sel_stock = ss_display_df.iloc[ss_rows_sel[0]]['종목명']
                        ss_sel_code = ss_display_df.iloc[ss_rows_sel[0]]['stock_code']
                        if ss_click_action == "💬 AI 요약 보기 (팝업)":
                            trigger = st.session_state.get('dialog_trigger_id', 0) + 1
                            st.session_state['dialog_trigger_id'] = trigger
                            st.session_state['show_summary_dialog'] = {"stock": ss_sel_stock, "code": ss_sel_code, "trigger_id": trigger}
                        else:
                            st.session_state['pending_search'] = ss_sel_stock
                            st.session_state['last_search_keyword'] = ss_sel_stock
                            st.session_state['scrn_select_radio'] = "체결 로그"
                        st.session_state['ss_reset_counter'] = ss_reset_key + 1
                        st.rerun()

        elif scrn_select == "신용잔고·프로그램매매 추이":
            # 🌟 [신규 2026-08-01] 신용잔고 상위 + 프로그램매매 동향을 함께 보여주는 화면.
            # "진짜 선행지표 찾기" 연구에도 데이터로 활용 가능. ⚠️ 이 화면도 실제 KIS API 응답으로
            # 검증되지 못한 상태 — 데이터가 비어 보이거나 이상하면 수집 스크립트를 먼저 확인해야 함.
            # 📅 [수정 2026-08-02] "공대치" 화면과 동일한 이유로, 날짜 계산/세션state 초기화를 컬럼
            # 블록보다 앞으로 옮김 — 좌측 컬럼 안에서도 "조회 날짜" 안내 캡션을 표시하기 위해.
            now_kst = datetime.utcnow() + timedelta(hours=9)
            if now_kst.time() < datetime.strptime("16:00", "%H:%M").time():
                target_dt = now_kst - timedelta(days=1)
            else:
                target_dt = now_kst
            target_dt = target_dt.replace(hour=12, minute=0, second=0, microsecond=0)
            cp_today_kor = get_latest_market_open_date(target_dt)
            cp_min_date = cp_today_kor - timedelta(days=90)

            import calendar
            from st_click_detector import click_detector

            if 'cp_cal_year' not in st.session_state:
                st.session_state.cp_cal_year = cp_today_kor.year
                st.session_state.cp_cal_month = cp_today_kor.month
                st.session_state.cp_selected_date = cp_today_kor
                st.session_state.cp_cal_reset = 0
                # 🔧 [수정 2026-08-02] "공대치" 화면과 동일한 이유로 터치 플래그 도입 — 신용잔고/
                # 프로그램매매 각각의 실제 최신 수집일이 달력의 "이론상 최신 거래일"과 어긋날 수 있어,
                # 사용자가 실제로 날짜를 클릭하기 전까지는 target_date=None으로 넘겨 기존 동작 유지.
                st.session_state.cp_date_touched = False

            col_cp_left, col_cp_right = st.columns([1.8, 1])
            with col_cp_left:
                st.markdown("<h4 style='color:#4C4686; border-left: 4px solid #4C4686; padding-left: 10px;'>💳 신용잔고·프로그램매매 추이</h4>", unsafe_allow_html=True)
                st.caption("신용(융자/대주)잔고가 몰린 종목과, 오늘 프로그램매매가 어느 투자자 주체로 몰렸는지를 함께 보여주는 화면입니다.")
                # 🔧 [수정 2026-08-02] "외기 TOP100" 화면과 동일하게, 행 클릭 동작 선택 라디오를 달력과
                # 같은 줄(왼쪽 컬럼)에 배치 — 좌측 컬럼(제목+설명만)이 우측 달력보다 훨씬 짧아서 달력
                # 아래에 큰 빈 공간이 남아 보이던 문제를 줄이기 위함(왼쪽 컬럼 내용을 늘려 높이를 맞춤).
                cb_click_action = st.radio(
                    "👇 표에서 종목(행)을 클릭했을 때 동작을 선택하세요:",
                    ["📊 시계열 추적 (차트 이동)", "💬 AI 요약 보기 (팝업)"],
                    horizontal=True,
                    key="cb_click_action"
                )
                # 🔧 [수정 2026-08-02] 날짜 상태 안내 캡션도 좌측 컬럼 안으로 이동 — "공대치"와 동일한
                # 이유(좌측 컬럼 높이를 늘려 우측 달력과의 빈 공간을 줄이기 위함).
                if st.session_state.get('cp_date_touched', False):
                    st.caption(f"📅 조회 날짜: {st.session_state.cp_selected_date.strftime('%Y-%m-%d')}" + (" (최신 거래일)" if st.session_state.cp_selected_date == cp_today_kor else " (과거 조회)"))
                else:
                    st.caption("📅 각 항목의 최신 수집일 기준으로 표시 중입니다 (달력에서 과거 날짜를 선택할 수 있습니다)")

            with col_cp_right:
                # 📅 [신규 2026-08-02] "공대치" 화면과 동일한 커스텀 HTML 달력 연동.
                # 신용잔고 상위종목/프로그램매매 투자자별 당일 동향은 선택 날짜 기준으로 조회.
                # (아래 프로그램매매 시장 일별 순매수 추이 line chart는 이미 여러 날짜를 보여주는
                # 추세 차트라 달력 미연동 — 그대로 유지.)
                cp_cal_year = st.session_state.cp_cal_year
                cp_cal_month = st.session_state.cp_cal_month
                cp_selected_date = st.session_state.cp_selected_date

                # 🔧 [수정 2026-08-02] "공대치"와 동일한 이유로 달력을 소폭 컴팩트하게 렌더링(바깥
                # padding/줄간격/셀 padding/폰트 크기 축소) — 클릭 가능 영역/가독성은 그대로 유지.
                cp_html_cal = f"""
                <div style="max-width: 230px; margin-left: auto; background: #1a1c24; padding: 6px; border-radius: 10px; font-family: 'Inter', sans-serif; box-shadow: 0 4px 6px rgba(0,0,0,0.3);">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; color: white;">
                        <a href='#' id='cp_cal_prev' style='color: #888; text-decoration: none; padding: 2px 8px; background: #2a2d3a; border-radius: 4px; font-weight: bold; font-size: 12px;'>&lt;</a>
                        <strong style="font-size: 14px;">{cp_cal_year}년 {cp_cal_month}월</strong>
                        <a href='#' id='cp_cal_next' style='color: #888; text-decoration: none; padding: 2px 8px; background: #2a2d3a; border-radius: 4px; font-weight: bold; font-size: 12px;'>&gt;</a>
                    </div>
                    <div style="display: grid; grid-template-columns: repeat(7, 1fr); text-align: center; gap: 2px; font-size: 10px; font-weight: bold; margin-bottom: 3px; line-height: 1.2;">
                        <div style="color: #ff4b4b;">일</div>
                        <div style="color: #aaa;">월</div>
                        <div style="color: #aaa;">화</div>
                        <div style="color: #aaa;">수</div>
                        <div style="color: #aaa;">목</div>
                        <div style="color: #aaa;">금</div>
                        <div style="color: #4B89B5;">토</div>
                    </div>
                    <div style="display: grid; grid-template-columns: repeat(7, 1fr); text-align: center; gap: 2px; font-size: 10px; line-height: 1.2;">
                """

                cp_c = calendar.Calendar(firstweekday=6)
                for week in cp_c.monthdatescalendar(cp_cal_year, cp_cal_month):
                    for day in week:
                        if day.month == cp_cal_month:
                            bg_color = "transparent"
                            color = "white"
                            border = "1px solid transparent"

                            if day == cp_selected_date:
                                bg_color = "#4C4686"
                                color = "white"
                            elif day.weekday() == 6:
                                color = "#ff4b4b"
                            elif day.weekday() == 5:
                                color = "#4B89B5"

                            if day == cp_today_kor and day != cp_selected_date:
                                border = "1px solid #4C4686"

                            if day > cp_today_kor or day < cp_min_date:
                                cp_html_cal += f"<div style='padding: 3px; color: #444; border: {border}; border-radius: 4px;'>{day.day}</div>"
                            else:
                                cp_html_cal += f"<a href='#' id='cp_cal_date_{day.strftime('%Y-%m-%d')}' style='padding: 3px; background: {bg_color}; color: {color}; border: {border}; text-decoration: none; border-radius: 4px; display: block; font-weight: bold;'>{day.day}</a>"
                        else:
                            cp_html_cal += "<div></div>"

                cp_html_cal += "</div></div>"

                cp_clicked = click_detector(cp_html_cal, key=f"cp_cal_ui_{st.session_state.cp_cal_reset}")

            if cp_clicked:
                if cp_clicked == 'cp_cal_prev':
                    if st.session_state.cp_cal_month == 1:
                        st.session_state.cp_cal_month = 12
                        st.session_state.cp_cal_year -= 1
                    else:
                        st.session_state.cp_cal_month -= 1
                    st.session_state.cp_cal_reset += 1
                    st.rerun()
                elif cp_clicked == 'cp_cal_next':
                    if st.session_state.cp_cal_month == 12:
                        st.session_state.cp_cal_month = 1
                        st.session_state.cp_cal_year += 1
                    else:
                        st.session_state.cp_cal_month += 1
                    st.session_state.cp_cal_reset += 1
                    st.rerun()
                elif cp_clicked.startswith('cp_cal_date_'):
                    date_str = cp_clicked.split('cp_cal_date_')[1]
                    st.session_state.cp_selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                    st.session_state.cp_date_touched = True
                    st.session_state.cp_cal_reset += 1
                    st.rerun()

            cp_selected_date = st.session_state.cp_selected_date
            cp_sel_date_str = cp_selected_date.strftime("%Y-%m-%d")
            # (날짜 상태 안내 캡션은 위쪽 헤더 좌측 컬럼으로 옮겨서 여기서는 더 이상 출력하지 않음.)
            cp_target_date_param = cp_sel_date_str if st.session_state.get('cp_date_touched', False) else None
            st.write("---")

            st.markdown("<h5 style='color:#FFFFFF; margin-top:10px;'>📋 신용잔고 상위종목 (융자잔고 금액 기준)</h5>", unsafe_allow_html=True)
            cb_date, cb_rows = get_credit_balance_ranking(limit=30, target_date=cp_target_date_param)
            if not cb_rows:
                if cp_target_date_param:
                    st.info(f"💡 {cp_target_date_param} 기준 신용잔고 상위종목 데이터가 없습니다. 달력에서 다른 날짜를 선택해보세요.")
                else:
                    st.info("💡 신용잔고 상위종목 데이터가 아직 없습니다. 수집 스크립트가 최소 1회 실행된 이후 표시됩니다.")
            else:
                st.caption(f"{cb_date} 마감 기준 · 융자잔고 금액 상위 {len(cb_rows)}종목")
                # 🌟 [신규 2026-08-02] 대차잔고/공매도 표와 동일한 "행 클릭 → 시계열 추적/AI 요약" 패턴 적용.
                # 융자잔고비율/대주잔고비율은 문자열(object dtype)로 저장해 왼쪽 정렬 + 주황색 표시.
                # (cb_click_action 라디오는 위쪽 헤더 좌측 컬럼으로 이동했음 — 여기서는 그 값을 그대로 사용)
                cb_display_df = pd.DataFrame([{
                    "순위": int(r['rank']),
                    "종목명": r['stock_name'],
                    "stock_code": r.get('stock_code', ''),
                    "현재가": r['close_price'],
                    "등락률": r['change_rate'],
                    "융자잔고금액": r['loan_balance_amount'],
                    "융자잔고비율": f"({r['loan_balance_ratio']:.2f}%)",
                    "대주잔고금액": r['short_loan_balance_amount'],
                    "대주잔고비율": f"({r['short_loan_balance_ratio']:.2f}%)",
                } for r in cb_rows])

                def _cb_style(row):
                    styles = [''] * len(row)
                    color = '#ff4b4b' if (row['등락률'] or 0) >= 0 else '#4B89B5'
                    styles[row.index.get_loc('등락률')] = f'color: {color};'
                    styles[row.index.get_loc('융자잔고비율')] = 'color: #FFA500;'
                    styles[row.index.get_loc('대주잔고비율')] = 'color: #FFA500;'
                    return styles

                cb_styled = cb_display_df.style.apply(_cb_style, axis=1)
                cb_reset_key = st.session_state.get('cb_reset_counter', 0)
                cb_event = st.dataframe(
                    cb_styled,
                    column_order=["순위", "종목명", "현재가", "등락률", "융자잔고금액", "융자잔고비율", "대주잔고금액", "대주잔고비율"],
                    column_config={
                        # 🔧 [수정 2026-08-02, 3차] 헤더 라벨이 6자로 긴 컬럼(융자잔고금액/융자잔고비율/
                        # 대주잔고금액/대주잔고비율)은 100px로는 헤더 텍스트가 잘려서(...) 표시됨 —
                        # 140px로 넉넉하게 재조정.
                        "순위": st.column_config.NumberColumn(format="%d", width=48),
                        "종목명": st.column_config.TextColumn(width=120),
                        "현재가": st.column_config.NumberColumn(format="%,.0f", width=100),
                        "등락률": st.column_config.NumberColumn(format="%+.2f%%", width=100),
                        "융자잔고금액": st.column_config.NumberColumn(format="%,.0f", width=140),
                        "융자잔고비율": st.column_config.TextColumn(width=140),
                        "대주잔고금액": st.column_config.NumberColumn(format="%,.0f", width=140),
                        "대주잔고비율": st.column_config.TextColumn(width=140),
                    },
                    hide_index=True,
                    height=420,
                    use_container_width=False,
                    on_select="rerun",
                    selection_mode="single-row",
                    key=f"cb_dataframe_{cb_reset_key}"
                )
                if cb_event and "selection" in cb_event:
                    cb_rows_sel = cb_event["selection"]["rows"]
                    if cb_rows_sel and cb_rows_sel[0] < len(cb_display_df):
                        cb_sel_stock = cb_display_df.iloc[cb_rows_sel[0]]['종목명']
                        cb_sel_code = cb_display_df.iloc[cb_rows_sel[0]]['stock_code']
                        if cb_click_action == "💬 AI 요약 보기 (팝업)":
                            trigger = st.session_state.get('dialog_trigger_id', 0) + 1
                            st.session_state['dialog_trigger_id'] = trigger
                            st.session_state['show_summary_dialog'] = {"stock": cb_sel_stock, "code": cb_sel_code, "trigger_id": trigger}
                        else:
                            st.session_state['pending_search'] = cb_sel_stock
                            st.session_state['last_search_keyword'] = cb_sel_stock
                            st.session_state['scrn_select_radio'] = "체결 로그"
                        st.session_state['cb_reset_counter'] = cb_reset_key + 1
                        st.rerun()

            st.write("---")
            st.markdown("<h5 style='color:#FFFFFF; margin-top:10px;'>🤖 프로그램매매 투자자별 당일 동향</h5>", unsafe_allow_html=True)
            pt_date, pt_rows = get_program_trade_investor_today(target_date=cp_target_date_param)
            if not pt_rows:
                if cp_target_date_param:
                    st.info(f"💡 {cp_target_date_param} 기준 프로그램매매 투자자별 동향 데이터가 없습니다. 달력에서 다른 날짜를 선택해보세요.")
                else:
                    st.info("💡 프로그램매매 투자자별 동향 데이터가 아직 없습니다. 수집 스크립트가 최소 1회 실행된 이후 표시됩니다.")
            else:
                st.caption(f"{pt_date} 기준 · 순매수대금(억원) 큰 순")
                # 🌟 [2026-08-02] 사용자가 KIS 공식 안내를 확인해줌: '순매수대금'류 필드는 백만원 단위 정수로
                # 내려옴(예: API값 150 → 1억5,000만원, 12450 → 124억5,000만원) → 억원 = 백만원값 / 100.
                pt_chart_df = pd.DataFrame(pt_rows).set_index('investor_name')[['net_amount']].rename(columns={'net_amount': '순매수대금'})
                pt_chart_df['순매수대금'] = pt_chart_df['순매수대금'] / 100
                # 🌟 [2026-08-02] st.bar_chart는 x축 라벨 각도를 조절할 수 없어(세로로만 표시),
                # x축 라벨을 수평으로 보기 위해 이미 프로젝트에서 검증된 plotly(plotly_dark 템플릿)로 교체.
                fig_pt = go.Figure(data=[go.Bar(
                    x=pt_chart_df.index.tolist(),
                    y=pt_chart_df['순매수대금'].tolist(),
                    marker_color='#4C8BF5',
                    hovertemplate='%{x}<br>%{y:,.0f}억원<extra></extra>',
                )])
                fig_pt.update_layout(
                    template='plotly_dark',
                    plot_bgcolor='#11111b', paper_bgcolor='#11111b',
                    font_color='#e0e0e0',
                    height=260,
                    margin=dict(l=20, r=20, t=10, b=20),
                    xaxis=dict(tickangle=0),
                    # 🌟 [2026-08-02] tickformat 명시로 plotly 기본 k/M 자동축약(예: 40k) 방지 — 콤마 정수로 고정
                    yaxis=dict(title='억원', tickformat=',.0f'),
                )
                st.plotly_chart(fig_pt, use_container_width=True)

            st.write("---")
            st.markdown("<h5 style='color:#FFFFFF; margin-top:10px;'>📈 프로그램매매 시장 일별 순매수 추이</h5>", unsafe_allow_html=True)
            prog_trend_df = get_program_trade_market_trend(days=20)
            if prog_trend_df.empty:
                st.info("💡 프로그램매매 시장 일별 추이 데이터가 아직 없습니다. 수집 스크립트가 최소 1회 실행된 이후 표시됩니다.")
            else:
                # ⚠️ 아직 하루치 데이터만 쌓인 시계열이라 선이 아닌 점 하나로 보일 수 있음 —
                # 매일 자동 수집이 쌓일수록 추세선다운 모습을 갖추게 됨.
                # 🌟 [2026-08-02] 사용자가 KIS 공식 안내를 확인해줌: 이 값도 '매수대금-매도대금'으로 만든
                # 순매수대금류 필드라 백만원 단위 정수 — 억원 = 백만원값 / 100.
                pivot_df = prog_trend_df.pivot_table(index='trade_date', columns='market', values='net_amount', aggfunc='last') / 100
                fig_prog = go.Figure()
                # 🌟 [2026-08-02] 연도까지 표시하면 x축 자리를 많이 차지해서, "MM-DD"만 잘라서 표시
                x_labels_prog = [d[5:] if isinstance(d, str) and len(d) == 10 else str(d) for d in pivot_df.index]
                for col in pivot_df.columns:
                    fig_prog.add_trace(go.Scatter(
                        x=x_labels_prog,
                        y=pivot_df[col].tolist(),
                        mode='lines+markers',
                        name=col,
                        hovertemplate='%{x}<br>%{y:,.0f}억원<extra>' + str(col) + '</extra>',
                    ))
                fig_prog.update_layout(
                    template='plotly_dark',
                    plot_bgcolor='#11111b', paper_bgcolor='#11111b',
                    font_color='#e0e0e0',
                    height=220,
                    margin=dict(l=20, r=20, t=10, b=20),
                    xaxis=dict(tickangle=0, type='category'),
                    # 🌟 [2026-08-02] tickformat 명시로 plotly 기본 k/M 자동축약 방지 — 콤마 정수로 고정
                    yaxis=dict(title='억원', tickformat=',.0f'),
                    legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='left', x=0),
                )
                st.plotly_chart(fig_prog, use_container_width=True)
                st.caption("단위: 억원 (KIS 안내 기준 백만원 단위 응답을 억원으로 환산)")

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
                # 🔧 [수정 2026-07-31, 2번째] 사용자 포토샵 목업 기준 재배치: 타이틀은 단독 줄(전체
                # 폭)로 위에 두고, 그 아래 한 줄에 안내문구(정보박스)와 자산유형/시장 필터 라디오
                # 2개를 나란히 배치 — 같은 컬럼 행의 형제 요소들이라 상단이 자동으로 정렬됨(정보박스
                # 상단 = 라디오 상단). 라디오 열은 이 행의 마지막 컬럼이라 우측 끝이 전체 컨테이너
                # 폭에 맞춰지는데, 아래 "미국 테마 등락률" 위젯(hot_cols의 마지막 칸)도 동일하게
                # 컨테이너 우측 끝에서 끝나므로 두 우측 끝이 자연히 서로 맞음.
                if show_only_upper_limit:
                    st.subheader(f"📋 놀빅 상한가 종목 고래 체결 목록")
                else:
                    st.subheader(f"📋 실시간 놀빅 고래 체결 상황")

                # 🔧 [수정 2026-07-31, 4번째] 사용자 재피드백: 우측 정렬 CSS 시도는 Y축(상단 정렬)까지
                # 살짝 어긋나게 만들어서 반려 → 우측 정렬 CSS/마커 전부 제거하고, 더 단순한 방법으로
                # 전환: 라디오 옵션은 그대로 기본(좌측 정렬) 두고, 대신 컬럼 폭 자체를 조정해서
                # asset_col(자산유형 라디오)의 "좌측" 시작 지점이 hot_cols의 "미국 테마 등락률" 위젯
                # 좌측 시작 지점과 같은 비율(70%, hot_cols=[0.7,0.7,0.7,0.9]의 2.1/3.0 지점)에 오도록
                # 맞춤. 같은 3.0 단위 스케일을 그대로 재사용해 [2.1, 0.5, 0.4]로 구성 — info_col이
                # 2.1(=70%)을 차지하므로 그 다음 asset_col이 시작하는 지점이 정확히 hot_cols의 위젯
                # 시작 지점(2.1/3.0)과 일치함.
                info_col, asset_col, market_col = st.columns([2.1, 0.5, 0.4])
                with info_col:
                    if not show_only_upper_limit:
                        st.info("💡 당일 실시간 500 거래를 분석자료로 표시합니다.")
                with asset_col:
                    st.radio(
                        "🗂️ 자산 유형 필터",
                        ["개별 주식만 보기 🏢", "ETF만 보기 🌐", "전체 다 보기 📊"],
                        index=["개별 주식만 보기 🏢", "ETF만 보기 🌐", "전체 다 보기 📊"].index(asset_type),
                        key="asset_type_log",
                        horizontal=False,
                        label_visibility="collapsed",
                        on_change=sync_log_filters
                    )
                with market_col:
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
                # 🔧 [수정 2026-08-01] 사용자 요청: 카드 3개 폭을 각각 30%씩 줄이고, 남는 공간(전체의
                # 약 23%)에 미국 테마 등락률 위젯을 배치. 기존 3등분(각 1칸)에서 각 칸을 0.7로 줄이면
                # (1 - 0.7 = 0.3, 3칸 합산 0.9만큼 여유가 생김) 그 0.9를 새 위젯 칸에 배정.
                #
                # 🔧 [수정 2026-08-01, 2번째] 증시 시황 버튼 4개를 처음엔 카드+위젯 블록과 별개의
                # 새 st.columns(4) 행으로 추가했더니, 버튼 열이 전체 폭(카드 3개+위젯)에 맞춰 4등분되어
                # 버튼 오른쪽 끝이 위젯 오른쪽 끝까지 밀려나고, 위젯 박스가 카드보다 세로로 더 길어서
                # 버튼 줄과 위젯 하단이 안 맞는 문제를 사용자가 캡처로 지적함. → "카드 3개 + 버튼 4개"를
                # 하나의 왼쪽 칸(전체의 2.1/3.0 = 70%)으로 묶고, 위젯은 오른쪽 칸(0.9/3.0 = 30%)에 두는
                # 중첩 컬럼 구조로 변경 — 이러면 버튼 줄 폭이 구조적으로 항상 "카드 3개 폭"과 정확히
                # 일치함(3번째 카드 오른쪽 끝 = 버튼 4개 블록 오른쪽 끝).
                #
                # 🔧 [수정 2026-08-01, 3번째] 처음엔 CSS flex(justify-content:space-between)로 버튼
                # 행을 자동으로 칸 맨 아래까지 밀어보려 했으나(:has()로 컬럼 div를 조상 선택), 배포 후
                # 스크린샷 확인 결과 이 프로젝트의 Streamlit 버전에서는 안 먹혀서 버튼이 카드 바로
                # 아래에 거의 붙어버림(카드-위젯 높이 차이만큼 위젯 아래쪽에 여백만 남음). → 불확실한
                # CSS 트릭 대신, 카드와 버튼 사이에 고정 높이 여백(spacer)을 직접 넣는 훨씬 단순하고
                # 확실한 방법으로 교체. 여백 높이는 위젯 박스 실측 높이(헤더+8행+패딩 ≈ 200px대)에서
                # 카드 높이(110px)와 버튼 행 높이(~40px)를 뺀 값으로 대략 60px 근사(라이브 렌더링을
                # 볼 수 없는 세션이라 근사치 — 실제 화면 보고 필요하면 아래 spacer_px 값만 조정하면 됨).
                outer_rt_cols = st.columns([2.1, 0.9])

                with outer_rt_cols[0]:
                    hot_cols = st.columns(3)

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

                    # 🌟 [신규 2026-08-01] 국내/미국/일본/중국 "증시 시황" AI 요약 버튼 4개.
                    # 클릭하면 show_market_briefing_dialog 팝업이 뜨고, 그 안에서 지수 시세 기반 AI 요약을
                    # 보여줌(10분 캐시, Gemini 단일 모델 — 상세 설계는 함수 정의부 주석 참고).
                    # 버튼 색상은 사용자 요청대로 국가별로 다르게(빨/주/노/초), 기존 사이드바 버튼과 동일한
                    # CSS 클래스(btn-style-red/orange/yellow/green)를 그대로 재사용해 새 CSS 없이 통일감 유지.
                    # 🔧 [수정 2026-08-01, 2번째] 이 버튼 행을 카드와 같은 outer_rt_cols[0] 칸 안에 둬서
                    # 버튼 블록 폭이 항상 "카드 3개 폭"과 정확히 일치하게 함.
                    # 🔧 [수정 2026-08-01, 3번째] 고정 높이 spacer로 버튼 행을 아래로 밀어 오른쪽
                    # 위젯 박스 하단과 눈대중으로 맞춤 — 상세 배경은 위 "3번째" 주석 참고.
                    # 🔧 [수정 2026-08-01, 4번째] 60px로는 부족하다는 사용자 스크린샷 피드백 반영 —
                    # 30px 추가해서 90px로 조정.
                    # 🔧 [수정 2026-08-01, 5번째] 90px는 살짝 과했다는 피드백 — 5px 줄여서 85px로 조정.
                    spacer_px = 85
                    st.markdown(f'<div style="height:{spacer_px}px;"></div>', unsafe_allow_html=True)
                    market_btn_cols = st.columns(4)
                    market_btn_defs = [
                        ("국내", "btn-style-red", "btn_market_kr"),
                        ("미국", "btn-style-orange", "btn_market_us"),
                        ("일본", "btn-style-yellow", "btn_market_jp"),
                        ("중국", "btn-style-green", "btn_market_cn"),
                    ]
                    for m_col, (m_label, m_cls, m_key) in zip(market_btn_cols, market_btn_defs):
                        with m_col:
                            st.markdown(f'<div class="{m_cls}"></div>', unsafe_allow_html=True)
                            if st.button(f"{m_label} 증시 시황", key=m_key, use_container_width=True):
                                trigger_market = st.session_state.get('dialog_trigger_id', 0) + 1
                                st.session_state['dialog_trigger_id'] = trigger_market
                                st.session_state['show_market_briefing_dialog'] = {
                                    "market": m_label,
                                    "trigger_id": trigger_market
                                }
                                st.rerun()

                # 🇺🇸 [신규 2026-08-01] 오른쪽 칸(outer_rt_cols[1])에 미국 테마 등락률 위젯 배치.
                # us_theme_performance 테이블(FindingWhale.py가 매일 자동 수집, 국내 장 휴장일과 무관)에서
                # 최신 거래일 기준 테마 등락률을 뽑아서 컴팩트하게 보여줌.
                # 🔧 [수정 2026-07-31, 4번째] 사용자 피드백 반영: "상승 Top7/하락 Top7"으로 나누던 방식은
                # 값 크기 순위로 중간권(예: 15개 중 8위)에 있는 테마가 양쪽 다 못 들어가고 누락되는
                # 문제가 있었음(반도체 +0.90%가 화면에 안 보이는 사례로 발견). → 좌/우를 "순위"로만
                # 나눔: 전체 테마를 값 큰 순서(내림차순)로 세운 뒤 앞쪽 8개는 좌측, 나머지는 우측 —
                # 어떤 테마도 빠지지 않음. 색상은 좌/우 소속과 무관하게 각 항목의 실제 부호로 판단
                # (_us_row_html, 유지). 항목이 하나 더 늘어난 만큼 박스 높이도 아래로 살짝 키움.
                with outer_rt_cols[1]:
                    # 🔧 [수정 2026-08-01] 위젯 HTML 생성 로직을 render_us_theme_widget_html()로 공용화
                    # (아래 '테마킹' 화면에서도 동일 위젯을 재사용하기 위함). 동작은 이전과 동일함.
                    us_latest_date, us_left_items, us_right_items = get_us_theme_top_movers(left_count=8)
                    st.markdown(render_us_theme_widget_html(us_latest_date, us_left_items, us_right_items), unsafe_allow_html=True)

                # 트리거 체크는 함수 정의 위치(render_ai_summary_box/get_us_theme_top_movers보다 훨씬
                # 앞)가 아니라 반드시 여기(두 함수 정의 이후 지점)에 둬야 함 — 상세 이유는 함수
                # 정의부의 "🔧 [주의 2026-08-01]" 주석 참고.
                if 'show_market_briefing_dialog' in st.session_state:
                    data_m = st.session_state['show_market_briefing_dialog']
                    show_market_briefing_dialog(data_m['market'], data_m.get('trigger_id', 0))

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