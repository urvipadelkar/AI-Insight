"""Claude API provider (FALLBACK)"""
from llm.base_provider import LLMProvider
from llm.prompts import DATASET_ANALYSIS_PROMPT

class ClaudeProvider(LLMProvider):
    """Claude API provider (fallback if LMStudio unavailable)"""

    def __init__(self, api_key: str = None, model: str = "claude-3-5-sonnet-20241022"):
        try:
            from anthropic import Anthropic
            self.client = Anthropic(api_key=api_key)
            self.model = model
        except ImportError:
            print("[WARN] anthropic package not installed. Claude fallback unavailable.")
            self.client = None

    def analyze_dataset(self, profiles_json: str, sample_data: str,
                       user_context: str = None,
                       include_sample_data: bool = True) -> str:
        """Send to Claude API"""

        if not self.client:
            print("[ERROR] Claude client not initialized")
            return "{}"

        prompt = self._build_prompt(
            profiles_json,
            sample_data if include_sample_data else "",
            user_context
        )

        try:
            print("[INFO] Calling Claude API...")

            response = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}]
            )

            content = response.content[0].text
            print("[OK] Claude response received")
            return content

        except Exception as e:
            print(f"[ERROR] Claude API error: {e}")
            return "{}"

    def generate_text(self, prompt: str) -> str:
        """Send a raw prompt directly without template wrapping"""
        if not self.client:
            return ""
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=300,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text.strip()
        except Exception as e:
            print(f"[WARN] Claude generate_text failed: {e}")
            return ""

    def _build_prompt(self, profiles_json: str, sample_data: str,
                     context: str = None) -> str:
        """Build analysis prompt"""
        return DATASET_ANALYSIS_PROMPT.format(
            column_profiles=profiles_json,
            sample_data=sample_data,
            context=context or "No additional context provided"
        )
