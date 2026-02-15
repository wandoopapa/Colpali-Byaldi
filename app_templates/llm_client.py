# 4. 구성
# * 프로그램 구성
# - 프로그램 코드에는 '4. 구성'의 모든 내용이 코드 최상단에 전체 내용 기입 + 관련 코드 항목에 각각 코멘트 기입 필요 : 최종 : 최상단에 구성 전체 내용 기입 + 각 항목별 코멘트 기입 (다른 ai 혹은 프로그래머가 코드만 보고 코드 작성 가이드를 따를 수 있어야 함)
# - 사용자는 설치 파일만 실행, 나머지 설치 과정은 파이썬 코드가 자동으로 진행
# - '설치 GUI', '실행 GUI' 로 구분
# - 모든 과정은 GUI 를 적용하여 .pyw 로 cmd 창 없이 GUI로 진행
# - '설치 GUI' 파일을 실행하면, [폴더 생성 -> 파일 생성 -> 필요 라이브러리 자동 다운로드 및 설치] 까지 원클릭 진행
# - 설치가 완료 후, 설치된 '실행 GUI' 파일로 프로그램을 실행
# - 소스 코드는 반드시 영어(English)로 작성하여 코드 호환성 유지
# - GUI 출력(라벨, 버튼, 알림창)은 반드시 한국어(Korean)로 작성하여 사용자 편의성 극대화
# - 역할, 파트 별로 파일을 나누어서 1개의 폴더 안에 저장

from __future__ import annotations

from dataclasses import dataclass
import requests


@dataclass
class LLMSettings:
    api_key: str
    api_base: str
    model: str


class OpenAICompatibleClient:
    # Related item: provide VLM chat and connection test in runtime GUI.
    def __init__(self, settings: LLMSettings) -> None:
        self.settings = settings

    def _normalized_base_url(self) -> str:
        # Related item: clarify API Base URL by supporting default OpenAI endpoint.
        base = (self.settings.api_base or "").strip().rstrip("/")
        if not base:
            return "https://api.openai.com/v1"
        if base.endswith("/v1"):
            return base
        if base.endswith("/openai"):
            return base + "/v1"
        return base

    def check_connection(self) -> str:
        url = self._normalized_base_url() + "/models"
        headers = {"Authorization": f"Bearer {self.settings.api_key}"}
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        models = data.get("data", [])
        if not models:
            return "연결 성공 (모델 목록 없음 또는 비표준 응답)"
        model_ids = [m.get("id", "unknown") for m in models[:5]]
        return f"연결 성공 / 사용 가능 모델 예시: {', '.join(model_ids)}"

    def chat(self, prompt: str, context: str) -> str:
        url = self._normalized_base_url() + "/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.settings.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.settings.model,
            "messages": [
                {
                    "role": "system",
                    "content": "주어진 문맥만 사용해 한국어로 정확하게 답변하세요. 문맥에 없으면 없다고 답하세요.",
                },
                {
                    "role": "user",
                    "content": f"문맥:\n{context}\n\n질문:\n{prompt}",
                },
            ],
            "temperature": 0.1,
        }
        response = requests.post(url, headers=headers, json=payload, timeout=120)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]
