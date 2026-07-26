"""Runtime configuration for the Onairos Hermes helper."""

from pathlib import Path


API_BASE = "https://api2.onairos.uk"
CONNECT_BASE = "https://onairos.io"
HTTP_TIMEOUT_SECONDS = 15
MAX_RESPONSE_BYTES = 1_000_000
DEFAULT_POLL_TIMEOUT_SECONDS = 300.0
DEFAULT_POLL_INTERVAL_SECONDS = 2.5
MAX_PERSONA_CHARS = 24_000
MAX_SUMMARY_CHARS = 20_000
USER_AGENT = "Onairos-Hermes-Skill/1.0"
CA_BUNDLE_CANDIDATES = (
    Path("/etc/ssl/cert.pem"),
    Path("/etc/ssl/certs/ca-certificates.crt"),
    Path("/etc/pki/tls/certs/ca-bundle.crt"),
    Path("/etc/ssl/ca-bundle.pem"),
    Path("/etc/pki/ca-trust/extracted/pem/tls-ca-bundle.pem"),
)
