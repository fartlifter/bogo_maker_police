import streamlit as st
import requests
from bs4 import BeautifulSoup
from datetime import datetime, time
import time as t
from collections import defaultdict

# 인증 정보
client_id = "R7Q2OeVNhj8wZtNNFBwL"
client_secret = "49E810CBKY"

def parse_pubdate(pubdate_str):
    try:
        return datetime.strptime(pubdate_str, "%a, %d %b %Y %H:%M:%S %z")
    except:
        return None

def extract_article_text(url):
    if not url:
        return None
    try:
        html = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        if html.status_code == 200:
            soup = BeautifulSoup(html.text, "html.parser")
            content_div = soup.find("div", id="newsct_article")
            return content_div.get_text(separator="\n", strip=True) if content_div else None
        return None
    except:
        return None

def extract_media_name(url):
    try:
        domain = url.split("//")[-1].split("/")[0]
        parts = domain.split(".")
        if parts[0] == "www" and parts[1] == "news":
            media_key = parts[2]
        elif parts[0] == "www":
            media_key = parts[1]
        elif parts[0] == "news":
            media_key = parts[1]
        else:
            media_key = parts[0]

        media_mapping = {
            "chosun": "조선", "joongang": "중앙", "donga": "동아", "hani": "한겨레",
            "khan": "경향", "hankookilbo": "한국", "segye": "세계", "seoul": "서울",
            "kmib": "국민", "munhwa": "문화", "kbs": "KBS", "sbs": "SBS",
            "imnews": "MBC", "jtbc": "JTBC", "ichannela": "채널A", "tvchosun": "TV조선",
            "mk": "매경", "sedaily": "서경", "hankyung": "한경", "news1": "뉴스1",
            "newsis": "뉴시스", "yna": "연합"
        }
        return media_mapping.get(media_key.lower(), media_key.upper())
    except:
        return "[매체추출실패]"

def safe_api_request(url, headers, params, max_retries=3):
    for attempt in range(max_retries):
        res = requests.get(url, headers=headers, params=params)
        if res.status_code == 200:
            return res
        t.sleep(0.5)
    return res

# === Streamlit UI ===
st.title("📰 뉴스 수집기 (최적화 모드)")
st.markdown("선택한 시간 범위의 모든 기사 중 연합/뉴시스 기사 본문에서 키워드를 포함한 기사만 추출하여 분류합니다.")

# 날짜 선택
selected_date = st.date_input("날짜", value=datetime.today())
col1, col2 = st.columns(2)
with col1:
    start_time = st.time_input("시작 시각", value=time(0, 0))
with col2:
    end_time = st.time_input("종료 시각", value=time(23, 59))

start_datetime = datetime.combine(selected_date, start_time)
end_datetime = datetime.combine(selected_date, end_time)

# 키워드 선택
all_keywords = [
    '종로', '종암', '성북', '혜화', '동대문', '중랑', '노원', '강북', '도봉',
    '고려대', '참여연대', '경실련', '성균관대', '한국외대', '서울시립대', '경희대',
    '서울대병원', '북부지법', '북부지검', '상계백병원', '서울경찰청', '국가인권위원회',
    '경찰청', '중부', '남대문', '용산', '동국대', '숙명여대', '순천향대병원',
    '강남', '서초', '수서', '송파', '강동', '삼성의료원', '현대아산병원',
    '강남세브란스병원', '광진', '성동', '동부지검', '동부지법', '한양대', '건국대',
    '세종대', '마포', '서대문', '서부', '은평', '서부지검', '서부지법', '연세대',
    '신촌세브란스병원', '영등포', '양천', '구로', '강서', '남부지검', '남부지법',
    '군인권센터', '여의도성모병원', '고대구로병원', '관악', '금천', '동작', '방배',
    '서울대', '중앙대', '숭실대', '보라매병원'
]
default_selection = all_keywords[:22]
selected_keywords = st.multiselect("🗂️ 키워드 선택", all_keywords, default=default_selection)

# === 실행 ===
if st.button("✅ 뉴스 수집 시작"):
    with st.spinner("뉴스 수집 중..."):
        url = "https://openapi.naver.com/v1/search/news.json"
        headers = {
            "X-Naver-Client-Id": client_id,
            "X-Naver-Client-Secret": client_secret
        }
        seen_links = set()
        grouped = defaultdict(list)
        total = 0

        # 전체 기사 순회 (1000개까지)
        for start_index in range(1, 1001, 100):
            params = {
                "query": "",  # 전체 뉴스
                "sort": "date",
                "display": 100,
                "start": start_index
            }
            res = safe_api_request(url, headers, params)
            if res.status_code != 200:
                st.warning(f"API 호출 실패: {res.status_code}")
                break

            items = res.json().get("items", [])
            if not items:
                break

            for item in items:
                pub_date_dt = parse_pubdate(item["pubDate"])
                if not pub_date_dt:
                    continue
                pub_date_dt = pub_date_dt.replace(tzinfo=None)
                if pub_date_dt < start_datetime or pub_date_dt >= end_datetime:
                    continue

                media = extract_media_name(item.get("originallink", ""))
                if media not in ["연합", "뉴시스"]:
                    continue

                link = item.get("link")
                if not link or link in seen_links:
                    continue
                seen_links.add(link)

                body = extract_article_text(link)
                if not body:
                    continue

                matched_keywords = [kw for kw in selected_keywords if kw in body]
                if not matched_keywords:
                    continue

                title = BeautifulSoup(item["title"], "html.parser").get_text()

                for kw in matched_keywords:
                    grouped[kw].append({
                        "title": title,
                        "media": media,
                        "pubdate": pub_date_dt,
                        "body": body
                    })

                total += 1
                t.sleep(0.5)

    st.success(f"✅ 수집 완료: 총 {total}건의 기사 중 키워드 매칭됨")

    # 키워드별 출력
    for kw in selected_keywords:
        articles = grouped.get(kw, [])
        if articles:
            st.markdown(f"### 🔹 {kw} ({len(articles)}건)")
            for a in articles:
                st.markdown(f"**△{a['media']}/{a['title']}**")
                st.caption(a['pubdate'].strftime("%Y-%m-%d %H:%M:%S"))
                st.write(f"- {a['body']}")
