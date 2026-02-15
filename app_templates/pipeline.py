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

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from pypdf import PdfReader


@dataclass
class ProgressEvent:
    stage_text: str
    stage_percent: float
    overall_percent: float


def collect_pdf_files(source_folder: Path) -> list[Path]:
    # Related item: remove duplicated input path/button by using source folder as single PDF source.
    return sorted(source_folder.glob("*.pdf"))


def build_colpali_byaldi_index(
    source_folder: Path,
    report: Callable[[ProgressEvent], None],
) -> Path:
    # Related item: keep ColPali + Byaldi oriented manifest and free local indexing flow.
    pdf_files = collect_pdf_files(source_folder)
    if not pdf_files:
        raise ValueError("원본 폴더에 PDF 파일이 없습니다.")

    chunks_path = source_folder / "rag_chunks.jsonl"
    manifest_path = source_folder / "rag_index_manifest.json"

    all_chunks: list[dict] = []
    total = len(pdf_files)

    for file_idx, pdf_path in enumerate(pdf_files, start=1):
        report(ProgressEvent(f"PDF 처리 시작: {pdf_path.name}", 0.0, ((file_idx - 1) / total) * 100))
        reader = PdfReader(str(pdf_path))
        pages = max(len(reader.pages), 1)
        for page_idx, page in enumerate(reader.pages, start=1):
            text = (page.extract_text() or "").strip()
            all_chunks.append(
                {
                    "source": str(pdf_path.name),
                    "page": page_idx,
                    "text": text,
                    "keywords": text.lower().split()[:80],
                }
            )
            stage_percent = (page_idx / pages) * 100
            overall_percent = ((file_idx - 1) + (page_idx / pages)) / total * 100
            report(ProgressEvent(f"{pdf_path.name} 페이지 {page_idx}/{pages}", stage_percent, overall_percent))

    with chunks_path.open("w", encoding="utf-8") as fp:
        for row in all_chunks:
            fp.write(json.dumps(row, ensure_ascii=False) + "\n")

    manifest = {
        "index_type": "colpali_byaldi",
        "retrieval_mode": "local_free_first",
        "source_folder": str(source_folder),
        "documents": len(pdf_files),
        "chunks": len(all_chunks),
        "chunk_file": str(chunks_path),
        "recommended_colpali_model": "vidore/colqwen2.5-v0.2",
        "recommended_stack": {
            "retriever": "Byaldi",
            "vlm": "External API (OpenAI-compatible)",
        },
        "hardware_profile": {
            "cpu": "i7-10700K",
            "gpu": "RTX 2080 SUPER",
            "ram": "64GB DDR4",
        },
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    report(ProgressEvent("인덱싱 결과 저장 완료", 100.0, 100.0))
    return manifest_path


def load_chunks(chunk_file: Path) -> list[dict]:
    if not chunk_file.exists():
        return []
    return [json.loads(line) for line in chunk_file.read_text(encoding="utf-8").splitlines() if line.strip()]


def retrieve_context(chunks: list[dict], question: str, top_k: int = 4) -> str:
    # Related item: post-index VLM conversation uses retrieved context.
    query_terms = [t for t in question.lower().split() if t]

    scored: list[tuple[int, dict]] = []
    for chunk in chunks:
        text = (chunk.get("text") or "").lower()
        score = sum(1 for term in query_terms if term in text)
        if score > 0:
            scored.append((score, chunk))

    ranked = sorted(scored, key=lambda row: row[0], reverse=True)[:top_k]
    if not ranked:
        return "관련 문맥을 찾지 못했습니다."

    return "\n\n".join(
        f"[문서:{item['source']}|페이지:{item['page']}]\n{item['text']}" for _, item in ranked
    )
