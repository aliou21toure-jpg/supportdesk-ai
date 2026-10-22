from app.ai.anthropic_provider import AnthropicProvider
from app.ai.base import TriageProvider
from app.ai.rules_provider import RulesProvider
from app.config import Settings


def build_provider(settings: Settings) -> TriageProvider:
    use_anthropic = settings.ai_provider == "anthropic" or (
        settings.ai_provider == "auto" and bool(settings.anthropic_api_key)
    )
    if not use_anthropic:
        return RulesProvider()

    import anthropic  # imported lazily so the rules engine works without the SDK configured

    if not settings.anthropic_api_key:
        raise RuntimeError("AI_PROVIDER=anthropic but ANTHROPIC_API_KEY is empty")
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key, max_retries=2, timeout=30.0)
    return AnthropicProvider(client, settings.ai_model)
