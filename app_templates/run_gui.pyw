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

from PIL import Image, ImageTk

from config_manager import ConfigManager, RuntimeConfig
from history_manager import HistoryManager
from llm_client import LLMSettings, OpenAICompatibleClient
from pipeline import ProgressEvent, RetrievalResult, build_colpali_byaldi_index, load_chunks, retrieve_context
from ui_components import LabeledEntry


# Related item: researched external API presets including Google AI Studio.
PROVIDER_PRESETS: dict[str, dict[str, str]] = {
    "OpenAI": {
        "base": "https://api.openai.com/v1",
        "model": "gpt-4.1-mini",
        "note": "OpenAI 기본 엔드포인트입니다.",
    },
    "Google AI Studio (Gemini OpenAI 호환)": {
        "base": "https://generativelanguage.googleapis.com/v1beta/openai",
        "model": "gemini-2.5-flash",
        "note": "Google AI Studio/Gemini API의 OpenAI 호환 경로입니다. 모델 예: gemini-2.5-flash, gemini-2.0-flash.",
    },
    "OpenRouter": {
        "base": "https://openrouter.ai/api/v1",
        "model": "openai/gpt-4.1-mini",
        "note": "여러 제공자 모델을 단일 OpenAI 호환 API로 사용합니다.",
    },
    "Groq": {
        "base": "https://api.groq.com/openai/v1",
        "model": "llama-3.3-70b-versatile",
        "note": "저지연 OpenAI 호환 API입니다.",
    },
    "Together": {
        "base": "https://api.together.xyz/v1",
        "model": "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo",
        "note": "오픈 모델 중심의 OpenAI 호환 API입니다.",
    },
    "DeepSeek": {
        "base": "https://api.deepseek.com/v1",
        "model": "deepseek-chat",
        "note": "DeepSeek OpenAI 호환 API입니다.",
    },
    "xAI": {
        "base": "https://api.x.ai/v1",
        "model": "grok-2-latest",
        "note": "xAI Grok OpenAI 호환 API입니다.",
    },
    "직접 입력(커스텀)": {
        "base": "",
        "model": "",
        "note": "직접 Base URL/모델을 입력합니다.",
    },
}


class RuntimeGUI(tk.Tk):
    # Related item: dedicated runtime GUI separated from installer GUI.
    def __init__(self) -> None:
        super().__init__()
        self.title("ColPali + Byaldi 실행기")
        self.geometry("1280x860")

        self.base_dir = Path(__file__).resolve().parent
        self.config_manager = ConfigManager(self.base_dir / "runtime_config.json")
        self.history_manager = HistoryManager(self.base_dir / "HISTORY_VERSIONS.json")
        self.config = self.config_manager.load()

        self.overall_progress = tk.DoubleVar(value=0.0)
        self.step_progress = tk.DoubleVar(value=0.0)
        self.status_var = tk.StringVar(value="대기 중")
        self.chunk_file: Path | None = None
        self.preview_photo: ImageTk.PhotoImage | None = None

        self._build_ui()
        self._load_config_to_form()
        self._load_history_tree()

    def _build_ui(self) -> None:
        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=14, pady=14)

        main_tab = ttk.Frame(notebook, padding=12)
        chat_tab = ttk.Frame(notebook, padding=12)
        history_tab = ttk.Frame(notebook, padding=12)
        notebook.add(main_tab, text="인덱싱")
        notebook.add(chat_tab, text="VLM 대화")
        notebook.add(history_tab, text="개발 이력")

        self.source_entry = LabeledEntry(main_tab, "원본 폴더 경로 (해당 폴더의 모든 PDF 자동 인식)")
        self.source_entry.pack(fill="x")
        ttk.Button(main_tab, text="원본 폴더 선택", command=self.select_source_folder).pack(anchor="w")

        ttk.Label(
            main_tab,
            text="설명: 이미 인덱싱 완료된 동일 PDF는 자동 건너뜁니다. (중복 인덱싱 방지)",
        ).pack(anchor="w", pady=(8, 0))
        ttk.Button(main_tab, text="시스템 구성 제안 보기", command=self.show_architecture_proposal).pack(anchor="w", pady=(8, 0))

        ttk.Label(main_tab, textvariable=self.status_var).pack(anchor="w", pady=(14, 4))
        ttk.Label(main_tab, text="전체 진행률").pack(anchor="w")
        ttk.Progressbar(main_tab, variable=self.overall_progress, maximum=100).pack(fill="x")
        ttk.Label(main_tab, text="현재 항목 진행률").pack(anchor="w", pady=(10, 0))
        ttk.Progressbar(main_tab, variable=self.step_progress, maximum=100).pack(fill="x")

        self.log_box = tk.Text(main_tab, height=13)
        self.log_box.pack(fill="both", expand=True, pady=(12, 0))

        action_row = ttk.Frame(main_tab)
        action_row.pack(fill="x", pady=(10, 0))
        ttk.Button(action_row, text="인덱싱 설정 저장", command=self.save_config).pack(side="left")
        ttk.Button(action_row, text="ColPali+Byaldi 인덱싱 시작", command=self.run_indexing).pack(side="left", padx=(8, 0))

        # Related item: API Key belongs to VLM conversation area, not indexing area.
        self.api_key_entry = LabeledEntry(chat_tab, "외부 VLM API Key", show="*")
        self.api_key_entry.pack(fill="x")

        preset_row = ttk.Frame(chat_tab)
        preset_row.pack(fill="x", pady=(0, 4))
        ttk.Label(preset_row, text="API 제공자 프리셋").pack(side="left")
        self.provider_var = tk.StringVar(value="OpenAI")
        self.provider_combo = ttk.Combobox(
            preset_row,
            textvariable=self.provider_var,
            values=list(PROVIDER_PRESETS.keys()),
            state="readonly",
            width=40,
        )
        self.provider_combo.pack(side="left", padx=(8, 8))
        ttk.Button(preset_row, text="프리셋 적용", command=self.apply_provider_preset).pack(side="left")

        self.api_base_entry = LabeledEntry(chat_tab, "외부 VLM API Base URL (비우면 OpenAI 기본값)")
        self.api_base_entry.pack(fill="x")
        self.model_entry = LabeledEntry(chat_tab, "외부 VLM 모델명")
        self.model_entry.pack(fill="x")
        self.provider_note_var = tk.StringVar(value=PROVIDER_PRESETS["OpenAI"]["note"])
        ttk.Label(chat_tab, textvariable=self.provider_note_var, foreground="#2f4f4f").pack(anchor="w", pady=(0, 6))

        conn_row = ttk.Frame(chat_tab)
        conn_row.pack(fill="x", pady=(0, 8))
        ttk.Button(conn_row, text="VLM 설정 저장", command=self.save_config).pack(side="left")
        ttk.Button(conn_row, text="연결 상태 확인", command=self.check_vlm_connection).pack(side="left", padx=(8, 0))

        self.chat_question = tk.Text(chat_tab, height=4)
        ttk.Label(chat_tab, text="질문 입력").pack(anchor="w")
        self.chat_question.pack(fill="x")
        ttk.Button(chat_tab, text="질문 전송", command=self.ask_question).pack(anchor="w", pady=(8, 8))

        # Related item: split preview/context horizontally so both are fully visible.
        split_panel = ttk.Panedwindow(chat_tab, orient="horizontal")
        split_panel.pack(fill="both", expand=True, pady=(4, 8))

        left_frame = ttk.LabelFrame(split_panel, text="검색된 페이지 이미지 미리보기")
        right_frame = ttk.LabelFrame(split_panel, text="검색된 문맥 (Byaldi 검색 결과)")
        split_panel.add(left_frame, weight=1)
        split_panel.add(right_frame, weight=2)

        self.image_preview_label = ttk.Label(left_frame, text="이미지 없음", anchor="center")
        self.image_preview_label.pack(fill="both", expand=True, padx=6, pady=6)

        context_wrap = ttk.Frame(right_frame)
        context_wrap.pack(fill="both", expand=True)
        self.chat_context = tk.Text(context_wrap, wrap="word")
        context_scroll = ttk.Scrollbar(context_wrap, orient="vertical", command=self.chat_context.yview)
        self.chat_context.configure(yscrollcommand=context_scroll.set)
        self.chat_context.pack(side="left", fill="both", expand=True)
        context_scroll.pack(side="left", fill="y")

        self.chat_answer = tk.Text(chat_tab, height=10)
        ttk.Label(chat_tab, text="VLM 답변").pack(anchor="w", pady=(8, 0))
        self.chat_answer.pack(fill="both", expand=True)

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
        self._sync_provider_from_current_values()

    def _sync_provider_from_current_values(self) -> None:
        current_base = self.api_base_entry.get().strip().rstrip("/")
        for provider_name, preset in PROVIDER_PRESETS.items():
            preset_base = preset["base"].rstrip("/")
            if preset_base and current_base == preset_base:
                self.provider_var.set(provider_name)
                self.provider_note_var.set(preset["note"])
                return
        self.provider_var.set("직접 입력(커스텀)")
        self.provider_note_var.set(PROVIDER_PRESETS["직접 입력(커스텀)"]["note"])

    # Related item: add Google AI Studio and other external API presets.
    def apply_provider_preset(self) -> None:
        provider = self.provider_var.get()
        preset = PROVIDER_PRESETS.get(provider)
        if not preset:
            return
        if preset["base"]:
            self.api_base_entry.set(preset["base"])
        if preset["model"]:
            self.model_entry.set(preset["model"])
        self.provider_note_var.set(preset["note"])
        messagebox.showinfo("프리셋 적용", f"{provider} 설정이 적용되었습니다.")

    def _build_settings(self) -> LLMSettings:
        return LLMSettings(
            api_key=self.api_key_entry.get(),
            api_base=self.api_base_entry.get(),
            model=self.model_entry.get(),
        )

    # Related item: user chooses source folder from runtime GUI.
    def select_source_folder(self) -> None:
        folder = filedialog.askdirectory(title="원본 폴더 선택")
        if folder:
            self.source_entry.set(folder)

    def save_config(self) -> None:
        cfg = RuntimeConfig(
            source_folder=self.source_entry.get(),
            llm_api_key=self.api_key_entry.get(),
            llm_api_base=self.api_base_entry.get(),
            llm_model=self.model_entry.get(),
            index_name="colpali_byaldi",
        )
        self.config_manager.save(cfg)
        self.config = cfg
        messagebox.showinfo("저장 완료", "설정이 저장되었습니다.")

    # Related item: proactive architecture suggestion instead of blind execution.
    def show_architecture_proposal(self) -> None:
        proposal = (
            "권장 ColPali + Byaldi 구성 제안\n\n"
            "1) 인덱싱 단계(로컬 무료):\n"
            "- PDF 페이지를 이미지(PNG)로 생성 (멀티모달 인덱싱 핵심)\n"
            "- 이미 인덱싱된 파일은 자동 PASS 처리 (재처리 방지)\n"
            "- index_type=colpali_byaldi, modality=image_first로 기록\n\n"
            "2) 검색 단계(Byaldi):\n"
            "- 질문과 관련된 페이지를 우선 검색\n"
            "- 텍스트 문맥 + 페이지 이미지 경로를 함께 반환\n\n"
            "3) 생성 단계(VLM API):\n"
            "- 검색 근거(문맥+이미지)를 기준으로 외부 VLM 응답 생성\n"
        )
        messagebox.showinfo("시스템 구성 제안", proposal)

    def run_indexing(self) -> None:
        if not self.source_entry.get():
            messagebox.showwarning("확인", "원본 폴더를 선택하세요.")
            return
        self.save_config()
        threading.Thread(target=self._run_indexing_worker, daemon=True).start()

    def _run_indexing_worker(self) -> None:
        source_folder = Path(self.source_entry.get())
        try:
            manifest = build_colpali_byaldi_index(source_folder, self._on_progress)
            self.chunk_file = source_folder / "rag_chunks.jsonl"
            self._append_log(f"완료: {manifest}")
            self.status_var.set("인덱싱 완료")
            messagebox.showinfo("완료", f"인덱싱 완료\n결과: {manifest}\n이제 'VLM 대화' 탭에서 연결상태 확인 후 질의하세요.")
        except Exception as exc:  # noqa: BLE001
            self._append_log(f"오류: {exc}")
            self.status_var.set("인덱싱 실패")
            messagebox.showerror("오류", str(exc))

    def check_vlm_connection(self) -> None:
        settings = self._build_settings()
        if not settings.api_key:
            messagebox.showwarning("확인", "VLM API Key를 입력하세요.")
            return

        def _worker() -> None:
            try:
                msg = OpenAICompatibleClient(settings).check_connection()
                messagebox.showinfo("연결 상태", msg)
            except Exception as exc:  # noqa: BLE001
                messagebox.showerror("연결 실패", str(exc))

        threading.Thread(target=_worker, daemon=True).start()

    def _set_preview_image(self, image_paths: list[str]) -> None:
        if not image_paths:
            self.image_preview_label.configure(text="이미지 없음", image="")
            self.preview_photo = None
            return

        first_image = Path(image_paths[0])
        if not first_image.exists():
            self.image_preview_label.configure(text="이미지 파일을 찾을 수 없습니다.", image="")
            self.preview_photo = None
            return

        image = Image.open(first_image)
        image.thumbnail((560, 560))
        self.preview_photo = ImageTk.PhotoImage(image)
        self.image_preview_label.configure(text="", image=self.preview_photo)

    def ask_question(self) -> None:
        question = self.chat_question.get("1.0", "end").strip()
        if not question:
            messagebox.showwarning("확인", "질문을 입력하세요.")
            return

        source_folder = Path(self.source_entry.get() or self.base_dir)
        chunk_file = self.chunk_file or (source_folder / "rag_chunks.jsonl")
        chunks = load_chunks(chunk_file)
        retrieval: RetrievalResult = retrieve_context(chunks, question)

        self.chat_context.delete("1.0", "end")
        self.chat_context.insert("end", retrieval.context_text)
        self._set_preview_image(retrieval.image_paths)

        settings = self._build_settings()
        if not all([settings.api_key, settings.model]):
            messagebox.showwarning("확인", "VLM 탭에서 API Key와 모델명을 입력하세요. (Base URL은 비워도 됩니다)")
            return

        if "generativelanguage.googleapis.com" in settings.api_base and "key" in settings.model.lower():
            messagebox.showwarning("확인", "모델명 칸에 API Key가 입력된 것 같습니다. 예: gemini-2.5-flash")
            return

        def _worker() -> None:
            try:
                answer = OpenAICompatibleClient(settings).chat(question, retrieval.context_text)
                self.chat_answer.delete("1.0", "end")
                self.chat_answer.insert("end", answer)
            except Exception as exc:  # noqa: BLE001
                messagebox.showerror("VLM 호출 오류", str(exc))

        threading.Thread(target=_worker, daemon=True).start()

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
