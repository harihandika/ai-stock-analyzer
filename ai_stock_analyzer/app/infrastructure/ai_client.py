"""Anthropic failures are failures, never synthetic investment recommendations."""

import json

from anthropic import APIError, APITimeoutError, AsyncAnthropic

from app.core.config import settings
from app.core.errors import AnalysisError


async def call_claude_sonnet(system_prompt: str, user_prompt: str) -> dict:
    if not settings.ANTHROPIC_API_KEY or settings.ANTHROPIC_API_KEY == "mock-key-for-testing":
        raise AnalysisError("AI_NOT_CONFIGURED", "Layanan AI belum dikonfigurasi.", status=503)
    try:
        async with AsyncAnthropic(
            api_key=settings.ANTHROPIC_API_KEY, timeout=60, max_retries=0
        ) as client:
            response = await client.messages.create(
                model=settings.AI_MODEL_OPERATIONAL,
                max_tokens=2048,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
                temperature=0.1,
            )
        raw = "".join(block.text for block in response.content if block.type == "text").strip()
        if raw.startswith("\u0060\u0060\u0060"):
            raw = raw.split("\n", 1)[1].rsplit("\u0060\u0060\u0060", 1)[0].strip()
        result = json.loads(raw)
        if not isinstance(result, dict):
            raise ValueError("Expected object")
        result["tokens_used"] = response.usage.input_tokens + response.usage.output_tokens
        return result
    except APITimeoutError as exc:
        raise AnalysisError(
            "AI_TIMEOUT", "Layanan AI melewati batas waktu. Silakan coba lagi.", status=504
        ) from exc
    except APIError as exc:
        raise AnalysisError(
            "AI_PROVIDER_ERROR", "Layanan AI tidak dapat dihubungi. Silakan coba lagi."
        ) from exc
    except (ValueError, TypeError, IndexError) as exc:
        raise AnalysisError(
            "AI_INVALID_RESPONSE", "Respons AI tidak valid; hasil terakhir dipertahankan."
        ) from exc
