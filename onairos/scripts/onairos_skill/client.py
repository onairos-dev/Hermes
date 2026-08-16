"""Browser-consent workflow for Onairos."""

from __future__ import annotations

import json
from pathlib import Path
import time
import urllib.error
import urllib.request
import webbrowser

from .config import (
    API_BASE,
    CONNECT_BASE,
    DEFAULT_POLL_INTERVAL_SECONDS,
    DEFAULT_POLL_TIMEOUT_SECONDS,
    USER_AGENT,
)
from .persona import format_persona
from .state import (
    default_state_dir,
    delete_state,
    read_state,
    state_path,
    valid_session_key,
    valid_uuid,
    write_state,
)
from .transport import default_urlopen, network_error, request_json, service_error


def _invalid_response(message: str) -> dict:
    return {"ok": False, "error": "invalid_response", "message": message}


def _session_request(edge: bool = False) -> urllib.request.Request:
    return urllib.request.Request(
        f"{API_BASE}/mcp/hermes/session",
        data=json.dumps({"mode": "edge"} if edge else {}).encode("utf-8"),
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
        },
    )


def _open_browser(connect_url: str, browser_open) -> bool:
    try:
        return bool(browser_open(connect_url))
    except Exception:
        return False


def connect(
    session_key: str,
    *,
    state_dir: Path | str | None = None,
    urlopen=default_urlopen,
    browser_open=webbrowser.open,
    edge: bool = False,
) -> dict:
    """Create a one-time Onairos session and open the consent page."""
    if not valid_session_key(session_key):
        return {
            "ok": False,
            "error": "invalid_session",
            "message": "Hermes did not provide a valid session identity.",
        }

    target_dir = Path(state_dir) if state_dir is not None else default_state_dir()
    target_path = state_path(session_key, target_dir)
    try:
        payload = request_json(_session_request(edge), urlopen)
    except urllib.error.HTTPError as error:
        return service_error("start the connection", error.code)
    except urllib.error.URLError as error:
        return network_error(error, "start the connection")
    except (TimeoutError, OSError) as error:
        return network_error(error, "start the connection")
    except (UnicodeError, ValueError, json.JSONDecodeError):
        return _invalid_response("Onairos returned an invalid session response. Try again.")

    session_id = payload.get("sessionId")
    if not valid_uuid(session_id):
        return _invalid_response("Onairos returned an invalid session response. Try again.")
    try:
        write_state(target_path, session_id)
    except OSError:
        return {
            "ok": False,
            "error": "state_error",
            "message": "Could not save the private connection state.",
        }

    connect_url = f"{CONNECT_BASE}/{'edge' if edge else 'connect'}?session={session_id}"
    browser_opened = _open_browser(connect_url, browser_open)
    message = (
        "Complete the connection in your browser."
        if browser_opened
        else "Open the connection URL in your browser to continue."
    )
    return {
        "ok": True,
        "status": "pending",
        "connect_url": connect_url,
        "browser_opened": browser_opened,
        "message": message,
    }


def _poll_request(session_id: str) -> urllib.request.Request:
    return urllib.request.Request(
        f"{API_BASE}/mcp/hermes/result/{session_id}",
        method="GET",
        headers={"Accept": "application/json", "User-Agent": USER_AGENT},
    )


def _poll_connection(
    session_id: str,
    target_path: Path,
    *,
    urlopen,
    sleep,
    monotonic,
    timeout_seconds: float,
    poll_interval_seconds: float,
) -> tuple[str | None, dict | None, dict | None]:
    deadline = monotonic() + max(0.0, float(timeout_seconds))
    while True:
        try:
            payload = request_json(_poll_request(session_id), urlopen)
        except urllib.error.HTTPError as error:
            if error.code == 404:
                delete_state(target_path)
                return None, None, {
                    "ok": False,
                    "error": "expired",
                    "message": "The connection expired. Connect again.",
                }
            return None, None, service_error("check the connection", error.code)
        except urllib.error.URLError as error:
            return None, None, network_error(error, "check the connection")
        except (TimeoutError, OSError) as error:
            return None, None, network_error(error, "check the connection")
        except (UnicodeError, ValueError, json.JSONDecodeError):
            return None, None, _invalid_response("Onairos returned an invalid status. Try again.")

        status_value = payload.get("status")
        if status_value == "pending":
            remaining = deadline - monotonic()
            if remaining <= 0:
                return None, None, {
                    "ok": False,
                    "error": "pending",
                    "message": "Finish the connection in your browser, then try sync again.",
                }
            sleep(min(max(0.01, float(poll_interval_seconds)), remaining))
            continue
        if status_value != "complete":
            return None, None, _invalid_response("Onairos returned an invalid status. Try again.")

        delete_state(target_path)
        token = payload.get("token")
        if not isinstance(token, str) or not token:
            return None, None, {
                "ok": False,
                "error": "consumed",
                "message": "The one-time connection was consumed. Connect again.",
            }
        return token, payload, None


def _traits_request(token: str) -> urllib.request.Request:
    return urllib.request.Request(
        f"{API_BASE}/traits-only",
        data=b"{}",
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
            "Authorization": f"Bearer {token}",
        },
    )


def sync(
    session_key: str,
    *,
    state_dir: Path | str | None = None,
    urlopen=default_urlopen,
    sleep=time.sleep,
    monotonic=time.monotonic,
    timeout_seconds: float = DEFAULT_POLL_TIMEOUT_SECONDS,
    poll_interval_seconds: float = DEFAULT_POLL_INTERVAL_SECONDS,
) -> dict:
    """Consume a completed relay once and return an allowlisted persona."""
    if not valid_session_key(session_key):
        return {
            "ok": False,
            "error": "invalid_session",
            "message": "Hermes did not provide a valid session identity.",
        }

    target_dir = Path(state_dir) if state_dir is not None else default_state_dir()
    target_path = state_path(session_key, target_dir)
    session_id, state_error = read_state(target_path)
    if state_error == "no_session":
        return {"ok": False, "error": "no_session", "message": "Connect first."}
    if state_error:
        return {
            "ok": False,
            "error": "invalid_state",
            "message": "The saved connection was invalid. Connect again.",
        }

    token, relay_payload, poll_error = _poll_connection(
        session_id,
        target_path,
        urlopen=urlopen,
        sleep=sleep,
        monotonic=monotonic,
        timeout_seconds=timeout_seconds,
        poll_interval_seconds=poll_interval_seconds,
    )
    if poll_error is not None:
        return poll_error

    try:
        traits_payload = request_json(_traits_request(token), urlopen)
    except Exception:
        return {
            "ok": False,
            "error": "consumed",
            "message": "The one-time connection was consumed before traits loaded. Connect again.",
        }
    contacts = relay_payload.get("contacts", []) if isinstance(relay_payload, dict) else []
    return {
        "ok": True,
        "status": "complete",
        "persona": format_persona(traits_payload),
        **({"contacts": contacts, "contact_count": len(contacts)} if contacts else {}),
    }
