"""A bounded, authenticated web-chat adapter for JARVIS's v4 model provider.

This deliberately does not instantiate the Windows desktop agent or expose its
OS tools. Conversation history is supplied by the browser; no server-side
state, credentials or prompts are written to disk.
"""

from __future__ import annotations

import contextlib
import hashlib
import hmac
import json
import logging
import os
from email.message import Message
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlsplit

from jarvis.agent import prompts
from jarvis.providers.base import ModelUnavailable, ProviderError, RateLimited
from jarvis.providers.openai_compat import OpenAICompatProvider

log = logging.getLogger(__name__)

# A distinct free-inference model, rather than a paid model using free credits.
# Its availability and provider terms may change independently of this app.
MODEL = "reflection/beam-free"
GATEWAY_URL = "https://ai-gateway.vercel.sh/v1"
MAX_BODY_BYTES = 48 * 1024
MAX_MESSAGES = 24
MAX_MESSAGE_CHARS = 4000
MAX_TOTAL_CHARS = 20000
MAX_OUTPUT_TOKENS = 1024
PROVIDER_TIMEOUT = 45.0

WEB_RULES = (
    "This is JARVIS's cloud web chat, not the Windows desktop app. "
    "Answer in the language the user uses. Be helpful, accurate and clear. "
    "You have no tools in this chat: you cannot see the user's screen, access their "
    "computer or files, browse the web, send messages, run code or perform actions. "
    "Do not claim you have performed an action or have real-time information. "
    "When asked to do something unavailable, explain the limitation and offer "
    "practical instructions instead. Only use the conversation as context."
)
SYSTEM_PROMPT = "\n\n".join((
    prompts.IDENTITY.replace(
        "running on their Windows computer", "running as a cloud-based web assistant"
    ).format(user="the user", address="you", style="warm and concise"),
    WEB_RULES,
    prompts.SAFETY,
))


def _configured_access_key() -> str | None:
    key = os.environ.get("JARVIS_ACCESS_KEY", "")
    # Long, randomly generated URL-safe keys are recommended. Failing closed is
    # important: a missing key must never expose the owner's model account.
    if not (32 <= len(key) <= 512) or any(not (32 < ord(c) < 127) for c in key):
        return None
    return key


def _authorized(header: str, configured: str) -> bool:
    if not header.startswith("Bearer ") or len(header) > 520:
        return False
    candidate = header[7:]
    # Compare fixed-length digests, including for keys of differing lengths.
    supplied = hashlib.sha256(candidate.encode("utf-8")).digest()
    expected = hashlib.sha256(configured.encode("utf-8")).digest()
    return hmac.compare_digest(supplied, expected)


def _gateway_credential(headers: Message) -> str | None:
    # An explicit API key wins. Vercel supplies its rotating OIDC token in each
    # function request, while `vercel env pull` supplies an env var locally.
    api_key = os.environ.get("AI_GATEWAY_API_KEY")
    if api_key:
        return api_key
    if os.environ.get("VERCEL") == "1" and os.environ.get("VERCEL_ENV") != "development":
        return headers.get("x-vercel-oidc-token") or None
    return os.environ.get("VERCEL_OIDC_TOKEN") or None


class GatewayProvider(OpenAICompatProvider):
    """Pass the request's short-lived credential without mutating process env."""

    def __init__(self, credential: str) -> None:
        super().__init__("vercel-gateway", {
            "base_url": GATEWAY_URL,
            "max_tokens_field": "max_tokens",
        })
        self._gateway_credential = credential

    def _key(self) -> str:
        return self._gateway_credential


def _messages_from_body(body: object) -> list[dict[str, str]]:
    if not isinstance(body, dict) or not isinstance(body.get("messages"), list):
        raise ValueError("Tin nhắn không hợp lệ.")
    messages = body["messages"]
    if not 1 <= len(messages) <= MAX_MESSAGES:
        raise ValueError("Số lượng tin nhắn không hợp lệ.")
    clean: list[dict[str, str]] = []
    total = 0
    for message in messages:
        if not isinstance(message, dict) or message.get("role") not in ("user", "assistant"):
            raise ValueError("Vai trò tin nhắn không hợp lệ.")
        content = message.get("content")
        if not isinstance(content, str) or not content.strip() or len(content) > MAX_MESSAGE_CHARS:
            raise ValueError("Mỗi tin nhắn phải có từ 1 đến 4.000 ký tự.")
        total += len(content)
        clean.append({"role": message["role"], "content": content})
    if total > MAX_TOTAL_CHARS or clean[-1]["role"] != "user":
        raise ValueError("Lịch sử trò chuyện quá dài hoặc thiếu câu hỏi cuối.")
    return clean


class handler(BaseHTTPRequestHandler):  # noqa: N801 - Vercel's required export
    """GET verifies access; POST calls the existing JARVIS cloud provider."""

    def log_message(self, format: str, *args: object) -> None:
        # Do not log headers, messages, credentials or query strings.
        pass

    def _json(self, status: int, payload: dict, extra_headers: dict[str, str] | None = None) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Length", str(len(body)))
        for name, value in (extra_headers or {}).items():
            self.send_header(name, value)
        self.end_headers()
        with contextlib.suppress(BrokenPipeError, ConnectionResetError):
            self.wfile.write(body)

    def _check_access(self) -> bool:
        origin = self.headers.get("Origin")
        if origin:
            try:
                parsed = urlsplit(origin)
                valid_origin = (parsed.scheme in ("http", "https") and not parsed.path and not parsed.query
                                and not parsed.fragment and parsed.netloc.lower() == self.headers.get("Host", "").lower())
            except ValueError:
                valid_origin = False
            if not valid_origin:
                self._json(403, {"error": "Nguồn yêu cầu không hợp lệ.", "code": "invalid_origin"})
                return False
        key = _configured_access_key()
        if key is None:
            self._json(503, {"error": "Máy chủ chưa thiết lập khóa truy cập an toàn.", "code": "access_not_configured"})
            return False
        if not _authorized(self.headers.get("Authorization", ""), key):
            self._json(401, {"error": "Khóa truy cập không đúng.", "code": "unauthorized"})
            return False
        return True

    def do_GET(self) -> None:  # noqa: N802
        if not self._check_access():
            return
        if not _gateway_credential(self.headers):
            self._json(503, {"error": "AI Gateway chưa được cấu hình trên máy chủ.", "code": "model_not_configured"})
            return
        self._json(200, {"ok": True, "model": MODEL, "provider": "Vercel AI Gateway"})

    def do_POST(self) -> None:  # noqa: N802
        if not self._check_access():
            return
        if self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower() != "application/json":
            self._json(415, {"error": "Yêu cầu phải dùng JSON.", "code": "invalid_content_type"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = 0
        if not 0 < length <= MAX_BODY_BYTES:
            self._json(413, {"error": "Yêu cầu quá lớn hoặc không có nội dung.", "code": "invalid_size"})
            return
        try:
            data = json.loads(self.rfile.read(length))
            messages = _messages_from_body(data)
        except (ValueError, UnicodeDecodeError, json.JSONDecodeError):
            self._json(400, {"error": "Nội dung hoặc lịch sử trò chuyện không hợp lệ.", "code": "invalid_messages"})
            return
        credential = _gateway_credential(self.headers)
        if credential is None:
            self._json(503, {"error": "AI Gateway chưa được cấu hình trên máy chủ.", "code": "model_not_configured"})
            return
        provider = GatewayProvider(credential)
        try:
            result = provider.chat(
                [{"role": "system", "content": SYSTEM_PROMPT}, *messages],
                MODEL,
                max_tokens=MAX_OUTPUT_TOKENS,
                timeout=PROVIDER_TIMEOUT,
            )
            if not result.text.strip():
                self._json(502, {"error": "Mô hình không trả về nội dung. Hãy thử lại.", "code": "empty_response"})
                return
        except RateLimited:
            self._json(429, {"error": "Mô hình đang giới hạn lượt dùng. Hãy thử lại sau.", "code": "rate_limited"})
            return
        except ModelUnavailable:
            log.warning("AI model unavailable")
            self._json(502, {"error": "Mô hình AI hiện không khả dụng. Hãy liên hệ chủ sở hữu triển khai.", "code": "model_unavailable"})
            return
        except ProviderError as exc:
            # Provider responses may contain sensitive details; do not echo them.
            log.warning("AI Gateway request failed")
            if not exc.retryable:
                self._json(502, {"error": "AI Gateway từ chối truy cập. Hãy kiểm tra xác minh tài khoản, cấu hình và quyền sử dụng mô hình.", "code": "provider_access_denied"})
            else:
                self._json(502, {"error": "Không kết nối được mô hình AI. Kiểm tra AI Gateway hoặc thử lại sau.", "code": "provider_error"})
            return
        except Exception:  # noqa: BLE001 - don't leak credentials or provider details
            log.warning("Unexpected AI Gateway failure")
            self._json(502, {"error": "Không thể nhận phản hồi từ mô hình AI. Hãy thử lại.", "code": "provider_error"})
            return
        self._json(200, {"ok": True, "message": result.text, "model": MODEL})
