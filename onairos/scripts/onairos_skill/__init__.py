"""Public surface of the bundled Onairos Hermes helper."""

from .client import connect, sync
from .config import MAX_PERSONA_CHARS, MAX_RESPONSE_BYTES, MAX_SUMMARY_CHARS
from .persona import format_persona
from .state import default_state_dir, state_path
from .transport import build_ssl_context, default_urlopen


__all__ = (
    "MAX_PERSONA_CHARS",
    "MAX_RESPONSE_BYTES",
    "MAX_SUMMARY_CHARS",
    "build_ssl_context",
    "connect",
    "default_state_dir",
    "default_urlopen",
    "format_persona",
    "state_path",
    "sync",
)
