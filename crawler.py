import streamlit as st
import streamlit.components.v1 as components
import re

# 테스트용 기사 리스트 (1개 또는 여러 개)
test_articles = [
    {
        "매체": "경향",
        "제목": "[단독] 검찰, ‘광화문 현판 한글화’ 반대 인사들 전격 조사 착수…문화계 반발 확산",
        "날짜": "2025-06-22 12:00:00",
        "링크": "https://news.example.com/article1",
        "본문": "검찰이 최근 문화재청의 광화문 현판 복원안에 반대했던 인사들을 상대로 수사에 착수한 것으로 확인됐다...",
        "하이라이트": "검찰이 <mark>광화문 현판</mark> 관련자들을 조사하기 시작했다..."
    }
]

# 디버깅용 반복 출력
for result in test_articles:
    full_title = f"△{result['매체']} / {result['제목']}"
    st.subheader("🧪 제목 디버깅 출력 비교")

    st.text("1. st.text()")
    st.text(full_title)

    st.text("2. st.write()")
    st.write(full_title)

    st.text("3. st.markdown()")
    st.markdown(f"**{full_title}**")

    st.text("4. st.markdown(HTML, unsafe_allow_html=True)")
    st.markdown(
        f"<p style='white-space: normal; word-break: break-word; font-weight: bold; color: red;'>{full_title}</p>",
        unsafe_allow_html=True
    )

    st.text("5. components.html()")
    components.html(f"""
        <div style="
            font-size: 16px;
            font-weight: bold;
            white-space: normal;
            word-break: break-word;
            overflow-wrap: break-word;
            color: green;
        ">
            {full_title}
        </div>
    """, height=80)

    st.text("6. st.text_area()")
    st.text_area("제목 (text_area)", value=full_title, height=60)

    st.caption(result["날짜"])
    st.markdown(f"🔗 [원문 보기]({result['링크']})")
    st.markdown(f"- {result['하이라이트']}", unsafe_allow_html=True)
