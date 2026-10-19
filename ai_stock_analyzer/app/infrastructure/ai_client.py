"""Anthropic failures are failures, never synthetic investment recommendations."""

import json
import re

import httpx
from anthropic import APIError, APITimeoutError, AsyncAnthropic

from app.core.config import settings
from app.core.errors import AnalysisError


def ai_identity():
    return settings.AI_PROVIDER, (
        settings.GEMINI_MODEL if settings.AI_PROVIDER == "gemini" else settings.AI_MODEL_OPERATIONAL
    )


def ai_configured():
    return bool(
        settings.GEMINI_API_KEY if settings.AI_PROVIDER == "gemini" else settings.ANTHROPIC_API_KEY
    )


async def call_analysis_model(system_prompt: str, user_prompt: str) -> dict:
    if settings.AI_PROVIDER == "anthropic":
        return await call_claude_sonnet(system_prompt, user_prompt)
    from app.domain.schemas.analysis import ModelAnalysis

    if not settings.GEMINI_API_KEY:
        raise AnalysisError("AI_NOT_CONFIGURED", "Layanan AI belum dikonfigurasi.", status=503)
    if not re.fullmatch(r"[a-zA-Z0-9_.-]+", settings.GEMINI_MODEL):
        raise AnalysisError("AI_NOT_CONFIGURED", "Nama model AI tidak valid.", status=503)
    schema = ModelAnalysis.model_json_schema()
    schema["properties"].pop("tokens_used", None)
    try:
        async with httpx.AsyncClient(timeout=60, follow_redirects=False) as client:
            response = await client.post(
                "https://generativelanguage.googleapis.com/v1beta/models/"
                + settings.GEMINI_MODEL
                + ":generateContent",
                headers={"x-goog-api-key": settings.GEMINI_API_KEY},
                json={
                    "systemInstruction": {"parts": [{"text": system_prompt}]},
                    "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
                    "generationConfig": {
                        "temperature": 0.1,
                        "maxOutputTokens": 4096,
                        "responseMimeType": "application/json",
                        "responseJsonSchema": schema,
                    },
                },
            )
            if response.status_code == 429:
                raise AnalysisError(
                    "AI_RATE_LIMITED", "Batas provider AI tercapai; coba lagi nanti.", status=503
                )
            response.raise_for_status()
            payload = response.json()
        candidate = payload["candidates"][0]
        if candidate.get("finishReason") != "STOP":
            raise ValueError("Incomplete or refused response")
        raw = "".join(
            p.get("text", "") for p in candidate["content"]["parts"] if not p.get("thought")
        )
        result = json.loads(raw)
        if not isinstance(result, dict):
            raise ValueError("Expected object")
        result["tokens_used"] = payload.get("usageMetadata", {}).get("totalTokenCount", 0)
        result["_model_name"] = payload.get("modelVersion", settings.GEMINI_MODEL)
        return result
    except httpx.TimeoutException as exc:
        raise AnalysisError("AI_TIMEOUT", "Provider AI melewati batas waktu.", status=504) from exc
    except httpx.HTTPError as exc:
        raise AnalysisError("AI_PROVIDER_ERROR", "Provider AI tidak dapat dihubungi.") from exc
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        raise AnalysisError(
            "AI_INVALID_RESPONSE", "Respons AI tidak lengkap atau tidak valid."
        ) from exc


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
        if response.stop_reason != "end_turn":
            raise ValueError("Incomplete or refused response")
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
