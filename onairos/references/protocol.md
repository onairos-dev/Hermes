# Onairos profile protocol

This reference explains the helper's internal contract; it is not permission for the agent to call these endpoints directly. Only `scripts/onairos.py` owns the transport.

## State machine

1. `connect` creates a ten-minute relay session with `POST https://api2.onairos.uk/mcp/hermes/session`.
2. The helper validates the returned UUID, stores only that ID in private local state, and opens `https://onairos.io/connect?session=<uuid>`.
3. The user signs in and explicitly chooses which sources to connect in the browser.
4. `sync` polls `GET https://api2.onairos.uk/mcp/hermes/result/<uuid>` only after the user confirms completion.
5. A completed relay returns a one-time token. The helper keeps it in process memory only and immediately exchanges it with `POST https://api2.onairos.uk/traits-only`.
6. The helper returns a compact, allowlisted persona. Hermes writes that text with its own `memory` tool.

## Local state and privacy

- Default state directory: `${HERMES_HOME}/state/onairos`, or `~/.hermes/state/onairos` when `HERMES_HOME` is unset.
- The filename is a SHA-256 digest of the Hermes session ID. Raw session keys are not placed in paths.
- On POSIX systems the directory is mode `0700` and state files are mode `0600`.
- State contains only `{"sessionId":"<uuid>"}`. It never contains access tokens or persona data.
- Completed, expired, malformed-complete, and consumed relays delete local state. Retryable pre-token network errors and pending relays retain it.
- Persona formatting accepts only archetype, ranked positive traits, personality dimensions, the full sanitized user summary, growth-area labels, up to three sanitized suggested actions, and connected-platform names. It rejects summaries containing instruction-like directives or apparent secret values, removes control characters, and caps summary text at 20,000 characters and total helper output at 24,000. Exceptional clipping is identified with an explicit marker. Hermes then curates that source through its bounded `user` and optional `memory` targets instead of writing it verbatim.
- HTTPS verification uses Python's configured trust roots. When a Python installation exposes no default CA file or directory, the helper loads the first available operating-system-managed CA bundle; it never disables certificate verification.

## Result meanings

| Result | Meaning | Agent action |
| --- | --- | --- |
| `pending` | Browser consent is not complete | Ask the user to finish, then wait |
| `no_session` | Connect was not run for this Hermes session | Start a fresh connection |
| `expired` | The ten-minute relay no longer exists | Start a fresh connection |
| `invalid_state` | Local session state failed validation | Start a fresh connection |
| `invalid_session` | Hermes supplied no safe session identity | Stop without connecting |
| `consumed` | The one-time result cannot be reused | Start a fresh connection |
| `network_error` | A DNS, timeout, TLS, or connection failure occurred before token pickup | Report the safe `reason`, then wait for an explicit retry request |
| `service_error` | Onairos returned a non-success HTTP response | Report the safe `status`, then wait for an explicit retry request |
| `invalid_response` | The service returned an unexpected shape | Report it once, then wait for an explicit retry request |

Never log exceptions containing authorization values, expose tokens to the model, copy raw service payloads into USER memory, or retry automatically after a helper error.

Hermes' `memory` replace action uses `old_text` as a locator substring and replaces the entire containing entry with `content`. `target: "user"` writes USER.md and `target: "memory"` writes MEMORY.md; their default limits are 1,375 and 2,200 characters respectively unless the user configured overrides. If more than one different entry matches, the tool refuses the operation and returns an inventory so the agent can choose unique locators rather than overwriting ambiguously.
