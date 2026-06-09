"""Ollama local/remote inference provider"""
import requests
import json
from llm.base_provider import LLMProvider
from llm.prompts import DATASET_ANALYSIS_PROMPT

class OllamaProvider(LLMProvider):
    """Ollama inference (supports local and remote servers)"""

    def __init__(self, base_url: str = "http://localhost:11434",
                 model: str = "qwen2.5-coder"):
        self.base_url = base_url
        self.model = model
        self.timeout = 300  # Ollama remote inference can be slower (5 minutes)

    def analyze_dataset(self, profiles_json: str, sample_data: str,
                       user_context: str = None,
                       include_sample_data: bool = True) -> str:
        """Send analysis request to Ollama (native /api/generate endpoint)"""

        prompt = self._build_prompt(
            profiles_json,
            sample_data if include_sample_data else "",
            user_context
        )

        try:
            print(f"[INFO] Calling Ollama at {self.base_url}...")
            print(f"[INFO] Using model: {self.model}")

            # Quick connectivity test first (10 second timeout)
            print(f"[INFO] Testing connectivity (10s timeout)...")
            try:
                test_response = requests.get(f"{self.base_url}/api/tags", timeout=10)
                test_response.raise_for_status()
                print(f"[OK] Ollama server is responding")
            except (TimeoutError, ConnectionError, requests.exceptions.RequestException) as test_err:
                print(f"[ERROR] Ollama server not responding: {type(test_err).__name__}")
                return "{}"

            print(f"[INFO] Sending analysis request (timeout: {self.timeout}s)...")

            # Use native Ollama API endpoint (more reliable)
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "temperature": 0.7,
                    "top_k": 40,
                    "top_p": 0.9,
                    "stream": False,
                },
                timeout=self.timeout
            )

            print(f"[DEBUG] Response status: {response.status_code}")
            response.raise_for_status()

            data = response.json()
            content = data.get('response', '')
            print("[OK] Ollama response received")
            return content

        except (requests.exceptions.ConnectionError, ConnectionError) as e:
            print(f"[ERROR] Cannot connect to Ollama at {self.base_url}")
            print(f"[ERROR] Details: {type(e).__name__}")
            return "{}"
        except (requests.exceptions.Timeout, TimeoutError) as e:
            print(f"[ERROR] Ollama request timed out after {self.timeout}s")
            print(f"[ERROR] This may mean:")
            print(f"  1. The model '{self.model}' needs to be loaded on the Ollama server")
            print(f"  2. The Ollama server is busy/slow")
            print(f"  3. Network latency is high")
            print(f"[TIP] Try using a local Ollama instance or another LLM provider")
            return "{}"
        except requests.exceptions.HTTPError as e:
            try:
                print(f"[ERROR] HTTP Error: {response.status_code}")
                print(f"[ERROR] Response: {response.text[:500]}")
            except:
                print(f"[ERROR] HTTP Error: {e}")
            return "{}"
        except Exception as e:
            print(f"[ERROR] Ollama error: {type(e).__name__}: {str(e)[:100]}")
            return "{}"

    def generate_text(self, prompt: str) -> str:
        """Send a raw prompt directly to Ollama without template wrapping"""
        try:
            test_response = requests.get(f"{self.base_url}/api/tags", timeout=10)
            test_response.raise_for_status()
        except Exception:
            return ""

        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "temperature": 0.3,
                    "stream": False,
                },
                timeout=60,
            )
            response.raise_for_status()
            return response.json().get('response', '').strip()
        except Exception as e:
            print(f"[WARN] Ollama generate_text failed: {e}")
            return ""

    def _build_prompt(self, profiles_json: str, sample_data: str,
                     context: str = None) -> str:
        """Build analysis prompt"""
        return DATASET_ANALYSIS_PROMPT.format(
            column_profiles=profiles_json,
            sample_data=sample_data,
            context=context or "No additional context provided"
        )
