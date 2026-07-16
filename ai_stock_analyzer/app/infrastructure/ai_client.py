"""
AI Stock Analyzer - Anthropic SDK Wrapper
Mengatur koneksi ke Claude Sonnet.
"""
import json
import logging
from anthropic import AsyncAnthropic, APITimeoutError, APIStatusError

from app.core.config import settings

logger = logging.getLogger(__name__)

async def call_claude_sonnet(system_prompt: str, user_prompt: str) -> dict:
    """
    Memanggil Claude Sonnet via Anthropic SDK.
    Mengembalikan dict hasil parsing JSON dari balasan AI.
    """
    if not settings.ANTHROPIC_API_KEY or settings.ANTHROPIC_API_KEY == "mock-key-for-testing":
        logger.warning("Mock Anthropic API Key terdeteksi. Menggunakan mock response.")
        return {
            "wyckoff_phase": "Tidak diketahui (Mock)",
            "vpa_insight": "Mock VPA insight - Harap masukkan API key asli.",
            "recommendation": "HOLD",
            "confidence_score": 0.0,
            "summary_id": "mock-summary"
        }

    client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    try:
        response = await client.messages.create(
            model="claude-3-sonnet-20240229", # Model terbaru standard untuk Sonnet 3
            max_tokens=1024,
            system=system_prompt,
            messages=[
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1 # Suhu rendah untuk konsistensi analisis JSON
        )
        
        # Ekstrak teks dari balasan pertama (asumsi balasan adalah text block JSON)
        raw_text = response.content[0].text
        
        try:
            # Cari substring JSON di dalam balasan (jaga-jaga Claude menambahkan narasi)
            start_idx = raw_text.find('{')
            end_idx = raw_text.rfind('}') + 1
            if start_idx != -1 and end_idx != 0:
                json_str = raw_text[start_idx:end_idx]
                return json.loads(json_str)
            else:
                raise ValueError("JSON object tidak ditemukan pada response Claude")
                
        except json.JSONDecodeError as je:
            logger.error(f"Gagal memparsing JSON dari balasan Claude: {je}\nRaw Text: {raw_text}")
            return __get_fallback_response()
            
    except APITimeoutError:
        logger.error("Timeout memanggil Anthropic API")
        return __get_fallback_response("API Timeout")
    except APIStatusError as status_err:
        logger.error(f"Anthropic API Error: {status_err.status_code} - {status_err.message}")
        return __get_fallback_response(f"API Error {status_err.status_code}")
    except Exception as e:
        logger.error(f"Unexpected error memanggil Claude: {e}")
        return __get_fallback_response(str(e))

def __get_fallback_response(reason: str = "Format Invalid") -> dict:
    """Mengembalikan format gagal/fallback jika terjadi error"""
    return {
        "wyckoff_phase": "Unknown",
        "vpa_insight": f"Gagal menganalisis karena: {reason}",
        "recommendation": "HOLD",
        "confidence_score": 0.0,
        "summary_id": "error-summary"
    }
