from __future__ import annotations

# 애플리케이션 전역 설정과 환경변수 로딩을 담당합니다.
from dataclasses import dataclass
from pathlib import Path
import os

from dotenv import dotenv_values, load_dotenv


BASE_DIR = Path(__file__).resolve().parent
TEST_STYLE_FILES = [BASE_DIR / "test" / "Test1.md", BASE_DIR / "test" / "Test2.md"]


@dataclass(frozen=True)
class AppConfig:
    google_api_key: str
    google_model: str = "gemini-2.5-flash-lite"
    temperature: float = 0.5


def load_config() -> AppConfig:
    """.env를 읽고 필수 설정을 검증한 뒤 AppConfig를 반환합니다."""
    env_path = BASE_DIR / ".env"

    # 기본 로딩(프로세스 환경변수 포함)
    load_dotenv(dotenv_path=env_path, override=True)

    def _clean(value: str) -> str:
        # .env 값에 공백/따옴표가 섞여 있어도 안전하게 정리합니다.
        return value.strip().strip('"').strip("'")

    # 일반 키 로딩
    api_key = _clean(os.getenv("GOOGLE_API_KEY", ""))
    model = _clean(os.getenv("GOOGLE_MODEL", "gemini-2.5-flash-lite"))
    temp_raw = _clean(os.getenv("GOOGLE_TEMPERATURE", "0.5"))

    # BOM(\ufeff)으로 깨진 키 대응
    if not api_key and env_path.exists():
        parsed = {k.lstrip("\ufeff"): (v or "") for k, v in dotenv_values(env_path).items()}
        api_key = _clean(parsed.get("GOOGLE_API_KEY", ""))
        model = _clean(parsed.get("GOOGLE_MODEL", model))
        temp_raw = _clean(parsed.get("GOOGLE_TEMPERATURE", temp_raw))

    if not api_key:
        raise ValueError(
            "GOOGLE_API_KEY.env 파일 또는 환경변수를 확인하세요."
        )

    temperature = float(temp_raw or "0.5")
    return AppConfig(google_api_key=api_key, google_model=model, temperature=temperature)
