import streamlit as st
import requests
from bs4 import BeautifulSoup
from datetime import datetime, time
from zoneinfo import ZoneInfo
import time as t
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

# === 인증 정보 ===
client_id = "R7Q2OeVNhj8wZtNNFBwL"
client_secret = "49E810CBKY"

# ✅ CSS 삽입: 제목 잘림 문제 해결
st.markdown("""
    <style>
    .element-container:has(.stText),
    .element-container:has(.stMarkdown),
    .element-container:has(.stCaption) {
        overflow: visible !important;
        white-space: normal !important;
        text-overflow: initial !important;
        max-width: none !important;
        display: block !important;
    }

    .stMarkdown, .stText, .stCaption {
        white-space: normal !important;
        word-break: break-word !important;
        overflow-wrap: break-word !important;
        text-overflow: initial !important;
    }
    </style>
""", unsafe_allow_html=True)

# === 기본 UI ===
st.title("📰 단독기사 수집기_경찰팀")
st.markdown("✅ [단독] 기사를 수집하고 선택한 키워드가 본문에 포함된 기사만 필터링합니다.")

now = datetime.now(ZoneInfo("Asia/Seoul"))
today = now.date()

col1, col2 = st.columns(2)
with col1:
    start_date = st.date_input("시작 날짜", value=today)
    start_time = st.time_input("시작 시각", value=time(0, 0))
    start_dt = datetime.combine(start_date, start_time).replace(tzinfo=ZoneInfo("Asia/Seoul"))

with col2:
    end_date = st.date_input("종료 날짜", value=today, key="end_date")
    end_time = st.time_input("종료 시각", value=time(now.hour, now.minute))
    end_dt = datetime.combine(end_date, end_time).replace(tzinfo=ZoneInfo("Asia/Seoul"))

# === 키워드 그룹 ===
keyword_groups = {
    '시경': ['서울경찰청'],
    '본청': ['경찰청'],
    '종혜북': ['종로', '종암', '성북', '고려대', '참여연대', '혜화', '동대문', '중랑', '성균관대', '한국외대', '서울시립대', '경희대', '경실련', '서울대병원', '노원', '강북', '도봉', '북부지법', '북부지검', '상계백병원', '국가인권위원회'],
    '마포중부': ['마포', '서대문', '서부', '은평', '서부지검', '서부지법', '연세대', '신촌세브란스병원', '군인권센터', '중부', '남대문', '용산', '동국대', '숙명여대', '순천향대병원'],
    '영등포관악': ['영등포', '양천', '구로', '강서', '남부지검', '남부지법', '여의도성모병원', '고대구로병원', '관악', '금천', '동작', '방배', '서울대', '중앙대', '숭실대', '보라매병원'],
    '강남광진': ['강남', '서초', '수서', '송파', '강동', '삼성의료원', '현대아산병원', '강남세브란스병원', '광진', '성동', '동부지검', '동부지법', '한양대', '건국대', '세종대']
}
group_labels = list(keyword_groups.keys())
default_groups = ['시경', '종혜북']

selected_groups = st.multiselect("📚 지역 그룹 선택", group_labels, default=default_groups)
selected_keywords = []
for group in selected_groups:
    selected_keywords.extend(keyword_groups[group])

use_keyword_filter = st.checkbox("📎 키워드 포함 기사만 필터링", value=True)

# === 유틸 함수들 ===
def parse_pubdate(pubdate_str):
    try:
        return datetime.strptime(pubdate_str, "%a, %d %b %Y %H:%M:%S %z")
    except:
        return None

def extract_article_text(url):
    try:
        if "n.news.naver.com" not in url:
            return None
        html = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
        if html.status_code == 200:
            soup = BeautifulSoup(html.text, "html.parser")
            content_div = soup.find("div", id="newsct_article")
            return content_div.get_text(separator="\n", strip=True) if content_div else None
    except:
        pass
    return None

def extract_media_name(url):
    try:
        domain = url.split("//")[-1].split("/")[0]
        parts = domain.split(".")
        composite_key = f"{parts[-3]}.{parts[-2]}" if len(parts) >= 3 else parts[0]
        media_mapping = {
            "chosun": "조선", "joongang": "중앙", "donga": "동아", "hani": "한겨레",
            "khan": "경향", "segye": "세계", "yna": "연합", "newsis": "뉴시스"
        }
        return media_mapping.get(composite_key, composite_key.upper())
    except:
        return "[매체추출실패]"

def safe_api_request(url, headers, params, max_retries=3):
    for _ in range(max_retries):
        try:
            res = requests.get(url, headers=headers, params=params, timeout=5)
            if res.status_code == 200:
                return res
            t.sleep(0.5)
        except:
            t.sleep(0.5)
    return res

def fetch_and_filter(item, start_dt, end_dt, selected_keywords, use_keyword_filter):
    title = BeautifulSoup(item["title"], "html.parser").get_text()
    if "[단독]" not in title:
        return None
    pub_dt = parse_pubdate(item.get("pubDate"))
    if not pub_dt or not (start_dt <= pub_dt <= end_dt):
        return None
    link = item.get("link")
    if not link or "n.news.naver.com" not in link:
        return None
    body = extract_article_text(link)
    if not body:
        return None
    matched_keywords = []
    if use_keyword_filter and selected_keywords:
        matched_keywords = [kw for kw in selected_keywords if kw in body]
        if not matched_keywords:
            return None
    highlighted_body = body
    for kw in matched_keywords:
        highlighted_body = highlighted_body.replace(kw, f"<mark>{kw}</mark>")
    highlighted_body = highlighted_body.replace("\n", "<br><br>")
    media = extract_media_name(item.get("originallink", ""))
    return {
        "키워드": "[단독]",
        "매체": media,
        "제목": title,
        "날짜": pub_dt.strftime("%Y-%m-%d %H:%M:%S"),
        "본문": body,
        "필터일치": ", ".join(matched_keywords),
        "링크": link,
        "하이라이트": highlighted_body,
        "pub_dt": pub_dt
    }

# === 수집 실행 ===
if st.button("✅ [단독] 뉴스 수집 시작"):
    with st.spinner("뉴스 수집 중..."):
        status_text = st.empty()
        progress_bar = st.progress(0)
        headers = {
            "X-Naver-Client-Id": client_id,
            "X-Naver-Client-Secret": client_secret
        }
        seen_links = set()
        all_articles = []
        total = 0

        for start_index in range(1, 1001, 100):
            progress_bar.progress(min(start_index / 1000, 1.0))
            status_text.markdown(f"🟡 수집 중... **{total}건 수집됨**")
            params = {
                "query": "[단독]",
                "sort": "date",
                "display": 100,
                "start": start_index
            }
            res = safe_api_request("https://openapi.naver.com/v1/search/news.json", headers, params)
            if res.status_code != 200:
                st.warning(f"API 호출 실패: {res.status_code}")
                break
            items = res.json().get("items", [])
            if not items:
                break

            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = [
                    executor.submit(fetch_and_filter, item, start_dt, end_dt, selected_keywords, use_keyword_filter)
                    for item in items
                ]
                for future in as_completed(futures):
                    result = future.result()
                    if result and result["링크"] not in seen_links:
                        seen_links.add(result["링크"])
                        all_articles.append(result)

                        # ✅ 제목도 본문처럼 출력 (CSS 덕분에 잘림 없음)
                        st.write(f"△{result['매체']} / {result['제목']}")
                        st.caption(result["날짜"])
                        st.markdown(f"🔗 [원문 보기]({result['링크']})")
                        if result["필터일치"]:
                            st.write(f"**일치 키워드:** {result['필터일치']}")
                        st.markdown(f"- {result['하이라이트']}", unsafe_allow_html=True)
                        total += 1
                        status_text.markdown(f"🟡 수집 중... **{total}건 수집됨**")

        progress_bar.empty()
        status_text.markdown(f"✅ 수집 완료: 총 **{total}건**")
        st.success(f"✅ 수집 완료: 총 {total}건")

        if all_articles:
            text_block = ""
            for row in all_articles:
                clean_title = re.sub(r"\[단독\]|\(단독\)|【단독】|ⓧ단독|^단독\s*[:-]?", "", row['제목']).strip()
                wrapped_title = f"△{row['매체']} / {clean_title}"
                wrapped_title = re.sub(r"(.{60,80})\s", r"\1\n", wrapped_title)
                text_block += f"{wrapped_title}\n- {row['본문']}\n\n"

            # ✅ 복사용 텍스트도 줄바꿈 포함
            st.text_area("복사할 기사 모음", value=text_block.strip(), height=600)
            st.caption("위 내용을 복사해서 사용하세요.")
