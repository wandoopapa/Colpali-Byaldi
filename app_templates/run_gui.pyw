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
# * 실행 GUI
# - PDF 변환이 진행되는 과정을 검은색 CMD 창이 아닌, '실행 GUI' 로딩 창(Progress Bar)으로 표현
# - PDF 파일 업로드는 '실행 GUI' 안의 버튼을 이용하여 사용자가 적용
# - 작업 과정은 항목 별로 총 작업량 대비 현재 작업량을 퍼센티지화 하여 진척률을 확인할 수 있는 시각적 이미지 적용
# - 작업 진행률은 전체 항목과 현재 항목을 구분하여 Progress Bar 를 각각 적용
# - 원본 파일을 불러오는 폴더를 '실행 GUI' 상에서 사용자가 지정
# - 프로그램을 제작하는 과정에서 누적된 패치 및 업데이트 사항에 대한 모든 내용을 누락없이 표시 (시스템 개발 역사 페이지는 버전별로 폴더형식으로 눌러서 열어볼 수 있또록 누락없이 모든 내용 기입,핵심 요약이 아니라 관련 내용이 자세하게 기입

from __future__ import annotations

import threading
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from config_manager import ConfigManager, RuntimeConfig
from history_manager import HistoryManager
from pipeline import ProgressEvent, build_index
from ui_components import LabeledEntry


class RuntimeGUI(tk.Tk):
    # Related item: dedicated runtime GUI separated from installer GUI.
    def __init__(self) -> None:
        super().__init__()
        self.title("ColPali + Byaldi 실행기")
        self.geometry("980x680")

        self.base_dir = Path(__file__).resolve().parent
        self.config_manager = ConfigManager(self.base_dir / "runtime_config.json")
        self.history_manager = HistoryManager(self.base_dir / "HISTORY_VERSIONS.json")
        self.config = self.config_manager.load()

        self.current_pdf_files: list[Path] = []

        self.overall_progress = tk.DoubleVar(value=0.0)
        self.step_progress = tk.DoubleVar(value=0.0)
        self.status_var = tk.StringVar(value="대기 중")

        self._build_ui()
        self._load_config_to_form()
        self._load_history_tree()

    def _build_ui(self) -> None:
        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=14, pady=14)

        main_tab = ttk.Frame(notebook, padding=12)
        history_tab = ttk.Frame(notebook, padding=12)
        notebook.add(main_tab, text="실행")
        notebook.add(history_tab, text="개발 이력")

        self.source_entry = LabeledEntry(main_tab, "원본 폴더 경로")
        self.source_entry.pack(fill="x")
        ttk.Button(main_tab, text="원본 폴더 선택", command=self.select_source_folder).pack(anchor="w")

        self.api_key_entry = LabeledEntry(main_tab, "외부 LLM API Key", show="*")
        self.api_key_entry.pack(fill="x", pady=(8, 0))
        self.api_base_entry = LabeledEntry(main_tab, "외부 LLM API Base URL")
        self.api_base_entry.pack(fill="x")
        self.model_entry = LabeledEntry(main_tab, "외부 LLM 모델명")
        self.model_entry.pack(fill="x")
        self.index_name_entry = LabeledEntry(main_tab, "인덱스 이름")
        self.index_name_entry.pack(fill="x")

        pdf_row = ttk.Frame(main_tab)
        pdf_row.pack(fill="x", pady=(8, 0))
        ttk.Button(pdf_row, text="PDF 파일 선택", command=self.select_pdf_files).pack(side="left")
        self.pdf_label = ttk.Label(pdf_row, text="선택된 PDF: 0개")
        self.pdf_label.pack(side="left", padx=(12, 0))

        ttk.Label(main_tab, textvariable=self.status_var).pack(anchor="w", pady=(14, 4))
        ttk.Label(main_tab, text="전체 진행률").pack(anchor="w")
        ttk.Progressbar(main_tab, variable=self.overall_progress, maximum=100).pack(fill="x")
        ttk.Label(main_tab, text="현재 항목 진행률").pack(anchor="w", pady=(10, 0))
        ttk.Progressbar(main_tab, variable=self.step_progress, maximum=100).pack(fill="x")

        self.log_box = tk.Text(main_tab, height=12)
        self.log_box.pack(fill="both", expand=True, pady=(12, 0))

        action_row = ttk.Frame(main_tab)
        action_row.pack(fill="x", pady=(10, 0))
        ttk.Button(action_row, text="설정 저장", command=self.save_config).pack(side="left")
        ttk.Button(action_row, text="PDF 인덱싱 시작", command=self.run_indexing).pack(side="left", padx=(8, 0))

        self.history_tree = ttk.Treeview(history_tab)
        self.history_tree.pack(side="left", fill="both", expand=True)
        self.history_tree.bind("<<TreeviewSelect>>", self.on_history_select)

        history_scroll = ttk.Scrollbar(history_tab, orient="vertical", command=self.history_tree.yview)
        history_scroll.pack(side="left", fill="y")
        self.history_tree.configure(yscrollcommand=history_scroll.set)

        self.history_text = tk.Text(history_tab, width=65)
        self.history_text.pack(side="left", fill="both", expand=True, padx=(12, 0))

    def _load_config_to_form(self) -> None:
        self.source_entry.set(self.config.source_folder)
        self.api_key_entry.set(self.config.llm_api_key)
        self.api_base_entry.set(self.config.llm_api_base)
        self.model_entry.set(self.config.llm_model)
        self.index_name_entry.set(self.config.index_name)

    # Related item: user chooses source folder from runtime GUI.
    def select_source_folder(self) -> None:
        folder = filedialog.askdirectory(title="원본 폴더 선택")
        if folder:
            self.source_entry.set(folder)

    # Related item: user uploads PDF files from runtime GUI.
    def select_pdf_files(self) -> None:
        files = filedialog.askopenfilenames(title="PDF 파일 선택", filetypes=[("PDF 파일", "*.pdf")])
        self.current_pdf_files = [Path(f) for f in files]
        self.pdf_label.configure(text=f"선택된 PDF: {len(self.current_pdf_files)}개")

    def save_config(self) -> None:
        cfg = RuntimeConfig(
            source_folder=self.source_entry.get(),
            llm_api_key=self.api_key_entry.get(),
            llm_api_base=self.api_base_entry.get(),
            llm_model=self.model_entry.get(),
            index_name=self.index_name_entry.get() or "default_index",
        )
        self.config_manager.save(cfg)
        self.config = cfg
        messagebox.showinfo("저장 완료", "설정이 저장되었습니다.")

    def run_indexing(self) -> None:
        if not self.current_pdf_files:
            messagebox.showwarning("확인", "먼저 PDF 파일을 선택하세요.")
            return
        self.save_config()
        threading.Thread(target=self._run_indexing_worker, daemon=True).start()

    def _run_indexing_worker(self) -> None:
        output_dir = Path(self.source_entry.get() or self.base_dir)
        index_name = self.index_name_entry.get() or "default_index"
        try:
            manifest = build_index(self.current_pdf_files, output_dir, index_name, self._on_progress)
            self._append_log(f"완료: {manifest}")
            self.status_var.set("인덱싱 완료")
            messagebox.showinfo("완료", f"인덱싱 완료\n결과: {manifest}")
        except Exception as exc:  # noqa: BLE001
            self._append_log(f"오류: {exc}")
            self.status_var.set("인덱싱 실패")
            messagebox.showerror("오류", str(exc))

    def _on_progress(self, event: ProgressEvent) -> None:
        self.status_var.set(event.stage_text)
        self.step_progress.set(event.stage_percent)
        self.overall_progress.set(event.overall_percent)
        self._append_log(f"[{event.overall_percent:5.1f}%] {event.stage_text}")

    def _append_log(self, text: str) -> None:
        self.log_box.insert("end", text + "\n")
        self.log_box.see("end")

    # Related item: full versioned development history in folder-like tree.
    def _load_history_tree(self) -> None:
        data = self.history_manager.load_versions()
        root = self.history_tree.insert("", "end", text="시스템 개발 역사", values=("root",))
        for version in data.get("versions", []):
            node = self.history_tree.insert(root, "end", text=version["version"], values=("version",))
            self.history_tree.insert(node, "end", text="상세 내용", values=("details", version["details"]))

    def on_history_select(self, _event: object) -> None:
        selected = self.history_tree.selection()
        if not selected:
            return
        node = selected[0]
        values = self.history_tree.item(node, "values")
        if values and values[0] == "details":
            details = values[1]
            self.history_text.delete("1.0", "end")
            self.history_text.insert("end", details)


if __name__ == "__main__":
    RuntimeGUI().mainloop()
