from __future__ import annotations
import os
import re
import streamlit as st

from agent import BlogAgentPipeline
from config import load_config
from naver_map import crawl_place_tabs, merge_blog_input_with_crawl
from prompt import BlogInput
from ui import (
    apply_custom_style,
    init_session_state,
    render_form,
    run_blog_with_progress,
    run_comments_with_progress,
    run_prompt_with_progress,
    render_sidebar,
)


def _count_chars(text: str) -> tuple[int, int]:
    """전체 글자수와 공백 제외 글자수를 반환합니다."""
    total = len(text)
    non_space = len(re.sub(r"\s+", "", text))
    return total, non_space


def main() -> None:
    st.set_page_config(page_title="블로그 자동생성 AI Agent", page_icon="📝", layout="wide")
    apply_custom_style()
    init_session_state()

    total_chars, non_space_chars = _count_chars(st.session_state.blog_markdown)

    st.markdown('<div class="title">블로그 자동생성 AI Agent</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="subtitle">1단계 프롬프트 생성 / 2단계 블로그 작성 / 3단계 댓글(사이드바)</div>',
        unsafe_allow_html=True,
    )

    temperature, model = render_sidebar(total_chars=total_chars, non_space_chars=non_space_chars)
    user_input, run_crawl = render_form()

    with st.expander("입력 가이드", expanded=False):
        st.write("구체적인 메뉴, 위치 키워드, 체감 포인트를 넣을수록 결과 품질이 좋아집니다.")

    if run_crawl:
        try:
            if not user_input.map_url.strip():
                st.warning("먼저 네이버 지도 URL을 입력해주세요.")
            else:
                crawled = crawl_place_tabs(user_input.map_url)
                st.session_state.crawled_place_id = crawled.place_id
                st.session_state.crawled_home_text = crawled.home_text
                st.session_state.crawled_menu_text = crawled.menu_text
                st.session_state.crawled_info_text = crawled.info_text
                st.session_state.crawled_news_text = crawled.news_text

                # 자동 입력은 하지 않고, 사용자 입력용 placeholder 예시만 갱신합니다.
                base = {
                    "map_url": user_input.map_url,
                    "place_name": "",
                    "business_hours": "",
                    "location_info": "",
                    "home_tab_info": "",
                    "menu_tab_info": "",
                    "info_tab_info": "",
                    "news_tab_info": "",
                    "parking_or_tips": "",
                    "interior_and_menu": "",
                    "signature_taste": "",
                    "tone": "정보형",
                    "target_keyword": "",
                }
                examples = merge_blog_input_with_crawl(base, crawled)
                st.session_state.example_place_name = examples.get("place_name", "")
                st.session_state.example_business_hours = examples.get("business_hours", "")
                st.session_state.example_location_info = examples.get("location_info", "")
                st.session_state.example_parking_or_tips = examples.get("parking_or_tips", "")
                st.session_state.example_target_keyword = examples.get("target_keyword", "")
                st.success(f"탭 크롤링 완료: placeId {crawled.place_id}")
                st.rerun()
        except Exception as map_error:
            st.warning(f"네이버 지도 정보 수집 실패: {map_error}")

    action_col1, action_col2 = st.columns(2)
    with action_col1:
        run_prompt = st.button("1단계 실행 (프롬프트 생성)", type="primary", use_container_width=True)
    with action_col2:
        run_blog = st.button("2단계 실행 (블로그 생성)", use_container_width=True)

    if run_prompt:
        try:
            os.environ["GOOGLE_TEMPERATURE"] = str(temperature)
            os.environ["GOOGLE_MODEL"] = model
            config = load_config()
            pipeline = BlogAgentPipeline(config)
            prompt_result = run_prompt_with_progress(pipeline, BlogInput(**user_input.__dict__))
            st.session_state.user_prompt = prompt_result
            st.session_state.editable_user_prompt = prompt_result
            st.rerun()
        except Exception as e:
            st.error(f"실행 중 오류가 발생했습니다: {e}")

    if run_blog:
        if not st.session_state.editable_user_prompt.strip():
            st.warning("먼저 1단계를 실행해 프롬프트를 생성해주세요.")
        else:
            try:
                os.environ["GOOGLE_TEMPERATURE"] = str(temperature)
                os.environ["GOOGLE_MODEL"] = model
                config = load_config()
                pipeline = BlogAgentPipeline(config)
                st.session_state.blog_markdown = run_blog_with_progress(
                    pipeline, st.session_state.editable_user_prompt
                )
                st.session_state.comments = ""
                st.rerun()
            except Exception as e:
                st.error(f"블로그 생성 중 오류가 발생했습니다: {e}")

    result_col1, result_col2 = st.columns(2)
    with result_col1:
        st.subheader("프롬프트 결과 (수정 가능)")
        st.text_area(
            "2단계 실행 전 프롬프트를 직접 수정하세요.",
            key="editable_user_prompt",
            height=420,
            placeholder="아직 생성되지 않았습니다.",
        )
    with result_col2:
        st.subheader("블로그 결과")
        if st.session_state.blog_markdown:
            st.markdown(st.session_state.blog_markdown)
        else:
            st.info("아직 생성되지 않았습니다.")

    st.sidebar.divider()
    st.sidebar.subheader("3단계 댓글 생성")
    run_comments = st.sidebar.button("댓글 생성 실행", use_container_width=True)
    if run_comments:
        if not st.session_state.blog_markdown:
            st.sidebar.warning("먼저 2단계 블로그를 생성해주세요.")
        else:
            try:
                os.environ["GOOGLE_TEMPERATURE"] = str(temperature)
                os.environ["GOOGLE_MODEL"] = model
                config = load_config()
                pipeline = BlogAgentPipeline(config)
                st.session_state.comments = run_comments_with_progress(
                    pipeline, st.session_state.blog_markdown
                )
                st.rerun()
            except Exception as e:
                st.sidebar.error(f"댓글 생성 중 오류가 발생했습니다: {e}")

    st.sidebar.markdown(st.session_state.comments or "아직 댓글이 생성되지 않았습니다.")


if __name__ == "__main__":
    main()
