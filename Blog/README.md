# 블로그 자동생성 AI Agent

`test/promt.md` 요구사항을 반영한 Streamlit + LangChain + Google Gemini 기반 예제입니다.

## 1) 파일 구조

```text
.
├─ app.py            # Streamlit 앱 진입점
├─ ui.py             # 화면 UI, 입력 폼/탭/사이드바/진행 상태
├─ agent.py          # LangChain Agent 3종과 실행 파이프라인
├─ prompt.py         # 입력 데이터 구조와 프롬프트 정책
├─ config.py         # .env 로딩, 모델 설정
├─ requirements.txt  # 의존성
├─ .env.example      # 환경변수 예시
└─ test/
   ├─ promt.md
   ├─ Test1.md       # 문체 참고 1
   └─ Test2.md       # 문체 참고 2
```

## 2) 실행 방법

1. 가상환경 생성/활성화
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. 의존성 설치
```powershell
pip install -r requirements.txt
```

3. 환경변수 파일 생성
```powershell
Copy-Item .env.example .env
```
`.env` 파일의 `GOOGLE_API_KEY`를 실제 키로 교체합니다.

4. 실행
```powershell
streamlit run app.py
```

## 3) 화면 흐름

1. 사이드바에서 모델/temperature 설정
2. 메인 입력 폼에서 장소/메뉴/톤/키워드 입력
3. `AI Agent 실행` 클릭
4. 탭에서 순서대로 확인
- 프롬프트 미리보기: Prompt Builder Agent 결과
- 최종 블로그: Blog Writer Agent 결과
- 댓글: Comment Agent 결과

## 4) Agent 구조

- Prompt Builder Agent: 사용자 답변을 전문 블로거용 요청 프롬프트로 재구성
- Blog Writer Agent: 재구성된 프롬프트로 Markdown 블로그 본문 생성
- Comment Agent: 본문 기반 자연스러운 댓글 5개 생성

각 Agent는 LangChain `AgentExecutor` 기반으로 분리되어 있어 역할이 명확합니다.
