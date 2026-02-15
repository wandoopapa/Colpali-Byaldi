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
# * '설치 GUI'
# - 라이브러리가 설치되는 과정을 검은색 CMD 창이 아닌, '설치 GUI' 로딩 창(Progress Bar)으로 표현
# - 모든 설치 과정은 항목 별로 총 작업량 대비 현재 작업량을 퍼센티지화 하여 진척률을 확인할 수 있는 시각적 이미지 적용
# - 설치 진행률은 전체 항목과 현재 항목을 구분하여 Progress Bar 를 각각 적용
# - 설치 폴더를 '설치 GUI' 안의 버튼을 이용하여 사용자가 지정
# - 결과 파일은 지정 된 설치 폴더에 하위폴더 없이 저장
# * 실행 GUI
# - PDF 변환이 진행되는 과정을 검은색 CMD 창이 아닌, '실행 GUI' 로딩 창(Progress Bar)으로 표현
# - PDF 파일 업로드는 '실행 GUI' 안의 버튼을 이용하여 사용자가 적용
# - 작업 과정은 항목 별로 총 작업량 대비 현재 작업량을 퍼센티지화 하여 진척률을 확인할 수 있는 시각적 이미지 적용
# - 작업 진행률은 전체 항목과 현재 항목을 구분하여 Progress Bar 를 각각 적용
# - 원본 파일을 불러오는 폴더를 '실행 GUI' 상에서 사용자가 지정
# - 프로그램을 제작하는 과정에서 누적된 패치 및 업데이트 사항에 대한 모든 내용을 누락없이 표시 (시스템 개발 역사 페이지는 버전별로 폴더형식으로 눌러서 열어볼 수 있또록 누락없이 모든 내용 기입,핵심 요약이 아니라 관련 내용이 자세하게 기입

from __future__ import annotations

import shutil
import subprocess
import sys
import threading
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk


# Related item: split roles by file, copied from templates in one folder.
TEMPLATE_FILES = [
    "run_gui.pyw",
    "pipeline.py",
    "config_manager.py",
    "history_manager.py",
    "ui_components.py",
    "llm_client.py",
    "requirements_runtime.txt",
    "HISTORY_VERSIONS.json",
]

# Related item: free + quality defaults for GPU environment.
PACKAGE_LIST = [
    "pip",
    "setuptools",
    "wheel",
    "pypdf",
    "pypdfium2",
    "pillow",
    "requests",
    "torch",
    "transformers",
    "byaldi",
]


class InstallerGUI(tk.Tk):
    # Related item: installer GUI is the only entry-point for end users.
    def __init__(self) -> None:
        super().__init__()
        self.title("ColPali + Byaldi 설치 도우미")
        self.geometry("780x520")
        self.resizable(False, False)

        self.base_dir = Path(__file__).resolve().parent
        self.target_dir = tk.StringVar(value=str(self.base_dir))
        self.status_var = tk.StringVar(value="설치 대기 중")
        self.current_step_var = tk.StringVar(value="현재 작업: 없음")

        self.overall_progress = tk.DoubleVar(value=0.0)
        self.step_progress = tk.DoubleVar(value=0.0)

        self._build_ui()

    def _build_ui(self) -> None:
        frm = ttk.Frame(self, padding=16)
        frm.pack(fill="both", expand=True)

        ttk.Label(frm, text="설치 폴더", font=("Malgun Gothic", 11, "bold")).pack(anchor="w")
        path_row = ttk.Frame(frm)
        path_row.pack(fill="x", pady=(8, 12))
        ttk.Entry(path_row, textvariable=self.target_dir).pack(side="left", fill="x", expand=True)
        ttk.Button(path_row, text="폴더 선택", command=self.choose_folder).pack(side="left", padx=(8, 0))

        ttk.Label(frm, textvariable=self.status_var).pack(anchor="w", pady=(4, 4))
        ttk.Label(frm, textvariable=self.current_step_var, foreground="#2f4f4f").pack(anchor="w")

        ttk.Label(frm, text="전체 진행률").pack(anchor="w", pady=(14, 4))
        ttk.Progressbar(frm, variable=self.overall_progress, maximum=100).pack(fill="x")

        ttk.Label(frm, text="현재 항목 진행률").pack(anchor="w", pady=(14, 4))
        ttk.Progressbar(frm, variable=self.step_progress, maximum=100).pack(fill="x")

        self.log_box = tk.Text(frm, height=14, wrap="word")
        self.log_box.pack(fill="both", expand=True, pady=(14, 0))

        ttk.Button(frm, text="원클릭 설치 시작", command=self.start_installation).pack(fill="x", pady=(12, 0))

    def choose_folder(self) -> None:
        folder = filedialog.askdirectory(title="설치 폴더 선택")
        if folder:
            self.target_dir.set(folder)

    def start_installation(self) -> None:
        target = Path(self.target_dir.get()).expanduser().resolve()
        target.mkdir(parents=True, exist_ok=True)
        threading.Thread(target=self._run_installation, daemon=True).start()

    def _run_installation(self) -> None:
        try:
            target = Path(self.target_dir.get()).expanduser().resolve()
            self._set_status("설치 준비 중")
            steps = ["폴더 준비", "파일 복사", "라이브러리 설치", "완료 처리"]

            for idx, step in enumerate(steps, start=1):
                self._set_current_step(step)
                self._set_step(5)
                if step == "폴더 준비":
                    target.mkdir(parents=True, exist_ok=True)
                    self._log(f"설치 폴더 준비 완료: {target}")
                    self._set_step(100)
                elif step == "파일 복사":
                    self._copy_files(target)
                elif step == "라이브러리 설치":
                    self._install_packages(target)
                elif step == "완료 처리":
                    self._write_bootstrap_note(target)
                    self._set_step(100)

                self._set_overall((idx / len(steps)) * 100)

            self._set_status("설치 완료")
            messagebox.showinfo("완료", "설치가 완료되었습니다. 설치 폴더의 run_gui.pyw를 실행하세요.")
        except Exception as exc:  # noqa: BLE001
            self._set_status("설치 실패")
            self._log(f"오류: {exc}")
            messagebox.showerror("오류", f"설치 중 문제가 발생했습니다:\n{exc}")

    def _copy_files(self, target: Path) -> None:
        template_dir = self.base_dir / "app_templates"
        total = len(TEMPLATE_FILES)
        for i, file_name in enumerate(TEMPLATE_FILES, start=1):
            shutil.copy2(template_dir / file_name, target / file_name)
            self._log(f"파일 생성/복사 완료: {file_name}")
            self._set_step((i / total) * 100)

    def _install_packages(self, target: Path) -> None:
        total = len(PACKAGE_LIST)
        for i, package in enumerate(PACKAGE_LIST, start=1):
            self._log(f"패키지 설치 시작: {package}")
            self._set_step(((i - 1) / total) * 100)
            cmd = [sys.executable, "-m", "pip", "install", "--upgrade", package]
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=target)
            if result.returncode != 0:
                raise RuntimeError(f"{package} 설치 실패\n{result.stderr}")
            self._set_step((i / total) * 100)
            self._log(f"패키지 설치 완료: {package}")

    def _write_bootstrap_note(self, target: Path) -> None:
        note = target / "INSTALL_DONE.txt"
        note.write_text(
            "설치가 완료되었습니다.\n"
            "실행 방법: run_gui.pyw 더블클릭\n"
            "권장 GPU: RTX 2080 SUPER 이상\n"
            "권장 모델: vidore/colqwen2.5-v0.2 (무료 공개 모델)\n",
            encoding="utf-8",
        )
        self._log("INSTALL_DONE.txt 작성 완료")

    def _set_status(self, text: str) -> None:
        self.status_var.set(text)

    def _set_current_step(self, text: str) -> None:
        self.current_step_var.set(f"현재 작업: {text}")

    def _set_overall(self, value: float) -> None:
        self.overall_progress.set(value)

    def _set_step(self, value: float) -> None:
        self.step_progress.set(value)

    def _log(self, text: str) -> None:
        self.log_box.insert("end", text + "\n")
        self.log_box.see("end")


if __name__ == "__main__":
    InstallerGUI().mainloop()
