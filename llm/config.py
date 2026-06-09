"""LLM configuration and factory"""
from dataclasses import dataclass
from typing import Optional

@dataclass
class LLMConfig:
    """LLM provider configuration"""
    provider: str              # 'lmstudio', 'claude'
    model_name: str
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    include_sample_data: bool = True
    temperature: float = 0.7
    max_tokens: int = 4000

class LLMFactory:
    """Factory for creating LLM providers"""

    @staticmethod
    def create(config: LLMConfig):
        """Create LLM provider based on config"""
        if config.provider == 'lmstudio':
            from llm.lmstudio_provider import LMStudioProvider
            return LMStudioProvider(
                base_url=config.base_url or "http://localhost:1234/v1",
                model=config.model_name
            )
        elif config.provider == 'ollama':
            from llm.ollama_provider import OllamaProvider
            return OllamaProvider(
                base_url=config.base_url or "http://localhost:11434",
                model=config.model_name
            )
        elif config.provider == 'claude':
            from llm.claude_provider import ClaudeProvider
            return ClaudeProvider(
                api_key=config.api_key,
                model=config.model_name
            )
        else:
            raise ValueError(f"Unknown provider: {config.provider}")

# Default configuration - Ollama as primary (remote high-end machine)
DEFAULT_CONFIG = LLMConfig(
    provider='ollama',
    model_name='qwen2.5-coder:14b',
    base_url='http://ollama.osourceglobal.com:11434',
    include_sample_data=True
)
