if st.button("✅ 뉴스 수집 시작"):
    with st.spinner("뉴스 수집 중..."):
        progress_bar = st.progress(0)
        headers = {
            "X-Naver-Client-Id": client_id,
            "X-Naver-Client-Secret": client_secret
        }
        seen_links = set()
        grouped = defaultdict(list)
        total = 0

        # 예상 반복 횟수 계산 (단독 10회 + 키워드당 10회)
        keyword_loop_count = len(selected_keywords) * 10 if collect_keywords else 0
        dandok_loop_count = 10 if collect_dandok else 0
        estimated_loops = keyword_loop_count + dandok_loop_count
        loop_counter = 0

        if collect_dandok:
            st.subheader("🟡 [단독] 기사")
            for start_index in range(1, 1001, 100):
                loop_counter += 1
                progress_bar.progress(min(loop_counter / estimated_loops, 1.0))

                params = {
                    "query": "[단독]",
                    "sort": "date",
                    "display": 100,
                    "start": start_index
                }
                res = safe_api_request("https://openapi.naver.com/v1/search/news.json", headers, params)
                if res.status_code != 200:
                    st.warning(f"[단독] API 호출 실패: {res.status_code}")
                    break
                items = res.json().get("items", [])
                if not items:
                    break
                for item in items:
                    title = BeautifulSoup(item["title"], "html.parser").get_text()
                    if "[단독]" not in title:
                        continue
                    pub_dt = parse_pubdate(item.get("pubDate"))
                    if not pub_dt or not (start_dt <= pub_dt <= end_dt):
                        continue
                    link = item.get("link")
                    if not link or link in seen_links:
                        continue
                    seen_links.add(link)
                    body = extract_article_text(link)
                    if not body:
                        continue
                    media = extract_media_name(item.get("originallink", ""))
                    st.markdown(f"**△{media}/{title}**")
                    st.caption(pub_dt.strftime("%Y-%m-%d %H:%M:%S"))
                    st.write(f"- {body}")
                    total += 1
                    t.sleep(0.5)

        if collect_keywords:
            st.subheader("🔵 키워드 기사 (연합/뉴시스)")
            for keyword in selected_keywords:
                for start_index in range(1, 1001, 100):
                    loop_counter += 1
                    progress_bar.progress(min(loop_counter / estimated_loops, 1.0))

                    params = {
                        "query": f'"{keyword}"',
                        "sort": "date",
                        "display": 100,
                        "start": start_index
                    }
                    res = safe_api_request("https://openapi.naver.com/v1/search/news.json", headers, params)
                    if res.status_code != 200:
                        st.warning(f"[{keyword}] API 호출 실패: {res.status_code}")
                        break
                    items = res.json().get("items", [])
                    if not items:
                        break
                    for item in items:
                        pub_dt = parse_pubdate(item.get("pubDate"))
                        if not pub_dt or not (start_dt <= pub_dt <= end_dt):
                            continue
                        media = extract_media_name(item.get("originallink", ""))
                        if media not in ["연합", "뉴시스"]:
                            continue
                        link = item.get("link")
                        if not link or link in seen_links:
                            continue
                        seen_links.add(link)
                        body = extract_article_text(link)
                        if not body or keyword not in body:
                            continue
                        title = BeautifulSoup(item["title"], "html.parser").get_text()
                        grouped[keyword].append({
                            "title": title,
                            "media": media,
                            "pubdate": pub_dt,
                            "body": body
                        })
                        total += 1
                        t.sleep(0.5)

        progress_bar.empty()  # ✅ 수집 끝나면 진행 표시 제거
        st.success(f"✅ 수집 완료: 총 {total}건")
