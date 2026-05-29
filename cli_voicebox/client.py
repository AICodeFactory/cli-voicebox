"""HTTP client for Voicebox REST API."""

from __future__ import annotations

from typing import Any

import httpx

from cli_voicebox.config import CliConfig


class VoiceboxError(Exception):
    """Voicebox API error with optional HTTP status."""

    def __init__(self, message: str, status_code: int | None = None, body: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.body = body


class VoiceboxClient:
    """Thin wrapper around Voicebox HTTP endpoints."""

    def __init__(self, config: CliConfig):
        self.config = config
        self._client = httpx.Client(
            base_url=config.base_url,
            timeout=httpx.Timeout(config.timeout_seconds),
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "VoiceboxClient":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def _raise_for_response(self, response: httpx.Response) -> None:
        if response.is_success:
            return
        body: Any
        try:
            body = response.json()
        except Exception:
            body = response.text
        msg = f"HTTP {response.status_code}"
        if isinstance(body, dict) and "detail" in body:
            msg = f"{msg}: {body['detail']}"
        elif body:
            msg = f"{msg}: {body}"
        raise VoiceboxError(msg, status_code=response.status_code, body=body)

    def get_root(self) -> Any:
        response = self._client.get("/")
        self._raise_for_response(response)
        if not response.content:
            return None
        try:
            return response.json()
        except Exception:
            return response.text

    def get_health(self) -> dict[str, Any]:
        response = self._client.get("/health")
        self._raise_for_response(response)
        data = response.json()
        if not isinstance(data, dict):
            raise VoiceboxError("Unexpected /health response (expected JSON object)")
        return data

    def list_profiles(self) -> list[dict[str, Any]]:
        response = self._client.get("/profiles")
        self._raise_for_response(response)
        data = response.json()
        if isinstance(data, list):
            return data
        if isinstance(data, dict) and "profiles" in data:
            profiles = data["profiles"]
            if isinstance(profiles, list):
                return profiles
        raise VoiceboxError("Unexpected /profiles response shape")

    def list_history(self, limit: int | None = None) -> Any:
        params: dict[str, Any] = {}
        if limit is not None:
            params["limit"] = limit
        response = self._client.get("/history", params=params or None)
        self._raise_for_response(response)
        return response.json()

    def generate(self, payload: dict[str, Any]) -> tuple[dict[str, Any] | None, bytes | None]:
        """
        POST /generate.

        Returns (json_metadata, raw_audio_bytes). One of them may be set.
        """
        response = self._client.post("/generate", json=payload)
        self._raise_for_response(response)
        content_type = response.headers.get("content-type", "")
        if "application/json" in content_type:
            data = response.json()
            if not isinstance(data, dict):
                raise VoiceboxError("Unexpected /generate JSON response")
            return data, None
        if content_type.startswith("audio/") or content_type == "application/octet-stream":
            return None, response.content
        # Fallback: try JSON, else treat as binary audio
        try:
            data = response.json()
            if isinstance(data, dict):
                return data, None
        except Exception:
            pass
        return None, response.content

    def download_audio(self, generation_id: str) -> bytes:
        response = self._client.get(f"/audio/{generation_id}")
        self._raise_for_response(response)
        return response.content

    def models_status(self) -> Any:
        response = self._client.get("/models/status")
        self._raise_for_response(response)
        return response.json()
