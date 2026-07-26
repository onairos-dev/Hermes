"""Hardened JSON transport over HTTPS."""

from __future__ import annotations

import json
from pathlib import Path
import socket
import ssl
import urllib.error
import urllib.request

from .config import CA_BUNDLE_CANDIDATES, HTTP_TIMEOUT_SECONDS, MAX_RESPONSE_BYTES


def build_ssl_context(
    *,
    create_context=ssl.create_default_context,
    default_verify_paths=ssl.get_default_verify_paths,
    ca_candidates=CA_BUNDLE_CANDIDATES,
):
    """Use Python's roots, falling back to an OS-managed bundle when absent."""
    context = create_context()
    verify_paths = default_verify_paths()
    if verify_paths.cafile or verify_paths.capath:
        return context

    for candidate in ca_candidates:
        try:
            if Path(candidate).is_file():
                context.load_verify_locations(cafile=str(candidate))
                break
        except (OSError, ssl.SSLError):
            continue
    return context


def default_urlopen(
    request,
    timeout,
    *,
    urlopen=urllib.request.urlopen,
    build_context=build_ssl_context,
):
    """Open HTTPS with certificate verification across Python installations."""
    return urlopen(request, timeout=timeout, context=build_context())


def request_json(request: urllib.request.Request, urlopen) -> dict:
    """Read one bounded JSON object from a successful response."""
    with urlopen(request, timeout=HTTP_TIMEOUT_SECONDS) as response:
        status = response.getcode()
        if status is not None and not 200 <= int(status) < 300:
            raise urllib.error.HTTPError(
                request.full_url,
                int(status),
                "Onairos request failed",
                {},
                None,
            )
        try:
            raw = response.read(MAX_RESPONSE_BYTES + 1)
        except TypeError:
            raw = response.read()
    if len(raw) > MAX_RESPONSE_BYTES:
        raise ValueError("response too large")
    parsed = json.loads(raw.decode("utf-8"))
    if not isinstance(parsed, dict):
        raise ValueError("response must be an object")
    return parsed


def service_error(action: str, status: int) -> dict:
    """Return a safe HTTP failure without exposing response bodies."""
    return {
        "ok": False,
        "error": "service_error",
        "status": int(status),
        "message": f"Onairos could not {action} (HTTP {int(status)}).",
    }


def network_error(error: BaseException, action: str) -> dict:
    """Classify a transport failure without echoing exception details."""
    cause = error.reason if isinstance(error, urllib.error.URLError) else error
    if isinstance(cause, socket.gaierror):
        reason = "dns"
        message = "Could not resolve the Onairos service address."
    elif isinstance(cause, ssl.SSLError):
        reason = "tls"
        message = "Could not establish a secure connection to Onairos."
    elif isinstance(cause, (TimeoutError, socket.timeout)):
        reason = "timeout"
        message = f"Timed out while trying to {action}."
    else:
        reason = "connection"
        message = f"Could not {action} because the connection failed."
    return {
        "ok": False,
        "error": "network_error",
        "reason": reason,
        "message": message,
    }
