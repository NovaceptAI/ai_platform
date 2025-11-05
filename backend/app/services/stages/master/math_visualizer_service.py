# app/services/math_visualizer_service.py
from __future__ import annotations

import io
import os
import json
import tempfile
import uuid
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

# File parsing
from PyPDF2 import PdfReader
from docx import Document

# OpenAI (Azure) via SDK + rotating key manager
import openai
from app.services.openai_key_manager import key_manager

log = logging.getLogger(__name__)

OPENAI_API_TYPE = "azure"
OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2023-03-15-preview")
DEFAULT_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4.1")


@dataclass
class MathVisualizerInput:
    method: str                          # "text" | "document"
    text: Optional[str] = None
    file_storage: Optional[FileStorage] = None
    filename: Optional[str] = None
    # options
    difficulty: Optional[str] = None     # "beginner" | "intermediate" | "advanced"
    level: Optional[str] = None          # "school" | "college" | "olympiad"
    show_hints: bool = True
    practice_count: int = 3
    visualize_types: Optional[List[str]] = None  # ["graph","geometry","number_line","flowchart"]


class MathVisualizerService:
    """
    Core logic to:
      - validate input
      - extract text from files
      - construct a deterministic prompt for Azure OpenAI
      - parse + normalize model output to a strict JSON shape

    Uses shared `key_manager` to rotate Azure OpenAI credentials across slots.
    """

    MAX_FILE_MB = 25
    ALLOWED_EXT = {".pdf", ".docx", ".txt"}

    def __init__(self, openai_engine: str = DEFAULT_DEPLOYMENT):
        self.openai_engine = openai_engine
        self._use_new_credentials()

    # ---------------- Public API ----------------
    def solve(self, mvi: MathVisualizerInput) -> Dict[str, Any]:
        self._validate(mvi)
        problem_text, meta = self._collect_text(mvi)

        prompt = self._build_prompt(
            problem_text=problem_text,
            options=dict(
                difficulty=(mvi.difficulty or "intermediate"),
                level=(mvi.level or "school"),
                show_hints=bool(mvi.show_hints),
                practice_count=int(mvi.practice_count or 3),
                visualize_types=(mvi.visualize_types or ["graph", "number_line", "geometry"]),
            ),
            meta=meta,
        )
        raw = self._call_llm(prompt, max_tokens=1500)
        raw_json = self._parse_json_or_raise(raw)
        return self._normalize(raw_json, meta)

    # ---------------- Credentials ----------------
    def _use_new_credentials(self) -> None:
        api_key, api_base, idx = key_manager.get_next()
        openai.api_type = OPENAI_API_TYPE
        openai.api_version = OPENAI_API_VERSION
        openai.api_key = api_key
        openai.api_base = api_base
        log.info(f"[MathVisualizerService] Using Azure slot #{idx} ({api_base})")

    # ---------------- LLM Call ----------------
    def _call_llm(self, prompt: str, max_tokens: int = 1200) -> str:
        try:
            resp = openai.ChatCompletion.create(
                engine=self.openai_engine,
                messages=[
                    {"role": "system", "content": "You are a helpful math tutor and visualization expert."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
                max_tokens=max_tokens,
                timeout=60,
            )
            return resp["choices"][0]["message"]["content"].strip()
        except openai.error.RateLimitError as e:
            log.warning(f"Rate limit in MathVisualizerService: {e}; rotating key.")
            self._use_new_credentials()
            raise

    def _parse_json_or_raise(self, content: str) -> Dict[str, Any]:
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            start = content.find("{")
            end = content.rfind("}")
            if start != -1 and end != -1 and end > start:
                return json.loads(content[start:end + 1])
            raise RuntimeError("Model did not return valid JSON.")

    # ---------------- Helpers ----------------
    def _validate(self, mvi: MathVisualizerInput) -> None:
        method = (mvi.method or "").strip().lower()
        if method not in {"text", "document"}:
            raise ValueError("Invalid method. Use 'text' or 'document'.")

        if method == "text":
            if not (mvi.text and len(mvi.text.strip()) >= 5):
                raise ValueError("Provide a math problem (min 5 characters).")

        if method == "document":
            if not mvi.file_storage:
                raise ValueError("Please upload a document.")
            # size
            mvi.file_storage.stream.seek(0, io.SEEK_END)
            size = mvi.file_storage.stream.tell()
            mvi.file_storage.stream.seek(0)
            if size > self.MAX_FILE_MB * 1024 * 1024:
                raise ValueError(f"File too large (max {self.MAX_FILE_MB}MB).")
            # ext
            fn = mvi.filename or mvi.file_storage.filename or ""
            ext = os.path.splitext(fn)[1].lower()
            if ext not in self.ALLOWED_EXT:
                raise ValueError(f"Unsupported file type '{ext}'. Allowed: {', '.join(sorted(self.ALLOWED_EXT))}")

        # clamp practice_count
        if mvi.practice_count is None:
            mvi.practice_count = 3
        mvi.practice_count = max(0, min(int(mvi.practice_count), 10))

    def _collect_text(self, mvi: MathVisualizerInput) -> Tuple[str, Dict[str, Any]]:
        method = mvi.method.strip().lower()
        if method == "text":
            t = mvi.text.strip()
            return t, {"method": "text", "length": len(t)}

        # document path
        fs = mvi.file_storage
        filename = secure_filename(mvi.filename or fs.filename or f"upload-{uuid.uuid4().hex}")
        ext = os.path.splitext(filename)[1].lower()

        with tempfile.NamedTemporaryFile(prefix="mpv_", suffix=ext, delete=False) as tmp:
            file_path = tmp.name
            fs.save(file_path)

        try:
            if ext == ".pdf":
                extracted = self._extract_pdf(file_path)
            elif ext == ".docx":
                extracted = self._extract_docx(file_path)
            else:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    extracted = f.read()

            extracted = (extracted or "").strip()
            if not extracted:
                raise ValueError("Could not extract text from the uploaded file.")

            return extracted, {"method": "document", "filename": filename}
        finally:
            try:
                os.remove(file_path)
            except Exception:
                pass

    def _extract_pdf(self, path: str) -> str:
        reader = PdfReader(path)
        chunks = []
        for page in reader.pages:
            txt = page.extract_text() or ""
            if txt.strip():
                chunks.append(txt)
        return "\n".join(chunks)

    def _extract_docx(self, path: str) -> str:
        doc = Document(path)
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())

    def _build_prompt(self, problem_text: str, options: Dict[str, Any], meta: Dict[str, Any]) -> str:
        visualize_types = options.get("visualize_types", [])
        practice_count = int(options.get("practice_count", 3))
        level = options.get("level", "school")
        difficulty = options.get("difficulty", "intermediate")

        return f"""
        You are a math expert and visualization designer. Solve the problem and produce VISUAL-FIRST artifacts.

        INPUT PROBLEM (verbatim):
        ---
        {problem_text[:120000]}
        ---

        CONSTRAINTS & PREFERENCES:
        - Target level: "{level}"   | Difficulty: "{difficulty}"
        - Visualize types (try to include where applicable): {visualize_types}
        - Provide hints before full details where possible.
        - Keep JSON strictly valid (NO markdown). No trailing commas.

        RETURN STRICT JSON WITH EXACT SHAPE:

        {{
        "problem": "string (original or clarified)",
        "interpretation": "short explanation of what is being asked",
        "final_answer": "concise answer in simplest form",
        "checks": ["quick verification(s) a student can run"],
        "formulas": ["list key formulas used, LaTeX allowed"],
        "steps": [
            {{
            "id": 1,
            "title": "short step title",
            "hint": "one-sentence hint",
            "detail": "3-6 sentence explanation; use LaTeX where appropriate, keep <= 120 words",
            "formula": "optional formula used in this step (LaTeX or plain)"
            }}
        ],
        "diagrams": [
            {{
            "type": "graph" | "geometry" | "number_line" | "flowchart",
            "title": "short title",
            "svg": "OPTIONAL: an inline <svg>...</svg> with simple shapes only",
            "plot": {{
                "x": [numbers], "y": [numbers],
                "series_label": "optional label",
                "x_label": "string", "y_label": "string"
            }}
            }}
        ],
        "alternates": ["briefly describe other possible solving methods"],
        "practice": [
            {{
            "question": "new practice problem",
            "answer": "short answer",
            "difficulty": "beginner|intermediate|advanced"
            }}
        ],
        "latex": {{
            "problem": "LaTeX form of problem if helpful",
            "answer": "LaTeX form of final answer if helpful"
        }}
        }}

        RULES:
        - Include 4–8 steps typically (can be fewer for trivial problems).
        - If a graph helps (linear/quadratic/inequality/trig), include a 'graph' diagram with numeric arrays in 'plot'.
        - If geometry, include a minimal 'geometry' svg (lines/circles/polylines; no external fonts).
        - For number_line inequalities/intervals, include 'number_line' svg or a 'plot' with x-only.
        - Keep everything compact and classroom-ready.
        """.strip()

    def _normalize(self, raw: Dict[str, Any], meta: Dict[str, Any]) -> Dict[str, Any]:
        def s(v, default=""):
            return (v or default) if isinstance(v, str) else default

        out: Dict[str, Any] = {
            "problem": s(raw.get("problem")),
            "interpretation": s(raw.get("interpretation")),
            "final_answer": s(raw.get("final_answer")),
            "checks": list(raw.get("checks") or [])[:5],
            "formulas": list(raw.get("formulas") or [])[:12],
            "steps": [],
            "diagrams": [],
            "alternates": list(raw.get("alternates") or [])[:5],
            "practice": [],
            "latex": {
                "problem": s(raw.get("latex", {}).get("problem")),
                "answer": s(raw.get("latex", {}).get("answer")),
            },
            "meta": meta,
        }

        steps = raw.get("steps") or []
        for i, st in enumerate(steps, start=1):
            out["steps"].append({
                "id": int(st.get("id") or i),
                "title": s(st.get("title"), f"Step {i}"),
                "hint": s(st.get("hint")),
                "detail": s(st.get("detail")),
                "formula": s(st.get("formula")),
            })

        diags = raw.get("diagrams") or []
        for d in diags[:6]:
            typ = s(d.get("type"))
            # normalize plot arrays
            plot = d.get("plot") or {}
            px = plot.get("x") or []
            py = plot.get("y") or []
            # sanitize numeric arrays
            px = [float(x) for x in px if isinstance(x, (int, float))]
            py = [float(y) for y in py if isinstance(y, (int, float))]
            out["diagrams"].append({
                "type": typ,
                "title": s(d.get("title")),
                "svg": s(d.get("svg")),
                "plot": {
                    "x": px,
                    "y": py,
                    "series_label": s(plot.get("series_label")),
                    "x_label": s(plot.get("x_label")),
                    "y_label": s(plot.get("y_label")),
                } if (px or py) else None,
            })

        practice = raw.get("practice") or []
        for p in practice[:10]:
            out["practice"].append({
                "question": s(p.get("question")),
                "answer": s(p.get("answer")),
                "difficulty": s(p.get("difficulty")),
            })

        return out
