from __future__ import annotations

# Streamlit 앱 진입점입니다.
import os
import re
import streamlit as st

from agent import BlogAgentPipeline
from config import load_config
from ui import (
    apply_custom_style,
    init_session_state,
    render_form,
    render_result_tabs,
    render_sidebar,
    run_comments_with_progress,
    run_with_progress,
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
        '<div class="subtitle">1단계 프롬프트 생성 → 2단계 블로그 작성 → 3단계 댓글(별도 실행)</div>',
        unsafe_allow_html=True,
    )

    temperature, model = render_sidebar(total_chars=total_chars, non_space_chars=non_space_chars)
    user_input = render_form()

    with st.expander("입력 가이드", expanded=False):
        st.write("구체적인 메뉴, 위치 키워드, 체감 포인트를 넣을수록 결과 품질이 좋아집니다.")

    run_main = st.button("1~2단계 실행 (프롬프트+블로그)", type="primary", use_container_width=True)

    if run_main:
        try:
            os.environ["GOOGLE_TEMPERATURE"] = str(temperature)
            os.environ["GOOGLE_MODEL"] = model
            config = load_config()
            pipeline = BlogAgentPipeline(config)
            result = run_with_progress(pipeline, user_input)

            st.session_state.user_prompt = result["user_prompt"]
            st.session_state.blog_markdown = result["blog_markdown"]
            st.session_state.comments = ""
            st.rerun()
        except Exception as e:
            st.error(f"실행 중 오류가 발생했습니다: {e}")

    prompt_tab, blog_tab, comment_tab = render_result_tabs()

    with prompt_tab:
        st.subheader("2) 자동 생성된 User Prompt 미리보기")
        st.code(st.session_state.user_prompt or "아직 생성되지 않았습니다.", language="markdown")

    with blog_tab:
        st.subheader("3) 최종 블로그 결과")
        if st.session_state.blog_markdown:
            st.markdown(st.session_state.blog_markdown)
        else:
            st.info("아직 블로그 결과가 없습니다.")

    with comment_tab:
        st.subheader("추천 댓글")

        run_comments = st.button("3단계 실행 (댓글 생성)", use_container_width=True)
        if run_comments:
            if not st.session_state.blog_markdown:
                st.warning("먼저 1~2단계를 실행해 블로그 본문을 생성해주세요.")
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
                    st.error(f"댓글 생성 중 오류가 발생했습니다: {e}")

        st.markdown(st.session_state.comments or "아직 댓글이 생성되지 않았습니다.")


if __name__ == "__main__":
    main()
