"""Shared LLM factory — supports anthropic, groq, and openai."""
from app.config import settings


def build_llm(max_tokens: int = 1024):
    provider = settings.LLM_PROVIDER.lower()

    if provider == "groq":
        from langchain_groq import ChatGroq
        return ChatGroq(
            model=settings.LLM_MODEL,
            api_key=settings.GROQ_API_KEY,
            temperature=0.3,
            max_tokens=max_tokens,
        )

    if provider == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=settings.LLM_MODEL,
            api_key=settings.OPENAI_API_KEY,
            temperature=0.3,
            max_tokens=max_tokens,
        )

    # default: anthropic
    from langchain_anthropic import ChatAnthropic
    return ChatAnthropic(
        model=settings.LLM_MODEL,
        api_key=settings.ANTHROPIC_API_KEY,
        temperature=0.3,
        max_tokens=max_tokens,
    )
