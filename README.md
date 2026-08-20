# Onairos for Hermes

Give Hermes a secure, consented understanding of who you are from the first conversation.

Onairos connects your existing persona to Hermes, then lets Hermes curate the useful context into its own durable memory. Authentication stays in your browser, and the agent receives only a sanitized persona—not your passwords, cookies, tokens, or raw account history.

Built by the [Onairos team](https://onairos.io).

## Install

```bash
hermes skills install onairos-dev/Hermes/onairos
```

Restart Hermes after installation. To skip the confirmation prompt, append `--yes`.

## Connect your profile

In Hermes, run:

```text
/onairos connect
```

Hermes opens the secure Onairos connection page and also provides a fallback link. Sign in, choose the sources you want to connect, and wait for **Profile synced**. Then return to Hermes and say:

```text
done
```

Hermes curates your persona into user memory and may save useful, durable working context when your profile contains it. The updated context loads automatically at the start of your next Hermes session.

## What Hermes can learn

- Your archetype and strongest traits
- Enduring interests, preferences, and goals
- The substance of your Onairos profile summary
- Growth areas and suggested actions
- Useful project or workflow context, when present

The skill does not send a raw activity dump to Hermes.

## Privacy by design

- Authentication and consent happen in your browser.
- You choose which sources to connect.
- The skill never asks for a password, token, cookie, or raw export.
- The local helper stores only a short-lived relay-session identifier.
- One-time access tokens remain in process memory and are never shown to Hermes.
- Only allowlisted, sanitized persona fields are returned to the agent.
- Hermes writes through its own memory tool; the skill never edits memory files directly.
- Connection links expire after thirty minutes, and completed results cannot be reused.

## Refresh your profile

Run `/onairos connect` again whenever you want to refresh your persona. Hermes replaces the previous Onairos entries while leaving unrelated memory untouched.

## Upgrading from the legacy MCP

Do not run the skill and the old Onairos MCP together. Remove the old `onairos` MCP configuration, uninstall `onairos-hermes-mcp` if it is still installed, restart Hermes, and then install this skill.

## Uninstall

```bash
hermes skills uninstall onairos
```

## Requirements

- [Hermes Agent](https://hermes-agent.nousresearch.com/)
- Python 3
- An Onairos account

## License

MIT © 2026 Onairos
