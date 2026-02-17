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
    if "editable_user_prompt" not in st.session_state:
        st.session_state.editable_user_prompt = ""
    if "blog_markdown" not in st.session_state:
        st.session_state.blog_markdown = ""
    if "comments" not in st.session_state:
        st.session_state.comments = ""
    if "map_url" not in st.session_state:
        st.session_state.map_url = ""
    if "place_name" not in st.session_state:
        st.session_state.place_name = ""
    if "business_hours" not in st.session_state:
        st.session_state.business_hours = ""
    if "location_info" not in st.session_state:
        st.session_state.location_info = ""
    if "home_tab_info" not in st.session_state:
        st.session_state.home_tab_info = ""
    if "menu_tab_info" not in st.session_state:
        st.session_state.menu_tab_info = ""
    if "info_tab_info" not in st.session_state:
        st.session_state.info_tab_info = ""
    if "news_tab_info" not in st.session_state:
        st.session_state.news_tab_info = ""
    if "parking_or_tips" not in st.session_state:
        st.session_state.parking_or_tips = ""
    if "interior_and_menu" not in st.session_state:
        st.session_state.interior_and_menu = ""
    if "signature_taste" not in st.session_state:
        st.session_state.signature_taste = ""
    if "tone" not in st.session_state:
        st.session_state.tone = "정보형"
    if "target_keyword" not in st.session_state:
        st.session_state.target_keyword = ""
    if "crawled_place_id" not in st.session_state:
        st.session_state.crawled_place_id = ""
    if "crawled_home_text" not in st.session_state:
        st.session_state.crawled_home_text = ""
    if "crawled_menu_text" not in st.session_state:
        st.session_state.crawled_menu_text = ""
    if "crawled_info_text" not in st.session_state:
        st.session_state.crawled_info_text = ""
    if "crawled_news_text" not in st.session_state:
        st.session_state.crawled_news_text = ""
    if "example_place_name" not in st.session_state:
        st.session_state.example_place_name = ""
    if "example_business_hours" not in st.session_state:
        st.session_state.example_business_hours = ""
    if "example_location_info" not in st.session_state:
        st.session_state.example_location_info = ""
    if "example_parking_or_tips" not in st.session_state:
        st.session_state.example_parking_or_tips = ""
    if "example_target_keyword" not in st.session_state:
        st.session_state.example_target_keyword = ""


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


def render_form() -> tuple[BlogInput, bool]:
    left_col, right_col = st.columns(2)

    with left_col:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.subheader("1) 네이버 지도 탭 수집")
        map_url = st.text_input(
            "네이버 지도 URL",
            placeholder="https://naver.me/...",
            key="map_url",
        )
        run_crawl = st.button("지도 탭 수집 실행", use_container_width=True)
        if st.session_state.crawled_place_id:
            st.caption(f"최근 수집 placeId: {st.session_state.crawled_place_id}")

        st.text_area(
            "홈 탭 수집 결과(읽기 전용)",
            value=st.session_state.crawled_home_text,
            height=140,
            disabled=True,
        )
        st.text_area(
            "메뉴 탭 수집 결과(읽기 전용)",
            value=st.session_state.crawled_menu_text,
            height=140,
            disabled=True,
        )
        st.text_area(
            "정보 탭 수집 결과(읽기 전용)",
            value=st.session_state.crawled_info_text,
            height=140,
            disabled=True,
        )
        st.text_area(
            "소식 탭 수집 결과(읽기 전용)",
            value=st.session_state.crawled_news_text,
            height=120,
            disabled=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

    with right_col:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.subheader("2) 사용자 질문 입력")
        st.caption("지도 수집 결과는 자동 입력되지 않습니다. 아래 입력란에 직접 작성하세요.")

        col1, col2 = st.columns(2)
        with col1:
            place_name = st.text_input(
                "다녀온 곳은 어디인가요?",
                key="place_name",
                placeholder=st.session_state.example_place_name or "예: 코미호미",
            )
            business_hours = st.text_area(
                "영업시간은 어떤가요?",
                height=150,
                key="business_hours",
                placeholder=st.session_state.example_business_hours or "예: 매일 09:00-20:00",
            )
            location_info = st.text_area(
                "위치/근처 랜드마크 정보를 적어주세요.",
                height=170,
                key="location_info",
                placeholder=st.session_state.example_location_info or "예: 설악 IC에서 가평역 방향",
            )
            target_keyword = st.text_input(
                "핵심 SEO 키워드",
                key="target_keyword",
                placeholder=st.session_state.example_target_keyword or "예: 가평 카페 추천",
            )
        with col2:
            parking_or_tips = st.text_area(
                "주차/알아두면 좋은 정보",
                height=150,
                key="parking_or_tips",
                placeholder=st.session_state.example_parking_or_tips or "예: 주차 가능, 무선 인터넷",
            )
            interior_and_menu = st.text_area("매장 내부/먹은 메뉴", height=170, key="interior_and_menu")
            signature_taste = st.text_area("특별히 맛있었던 포인트", height=170, key="signature_taste")
            tone = st.selectbox("글의 톤", ["정보형", "경험담", "스토리텔링", "마케팅"], key="tone")
        st.markdown("</div>", unsafe_allow_html=True)

    return BlogInput(
        map_url=st.session_state.map_url,
        place_name=place_name,
        business_hours=business_hours,
        location_info=location_info,
        home_tab_info=st.session_state.crawled_home_text,
        menu_tab_info=st.session_state.crawled_menu_text,
        info_tab_info=st.session_state.crawled_info_text,
        news_tab_info=st.session_state.crawled_news_text,
        parking_or_tips=parking_or_tips,
        interior_and_menu=interior_and_menu,
        signature_taste=signature_taste,
        tone=tone,
        target_keyword=target_keyword,
    ), run_crawl


def run_prompt_with_progress(pipeline, payload: BlogInput) -> str:
    """1단계(프롬프트) 실행용 진행 UI"""
    progress = st.progress(0)
    with st.spinner("1단계 Prompt Builder Agent 실행 중..."):
        result = pipeline.build_user_prompt(payload)
        progress.progress(100)
    return result


def run_blog_with_progress(pipeline, user_prompt: str) -> str:
    """2단계(블로그) 실행용 진행 UI"""
    progress = st.progress(0)
    with st.spinner("2단계 Blog Writer Agent 실행 중..."):
        result = pipeline.write_blog(user_prompt)
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
