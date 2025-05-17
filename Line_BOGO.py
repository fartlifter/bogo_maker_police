import streamlit as st
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pytz
import time

# === API 인증 정보 ===
client_id = "R7Q2OeVNhj8wZtNNFBwL"
client_secret = "49E810CBKY"

# === 날짜 파싱 함수 ===
def parse_pubdate(pubdate_str):
    try:
        return datetime.strptime(pubdate_str, "%a, %d %b %Y %H:%M:%S %z")
    except:
        return None

# === 본문 추출 ===
def extract_article_text(url):
    try:
        html = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        if html.status_code == 200:
            soup = BeautifulSoup(html.text, "html.parser")
            content_div = soup.find("div", id="newsct_article")
            return content_div.get_text(separator="\n", strip=True) if content_div else "[본문 없음]"
        return f"[요청 실패: {html.status_code}]"
    except Exception as e:
        return f"[예외 발생: {e}]"

# === 매체명 추출 ===
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

# === Streamlit 앱 ===
st.title("📰 [단독] 네이버 뉴스 수집기")
st.markdown("시간 범위를 지정해 `[단독]` 기사를 수집하고 본문을 확인합니다.")

# 시간 입력
col1, col2 = st.columns(2)
with col1:
    start_time = st.datetime_input("시작 시각", value=datetime(2025, 5, 17, 18, 0, tzinfo=pytz.timezone("Asia/Seoul")))
with col2:
    end_time = st.datetime_input("종료 시각", value=datetime(2025, 5, 17, 19, 0, tzinfo=pytz.timezone("Asia/Seoul")))

if st.button("✅ 기사 수집 시작"):
    start_index = 1
    keep_collecting = True
    result_count = 0

    with st.spinner("뉴스 수집 중..."):
        while keep_collecting:
            url = "https://openapi.naver.com/v1/search/news.json"
            headers = {
                "X-Naver-Client-Id": client_id,
                "X-Naver-Client-Secret": client_secret
            }
            params = {
                "query": "[단독]",
                "sort": "date",
                "display": 100,
                "start": start_index
            }

            res = requests.get(url, headers=headers, params=params)
            if res.status_code != 200:
                st.error(f"API 호출 실패: {res.status_code}")
                break

            items = res.json().get("items", [])
            if not items:
                break

            for item in items:
                title = BeautifulSoup(item["title"], "html.parser").get_text()
                if "[단독]" not in title:
                    continue

                pub_date_str = item["pubDate"]
                pub_date_dt = parse_pubdate(pub_date_str)
                if not pub_date_dt:
                    continue

                if pub_date_dt < start_time:
                    keep_collecting = False
                    break

                if pub_date_dt >= end_time:
                    continue

                media = extract_media_name(item.get("originallink", ""))
                link = item["link"]
                body = extract_article_text(link)
                result_count += 1

                st.markdown(f"### △{media}/{title}")
                st.caption(pub_date_str)
                st.write(f"- {body}")

                time.sleep(0.5)

            start_index += 100

    if result_count == 0:
        st.info("지정한 시간 범위에서 [단독] 기사를 찾을 수 없습니다.")
    else:
        st.success(f"✅ 수집 완료: 총 {result_count}건 기사 출력됨.")
