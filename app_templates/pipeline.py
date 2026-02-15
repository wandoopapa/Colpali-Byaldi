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


def build_index(
    pdf_files: list[Path],
    output_dir: Path,
    index_name: str,
    report: Callable[[ProgressEvent], None],
) -> Path:
    # Related item: show progress by total and current item for PDF conversion/indexing.
    output_dir.mkdir(parents=True, exist_ok=True)
    chunks_path = output_dir / "rag_chunks.jsonl"
    manifest_path = output_dir / "rag_index_manifest.json"

    all_chunks: list[dict] = []
    total = max(len(pdf_files), 1)

    for file_idx, pdf_path in enumerate(pdf_files, start=1):
        report(ProgressEvent(f"PDF 처리 시작: {pdf_path.name}", 0.0, ((file_idx - 1) / total) * 100))
        reader = PdfReader(str(pdf_path))
        pages = max(len(reader.pages), 1)
        for page_idx, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            all_chunks.append(
                {
                    "source": str(pdf_path),
                    "page": page_idx,
                    "text": text.strip(),
                }
            )
            stage_percent = (page_idx / pages) * 100
            overall_percent = ((file_idx - 1) + (page_idx / pages)) / total * 100
            report(ProgressEvent(f"{pdf_path.name} 페이지 {page_idx}/{pages}", stage_percent, overall_percent))

    with chunks_path.open("w", encoding="utf-8") as fp:
        for row in all_chunks:
            fp.write(json.dumps(row, ensure_ascii=False) + "\n")

    manifest = {
        "index_name": index_name,
        "chunk_file": str(chunks_path),
        "documents": len(pdf_files),
        "chunks": len(all_chunks),
        "recommended_colpali_model": "vidore/colqwen2.5-v0.2",
        "recommended_byaldi_mode": "local_free_gpu",
        "hardware_profile": {
            "cpu": "i7-10700K",
            "gpu": "RTX 2080 SUPER",
            "ram": "64GB DDR4",
        },
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    report(ProgressEvent("인덱싱 결과 저장 완료", 100.0, 100.0))
    return manifest_path
