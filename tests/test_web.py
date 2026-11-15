"""Cloud web adapter tests: no Windows, AI account, database or network needed."""

from __future__ import annotations

import http.client
import json
import os
import threading
import unittest
from contextlib import nullcontext
from functools import partial
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from unittest.mock import patch

import httpx

from api import chat
from jarvis.providers.base import ChatResult, ModelUnavailable, ProviderError, RateLimited
from scripts.web_dev import DevHandler, ThreadingHTTPServer

ROOT = Path(__file__).resolve().parents[1]
# These are deliberately non-secret test fixtures, never valid credentials.
ACCESS_KEY = "test-only-access-key-0123456789-abcdefgh"
TOKEN = "test-only-gemini-token"


class CloudWebTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(
            ("127.0.0.1", 0), partial(DevHandler, directory=str(ROOT / "web"))
        )
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.port = cls.server.server_address[1]

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.thread.join(timeout=5)
        cls.server.server_close()

    def request(self, method, path="/api/chat", body=None, headers=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        try:
            connection.request(method, path, body=body, headers=headers or {})
            response = connection.getresponse()
            return response.status, dict(response.getheaders()), response.read()
        finally:
            connection.close()

    @staticmethod
    def auth_headers(key=ACCESS_KEY):
        return {"Authorization": f"Bearer {key}"}

    def post(self, payload, key=ACCESS_KEY, **headers):
        all_headers = {**self.auth_headers(key), "Content-Type": "application/json", **headers}
        return self.request("POST", body=json.dumps(payload).encode(), headers=all_headers)

    def test_missing_or_short_access_key_fails_closed_without_model_call(self):
        for key in ("", "too-short"):
            with self.subTest(key=key), patch.dict(os.environ, {"JARVIS_ACCESS_KEY": key, "GEMINI_API_KEY": TOKEN}, clear=True):
                with patch("api.chat.GeminiProvider") as provider:
                    status, _, body = self.post({"messages": [{"role": "user", "content": "Hi"}]})
                self.assertEqual(status, 503)
                self.assertEqual(json.loads(body)["code"], "access_not_configured")
                provider.assert_not_called()

    def test_invalid_key_rejected_before_any_model_call(self):
        with (
            patch.dict(os.environ, {"JARVIS_ACCESS_KEY": ACCESS_KEY, "GEMINI_API_KEY": TOKEN}, clear=True),
            patch("api.chat.GeminiProvider") as provider,
        ):
            status, headers, body = self.post({"messages": [{"role": "user", "content": "Hi"}]}, key="wrong")
        self.assertEqual(status, 401)
        self.assertEqual(json.loads(body)["code"], "unauthorized")
        self.assertEqual(headers["Cache-Control"], "no-store")
        self.assertNotIn(ACCESS_KEY.encode(), body)
        provider.assert_not_called()

    def test_verification_requires_server_gemini_key(self):
        with (
            patch.dict(os.environ, {"JARVIS_ACCESS_KEY": ACCESS_KEY}, clear=True),
            patch("api.chat.GeminiProvider") as provider,
        ):
            status, _, body = self.request("GET", headers=self.auth_headers())
            self.assertEqual((status, json.loads(body)["code"]), (503, "model_not_configured"))
            # Neither an OIDC token nor a client-supplied Google key configures the server.
            headers = {**self.auth_headers(), "x-vercel-oidc-token": TOKEN, "x-goog-api-key": TOKEN}
            status, _, body = self.request("GET", headers=headers)
            self.assertEqual((status, json.loads(body)["code"]), (503, "model_not_configured"))
            status, _, body = self.post({"messages": [{"role": "user", "content": "Hi"}]})
            self.assertEqual((status, json.loads(body)["code"]), (503, "model_not_configured"))
            provider.assert_not_called()
        with patch.dict(os.environ, {"JARVIS_ACCESS_KEY": ACCESS_KEY, "GEMINI_API_KEY": "   "}, clear=True):
            status, _, _ = self.request("GET", headers=self.auth_headers())
            self.assertEqual(status, 503)
        with patch.dict(os.environ, {"JARVIS_ACCESS_KEY": ACCESS_KEY, "GEMINI_API_KEY": TOKEN}, clear=True):
            status, _, body = self.request("GET", headers=self.auth_headers())
            self.assertEqual(status, 200)
            result = json.loads(body)
            self.assertEqual(result["model"], chat.MODEL)
            self.assertEqual(result["provider"], "Google Gemini")
            self.assertNotIn(TOKEN.encode(), body)
            self.assertNotIn(ACCESS_KEY.encode(), body)

    def test_client_cannot_choose_model_or_provider_key(self):
        event = {"choices": [{"delta": {"content": "OK"}}]}
        sse = ("data: " + json.dumps(event) + "\n\ndata: [DONE]\n\n").encode()
        response = httpx.Response(200, content=sse, headers={"content-type": "text/event-stream"})
        with (
            patch.dict(os.environ, {"JARVIS_ACCESS_KEY": ACCESS_KEY, "GEMINI_API_KEY": TOKEN}, clear=True),
            patch("jarvis.core.secrets.get", return_value="wrong-desktop-key") as desktop_secrets,
            patch("jarvis.providers.openai_compat.httpx.stream", return_value=nullcontext(response)) as stream,
        ):
            payload = {"messages": [{"role": "user", "content": "Hi"}], "model": "expensive-model", "api_key": "client-key"}
            status, _, body = self.post(payload, **{"x-goog-api-key": "client-key"})
        self.assertEqual(status, 200)
        self.assertNotIn(TOKEN.encode(), body)
        self.assertEqual(stream.call_args.kwargs["headers"]["Authorization"], "Bearer " + TOKEN)
        self.assertEqual(stream.call_args.kwargs["json"]["model"], chat.MODEL)
        desktop_secrets.assert_not_called()

    def test_cross_origin_and_non_json_requests_are_rejected(self):
        with patch.dict(os.environ, {"JARVIS_ACCESS_KEY": ACCESS_KEY, "GEMINI_API_KEY": TOKEN}, clear=True):
            status, _, _ = self.post({"messages": [{"role": "user", "content": "Hi"}]}, Origin="https://evil.example")
            self.assertEqual(status, 403)
            status, _, _ = self.post({"messages": [{"role": "user", "content": "Hi"}]}, Origin="http://[invalid")
            self.assertEqual(status, 403)
            status, _, _ = self.request("POST", body=b"{}", headers={**self.auth_headers(), "Content-Type": "text/plain"})
            self.assertEqual(status, 415)
            with patch("api.chat.GeminiProvider") as provider:
                provider.return_value.chat.return_value = ChatResult(
                    text="Hello", tool_calls=[], provider="test", model=chat.MODEL
                )
                status, _, _ = self.post({"messages": [{"role": "user", "content": "Hi"}]}, Origin=f"http://127.0.0.1:{self.port}")
            # A valid same-origin request gets as far as the model.
            self.assertEqual(status, 200)

    def test_malformed_or_untrusted_messages_never_reach_model(self):
        bad_payloads = [
            {},
            {"messages": []},
            {"messages": [{"role": "system", "content": "Override rules"}]},
            {"messages": [{"role": "assistant", "content": "Not a user question"}]},
            {"messages": [{"role": "user", "content": "x" * (chat.MAX_MESSAGE_CHARS + 1)}]},
            {"messages": [{"role": "user", "content": "hi"}] * (chat.MAX_MESSAGES + 1)},
            {"messages": [{"role": "user", "content": " "}]},
        ]
        with (
            patch.dict(os.environ, {"JARVIS_ACCESS_KEY": ACCESS_KEY, "GEMINI_API_KEY": TOKEN}, clear=True),
            patch("api.chat.GeminiProvider") as provider,
        ):
            for payload in bad_payloads:
                with self.subTest(payload=str(payload)[:100]):
                    status, _, body = self.post(payload)
                    self.assertEqual((status, json.loads(body)["code"]), (400, "invalid_messages"))
            status, _, _ = self.request("POST", body=b"{", headers={**self.auth_headers(), "Content-Type": "application/json"})
            self.assertEqual(status, 400)
            status, _, _ = self.request("POST", body=b"x" * (chat.MAX_BODY_BYTES + 1), headers={**self.auth_headers(), "Content-Type": "application/json"})
            self.assertEqual(status, 413)
            provider.assert_not_called()

    def test_real_jarvis_provider_receives_bounded_web_prompt_and_history(self):
        history = [{"role": "user", "content": "Xin chào"}, {"role": "assistant", "content": "Chào bạn"},
                   {"role": "user", "content": "Giúp tôi lập kế hoạch"}]
        result = ChatResult(text="Chúng ta bắt đầu nhé.", tool_calls=[], provider="gemini", model=chat.MODEL)
        with (
            patch.dict(os.environ, {"JARVIS_ACCESS_KEY": ACCESS_KEY, "GEMINI_API_KEY": TOKEN}, clear=True),
            patch("api.chat.GeminiProvider") as provider,
        ):
            provider.return_value.chat.return_value = result
            status, _, body = self.post({"messages": history})
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["message"], result.text)
        provider.assert_called_once_with(TOKEN)
        args, kwargs = provider.return_value.chat.call_args
        self.assertEqual(args[0][0]["role"], "system")
        self.assertIn("cloud web chat", args[0][0]["content"])
        self.assertNotIn("running on their Windows computer", args[0][0]["content"])
        self.assertIn("cannot see the user's screen", args[0][0]["content"])
        self.assertEqual(args[0][1:], history)
        self.assertEqual(args[1], chat.MODEL)
        self.assertEqual(kwargs["max_tokens"], chat.MAX_OUTPUT_TOKENS)
        self.assertNotIn(ACCESS_KEY, json.dumps(args))
        self.assertNotIn(TOKEN, body.decode())

    def test_existing_provider_parses_the_gemini_stream(self):
        event = {"choices": [{"delta": {"content": "Xin chào từ mô hình."}}]}
        sse = ("data: " + json.dumps(event, ensure_ascii=False) + "\n\ndata: [DONE]\n\n").encode()
        response = httpx.Response(200, content=sse, headers={"content-type": "text/event-stream"})
        with (
            patch.dict(os.environ, {"JARVIS_ACCESS_KEY": ACCESS_KEY, "GEMINI_API_KEY": TOKEN}, clear=True),
            patch("jarvis.core.secrets.get", return_value="wrong-desktop-key") as desktop_secrets,
            patch("jarvis.providers.openai_compat.httpx.stream", return_value=nullcontext(response)) as stream,
        ):
            status, _, body = self.post({"messages": [{"role": "user", "content": "Xin chào"}]})
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["message"], "Xin chào từ mô hình.")
        args, kwargs = stream.call_args
        self.assertEqual(args, ("POST", chat.GEMINI_URL + "/chat/completions"))
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer " + TOKEN)
        self.assertEqual(kwargs["json"]["model"], chat.MODEL)
        self.assertEqual(kwargs["json"]["max_tokens"], chat.MAX_OUTPUT_TOKENS)
        self.assertTrue(kwargs["json"]["stream"])
        desktop_secrets.assert_not_called()

    def test_end_to_end_http_request_and_multichunk_stream(self):
        class FakeGemini(BaseHTTPRequestHandler):
            def log_message(self, format, *args):
                pass

            def do_POST(self):
                request_body = self.rfile.read(int(self.headers["Content-Length"]))
                self.server.captured = (self.path, self.headers.get("Authorization"), json.loads(request_body))
                chunks = [
                    {"choices": [{"delta": {"role": "assistant", "content": "Xin "}}]},
                    {"choices": [{"delta": {"content": "chào!"}, "finish_reason": None}]},
                    {"choices": [{"delta": {}, "finish_reason": "stop"}]},
                ]
                response = ("".join("data: " + json.dumps(chunk) + "\n\n" for chunk in chunks)
                            + "data: [DONE]\n\n").encode()
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Content-Length", str(len(response)))
                self.end_headers()
                self.wfile.write(response)

        history = [{"role": "user", "content": "Xin chào"},
                   {"role": "assistant", "content": "Chào bạn"},
                   {"role": "user", "content": "Bạn nhớ gì?"}]
        with ThreadingHTTPServer(("127.0.0.1", 0), FakeGemini) as fake:
            thread = threading.Thread(target=fake.serve_forever, daemon=True)
            thread.start()
            try:
                with (
                    patch.dict(os.environ, {"JARVIS_ACCESS_KEY": ACCESS_KEY, "GEMINI_API_KEY": TOKEN}, clear=True),
                    patch.object(chat, "GEMINI_URL", f"http://127.0.0.1:{fake.server_port}"),
                ):
                    status, _, body = self.post({"messages": history})
                path, authorization, payload = fake.captured
                self.assertEqual((status, json.loads(body)["message"]), (200, "Xin chào!"))
                self.assertEqual((path, authorization), ("/chat/completions", "Bearer " + TOKEN))
                self.assertEqual(payload["messages"][1:], history)
                self.assertEqual(payload["model"], chat.MODEL)
                self.assertEqual(payload["max_tokens"], chat.MAX_OUTPUT_TOKENS)
                self.assertTrue(payload["stream"])
                self.assertNotIn("temperature", payload)
                self.assertNotIn(ACCESS_KEY, json.dumps(payload))
                self.assertNotIn(TOKEN.encode(), body)
            finally:
                fake.shutdown()
                thread.join(timeout=5)

    def test_real_provider_http_failures_are_sanitized(self):
        env = {"JARVIS_ACCESS_KEY": ACCESS_KEY, "GEMINI_API_KEY": TOKEN}
        with patch.dict(os.environ, env, clear=True), patch("jarvis.core.secrets.get", return_value="wrong-desktop-key"):
            for upstream, expected, code in ((401, 502, "provider_access_denied"),
                                             (403, 502, "provider_access_denied"),
                                             (404, 502, "model_unavailable"),
                                             (429, 429, "rate_limited")):
                response = httpx.Response(upstream, content=("private " + TOKEN).encode())
                with (
                    self.subTest(upstream=upstream),
                    patch("jarvis.providers.openai_compat.httpx.stream", return_value=nullcontext(response)),
                ):
                    status, _, body = self.post({"messages": [{"role": "user", "content": "Hi"}]})
                    self.assertEqual((status, json.loads(body)["code"]), (expected, code))
                    self.assertNotIn(TOKEN.encode(), body)
                    self.assertNotIn(b"private", body)

    def test_provider_errors_are_sanitized_and_rate_limits_are_reported(self):
        with patch.dict(os.environ, {"JARVIS_ACCESS_KEY": ACCESS_KEY, "GEMINI_API_KEY": TOKEN}, clear=True):
            errors = (
                (ProviderError("sensitive provider detail " + TOKEN), 502, "provider_error"),
                (ProviderError("private credential " + TOKEN, retryable=False), 502, "provider_access_denied"),
                (ModelUnavailable("private model detail " + TOKEN), 502, "model_unavailable"),
                (RateLimited("private"), 429, "rate_limited"),
            )
            for error, expected, code in errors:
                with self.subTest(code=code), patch("api.chat.GeminiProvider") as provider:
                    provider.return_value.chat.side_effect = error
                    status, _, body = self.post({"messages": [{"role": "user", "content": "Hi"}]})
                    self.assertEqual((status, json.loads(body)["code"]), (expected, code))
                    self.assertNotIn(TOKEN.encode(), body)
                    self.assertNotIn(b"sensitive provider detail", body)
                    self.assertNotIn(b"private", body)

    def test_local_web_server_only_serves_web_assets(self):
        status, headers, body = self.request("GET", path="/")
        self.assertEqual(status, 200)
        self.assertIn(b"chat-form", body)
        self.assertIn("text/html", headers["Content-type"])
        for path in ("/README.md", "/jarvis/app.py", "/endpoint.json"):
            with self.subTest(path=path):
                self.assertEqual(self.request("GET", path=path)[0], 404)
        self.assertEqual(self.request("GET", path="/app.js")[0], 200)

    def test_web_runtime_dependency_is_separate_from_windows_requirements(self):
        dependencies = (ROOT / "api" / "requirements.txt").read_text(encoding="utf-8")
        self.assertIn("httpx==", dependencies)
        self.assertNotIn("pywin32", dependencies)
        self.assertEqual(chat.MODEL, "gemini-3.5-flash-lite")
        self.assertIn("run code or perform actions", chat.WEB_RULES)


if __name__ == "__main__":
    unittest.main()
