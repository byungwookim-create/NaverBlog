from __future__ import annotations

# LangChain Agent 3종(프롬프트 빌더/본문 작성/댓글 작성)을 구성하고 실행합니다.
from pathlib import Path
from typing import Any, Dict

from langchain.agents import create_agent
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI

from config import AppConfig, TEST_STYLE_FILES
from prompt import (
    BLOG_WRITER_SYSTEM,
    COMMENT_WRITER_SYSTEM,
    PROMPT_BUILDER_SYSTEM,
    BlogInput,
    format_user_facts,
)


def _read_style_corpus(paths: list[Path]) -> str:
    """참고 스타일 MD 파일들을 읽어 하나의 코퍼스로 결합합니다."""
    chunks: list[str] = []
    for p in paths:
        if p.exists():
            txt = p.read_text(encoding="utf-8", errors="ignore").strip()
            if txt:
                chunks.append(f"[파일: {p.name}]\n{txt[:7000]}")
    if not chunks:
        return "스타일 참고 파일이 비어 있습니다. 자연스럽고 정보성 있는 블로그 톤으로 작성하세요."
    return "\n\n".join(chunks)


def _content_to_text(content: Any) -> str:
    """LangChain 메시지 content를 문자열로 정규화합니다."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict):
                text = item.get("text")
                if isinstance(text, str):
                    parts.append(text)
            elif isinstance(item, str):
                parts.append(item)
        return "\n".join(parts).strip()
    return str(content)


def _extract_text_from_state(state: Dict[str, Any]) -> str:
    """Agent 실행 결과(state)에서 마지막 AI 텍스트를 추출합니다."""
    messages = state.get("messages", [])
    for msg in reversed(messages):
        msg_type = getattr(msg, "type", "")
        if msg_type == "ai":
            return _content_to_text(getattr(msg, "content", ""))
    return ""


class BlogAgentPipeline:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.llm = ChatGoogleGenerativeAI(
            model=config.google_model,
            google_api_key=config.google_api_key,
            temperature=config.temperature,
        )
        self.style_corpus = _read_style_corpus(TEST_STYLE_FILES)

        self.style_tool = self._build_style_tool()
        self.format_guard_tool = self._build_format_guard_tool()

        self.prompt_builder = self._build_prompt_builder_agent()
        self.blog_writer = self._build_blog_writer_agent()
        self.comment_writer = self._build_comment_writer_agent()

    def _build_style_tool(self):
        style_corpus = self.style_corpus

        @tool("style_reference_reader")
        def style_reference_reader(query: str) -> str:
            """Test1.md와 Test2.md 기반 문체 레퍼런스를 반환합니다."""
            _ = query
            return style_corpus

        return style_reference_reader

    def _build_format_guard_tool(self):
        @tool("format_guard")
        def format_guard(query: str) -> str:
            """댓글 출력 형식 점검 기준을 반환합니다."""
            _ = query
            return "댓글은 1~5번 번호 목록, 각 한 줄, 과한 광고 문구 금지"

        return format_guard

    def _build_prompt_builder_agent(self):
        return create_agent(
            model=self.llm,
            tools=[self.style_tool],
            system_prompt=PROMPT_BUILDER_SYSTEM,
            name="prompt_builder_agent",
        )

    def _build_blog_writer_agent(self):
        return create_agent(
            model=self.llm,
            tools=[self.style_tool],
            system_prompt=BLOG_WRITER_SYSTEM,
            name="blog_writer_agent",
        )

    def _build_comment_writer_agent(self):
        return create_agent(
            model=self.llm,
            tools=[self.format_guard_tool],
            system_prompt=COMMENT_WRITER_SYSTEM,
            name="comment_writer_agent",
        )

    def build_user_prompt(self, user_input: BlogInput) -> str:
        """1단계: 사용자 메모를 전문 작성용 프롬프트로 변환합니다."""
        facts = format_user_facts(user_input)
        prompt_state = self.prompt_builder.invoke(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": (
                            "다음 사용자 메모를 바탕으로, 블로그 본문이 아닌 '작성용 프롬프트'만 작성해라.\n\n"
                            f"{facts}\n\n"
                            "출력은 프롬프트 원문만 제공하고, 블로그 본문/예시 문단은 쓰지 마라."
                        ),
                    }
                ]
            }
        )
        return _extract_text_from_state(prompt_state)

    def write_blog(self, final_prompt: str) -> str:
        """2단계: 생성된 프롬프트로 블로그 본문을 작성합니다."""
        blog_state = self.blog_writer.invoke(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": (
                            "아래 프롬프트를 기준으로 고품질 블로그 본문을 Markdown으로 작성해라.\n\n"
                            f"{final_prompt}\n\n"
                            "최종 블로그 본문만 출력해라."
                        ),
                    }
                ]
            }
        )
        return _extract_text_from_state(blog_state)

    def write_comments(self, blog_markdown: str) -> str:
        """3단계: 블로그 본문 기반 댓글을 생성합니다."""
        comment_state = self.comment_writer.invoke(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": (
                            "다음 블로그 글을 읽고 자연스러운 댓글 5개를 생성해라.\n\n"
                            f"{blog_markdown}"
                        ),
                    }
                ]
            }
        )
        return _extract_text_from_state(comment_state)

    def run(self, user_input: BlogInput) -> Dict[str, str]:
        """1~2단계만 실행합니다(댓글 제외)."""
        final_prompt = self.build_user_prompt(user_input)
        blog_markdown = self.write_blog(final_prompt)
        return {
            "user_prompt": final_prompt,
            "blog_markdown": blog_markdown,
        }
