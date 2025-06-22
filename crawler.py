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

                        # ✅ 제목: HTML block으로 출력해 줄바꿈되도록 처리
                        st.markdown(
                            f"<p style='white-space: normal; word-break: break-word; font-weight: bold;'>"
                            f"△{result['매체']} / {result['제목']}</p>",
                            unsafe_allow_html=True
                        )

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

            # ✅ 복사용 텍스트: 줄바꿈 포함하여 표시
            st.text_area("복사할 기사 모음", value=text_block.strip(), height=600)
            st.caption("위 내용을 복사해서 사용하세요.")
