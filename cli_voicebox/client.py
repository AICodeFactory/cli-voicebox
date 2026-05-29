"""HTTP client for Voicebox REST API."""

from __future__ import annotations

import time
from typing import Any

import httpx
from loguru import logger

from cli_voicebox.config import CliConfig

_ACTIVE_STATUSES = frozenset({"generating", "loading_model", "pending", "queued"})
_TERMINAL_OK = frozenset({"completed"})
_TERMINAL_FAIL = frozenset({"failed", "cancelled"})


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

    def _parse_error_body(self, response: httpx.Response) -> Any:
        try:
            return response.json()
        except Exception:
            return response.text

    def _format_http_error(self, response: httpx.Response) -> str:
        body = self._parse_error_body(response)
        msg = f"HTTP {response.status_code}"
        if isinstance(body, dict) and "detail" in body:
            detail = body["detail"]
            msg = f"{msg}: {detail}"
        elif body:
            msg = f"{msg}: {body}"
        return msg

    def _raise_for_response(self, response: httpx.Response) -> None:
        if response.is_success:
            return
        raise VoiceboxError(
            self._format_http_error(response),
            status_code=response.status_code,
            body=self._parse_error_body(response),
        )

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

    def list_history(
        self,
        *,
        profile_id: str | None = None,
        search: str | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"offset": offset}
        if profile_id:
            params["profile_id"] = profile_id
        if search:
            params["search"] = search
        if limit is not None:
            params["limit"] = limit
        response = self._client.get("/history", params=params)
        self._raise_for_response(response)
        data = response.json()
        if isinstance(data, dict) and "items" in data:
            return data
        if isinstance(data, list):
            return {"items": data, "total": len(data)}
        raise VoiceboxError("Unexpected /history response shape")

    def get_generation(self, generation_id: str) -> dict[str, Any]:
        response = self._client.get(f"/history/{generation_id}")
        self._raise_for_response(response)
        data = response.json()
        if not isinstance(data, dict):
            raise VoiceboxError("Unexpected /history/{id} response")
        return data

    def submit_generate(self, payload: dict[str, Any]) -> dict[str, Any]:
        """
        POST /generate — enqueue async generation.

        Returns generation metadata (usually status=generating).
        """
        response = self._client.post("/generate", json=payload)
        if response.is_success:
            data = response.json()
            if not isinstance(data, dict):
                raise VoiceboxError("Unexpected /generate JSON response")
            return data

        if response.status_code >= 500:
            recovered = self._recover_generation_after_server_error(payload)
            if recovered is not None:
                logger.warning(
                    "POST /generate returned HTTP {}; recovered generation {} from /history",
                    response.status_code,
                    recovered.get("id"),
                )
                return recovered

        raise VoiceboxError(
            self._format_http_error(response),
            status_code=response.status_code,
            body=self._parse_error_body(response),
        )

    def _recover_generation_after_server_error(
        self,
        payload: dict[str, Any],
    ) -> dict[str, Any] | None:
        """
        Voicebox may return HTTP 500 while the async job still runs.
        Recover by locating the newest matching row in /history.
        """
        profile_id = payload.get("profile_id")
        text = payload.get("text")
        if not profile_id or not text:
            return None

        history = self.list_history(
            profile_id=str(profile_id),
            search=str(text),
            limit=10,
        )
        items = history.get("items") or []
        if not isinstance(items, list):
            return None

        for item in items:
            if isinstance(item, dict) and item.get("text") == text:
                return item

        if items and isinstance(items[0], dict):
            return items[0]
        return None

    def wait_for_generation(
        self,
        generation_id: str,
        *,
        timeout_seconds: float | None = None,
        poll_interval: float = 1.0,
    ) -> dict[str, Any]:
        """Poll GET /history/{id} until generation completes or fails."""
        deadline = time.monotonic() + (
            timeout_seconds if timeout_seconds is not None else self.config.timeout_seconds
        )

        while time.monotonic() < deadline:
            gen = self.get_generation(generation_id)
            status = str(gen.get("status") or "completed").lower()

            if status in _TERMINAL_OK:
                return gen
            if status in _TERMINAL_FAIL:
                error = gen.get("error") or "generation failed"
                raise VoiceboxError(f"Generation failed: {error}", body=gen)

            if status not in _ACTIVE_STATUSES:
                # Unknown status — treat as done if audio exists
                if gen.get("audio_path"):
                    return gen

            time.sleep(poll_interval)

        raise VoiceboxError(
            f"Generation timed out after {timeout_seconds or self.config.timeout_seconds}s",
        )

    def generate_and_wait(
        self,
        payload: dict[str, Any],
        *,
        wait: bool = True,
        poll_interval: float = 1.0,
        timeout_seconds: float | None = None,
    ) -> dict[str, Any]:
        """Submit /generate and optionally wait until completed."""
        submitted = self.submit_generate(payload)
        generation_id = submitted.get("id")
        if not generation_id:
            raise VoiceboxError("No generation id in /generate response", body=submitted)

        if not wait:
            return submitted

        status = str(submitted.get("status") or "").lower()
        if status in _TERMINAL_OK:
            return submitted

        return self.wait_for_generation(
            str(generation_id),
            timeout_seconds=timeout_seconds,
            poll_interval=poll_interval,
        )

    def generate_stream(self, payload: dict[str, Any]) -> bytes:
        """POST /generate/stream — blocking WAV response (no history row)."""
        response = self._client.post("/generate/stream", json=payload)
        self._raise_for_response(response)
        return response.content

    def generate(self, payload: dict[str, Any]) -> tuple[dict[str, Any] | None, bytes | None]:
        """
        Legacy sync helper — prefer generate_and_wait or generate_stream.

        Uses async /generate + wait, then does not download audio bytes here.
        """
        meta = self.generate_and_wait(payload)
        return meta, None

    def download_audio(self, generation_id: str) -> bytes:
        response = self._client.get(f"/audio/{generation_id}")
        self._raise_for_response(response)
        return response.content

    def models_status(self) -> Any:
        response = self._client.get("/models/status")
        self._raise_for_response(response)
        return response.json()
