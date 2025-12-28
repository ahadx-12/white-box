from __future__ import annotations

import os

from main import detect_service


def test_detect_service_defaults_to_api_with_port() -> None:
    environ = os.environ.copy()
    environ.pop("TRUSTAI_SERVICE", None)
    environ["PORT"] = "9999"
    assert detect_service(environ) == "api"


def test_detect_service_invalid_defaults_to_api() -> None:
    environ = {"TRUSTAI_SERVICE": "invalid"}
    assert detect_service(environ) == "api"
