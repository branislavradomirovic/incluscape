import os
import json
import time
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from typing import Dict, List, Optional

class HRBAMatcherLLM:
    """Matches text to AAAQ indicators using local Ollama LLM."""

    def __init__(self):
        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.model = os.getenv("OLLAMA_MODEL", "qwen2.5:14b-instruct")
        # Ollama local generate endpoint
        self.api_endpoint = f"{self.base_url}/api/generate"

    def _call_ollama(self, prompt: str, stream: bool = False, on_progress=None) -> Optional[Dict]:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": bool(stream),
            "format": "json",
        }

        # session with retries/backoff to handle transient timeouts
        session = requests.Session()
        retries = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
        session.mount("http://", HTTPAdapter(max_retries=retries))
        session.mount("https://", HTTPAdapter(max_retries=retries))

        try:
            timeout_seconds = int(os.getenv("OLLAMA_TIMEOUT", "120"))
        except Exception:
            timeout_seconds = 120

        start_ts = time.time()
        try:
            if stream:
                with session.post(self.api_endpoint, json=payload, stream=True, timeout=timeout_seconds) as resp:
                    resp.raise_for_status()
                    response_text = ""
                    start_time = time.time()
                    for raw in resp.iter_lines(decode_unicode=True):
                        if not raw:
                            continue
                        line = raw.strip()
                        try:
                            obj = json.loads(line)
                        except Exception:
                            response_text += line
                            obj = None

                        if obj is not None:
                            part = None
                            for k in ("response", "content", "text", "generated_text", "output"):
                                if k in obj and isinstance(obj[k], str):
                                    part = obj[k]
                                    break
                            if part:
                                response_text += part
                                # emit a progress chunk if callback provided
                                try:
                                    if callable(on_progress):
                                        on_progress(part, obj, time.time() - start_time, False)
                                except Exception:
                                    pass
                            if obj.get("done"):
                                # indicate done chunk
                                try:
                                    if callable(on_progress):
                                        on_progress(None, obj, time.time() - start_time, True)
                                except Exception:
                                    pass
                                break

                        if time.time() - start_time > timeout_seconds:
                            print(f"Ollama: streaming exceeded timeout {timeout_seconds}s")
                            return {"error": "stream_timeout", "raw": response_text, "__elapsed_seconds": time.time() - start_time}

                    s = response_text.find("{")
                    e = response_text.rfind("}")
                    if s != -1 and e != -1 and e > s:
                        try:
                            data = json.loads(response_text[s : e + 1])
                            data["__elapsed_seconds"] = time.time() - start_time
                            # final parsed object - emit final progress
                            try:
                                if callable(on_progress):
                                    on_progress(None, data, time.time() - start_time, True)
                            except Exception:
                                pass
                            return data
                        except Exception:
                            return {"error": "failed_to_parse_stream", "raw": response_text}
                    return {"error": "no_json_in_stream", "raw": response_text}

            # non-streaming path
            resp = session.post(self.api_endpoint, json=payload, timeout=timeout_seconds)
            resp.raise_for_status()
            try:
                data = resp.json()
            except Exception:
                data = None

            candidate = None
            if isinstance(data, dict):
                for key in ("response", "content", "text", "generated_text", "output"):
                    if key in data and isinstance(data[key], (str, dict)):
                        candidate = data[key]
                        break

            if candidate is None:
                candidate = resp.text

            if isinstance(candidate, dict):
                result_obj = candidate
            else:
                try:
                    result_obj = json.loads(candidate) if candidate else data
                except Exception:
                    result_obj = None
                    if isinstance(candidate, str):
                        start = candidate.find("{")
                        end = candidate.rfind("}")
                        if start != -1 and end != -1 and end > start:
                            try:
                                result_obj = json.loads(candidate[start : end + 1])
                            except Exception:
                                result_obj = None

            duration = time.time() - start_ts
            if isinstance(result_obj, dict):
                result_obj["ollama_duration"] = duration
                # non-stream final callback
                try:
                    if callable(on_progress):
                        on_progress(None, result_obj, duration, True)
                except Exception:
                    pass
            return result_obj

        except requests.exceptions.Timeout:
            print(f"Ollama Error: request to {self.api_endpoint} timed out after {timeout_seconds}s")
            return None
        except requests.exceptions.RequestException as e:
            print(f"Ollama Error: {e}")
            return None

    def analyze_document_segment(self, text_segment: str, on_progress=None) -> Dict:
        prompt = f"""
You are an expert in Human Rights Based Approach (HRBA). Analyze the following text and score it
for Availability, Accessibility, Acceptability, and Quality (AAAQ).

Return ONLY a JSON object with numeric scores between 0.0 and 1.0 for keys:
  availability, accessibility, acceptability, quality
Also include a 'justification' key with 1-2 sentence explanation for the highest score.
Write the 'justification' value in Serbian (Latin script).

Text: """ + text_segment + """\n
Provide the JSON object and nothing else.
"""

        # Prefer streaming to receive partial/early JSON where supported
        result = self._call_ollama(prompt, stream=True, on_progress=on_progress)
        if not result:
            return {"error": "processing_failed"}

        # Basic validation: ensure required keys
        keys = ["availability", "accessibility", "acceptability", "quality"]
        if all(k in result for k in keys):
            # attach elapsed seconds when available
            elapsed = result.get("__elapsed_seconds")
            if elapsed:
                result["elapsed_seconds"] = float(elapsed)
            return result

        # If keys are nested or differently named, attempt to normalize
        normalized = {}
        for k in keys:
            if k in result:
                normalized[k] = result[k]
            else:
                # try uppercase variants
                normalized[k] = result.get(k.capitalize(), 0.0)

        justification = result.get("justification") or result.get("reason") or result.get("explanation")
        normalized["justification"] = justification
        return normalized

    def get_hrba_summary(self, text_list: List[str], on_progress=None) -> List[Dict]:
        processed = []
        total = len(text_list)
        for idx, seg in enumerate(text_list):
            if len(seg.strip()) > 50:
                # wrap on_progress to include segment index/total if provided
                wrapped = None
                if callable(on_progress):
                    def make_wrapper(i, t, cb):
                        def _w(part, obj, elapsed, done):
                            try:
                                cb(i, t, part, obj, elapsed, done)
                            except Exception:
                                pass
                        return _w
                    wrapped = make_wrapper(idx, total, on_progress)

                analysis = self.analyze_document_segment(seg, on_progress=wrapped)
                if not isinstance(analysis, dict):
                    analysis = {"error": "invalid_response"}
                analysis["original_text"] = (seg[:200] + "...") if len(seg) > 200 else seg
                processed.append(analysis)

        return processed
