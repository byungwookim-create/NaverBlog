from __future__ import annotations

import asyncio
import re
import sys
from dataclasses import dataclass
from urllib.parse import urljoin
from urllib.parse import urlparse
from urllib.request import Request, urlopen

try:
    from playwright.sync_api import sync_playwright
except Exception:  # pragma: no cover - runtime optional dependency
    sync_playwright = None


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
)


@dataclass(frozen=True)
class CrawledPlaceData:
    place_id: str
    source_url: str
    home_text: str
    menu_text: str
    info_text: str
    news_text: str


def extract_place_id(url: str) -> str:
    """네이버 지도/단축 URL에서 placeId를 추출합니다."""
    if not url.strip():
        raise ValueError("네이버 지도 URL이 비어 있습니다.")

    raw = url.strip()
    parsed = urlparse(raw)
    host = parsed.netloc.lower()
    if "naver.me" in host:
        req = Request(raw, headers={"User-Agent": USER_AGENT})
        with urlopen(req, timeout=10) as resp:
            raw = resp.geturl()

    patterns = [
        r"/entry/place/(\d+)",
        r"/place/(\d+)",
        r"placeId=(\d+)",
    ]
    for p in patterns:
        m = re.search(p, raw)
        if m:
            return m.group(1)

    raise ValueError("URL에서 placeId를 찾지 못했습니다.")


def _normalize_text(text: str) -> str:
    text = text.replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _extract_visible_panel_text(frame) -> str:
    script = """
() => {
  const selectors = [
    '.place_section',
    '.place_section_content',
    '#app-root',
    '#_pcmap_list_scroll_container',
    '.place_section',
    '.place_section_content',
    'body',
  ];
  let best = '';
  for (const sel of selectors) {
    const nodes = Array.from(document.querySelectorAll(sel));
    for (const node of nodes) {
      const txt = (node && node.innerText ? node.innerText.trim() : '');
      if (txt.length > best.length) best = txt;
    }
  }
  return best || '';
}
"""
    return _normalize_text(frame.evaluate(script))


def _get_place_frame(page):
    for frame in page.frames:
        if "pcmap.place.naver.com" in frame.url:
            return frame
    return None


def _extract_tab_links(frame) -> dict[str, str]:
    script = """
() => {
  const out = {};
  const links = Array.from(document.querySelectorAll('a[role="tab"]'));
  for (const a of links) {
    const text = (a.innerText || '').trim();
    const href = a.getAttribute('href') || '';
    if (!text || !href) continue;
    out[text] = href;
  }
  return out;
}
"""
    return frame.evaluate(script)


def _expand_business_hours(frame) -> bool:
    script = """
() => {
  const cands = Array.from(document.querySelectorAll('[aria-expanded="false"], a, button, [role="button"]'));
  const target = cands.find((el) => {
    const t = (el.innerText || '').trim();
    if (!t) return false;
    const hasExpandWord = t.includes('펼쳐보기') || t.includes('더보기');
    const hasTimePattern = /\\b\\d{1,2}:\\d{2}\\b/.test(t) || t.includes('라스트오더');
    return hasExpandWord && hasTimePattern;
  });
  if (target) {
    target.click();
    return true;
  }
  return false;
}
"""
    try:
        # lazy 렌더링 대응: 스크롤로 영업시간 블록 로드 유도
        frame.evaluate(
            """
() => {
  const box = document.querySelector('#_pcmap_list_scroll_container') || document.scrollingElement || document.documentElement;
  if (!box) return;
  const original = box.scrollTop || 0;
  box.scrollTop = Math.min(500, (box.scrollHeight || 500));
  box.scrollTop = original;
}
"""
        )
        return bool(frame.evaluate(script))
    except Exception:
        return False


def _extract_tab_sections_text(frame) -> str:
    script = """
() => {
  const blocks = [];
  const sections = Array.from(document.querySelectorAll('.place_section'));
  for (const section of sections) {
    const titleNode = section.querySelector('h2, h3, .place_section_header, .place_section_title');
    const title = (titleNode && titleNode.innerText ? titleNode.innerText : '').trim();
    const text = (section.innerText || '').trim();
    if (!text) continue;
    blocks.push({ title, text });
  }
  return blocks;
}
"""
    blocks: list[dict[str, str]] = frame.evaluate(script)

    cleaned: list[str] = []
    for block in blocks:
        raw_title = (block.get("title") or "").strip()
        title = re.sub(r"\d+$", "", raw_title).strip()
        text = _normalize_text(block.get("text") or "")
        if not text:
            continue

        # 헤더/푸터/버튼성 안내 블록 제거
        action_tokens = ["출발", "도착", "저장", "거리뷰", "공유"]
        action_hit_count = sum(1 for token in action_tokens if token in text)
        if ("알림받기" in text and "출발" in text and "도착" in text) or action_hit_count >= 3 or "페이지 닫기" in text:
            continue
        if "정보 수정 제안하기" in text:
            continue
        if text.startswith("메뉴판 이미지로 보기"):
            continue
        if len(text) < 10:
            continue

        if title and not text.startswith(title):
            cleaned.append(f"{title}\n{text}")
        else:
            cleaned.append(text)

    return _normalize_text("\n\n".join(cleaned))


def crawl_place_tabs(map_url: str, *, timeout_ms: int = 30000, headless: bool = True) -> CrawledPlaceData:
    """네이버 지도 좌측 패널의 홈/메뉴/정보/소식 탭 텍스트를 브라우저 크롤링으로 수집합니다."""
    if sync_playwright is None:
        raise RuntimeError(
            "playwright가 설치되어 있지 않습니다. "
            "`pip install playwright && playwright install chromium` 를 먼저 실행하세요."
        )

    # Windows + Streamlit 환경에서 Playwright subprocess 생성 실패(NotImplementedError) 방지
    if sys.platform.startswith("win"):
        try:
            policy = asyncio.get_event_loop_policy()
            if not isinstance(policy, asyncio.WindowsProactorEventLoopPolicy):
                asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        except Exception:
            pass

    place_id = extract_place_id(map_url)
    map_entry_home = f"https://map.naver.com/p/entry/place/{place_id}?placePath=%2Fhome"
    result: dict[str, str] = {"home": "", "menu": "", "info": "", "news": ""}

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=headless)
            context = browser.new_context(user_agent=USER_AGENT, locale="ko-KR")
            page = context.new_page()
            page.set_default_timeout(timeout_ms)

            page.goto(map_entry_home, wait_until="domcontentloaded")
            page.wait_for_timeout(3500)
            frame = _get_place_frame(page)
            if frame is None:
                raise RuntimeError("네이버 장소 패널 iframe을 찾지 못했습니다.")

            tab_links = _extract_tab_links(frame)
            label_to_key = {"홈": "home", "메뉴": "menu", "정보": "info", "소식": "news"}

            # 우선 홈은 현재 페이지에서 즉시 수집
            for _ in range(4):
                if _expand_business_hours(frame):
                    page.wait_for_timeout(700)
                    break
                page.wait_for_timeout(500)
            result["home"] = _extract_tab_sections_text(frame) or _extract_visible_panel_text(frame)

            for label, key in label_to_key.items():
                if key == "home":
                    continue
                href = tab_links.get(label)
                if not href:
                    # 탭 자체가 없는 장소는 빈 값으로 둡니다.
                    result[key] = ""
                    continue

                tab_url = urljoin("https://pcmap.place.naver.com", href)
                page.goto(tab_url, wait_until="domcontentloaded")
                page.wait_for_timeout(2200)
                tab_frame = _get_place_frame(page) or page.main_frame
                if key in {"home", "info"}:
                    for _ in range(3):
                        if _expand_business_hours(tab_frame):
                            page.wait_for_timeout(700)
                            break
                        page.wait_for_timeout(400)
                result[key] = _extract_tab_sections_text(tab_frame) or _extract_visible_panel_text(tab_frame)

            context.close()
            browser.close()
    except NotImplementedError as e:
        raise RuntimeError(
            "Playwright 브라우저 프로세스 실행에 실패했습니다. "
            "Windows 이벤트 루프 이슈일 수 있습니다. "
            "터미널에서 `playwright install chromium` 실행 후 앱을 재시작해 주세요."
        ) from e

    return CrawledPlaceData(
        place_id=place_id,
        source_url=map_entry_home,
        home_text=result["home"],
        menu_text=result["menu"],
        info_text=result["info"],
        news_text=result["news"],
    )


def _guess_place_name(text: str) -> str:
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if line == "네이버지도 검색":
            continue
        if line in {"홈", "메뉴", "정보", "소식", "리뷰", "사진"}:
            continue
        return line
    return ""


def _guess_business_hours(text: str) -> str:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    candidates = [ln for ln in lines if "영업" in ln or "라스트오더" in ln]
    return " / ".join(candidates[:3]).strip()


def merge_blog_input_with_crawl(input_dict: dict[str, str], crawled: CrawledPlaceData) -> dict[str, str]:
    """기존 사용자 입력을 유지하며, 비어 있는 필드를 크롤링 텍스트로 보강합니다."""
    out = dict(input_dict)

    place_name = _guess_place_name(crawled.home_text)
    if place_name and not out.get("place_name"):
        out["place_name"] = place_name

    business_hours = _guess_business_hours(crawled.home_text + "\n" + crawled.info_text)
    if business_hours and not out.get("business_hours"):
        out["business_hours"] = business_hours

    location_append = f"지도 링크: {crawled.source_url}"
    if out.get("location_info"):
        out["location_info"] = f'{out["location_info"].strip()}\n{location_append}'
    else:
        out["location_info"] = location_append

    if not out.get("home_tab_info"):
        out["home_tab_info"] = crawled.home_text
    if not out.get("menu_tab_info"):
        out["menu_tab_info"] = crawled.menu_text
    if not out.get("info_tab_info"):
        out["info_tab_info"] = crawled.info_text
    if not out.get("news_tab_info"):
        out["news_tab_info"] = crawled.news_text

    if not out.get("parking_or_tips"):
        info_lines = [ln.strip() for ln in crawled.info_text.splitlines() if ln.strip()]
        tips = [ln for ln in info_lines if ("주차" in ln or "편의" in ln or "무선 인터넷" in ln or "포장" in ln)]
        if tips:
            out["parking_or_tips"] = "\n".join(tips[:6])

    if not out.get("target_keyword"):
        out["target_keyword"] = out.get("place_name", "")

    return out
