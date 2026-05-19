"""
Robust JSON parser — xử lý output từ Gemini/Groq bọc trong ```json ... ``` blocks.
"""
import json
import re
import logging

logger = logging.getLogger(__name__)


def parse_json(text: str, fallback=None):
    """
    Extract và parse JSON từ AI response, kể cả khi bọc trong markdown blocks.

    Thử theo thứ tự:
    1. Raw parse
    2. Strip ```json ... ``` wrapper
    3. Tìm [...] hoặc {...} đầu tiên
    """
    if not text:
        return fallback

    # 1. Thử parse thẳng
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass

    # 2. Strip markdown code block: ```json ... ``` hoặc ``` ... ```
    cleaned = re.sub(r'^```(?:json)?\s*', '', text.strip(), flags=re.MULTILINE)
    cleaned = re.sub(r'\s*```$', '', cleaned.strip(), flags=re.MULTILINE)
    try:
        return json.loads(cleaned.strip())
    except json.JSONDecodeError:
        pass

    # 3. Tìm JSON array [...] hoặc object {...}
    for pattern in (r'\[[\s\S]*\]', r'\{[\s\S]*\}'):
        match = re.search(pattern, text)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass

    logger.warning(f"JSON parse failed. Preview: {text[:100]}")
    return fallback
