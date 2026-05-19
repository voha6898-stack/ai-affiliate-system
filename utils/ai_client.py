"""
Universal AI Client — hỗ trợ nhiều provider miễn phí
Priority: Claude (tốt nhất) → Gemini (miễn phí) → Groq (miễn phí, nhanh nhất)
"""
import os
import logging
import time
import threading
import requests
from collections import deque
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


class RateLimiter:
    """Token bucket — đảm bảo không vượt max_per_minute requests."""
    def __init__(self, max_per_minute: int = 12):
        self.max_per_minute = max_per_minute
        self.timestamps: deque = deque()
        self._lock = threading.Lock()

    def wait(self):
        """Block cho đến khi có thể gọi API an toàn."""
        with self._lock:
            now = time.time()
            window = 60.0
            # Xóa timestamps cũ hơn 60s
            while self.timestamps and now - self.timestamps[0] > window:
                self.timestamps.popleft()

            if len(self.timestamps) >= self.max_per_minute:
                # Phải chờ đến khi request cũ nhất ra khỏi window
                oldest = self.timestamps[0]
                wait_time = window - (now - oldest) + 1
                if wait_time > 0:
                    logger.info(f"Rate limiter: chờ {wait_time:.1f}s để tránh vượt giới hạn API...")
                    time.sleep(wait_time)

            self.timestamps.append(time.time())


class AIClient:
    """
    Provider-agnostic AI client.
    Tự động chọn provider dựa trên API key có sẵn.

    FREE OPTIONS (không cần credit card):
    - Google Gemini 2.5 Flash   : 250 req/ngày miễn phí
    - Google Gemini 2.5 Flash-Lite: 1000 req/ngày miễn phí
    - Groq (Llama 3.3 70B)      : 14,400 req/ngày miễn phí, SIÊU NHANH

    PAID (chất lượng nhất):
    - Anthropic Claude Sonnet
    """

    def __init__(self):
        self.anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")
        self.gemini_key = os.getenv("GEMINI_API_KEY", "")
        self.groq_key = os.getenv("GROQ_API_KEY", "")
        self.openrouter_key = os.getenv("OPENROUTER_API_KEY", "")

        self.provider = self._detect_provider()
        logger.info(f"AI Provider: {self.provider.upper()}")

        # Token usage tracking
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.estimated_cost = 0.0

        # Rate limiter: Gemini free = 15 RPM, ta dùng 12 để an toàn
        self._rate_limiter = RateLimiter(max_per_minute=12)

        # Init provider client
        self._init_client()

    def _detect_provider(self) -> str:
        """Tự động chọn provider tốt nhất có API key.
        Ưu tiên: Claude (tốt nhất) → Groq (nhanh, 14400/ngày) → Gemini → OpenRouter
        """
        if self.anthropic_key:
            return "claude"
        elif self.groq_key:
            return "groq"
        elif self.gemini_key:
            return "gemini"
        elif self.openrouter_key:
            return "openrouter"
        else:
            raise ValueError(
                "\n❌ Chưa có API key nào!\n"
                "Thêm ít nhất 1 key vào file .env:\n"
                "  GEMINI_API_KEY=...    (miễn phí tại aistudio.google.com)\n"
                "  GROQ_API_KEY=...      (miễn phí tại console.groq.com)\n"
                "  ANTHROPIC_API_KEY=... (trả phí tại console.anthropic.com)\n"
            )

    def _init_client(self):
        """Khởi tạo client cho provider được chọn."""
        if self.provider == "claude":
            import anthropic
            self._claude = anthropic.Anthropic(api_key=self.anthropic_key)

        elif self.provider == "gemini":
            # Dùng REST API trực tiếp, không cần SDK
            self._gemini_url = "https://generativelanguage.googleapis.com/v1beta/models"
            # Flash cho content chất lượng, Flash-Lite cho tasks rẻ tiền
            self._gemini_quality_model = "gemini-2.5-flash"
            self._gemini_cheap_model = "gemini-2.5-flash"  # dùng chung 1 model cho ổn định

        elif self.provider == "groq":
            self._groq_url = "https://api.groq.com/openai/v1/chat/completions"
            self._groq_quality_model = "llama-3.3-70b-versatile"
            self._groq_cheap_model = "llama-3.1-8b-instant"

        elif self.provider == "openrouter":
            self._or_url = "https://openrouter.ai/api/v1/chat/completions"
            self._or_quality_model = "google/gemini-2.5-flash"
            self._or_cheap_model = "meta-llama/llama-3.1-8b-instruct:free"

    # ─────────────────────────────────────────
    # PUBLIC INTERFACE
    # ─────────────────────────────────────────

    def complete(self, system_prompt: str, user_message: str,
                 quality: bool = True, max_tokens: int = 4096) -> str:
        """
        Gửi request tới AI provider đang dùng.

        Args:
            system_prompt: Hướng dẫn cho AI
            user_message: Nội dung yêu cầu
            quality: True = dùng model chất, False = dùng model rẻ/nhanh
            max_tokens: Số token tối đa
        """
        if self.provider == "claude":
            return self._call_claude(system_prompt, user_message, quality, max_tokens)
        elif self.provider == "gemini":
            return self._call_gemini(system_prompt, user_message, quality, max_tokens)
        elif self.provider == "groq":
            return self._call_groq(system_prompt, user_message, quality, max_tokens)
        elif self.provider == "openrouter":
            return self._call_openrouter(system_prompt, user_message, quality, max_tokens)

    def complete_cheap(self, system_prompt: str, user_message: str,
                       max_tokens: int = 2048) -> str:
        """Dùng model rẻ/nhanh cho tasks đơn giản (research, classification)."""
        return self.complete(system_prompt, user_message, quality=False, max_tokens=max_tokens)

    def complete_quality(self, system_prompt: str, user_message: str,
                         max_tokens: int = 8192) -> str:
        """Dùng model chất lượng cao cho content generation."""
        return self.complete(system_prompt, user_message, quality=True, max_tokens=max_tokens)

    # ─────────────────────────────────────────
    # PROVIDER IMPLEMENTATIONS
    # ─────────────────────────────────────────

    def _call_claude(self, system_prompt: str, user_message: str,
                     quality: bool, max_tokens: int) -> str:
        """Claude với prompt caching tiết kiệm chi phí."""
        import anthropic
        model = "claude-sonnet-4-6" if quality else "claude-haiku-4-5-20251001"

        system = [{"type": "text", "text": system_prompt,
                   "cache_control": {"type": "ephemeral"}}]

        for attempt in range(3):
            try:
                resp = self._claude.messages.create(
                    model=model,
                    max_tokens=max_tokens,
                    system=system,
                    messages=[{"role": "user", "content": user_message}]
                )
                self.total_input_tokens += resp.usage.input_tokens
                self.total_output_tokens += resp.usage.output_tokens
                return resp.content[0].text
            except anthropic.RateLimitError:
                wait = 60 * (attempt + 1)
                logger.warning(f"Rate limit Claude, chờ {wait}s...")
                time.sleep(wait)
        raise RuntimeError("Claude API failed after 3 retries")

    def _call_gemini(self, system_prompt: str, user_message: str,
                     quality: bool, max_tokens: int) -> str:
        """Google Gemini — miễn phí. Tự fallback sang model chính nếu lite bị lỗi."""
        # Thứ tự thử: cheap model trước, nếu fail thì dùng quality model
        models_to_try = (
            [self._gemini_cheap_model, self._gemini_quality_model]
            if not quality
            else [self._gemini_quality_model]
        )

        for model in models_to_try:
            result = self._gemini_request(model, system_prompt, user_message, max_tokens)
            if result:
                return result
            logger.warning(f"Model {model} failed, trying next...")

        return ""

    def _gemini_request(self, model: str, system_prompt: str,
                        user_message: str, max_tokens: int) -> str:
        """Gọi một Gemini model cụ thể với retry và rate limiting."""
        self._rate_limiter.wait()  # Đảm bảo không vượt 12 RPM
        url = f"{self._gemini_url}/{model}:generateContent?key={self.gemini_key}"
        payload = {
            "system_instruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"parts": [{"text": user_message}]}],
            "generationConfig": {"maxOutputTokens": max_tokens, "temperature": 0.7}
        }

        for attempt in range(3):
            try:
                resp = requests.post(url, json=payload, timeout=120)

                if resp.status_code == 429:
                    # Đọc thời gian retry chính xác từ response của Gemini
                    wait = 15  # default
                    try:
                        err_msg = resp.json().get("error", {}).get("message", "")
                        import re
                        m = re.search(r"retry in ([\d.]+)s", err_msg)
                        if m:
                            wait = int(float(m.group(1))) + 3
                    except Exception:
                        pass
                    wait = max(wait, 10) * (attempt + 1)
                    logger.info(f"Rate limit, chờ {wait}s...")
                    time.sleep(wait)
                    continue

                if resp.status_code in (503, 500, 502):
                    logger.warning(f"Gemini {resp.status_code}, chờ 10s...")
                    time.sleep(10)
                    continue

                resp.raise_for_status()
                data = resp.json()

                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts and parts[0].get("text"):
                        text = parts[0]["text"]
                        usage = data.get("usageMetadata", {})
                        self.total_input_tokens += usage.get("promptTokenCount", 0)
                        self.total_output_tokens += usage.get("candidatesTokenCount", 0)
                        return text

                return ""  # Empty response — try next model

            except requests.exceptions.Timeout:
                logger.warning(f"Gemini timeout attempt {attempt+1}")
                time.sleep(5)
            except Exception as e:
                logger.warning(f"Gemini error ({model}): {e}")
                if attempt == 2:
                    return ""

        return ""

    def _call_groq(self, system_prompt: str, user_message: str,
                   quality: bool, max_tokens: int) -> str:
        """Groq — Llama 70B, siêu nhanh, miễn phí."""
        model = self._groq_quality_model if quality else self._groq_cheap_model

        headers = {
            "Authorization": f"Bearer {self.groq_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            "max_tokens": min(max_tokens, 8000),  # Groq max output = 8192 tokens
            "temperature": 0.7,
        }

        for attempt in range(3):
            try:
                resp = requests.post(self._groq_url, headers=headers,
                                     json=payload, timeout=60)

                if resp.status_code == 429:
                    wait = 30 * (attempt + 1)
                    logger.warning(f"Groq rate limit, chờ {wait}s...")
                    time.sleep(wait)
                    continue

                resp.raise_for_status()
                data = resp.json()
                text = data["choices"][0]["message"]["content"]

                usage = data.get("usage", {})
                self.total_input_tokens += usage.get("prompt_tokens", 0)
                self.total_output_tokens += usage.get("completion_tokens", 0)
                return text

            except Exception as e:
                logger.error(f"Groq error attempt {attempt+1}: {e}")
                if attempt == 2:
                    raise
                time.sleep(5)

        return ""

    def _call_openrouter(self, system_prompt: str, user_message: str,
                         quality: bool, max_tokens: int) -> str:
        """OpenRouter — nhiều model miễn phí."""
        model = self._or_quality_model if quality else self._or_cheap_model

        headers = {
            "Authorization": f"Bearer {self.openrouter_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://affiliate-ai.local",
        }
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            "max_tokens": max_tokens,
        }

        resp = requests.post(self._or_url, headers=headers, json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]

    # ─────────────────────────────────────────
    # COST / USAGE SUMMARY
    # ─────────────────────────────────────────

    def get_cost_summary(self) -> dict:
        """Thống kê usage và chi phí ước tính."""
        if self.provider == "gemini":
            cost = 0.0  # Free tier
            savings = 0.0
        elif self.provider == "groq":
            cost = 0.0  # Free tier
            savings = 0.0
        elif self.provider == "claude":
            cost = (self.total_input_tokens / 1000 * 0.003 +
                    self.total_output_tokens / 1000 * 0.015)
            savings = 0.0
        else:
            cost = 0.0
            savings = 0.0

        return {
            "provider": self.provider,
            "total_cost_usd": round(cost, 4),
            "estimated_savings_usd": round(savings, 4),
            "input_tokens": self.total_input_tokens,
            "output_tokens": self.total_output_tokens,
            "cache_hit_rate": 0,
        }


# Singleton — dùng chung toàn app
claude = AIClient()  # Giữ tên 'claude' để không phải đổi code cũ
