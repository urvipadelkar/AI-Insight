"""LMStudio local inference provider (PRIMARY)"""
import requests
import json
from llm.base_provider import LLMProvider
from llm.prompts import DATASET_ANALYSIS_PROMPT

class LMStudioProvider(LLMProvider):
    """LMStudio local inference (Llama, Mistral, etc.)"""

    def __init__(self, base_url: str = "http://localhost:1234/v1",
                 model: str = "local-model"):
        self.base_url = base_url
        self.model = model
        self.timeout = 180  # Increased from 60s for local model inference

    def analyze_dataset(self, profiles_json: str, sample_data: str,
                       user_context: str = None,
                       include_sample_data: bool = True) -> str:
        """Send analysis request to LMStudio"""

        prompt = self._build_prompt(
            profiles_json,
            sample_data if include_sample_data else "",
            user_context
        )

        try:
            print(f"[INFO] Calling LMStudio at {self.base_url}...")

            response = requests.post(
                f"{self.base_url}/chat/completions",
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.7,
                    "max_tokens": 800,  # Reduced from 4000 for faster local inference
                },
                timeout=self.timeout
            )
            response.raise_for_status()

            data = response.json()
            content = data['choices'][0]['message']['content']
            print("[OK] LMStudio response received")
            return content

        except requests.exceptions.ConnectionError:
            print("[ERROR] Cannot connect to LMStudio. Make sure it's running on localhost:1234")
            return "{}"
        except requests.exceptions.Timeout:
            print(f"[ERROR] LMStudio request timed out after {self.timeout}s")
            return "{}"
        except Exception as e:
            print(f"[ERROR] LMStudio error: {e}")
            return "{}"

    def generate_text(self, prompt: str) -> str:
        """Send a raw prompt directly without template wrapping"""
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.3,
                    "max_tokens": 300,
                },
                timeout=60,
            )
            response.raise_for_status()
            return response.json()['choices'][0]['message']['content'].strip()
        except Exception as e:
            print(f"[WARN] LMStudio generate_text failed: {e}")
            return ""

    def _build_prompt(self, profiles_json: str, sample_data: str,
                     context: str = None) -> str:
        """Build analysis prompt"""
        return DATASET_ANALYSIS_PROMPT.format(
            column_profiles=profiles_json,
            sample_data=sample_data,
            context=context or "No additional context provided"
        )
