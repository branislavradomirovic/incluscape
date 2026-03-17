from config import Config
from document_processing.semantic_comparison.gemini_analyzer import GeminiSemanticAnalyzer
from document_processing.semantic_comparison.ollama_analyzer import OllamaSemanticAnalyzer


def get_semantic_analyzer():
    provider = Config.SEMANTIC_LLM_PROVIDER.lower()
    if provider == "gemini":
        return GeminiSemanticAnalyzer()
    if provider == "ollama":
        return OllamaSemanticAnalyzer()
    raise ValueError(
        f"Unsupported SEMANTIC_LLM_PROVIDER='{Config.SEMANTIC_LLM_PROVIDER}'. "
        "Use 'gemini' or 'ollama'."
    )
