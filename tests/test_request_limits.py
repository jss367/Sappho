"""Synthetic request tests without analysis downloads, corpora, or external services."""
import importlib.util
import io
import os
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import Mock, patch
from urllib.parse import urlencode
from werkzeug.test import EnvironBuilder


APP_PATH = Path(__file__).resolve().parents[1] / "sappho.py"
DEFAULT_LIMIT = 500_000


def load_app(environment=None):
    analysis = Mock(return_value=("synthetic text", [], {"word_count": 1}))
    stub = types.ModuleType("text_analysis")
    stub.analyze_text = analysis
    name = "sappho_request_limit_fixture"
    spec = importlib.util.spec_from_file_location(name, APP_PATH)
    module = importlib.util.module_from_spec(spec)
    # The application sees only synthetic environment settings, never real credentials.
    with patch.dict(os.environ, environment or {}, clear=True), patch.dict(
        sys.modules, {"text_analysis": stub, name: module}
    ):
        spec.loader.exec_module(module)
    module.app.config["TESTING"] = True
    return module.app, analysis


class RequestLimitTests(unittest.TestCase):
    def test_oversized_urlencoded_body_rejected_before_analysis(self):
        app, analysis = load_app()
        response = app.test_client().post(
            "/analyze-text", data=b"html=" + b"x" * DEFAULT_LIMIT,
            content_type="application/x-www-form-urlencoded",
        )
        self.assertEqual(response.status_code, 413)
        analysis.assert_not_called()

    def test_ordinary_request_returns_analysis_json(self):
        app, analysis = load_app()
        response = app.test_client().post("/analyze-text", data={"html": "<p>Hello</p>"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.get_json(),
            {"text": "synthetic text", "tokens": [], "metrics": {"word_count": 1}},
        )
        analysis.assert_called_once_with("<p>Hello</p>")

    def test_default_body_limit_accepts_exact_boundary(self):
        app, analysis = load_app()
        html = "x" * (DEFAULT_LIMIT - len(b"html="))
        response = app.test_client().post(
            "/analyze-text", data=("html=" + html).encode(),
            content_type="application/x-www-form-urlencoded",
        )
        self.assertEqual(response.status_code, 200)
        analysis.assert_called_once_with(html)

    def test_limit_applies_to_encoded_bytes(self):
        app, analysis = load_app()
        body = urlencode({"html": "é" * 90_000}).encode()
        self.assertGreater(len(body), DEFAULT_LIMIT)
        response = app.test_client().post(
            "/analyze-text", data=body, content_type="application/x-www-form-urlencoded",
        )
        self.assertEqual(response.status_code, 413)
        analysis.assert_not_called()

    def test_terminated_stream_without_content_length_is_bounded(self):
        app, analysis = load_app()
        builder = EnvironBuilder(path="/analyze-text", method="POST")
        self.addCleanup(builder.close)
        environ = builder.get_environ()
        environ.pop("CONTENT_LENGTH", None)
        environ["CONTENT_TYPE"] = "application/x-www-form-urlencoded"
        environ["wsgi.input"] = io.BytesIO(b"html=" + b"x" * DEFAULT_LIMIT)
        environ["wsgi.input_terminated"] = True
        response = app.test_client().open(environ)
        self.assertEqual(response.status_code, 413)
        analysis.assert_not_called()

    def test_default_limit_is_explicit_integer(self):
        app, _ = load_app()
        self.assertEqual(app.config["MAX_CONTENT_LENGTH"], DEFAULT_LIMIT)
        self.assertIsInstance(app.config["MAX_CONTENT_LENGTH"], int)

    def test_positive_environment_override_is_parsed_and_enforced(self):
        app, analysis = load_app({"MAX_CONTENT_LENGTH": "12"})
        self.assertEqual(app.config["MAX_CONTENT_LENGTH"], 12)
        client = app.test_client()
        accepted = client.post(
            "/analyze-text", data=b"html=1234567",
            content_type="application/x-www-form-urlencoded",
        )
        rejected = client.post(
            "/analyze-text", data=b"html=12345678",
            content_type="application/x-www-form-urlencoded",
        )
        self.assertEqual(accepted.status_code, 200)
        self.assertEqual(rejected.status_code, 413)
        analysis.assert_called_once_with("1234567")

    def test_invalid_environment_override_fails_closed(self):
        for value in ("", "unlimited", "None", "0", "-1", "1.5"):
            with self.subTest(value=value):
                with self.assertRaisesRegex(
                    ValueError, "MAX_CONTENT_LENGTH must be a positive integer"
                ):
                    load_app({"MAX_CONTENT_LENGTH": value})


if __name__ == "__main__":
    unittest.main()
