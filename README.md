# Colpali-Byaldi

GUI-first installer/runtime toolkit for local free RAG indexing with ColPali + Byaldi profile settings.

## Files
- `installer_gui.pyw`: One-click installer GUI.
- `app_templates/`: Runtime GUI and modular files copied to user-selected install folder.

## Quick start
1. Run `installer_gui.pyw`.
2. Select install folder.
3. Click **원클릭 설치 시작**.
4. After installation, run `run_gui.pyw` from the chosen folder.
5. In **인덱싱** tab, choose a source folder containing PDFs and run **ColPali+Byaldi 인덱싱 시작**.
6. In **VLM 대화** tab, input API Key/Model (Base URL is optional; default OpenAI), run **연결 상태 확인**, and then ask questions.
7. Check retrieved page image evidence in **검색된 페이지 이미지 미리보기**.


## External API presets
- OpenAI (default)
- Google AI Studio (Gemini OpenAI-compatible endpoint)
- OpenRouter
- Groq
- Together
- DeepSeek
- xAI
- Custom


## Google AI Studio tip
- Google AI Studio 사용 시 Base URL: `https://generativelanguage.googleapis.com/v1beta/openai`
- 모델명 예시: `gemini-2.5-flash`, `gemini-2.0-flash`
- 모델명 칸에는 API Key가 아니라 모델 ID를 입력해야 합니다.
