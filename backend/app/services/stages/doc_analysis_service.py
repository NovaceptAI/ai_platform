import os, json, logging, re, statistics
from typing import Dict, Any, List, Tuple
import openai
from app.services.openai_key_manager import key_manager

log = logging.getLogger(__name__)

OPENAI_API_TYPE = "azure"
OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2023-03-15-preview")
DEFAULT_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4.1")

# Entity types we’ll encourage (but won’t strictly enforce)
ENTITY_TYPES = ["PERSON","ORG","GPE","LOC","DATE","EVENT","WORK","PRODUCT","LAW","NORP","MISC"]

class DocAnalysisService:
    """
    Page-level extraction -> doc-level aggregation.
    - Entities: [{"text":"OpenAI","type":"ORG"}...]
    - Tags: ["transformers","nlp",...]
    - Stats: length estimates etc.
    - Mind map: nodes/edges JSON for simple rendering.
    """
    def __init__(self, openai_engine: str = DEFAULT_DEPLOYMENT):
        self.openai_engine = openai_engine
        self._use_new_credentials()

    def _use_new_credentials(self):
        api_key, api_base, idx = key_manager.get_next()
        openai.api_type = OPENAI_API_TYPE
        openai.api_version = OPENAI_API_VERSION
        openai.api_key = api_key
        openai.api_base = api_base
        log.info(f"[DocAnalysis] Using Azure slot #{idx} ({api_base})")

    def _chat(self, messages, temperature=0.2, max_tokens=600, timeout=35) -> str:
        try:
            r = openai.ChatCompletion.create(
                engine=self.openai_engine,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=timeout,
            )
            return r["choices"][0]["message"]["content"].strip()
        except openai.error.RateLimitError:
            self._use_new_credentials()
            raise

    # ---------- Page-level ----------
    def analyze_page(self, text: str, tag_top_k: int = 8, entity_top_k: int = 15) -> Dict[str, Any]:
        """
        Returns: {
          "tags": [str, ...],
          "entities": [{"text":str,"type":str}, ...],
          "length": {"chars":int,"words":int, "approx_tokens":int}
        }
        """
        if not text or not text.strip():
            return {"tags": [], "entities": [], "length": {"chars": 0, "words": 0, "approx_tokens": 0}}

        # Length rough stats without LLM
        words = len(re.findall(r"\w+", text))
        chars = len(text)
        approx_tokens = int(words * 1.33)  # very rough heuristic

        prompt = (
            "From the text below, extract:\n"
            "1) up to {k1} high-signal tags (short keywords), array of strings\n"
            "2) up to {k2} named entities with types (choose from PERSON, ORG, GPE, LOC, DATE, EVENT, WORK, PRODUCT, LAW, NORP, MISC)\n"
            "Respond ONLY JSON: {{\"tags\": [...], \"entities\": [{{\"text\":\"...\",\"type\":\"...\"}}, ...]}}\n\n"
            "TEXT:\n{t}"
        ).format(k1=tag_top_k, k2=entity_top_k, t=text[:12000])

        raw = self._chat(
            [
                {"role": "system", "content": "You are a precise information extraction assistant. Output valid JSON only."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=550,
        )

        tags, entities = [], []
        try:
            data = json.loads(raw)
            tags = [str(x).strip()[:32] for x in (data.get("tags") or []) if str(x).strip()]
            ents = data.get("entities") or []
            for e in ents:
                if isinstance(e, dict):
                    t = (e.get("text") or "").strip()
                    ty = (e.get("type") or "").strip().upper()
                    if t:
                        if ty not in ENTITY_TYPES: ty = "MISC"
                        entities.append({"text": t[:120], "type": ty})
        except Exception:
            # fallback: naive keywording by most frequent words of length>=6
            freq = {}
            for w in re.findall(r"[A-Za-z][A-Za-z\-]{5,}", text):
                freq[w.lower()] = freq.get(w.lower(), 0) + 1
            tags = [w for w, _ in sorted(freq.items(), key=lambda kv: -kv[1])[:tag_top_k]]

        return {
            "tags": tags[:tag_top_k],
            "entities": entities[:entity_top_k],
            "length": {"chars": chars, "words": words, "approx_tokens": approx_tokens},
        }

    # ---------- Document aggregation ----------
    def aggregate(self, per_page: List[Tuple[int, Dict[str, Any]]]) -> Dict[str, Any]:
        """
        Input: [(page, {tags, entities, length})...]
        Output: {
          "totals": {"pages":N, "words":int, "chars":int, "approx_tokens":int},
          "top_tags":[{"tag":str,"count":int,"pages":[...]}...],
          "entities_by_type":{"PERSON":[{"text":"...", "count":N, "pages":[...]}], ...}
        }
        """
        totals = {"pages": len(per_page), "words": 0, "chars": 0, "approx_tokens": 0}
        tag_map: Dict[str, Dict[str, Any]] = {}
        ent_map: Dict[str, Dict[str, Any]] = {}  # key: (type|text).lower()

        for page, dd in per_page:
            lens = dd.get("length") or {}
            totals["words"] += int(lens.get("words", 0))
            totals["chars"] += int(lens.get("chars", 0))
            totals["approx_tokens"] += int(lens.get("approx_tokens", 0))

            # tags
            for t in dd.get("tags") or []:
                node = tag_map.get(t.lower())
                if not node:
                    tag_map[t.lower()] = {"tag": t, "count": 1, "pages": [page]}
                else:
                    node["count"] += 1
                    if page not in node["pages"]:
                        node["pages"].append(page)

            # entities
            for e in dd.get("entities") or []:
                k = f'{e.get("type","MISC").upper()}|{(e.get("text") or "").lower()}'
                node = ent_map.get(k)
                if not node:
                    ent_map[k] = {"text": e.get("text"), "type": e.get("type","MISC").upper(), "count": 1, "pages": [page]}
                else:
                    node["count"] += 1
                    if page not in node["pages"]:
                        node["pages"].append(page)

        top_tags = sorted(tag_map.values(), key=lambda x: (-x["count"], x["tag"]))[:30]
        # bucket entities by type
        by_type = {}
        for v in ent_map.values():
            by_type.setdefault(v["type"], []).append(v)
        for ty in by_type:
            by_type[ty].sort(key=lambda x: (-x["count"], x["text"]))

        return {"totals": totals, "top_tags": top_tags, "entities_by_type": by_type}

    # ---------- Mind map (on demand) ----------
    def build_mind_map(self, text_all: str) -> Dict[str, Any]:
        """
        Returns a lightweight graph for a mind map:
        { "nodes": [{"id":"Topic A"}...], "edges": [{"source":"Topic A","target":"Topic B","label":"rel"}...] }
        """
        if not text_all or not text_all.strip():
            return {"nodes": [], "edges": []}

        # NOTE: No literal {id} / {source} in the string to avoid .format() conflicts.
        prompt = (
            "Create a concise mind map of the document topics and relationships.\n"
            "Return ONLY valid JSON with keys:\n"
            '- "nodes": array of objects, each with key "id"\n'
            '- "edges": array of objects, each with keys "source", "target", and optional "label"\n'
            "Keep at most 20 nodes and 30 edges. Use short labels.\n\n"
            f"TEXT:\n{text_all[:24000]}"
        )

        raw = self._chat(
            [
                {"role": "system", "content": "You are a concept mapping assistant. Output valid JSON only."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=700,
            timeout=45,
        )

        # Robust parsing: accept strings as nodes, missing labels, etc.
        try:
            data = json.loads(raw)
        except Exception:
            return {"nodes": [], "edges": []}

        nodes_raw = data.get("nodes") or []
        edges_raw = data.get("edges") or []

        nodes = []
        for n in nodes_raw:
            if isinstance(n, dict) and n.get("id"):
                nodes.append({"id": str(n["id"])[:64]})
            elif isinstance(n, str) and n.strip():
                nodes.append({"id": n.strip()[:64]})
        nodes = nodes[:20]

        edges = []
        for e in edges_raw:
            if not isinstance(e, dict):
                continue
            s = e.get("source"); t = e.get("target"); lbl = e.get("label", "")
            if s and t:
                edges.append({
                    "source": str(s)[:64],
                    "target": str(t)[:64],
                    "label": str(lbl)[:48] if lbl is not None else ""
                })
        edges = edges[:30]

        return {"nodes": nodes, "edges": edges}
