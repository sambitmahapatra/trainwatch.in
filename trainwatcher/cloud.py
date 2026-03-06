"""TrainWatcher Cloud client helpers."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional
import urllib.request

from .contracts import make_interpretation_result
from .exceptions import TrainWatcherError

DEFAULT_TIMEOUT = 10
DEFAULT_INTERPRET_TIMEOUT = 20
DEFAULT_BASE_URL = "https://trainwatch-notify.trainwatch.workers.dev"
DEFAULT_CREDENTIALS_PATH = os.getenv(
    "TRAINWATCHER_CREDENTIALS_PATH",
    os.getenv(
        "TRAINWATCH_CREDENTIALS_PATH",
        str(Path.home() / ".trainwatcher" / "credentials.json"),
    ),
)
_DISABLE_PROXY_ENV = "TRAINWATCHER_DISABLE_PROXY"
_LEGACY_DISABLE_PROXY_ENV = "TRAINWATCH_DISABLE_PROXY"


def add_email(email: str, base_url: Optional[str] = None, api_key_path: Optional[str] = None) -> str:
    """Register an email, verify via code, and store the API key locally."""
    base_url = resolve_base_url(base_url)
    _post_json(f"{base_url}/register", {"email": email})

    code = input("Enter the 6-digit verification code sent to your email: ").strip()
    if not code:
        raise TrainWatcherError("Verification code is required.")

    resp = _post_json(f"{base_url}/verify", {"email": email, "code": code})
    api_key = resp.get("api_key")
    if not api_key:
        raise TrainWatcherError("Verification failed: no API key returned.")

    save_credentials(
        {
            "api_key": api_key,
            "email": email,
            "base_url": base_url,
        },
        path=api_key_path,
    )
    return api_key


def verify_email(email: str, code: str, base_url: Optional[str] = None, api_key_path: Optional[str] = None) -> str:
    """Verify a code and store the API key locally (non-interactive)."""
    base_url = resolve_base_url(base_url)
    resp = _post_json(f"{base_url}/verify", {"email": email, "code": code})
    api_key = resp.get("api_key")
    if not api_key:
        raise TrainWatcherError("Verification failed: no API key returned.")

    save_credentials(
        {
            "api_key": api_key,
            "email": email,
            "base_url": base_url,
        },
        path=api_key_path,
    )
    return api_key


def delete_email(base_url: Optional[str] = None, api_key_path: Optional[str] = None) -> None:
    """Delete the registered email and remove local credentials."""
    creds = load_credentials(path=api_key_path)
    if not creds:
        raise TrainWatcherError("No credentials found.")

    base_url = resolve_base_url(base_url or creds.get("base_url"))
    api_key = creds.get("api_key")
    if not api_key:
        raise TrainWatcherError("Missing API key.")

    _post_json(
        f"{base_url}/delete",
        {},
        headers={"Authorization": f"Bearer {api_key}"},
    )

    clear_credentials(path=api_key_path)


def send_notification(
    message: str,
    subject: Optional[str] = None,
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
    api_key_path: Optional[str] = None,
) -> None:
    """Send a notification via the TrainWatcher Cloud backend."""
    if not message:
        raise TrainWatcherError("Message is required.")

    creds = load_credentials(path=api_key_path) if api_key is None else None
    api_key = api_key or (creds.get("api_key") if creds else None)
    if not api_key:
        raise TrainWatcherError("No API key available. Run add_email() first.")

    base_url = resolve_base_url(base_url or (creds.get("base_url") if creds else None))
    payload = {"message": message}
    if subject:
        payload["subject"] = subject

    _post_json(
        f"{base_url}/notify",
        payload,
        headers={"Authorization": f"Bearer {api_key}"},
    )


def request_interpretation(
    payload: Dict[str, Any],
    analysis: Dict[str, Any],
    *,
    mode: str = "hybrid",
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
    api_key_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Request hosted interpretation from the TrainWatcher backend."""
    creds = load_credentials(path=api_key_path) if api_key is None else None
    api_key = api_key or (creds.get("api_key") if creds else None)
    if not api_key:
        raise TrainWatcherError("No API key available for hosted interpretation. Run add_email() first.")

    base_url = resolve_base_url(base_url or (creds.get("base_url") if creds else None))
    response = _post_json(
        f"{base_url}/interpret",
        {"payload": payload, "analysis": analysis, "mode": mode},
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=DEFAULT_INTERPRET_TIMEOUT,
    )

    text = response.get("text")
    if not text:
        raise TrainWatcherError("Hosted interpretation returned no text.")

    return make_interpretation_result(
        mode=mode,
        text=str(text),
        provider=response.get("provider") or "hosted",
        model=response.get("model"),
        error=None,
    )


def get_base_url(base_url: Optional[str] = None) -> str:
    """Return the configured TrainWatcher backend URL."""
    return resolve_base_url(base_url)


def resolve_base_url(base_url: Optional[str]) -> str:
    resolved = base_url or os.getenv("TRAINWATCHER_BASE_URL") or os.getenv("TRAINWATCH_BASE_URL") or DEFAULT_BASE_URL
    if not resolved:
        raise TrainWatcherError(
            "Base URL not set. Provide base_url or set TRAINWATCHER_BASE_URL."
        )
    return resolved.rstrip("/")


def load_credentials(path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    env_key = os.getenv("TRAINWATCHER_API_KEY") or os.getenv("TRAINWATCH_API_KEY")
    env_url = os.getenv("TRAINWATCHER_BASE_URL") or os.getenv("TRAINWATCH_BASE_URL")
    if env_key:
        return {"api_key": env_key, "base_url": env_url}

    creds_path = Path(path or DEFAULT_CREDENTIALS_PATH)
    if not creds_path.exists():
        return None

    try:
        data = json.loads(creds_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise TrainWatcherError("Failed to read credentials file.") from exc
    except json.JSONDecodeError as exc:
        raise TrainWatcherError("Credentials file is invalid JSON.") from exc

    return data if isinstance(data, dict) else None


def save_credentials(data: Dict[str, Any], path: Optional[str] = None) -> None:
    creds_path = Path(path or DEFAULT_CREDENTIALS_PATH)
    creds_path.parent.mkdir(parents=True, exist_ok=True)
    creds_path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def clear_credentials(path: Optional[str] = None) -> None:
    creds_path = Path(path or DEFAULT_CREDENTIALS_PATH)
    if creds_path.exists():
        creds_path.unlink()

def credentials_available(path: Optional[str] = None) -> bool:
    if os.getenv("TRAINWATCHER_API_KEY") or os.getenv("TRAINWATCH_API_KEY"):
        return True
    creds_path = Path(path or DEFAULT_CREDENTIALS_PATH)
    return creds_path.exists()


def _post_json(
    url: str,
    payload: Dict[str, Any],
    headers: Optional[Dict[str, str]] = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> Dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/json")
    req.add_header("User-Agent", "TrainWatcher/0.2")

    if headers:
        for key, value in headers.items():
            req.add_header(key, value)

    opener = None
    disable_proxy = os.getenv(_DISABLE_PROXY_ENV, "") or os.getenv(_LEGACY_DISABLE_PROXY_ENV, "")
    if disable_proxy.strip().lower() in {"1", "true", "yes", "y"}:
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    try:
        if opener is None:
            response_ctx = urllib.request.urlopen(req, timeout=timeout)
        else:
            response_ctx = opener.open(req, timeout=timeout)

        with response_ctx as resp:
            raw = resp.read().decode("utf-8")
    except Exception as exc:
        raise TrainWatcherError(f"Request failed: {exc}") from exc

    try:
        data = json.loads(raw) if raw else {}
    except json.JSONDecodeError as exc:
        raise TrainWatcherError("Invalid JSON response.") from exc

    if isinstance(data, dict) and data.get("error"):
        raise TrainWatcherError(str(data.get("error")))

    return data if isinstance(data, dict) else {}
