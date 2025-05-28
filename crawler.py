import streamlit as st
import requests
from bs4 import BeautifulSoup
from datetime import datetime, time
from zoneinfo import ZoneInfo
import time as t
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

# ==================== API 인증 정보 ====================
client_id = "R7Q2OeVNhj8wZtNNFBwL"
client_secret = "49E810CBKY"
headers = {"User-Agent": "Mozilla/5.0"}

# ==================== 키워드 그룹 ====================
keyword_groups = {
    '시경': ['서울경찰청'],
    '본청': ['경찰청'],
    '종혜북': ['종로', '종암', '성북', '고려대', '참여연대', '혜화', '동대문', '중랑',
               '성균관대', '한국외대', '서울시립대', '경희대', '경실련', '서울대병원',
               '노원', '강북', '도봉', '북부지법', '북부지검', '상계백병원', '국가인권위원회'],
    '마포중부': ['마포', '서대문', '서부', '은평', '서부지검', '서부지법', '연세대',
                 '신촌세브란스병원', '군인권센터', '중부', '남대문', '용산', '동국대',
                 '숙명여대', '순천향대병원'],
    '영등포관악': ['영등포', '양천', '구로', '강서', '남부지검', '남부지법', '여의도성모병원',
                   '고대구로병원', '관악', '금천', '동작', '방배', '서울대', '중앙대', '숭실대', '보라매병원'],
    '강남광진': ['강남', '서초', '수서', '송파', '강동', '삼성의료원', '현대아산병원',
                 '강남세브란스병원', '광진', '성동', '동부지검', '동부지법', '한양대',
                 '건국대', '세종대']
}

# ==================== 하이라이팅 함수 ====================
def highlight_keywords(text, keywords):
    if not keywords:
        return text
    for kw in keywords:
        text = text.replace(kw, f"<mark>{kw}</mark>")
    return text

# ==================== 기사 본문 병렬 크롤링 ====================
def fetch_contents(articles, content_func):
    results = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_article = {executor.submit(content_func, art['url']): art for art in articles}
        for future in as_completed(future_to_article):
            art = future_to_article[future]
            try:
                content = future.result()
                art['content'] = content
                results.append(art)
            except:
                continue
    return results

# ==================== 기사 본문 추출 함수 ====================
def get_newsis_content(url):
    res = requests.get(url, headers=headers)
    soup = BeautifulSoup(res.text, "html.parser")
    content = soup.find("div", class_="viewer")
    return content.get_text(separator="\n", strip=True) if content else None

def get_yonhap_content(url):
    res = requests.get(url, headers=headers)
    soup = BeautifulSoup(res.text, "html.parser")
    content = soup.find("div", class_="story-news article")
    return content.get_text(separator="\n", strip=True) if content else None

def get_naver_content(url):
    if "n.news.naver.com" not in url:
        return None
    html = requests.get(url, headers=headers)
    if html.status_code == 200:
        soup = BeautifulSoup(html.text, "html.parser")
        content_div = soup.find("div", id="newsct_article")
        return content_div.get_text(separator="\n", strip=True) if content_div else None
    return None

# ==================== 기사 수집 함수 ====================
def collect_newsis_articles(start_dt, end_dt, status):
    articles, page = [], 1
    while True:
        status.markdown(f"🔄 뉴시스 페이지 {page} 수집 중...")
        url = f"https://www.newsis.com/realnews/?cid=realnews&day=today&page={page}"
        res = requests.get(url, headers=headers)
        soup = BeautifulSoup(res.text, "html.parser")
        items = soup.select("ul.articleList2 > li")
        if not items:
            break
        for item in items:
            title_tag = item.select_one("p.tit > a")
            time_tag = item.select_one("p.time")
            if not (title_tag and time_tag):
                continue
            match = re.search(r"\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}:\d{2}", time_tag.text)
            if not match:
                continue
            dt = datetime.strptime(match.group(), "%Y.%m.%d %H:%M:%S").replace(tzinfo=ZoneInfo("Asia/Seoul"))
            if dt < start_dt:
                return fetch_contents(articles, get_newsis_content)
            if dt > end_dt:
                continue
            articles.append({"source": "뉴시스", "title": title_tag.text.strip(), "datetime": dt, "url": "https://www.newsis.com" + title_tag['href']})
        page += 1
        t.sleep(0.2)
    return fetch_contents(articles, get_newsis_content)

def collect_yonhap_articles(start_dt, end_dt, status):
    articles, page = [], 1
    while True:
        status.markdown(f"🔄 연합뉴스 페이지 {page} 수집 중...")
        url = f"https://www.yna.co.kr/news/{page}?site=navi_latest_depth01"
        res = requests.get(url, headers=headers)
        soup = BeautifulSoup(res.text, "html.parser")
        items = soup.select("ul.list01 > li[data-cid]")
        if not items:
            break
        for item in items:
            title_tag = item.select_one(".tit-wrap .tit-news .title01")
            time_tag = item.select_one(".txt-time")
            if not (title_tag and time_tag):
                continue
            dt = datetime.strptime(f"2025-{time_tag.text.strip()}", "%Y-%m-%d %H:%M").replace(tzinfo=ZoneInfo("Asia/Seoul"))
            if dt < start_dt:
                return fetch_contents(articles, get_yonhap_content)
            if dt > end_dt:
                continue
            articles.append({"source": "연합뉴스", "title": title_tag.text.strip(), "datetime": dt, "url": f"https://www.yna.co.kr/view/{item['data-cid']}"})
        page += 1
        t.sleep(0.2)
    return fetch_contents(articles, get_yonhap_content)

def collect_naver_articles(start_dt, end_dt, selected_keywords, use_filter, status):
    results, seen = [], set()
    headers_naver = {"X-Naver-Client-Id": client_id, "X-Naver-Client-Secret": client_secret}
    for start in range(1, 301, 100):
        status.markdown(f"🔄 [단독] 기사 {start}번째부터 수집 중...")
        params = {"query": "[단독]", "sort": "date", "display": 100, "start": start}
        res = requests.get("https://openapi.naver.com/v1/search/news.json", headers=headers_naver, params=params)
        for item in res.json().get("items", []):
            title = BeautifulSoup(item["title"], "html.parser").get_text()
            link = item["link"]
            pub_date = datetime.strptime(item["pubDate"], "%a, %d %b %Y %H:%M:%S %z").astimezone(ZoneInfo("Asia/Seoul"))
            if not (start_dt <= pub_date <= end_dt) or link in seen:
                continue
            body = get_naver_content(link)
            if not body:
                continue
            seen.add(link)
            matched = [kw for kw in selected_keywords if kw in body] if use_filter else selected_keywords
            if use_filter and not matched:
                continue
            results.append({"source": "단독", "title": title, "datetime": pub_date, "content": body, "matched": matched})
    return results

# ==================== UI 실행 ====================
st.title("📰 뉴스 통합 수집기 (연합뉴스 · 뉴시스 · [단독])")
now = datetime.now(ZoneInfo("Asia/Seoul"))
today = now.date()
col1, col2 = st.columns(2)
with col1:
    start_date = st.date_input("시작 날짜", value=today)
    start_time = st.time_input("시작 시각", value=time(0, 0))
    start_dt = datetime.combine(start_date, start_time).replace(tzinfo=ZoneInfo("Asia/Seoul"))
with col2:
    end_date = st.date_input("종료 날짜", value=today)
    end_time = st.time_input("종료 시각", value=time(now.hour, now.minute))
    end_dt = datetime.combine(end_date, end_time).replace(tzinfo=ZoneInfo("Asia/Seoul"))

selected_groups = st.multiselect("📚 키워드 그룹 선택", list(keyword_groups), default=['시경', '종혜북'])
selected_keywords = [kw for group in selected_groups for kw in keyword_groups[group]]
use_filter = st.checkbox("🔍 키워드 포함 기사만 보기", value=True)
collect_general = st.checkbox("📰 연합뉴스·뉴시스 기사 수집", value=True)
collect_danok = st.checkbox("📌 [단독] 기사 수집", value=True)

if st.button("✅ 뉴스 수집 시작"):
    status = st.empty()
    general_articles = danok_articles = []
    if collect_general:
        with st.spinner("연합뉴스/뉴시스 수집 중..."):
            newsis = collect_newsis_articles(start_dt, end_dt, status)
            yonhap = collect_yonhap_articles(start_dt, end_dt, status)
            general_articles = newsis + yonhap
    if collect_danok:
        with st.spinner("[단독] 기사 수집 중..."):
            danok_articles = collect_naver_articles(start_dt, end_dt, selected_keywords, use_filter, status)

    if general_articles:
        st.markdown("## ◆ 연합뉴스·뉴시스")
        for a in general_articles:
            st.markdown(f"△{a['source']}/{a['title']}")
            st.caption(a['datetime'].strftime('%Y-%m-%d %H:%M'))
            highlighted = highlight_keywords(a['content'], selected_keywords)
            st.markdown(f"- {highlighted}", unsafe_allow_html=True)

    if danok_articles:
        st.markdown("## ◆ 단독")
        for a in danok_articles:
            st.markdown(f"△단독/{a['title']}")
            st.caption(a['datetime'].strftime('%Y-%m-%d %H:%M'))
            highlighted = highlight_keywords(a['content'], selected_keywords)
            st.markdown(f"- {highlighted}", unsafe_allow_html=True)

    text_block = "<보고>\n"
    if general_articles:
        text_block += "【사회면】\n"
        for a in general_articles:
            text_block += f"△{a['title']}\n-{a['content']}\n\n"
    if danok_articles:
        text_block += "【타지】\n"
        for a in danok_articles:
            text_block += f"△{a['title']}\n-{a['content']}\n\n"
    st.code(text_block.strip(), language="markdown")
    st.caption("복사해서 보고서 등에 활용하세요.")
