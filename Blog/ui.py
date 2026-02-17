from __future__ import annotations

# Streamlit UI 구성 및 사용자 상호작용을 담당합니다.
import time
import streamlit as st

from prompt import BlogInput


def apply_custom_style() -> None:
    """화려하고 현대적인 느낌을 위한 CSS를 적용합니다."""
    st.markdown(
        """
        <style>
        .stApp {
            background:
              radial-gradient(circle at 20% 10%, #ffe8d6 0%, transparent 30%),
              radial-gradient(circle at 80% 20%, #caf0f8 0%, transparent 35%),
              linear-gradient(120deg, #fff9f2 0%, #f7fbff 100%);
        }
        .glass-card {
            padding: 1rem 1.2rem;
            border-radius: 16px;
            background: rgba(255, 255, 255, 0.75);
            border: 1px solid rgba(255, 255, 255, 0.6);
            box-shadow: 0 10px 25px rgba(0,0,0,0.08);
            margin-bottom: 1rem;
        }
        .title {
            font-size: 2rem;
            font-weight: 800;
            color: #1d3557;
            margin-bottom: 0.2rem;
        }
        .subtitle {
            color: #457b9d;
            font-weight: 500;
            margin-bottom: 1rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def init_session_state() -> None:
    if "user_prompt" not in st.session_state:
        st.session_state.user_prompt = ""
    if "blog_markdown" not in st.session_state:
        st.session_state.blog_markdown = ""
    if "comments" not in st.session_state:
        st.session_state.comments = ""


def render_sidebar(total_chars: int = 0, non_space_chars: int = 0) -> tuple[float, str]:
    st.sidebar.header("설정")
    temperature = st.sidebar.slider("창의성(temperature)", 0.0, 1.0, 0.5, 0.1)
    model = st.sidebar.text_input("Google 모델명", value="gemini-2.0-flash-lite")
    st.sidebar.info("API 키는 .env 파일의 GOOGLE_API_KEY를 사용합니다.")

    st.sidebar.divider()
    st.sidebar.subheader("2단계 결과 통계")
    col1, col2 = st.sidebar.columns(2)
    col1.metric("전체 글자수", f"{total_chars:,}")
    col2.metric("공백 제외", f"{non_space_chars:,}")

    return temperature, model


def render_form() -> BlogInput:
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.subheader("1) 사용자 질문 입력")

    col1, col2 = st.columns(2)
    with col1:
        place_name = st.text_input("다녀온 곳은 어디인가요?")
        business_hours = st.text_area("영업시간은 어떤가요?", height=90)
        location_info = st.text_area("위치/근처 랜드마크 정보를 적어주세요.", height=90)
        target_keyword = st.text_input("핵심 SEO 키워드")
    with col2:
        parking_or_tips = st.text_area("주차/알아두면 좋은 정보", height=90)
        interior_and_menu = st.text_area("매장 내부/먹은 메뉴", height=90)
        signature_taste = st.text_area("특별히 맛있었던 포인트", height=90)
        tone = st.selectbox("글의 톤", ["정보형", "경험담", "스토리텔링", "마케팅"])

    st.markdown("</div>", unsafe_allow_html=True)

    return BlogInput(
        place_name=place_name,
        business_hours=business_hours,
        location_info=location_info,
        parking_or_tips=parking_or_tips,
        interior_and_menu=interior_and_menu,
        signature_taste=signature_taste,
        tone=tone,
        target_keyword=target_keyword,
    )


def render_result_tabs() -> tuple:
    return st.tabs(["프롬프트 미리보기", "최종 블로그", "댓글"])


def run_with_progress(pipeline, payload: BlogInput):
    """1~2단계(프롬프트/블로그) 실행용 진행 UI"""
    progress = st.progress(0)

    with st.spinner("1단계 Prompt Builder Agent 실행 중..."):
        time.sleep(0.4)
        progress.progress(40)

    with st.spinner("2단계 Blog Writer Agent 실행 중..."):
        result = pipeline.run(payload)
        progress.progress(100)

    return result


def run_comments_with_progress(pipeline, blog_markdown: str) -> str:
    """3단계(댓글) 별도 실행용 진행 UI"""
    progress = st.progress(0)
    with st.spinner("3단계 Comment Agent 실행 중..."):
        time.sleep(0.3)
        progress.progress(35)
        comments = pipeline.write_comments(blog_markdown)
        progress.progress(100)
    return comments
