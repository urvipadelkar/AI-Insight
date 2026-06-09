"""Abstract base class for LLM providers"""
from abc import ABC, abstractmethod
import json
import re

class LLMProvider(ABC):
    """Abstract base for all LLM providers"""

    @abstractmethod
    def analyze_dataset(self,
                       profiles_json: str,
                       sample_data: str,
                       user_context: str = None,
                       include_sample_data: bool = True) -> str:
        """
        Analyze dataset and return dashboard configuration suggestion.

        Args:
            profiles_json: JSON of column profiles
            sample_data: First 5 rows as formatted string
            user_context: Optional user hints about data
            include_sample_data: Whether to include actual row data in prompt

        Returns:
            JSON string with dashboard config suggestion
        """
        pass

    def generate_text(self, prompt: str) -> str:
        """Send a raw prompt and return plain text response.
        Override in subclasses for direct (non-templated) generation.
        Default falls back to analyze_dataset with the prompt as profiles_json.
        """
        return self.analyze_dataset(prompt, "", "")

    def extract_json_response(self, response: str) -> dict:
        """Parse JSON from LLM response"""
        try:
            # Try to extract JSON block from response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except json.JSONDecodeError:
                    pass

            # Try direct parsing
            return json.loads(response)
        except:
            return {}
