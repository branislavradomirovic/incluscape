import os
import json
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

    def _call_ollama(self, prompt: str) -> Optional[Dict]:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
        }

        # session with retries/backoff to handle transient timeouts
        session = requests.Session()
        retries = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
        session.mount("http://", HTTPAdapter(max_retries=retries))
        session.mount("https://", HTTPAdapter(max_retries=retries))

        try:
            resp = session.post(self.api_endpoint, json=payload, timeout=60)
            resp.raise_for_status()
            data = resp.json()

            # Ollama responses vary by version; try common fields that may contain text
            candidate = None
            if isinstance(data, dict):
                for key in ("response", "content", "text", "generated_text", "output"):
                    if key in data and isinstance(data[key], (str, dict)):
                        candidate = data[key]
                        break

            if candidate is None:
                candidate = resp.text

            if isinstance(candidate, dict):
                return candidate

            try:
                return json.loads(candidate)
            except Exception:
                start = candidate.find("{")
                end = candidate.rfind("}")
                if start != -1 and end != -1 and end > start:
                    try:
                        return json.loads(candidate[start : end + 1])
                    except Exception:
                        print("Ollama: failed to parse JSON from response text")
                        return None
                print("Ollama: no JSON found in response")
                return None

        except requests.exceptions.Timeout:
            print(f"Ollama Error: request to {self.api_endpoint} timed out")
            return None
        except requests.exceptions.RequestException as e:
            print(f"Ollama Error: {e}")
            return None

    def analyze_document_segment(self, text_segment: str) -> Dict:
        prompt = f"""
You are an expert in Human Rights Based Approach (HRBA). Analyze the following text and score it
for Availability, Accessibility, Acceptability, and Quality (AAAQ).

Return ONLY a JSON object with numeric scores between 0.0 and 1.0 for keys:
  availability, accessibility, acceptability, quality
Also include a 'justification' key with 1-2 sentence explanation for the highest score.

Text: """ + text_segment + """\n
Provide the JSON object and nothing else.
"""

        result = self._call_ollama(prompt)
        if not result:
            return {"error": "processing_failed"}

        # Basic validation: ensure required keys
        keys = ["availability", "accessibility", "acceptability", "quality"]
        if all(k in result for k in keys):
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

    def get_hrba_summary(self, text_list: List[str]) -> List[Dict]:
        processed = []
        for seg in text_list:
            if len(seg.strip()) > 50:
                analysis = self.analyze_document_segment(seg)
                if not isinstance(analysis, dict):
                    analysis = {"error": "invalid_response"}
                analysis["original_text"] = (seg[:200] + "...") if len(seg) > 200 else seg
                processed.append(analysis)

        return processed
