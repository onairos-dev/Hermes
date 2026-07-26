"""Private local handling for relay state."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import stat
import tempfile
import uuid


def default_state_dir() -> Path:
    """Return private, profile-scoped state storage without touching USER.md."""
    hermes_home = Path(os.environ.get("HERMES_HOME", "~/.hermes")).expanduser()
    return hermes_home / "state" / "onairos"


def valid_session_key(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip()) and len(value) <= 1024


def valid_uuid(value: object) -> bool:
    if not isinstance(value, str):
        return False
    try:
        parsed = uuid.UUID(value)
    except (ValueError, AttributeError):
        return False
    return str(parsed) == value.lower()


def state_path(session_key: str, state_dir: Path | str) -> Path:
    """Map an opaque Hermes session key to a non-revealing filename."""
    if not valid_session_key(session_key):
        raise ValueError("session key must be a non-empty string")
    digest = hashlib.sha256(str(session_key).encode("utf-8")).hexdigest()
    return Path(state_dir) / f"{digest}.json"


def delete_state(path: Path) -> None:
    try:
        path.unlink()
    except (FileNotFoundError, OSError):
        pass


def write_state(path: Path, session_id: str) -> None:
    """Atomically write only the relay UUID with private permissions."""
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if os.name == "posix":
        path.parent.chmod(0o700)

    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.stem}.",
        suffix=".tmp",
    )
    temporary_path = Path(temporary_name)
    try:
        if os.name == "posix":
            os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump({"sessionId": session_id}, handle, separators=(",", ":"))
        os.replace(temporary_path, path)
        if os.name == "posix":
            path.chmod(0o600)
    except BaseException:
        try:
            os.close(descriptor)
        except OSError:
            pass
        delete_state(temporary_path)
        raise


def read_state(path: Path) -> tuple[str | None, str | None]:
    """Read and validate a relay UUID, deleting malformed state."""
    if not path.exists():
        return None, "no_session"
    try:
        metadata = path.lstat()
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_size > 4096:
            raise ValueError("invalid state file")
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or set(data) != {"sessionId"}:
            raise ValueError("invalid state shape")
        session_id = data.get("sessionId")
        if not valid_uuid(session_id):
            raise ValueError("invalid session ID")
        return session_id, None
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError):
        delete_state(path)
        return None, "invalid_state"
