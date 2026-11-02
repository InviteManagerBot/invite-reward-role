<div align="center">

<a href="https://invite-count.xyz"><img src="https://invite-count.xyz/images/logo.png" alt="InviteCount" height="72"></a>

# Invite Reward Role

**Give a Discord role when a member reaches N invites, powered by InviteCount invite alerts.**

[![CI](https://github.com/InviteManagerBot/invite-reward-role/actions/workflows/ci.yml/badge.svg)](https://github.com/InviteManagerBot/invite-reward-role/actions/workflows/ci.yml)
![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-3776ab)
![discord.py 2.7](https://img.shields.io/badge/discord.py-2.7-5865f2)
[![InviteCount Premium](https://img.shields.io/badge/InviteCount-Premium-f5a623)](https://invite-count.xyz/premium)

[Add InviteCount](https://invite-count.xyz/invite) · [Documentation](https://invite-count.xyz/docs) · [Premium](https://invite-count.xyz/premium) · [Support](https://invite-count.xyz/support)

</div>

---

This is an **example bot you host yourself**, for your own server's reward roles. [InviteCount](https://invite-count.xyz)
tracks who invited whom; when a member reaches one of your **invite alerts** (10, 50, 100 invites…), InviteCount sends a
request to your webhook. This bot receives that request and gives the matching reward role.

It is a small, readable starting point that you can run as is or adapt.

> [!IMPORTANT]
> Invite alerts and their webhook are an **InviteCount Premium** feature. On a free server InviteCount sends no
> request, so this bot never gives a role. See [invite-count.xyz/premium](https://invite-count.xyz/premium).

## Features

- `/rewards add`, `/rewards remove`, `/rewards list` slash commands, visible to administrators only by default.
- Webhook server (aiohttp) that checks your server's secret in constant time and validates the JSON body.
- Idempotent: roles the member already has are skipped; lower rewards missed while the bot was offline are caught up.
- Clear logs for every failure: role above the bot, missing **Manage Roles**, deleted role, member who left.
- SQLite storage (built into Python, no database server to install), configuration through environment variables.
- Docker image, `docker-compose.yml`, and CI (ruff + tests).

## How it works

```
a member joins with an invite
        │
        ▼
InviteCount: the inviter now has exactly 50 invites, and 50 is an invite alert
        │  POST https://your-domain.example/webhook
        │  Authorization: <your server's webhook secret>
        ▼
this bot: checks the secret, then gives every reward role of 50 invites or less
```

### The request InviteCount sends

```http
POST /webhook HTTP/1.1
Content-Type: application/json
User-Agent: InviteCountBot (https://invite-count.xyz)
Authorization: <your server's webhook secret>

{
  "user": {"username": "john", "id": "987654321098765432", "avatar": "a1b2c3…", "discriminator": "0", "bot": false},
  "invites": 50,
  "guild_id": "123456789012345678",
  "type": "reached"
}
```

- The secret is sent **as is** in the `Authorization` header. There is no HMAC signature and no timestamp, so the bot
  compares the header with `WEBHOOK_SECRET` using `hmac.compare_digest` (constant time). This is why HTTPS is required:
  see [Security](#security).
- `invites` is the inviter's total (regular + bonus invites) and always equals one of your alert amounts.
- `type` is always `"reached"`. InviteCount sends nothing when a member loses invites, so this bot never removes a role
  on its own.
- `/alert-invites webhook test` sends the same body with `"invites": -1`; the bot logs it and gives nothing.
- InviteCount waits 5 seconds for an answer and does not follow redirects. The bot answers `200` right away and gives the
  roles in the background.

## Requirements

- A Discord server with **InviteCount Premium**, where you are an administrator.
- Python **3.11+**, or Docker.
- A public **HTTPS** address that reaches the bot: a VPS with a domain and a reverse proxy (Caddy, nginx…), or a tunnel
  such as Cloudflare Tunnel. InviteCount refuses private and local addresses.

## Setup

### 1. Create the Discord application

1. Open the [Discord Developer Portal](https://discord.com/developers/applications) → **New Application**.
2. **Bot** tab → **Reset Token**, and copy the token (it goes in `DISCORD_TOKEN`). No privileged intent is needed.
3. **OAuth2 → URL Generator**: scopes `bot` and `applications.commands`, bot permission **Manage Roles**. Open the
   generated link and add the bot to your server.
4. In **Server Settings → Roles**, drag the bot's role **above** every reward role. Discord does not let a bot give a
   role placed higher than its own.

### 2. Point InviteCount to the bot and get your server's secret

The secret is **not** an InviteCount key. InviteCount generates one secret **for your server** when you set the webhook
URL, and only your server's administrators can see it. No InviteCount credential is needed or exposed.

In your server, run these InviteCount commands:

```text
/alert-invites webhook url webhook_url:https://your-domain.example/webhook
/alert-invites webhook secret
```

The first saves the address (run it again if the address changes). The second shows your server's secret in a private
reply: put it in `WEBHOOK_SECRET` in your `.env`. Never share it, and if it leaks, run
`/alert-invites webhook reset-secret`, then copy the new one into `.env` and restart the bot.

### 3. Configure the bot

```bash
git clone https://github.com/InviteManagerBot/invite-reward-role.git
cd invite-reward-role
cp .env.example .env
```

| Variable | Required | Default | Description |
| --- | --- | --- | --- |
| `DISCORD_TOKEN` | yes | | Bot token from the Developer Portal. |
| `WEBHOOK_SECRET` | yes | | Your server's secret, from `/alert-invites webhook secret`. |
| `WEBHOOK_HOST` | no | `0.0.0.0` | Address the webhook server listens on. |
| `WEBHOOK_PORT` | no | `8080` | Port the webhook server listens on. |
| `WEBHOOK_PATH` | no | `/webhook` | Path of the endpoint (the URL given to InviteCount must end with it). |
| `DATABASE_PATH` | no | `data/rewards.db` | SQLite file holding the rewards. |
| `DEV_GUILD_ID` | no | | Server where slash commands are synced instantly (a global sync can take a few minutes). |
| `LOG_LEVEL` | no | `INFO` | `DEBUG`, `INFO`, `WARNING` or `ERROR`. |

### 4. Run it

**With Docker** (the database lives in the `rewards-data` volume):

```bash
docker compose up -d --build
docker compose logs -f
```

The port is bound to `127.0.0.1:8080`: point your HTTPS reverse proxy to it. With Caddy, for example:

```caddy
your-domain.example {
    reverse_proxy 127.0.0.1:8080
}
```

**With Python:**

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m reward_bot
```

The logs should show `Logged in as …` and `Listening for InviteCount alerts on http://0.0.0.0:8080/webhook`.

### 5. Add the rewards, and the same numbers as InviteCount alerts

InviteCount only calls the webhook when a member reaches the exact number of one of your **invite alerts**, so every
reward needs an alert with the same number:

```text
/rewards add role:@Recruiter invites:10        ← this bot
/alert-invites add amount:10                   ← InviteCount
```

With a reward at 10 invites but only a 15-invite alert in InviteCount, nobody gets the role at 10; members get it at 15,
when that alert fires (the bot gives every reward of 15 or less). Compare `/rewards list` with `/alert-invites list`.

The webhook works without the **Invite alerts** log; turn that log on with `/logger add` (or Dashboard → **Logs**) if
you also want a message in a channel. See
[Logs and invite alerts](https://invite-count.xyz/docs/features/logging-and-invite-alerts).

### 6. Test

```text
/alert-invites webhook test
```

InviteCount shows the status code it received (`200` means it works), and the bot logs
`Test alert received from InviteCount … the webhook works`. `https://your-domain.example/health` should also answer
`{"ok": true}`.

## Commands

| Command | Description |
| --- | --- |
| `/rewards add role invites` | Give `role` when a member reaches `invites`. Running it again for the same role changes the number. |
| `/rewards remove role` | Stop giving `role` (members who already have it keep it). |
| `/rewards list` | Show the rewards, lowest first. |

The commands are visible to administrators only. You can change who sees them in **Server Settings → Integrations →
your bot**.

## Security

- **Keep the secret private.** Anyone who knows it can make the bot give reward roles. It belongs in `.env` (ignored by
  git) or in your host's secret store, never in the code, a screenshot or a public channel. If it leaks, run
  `/alert-invites webhook reset-secret` and update `WEBHOOK_SECRET`.
- **Use HTTPS.** The secret travels in a header; over plain HTTP anyone on the path can read it. Terminate TLS in a
  reverse proxy and keep the bot's port closed to the outside (the compose file binds it to localhost).
- **No replay protection.** InviteCount sends no timestamp or nonce, so a captured request could be replayed. Behind
  HTTPS a request cannot be captured in practice, and a replay could only give roles up to an invite count the member
  already reached once.
- Give the bot **Manage Roles** only, and keep its role just above the reward roles, below your staff roles.

## Troubleshooting

| Symptom | Cause and fix |
| --- | --- |
| The test says the request could not be made | The URL is not reachable from the internet, its certificate is invalid, it redirects (redirects are not followed), or it takes more than 5 seconds to answer. |
| The test returns `401` | `WEBHOOK_SECRET` is not your server's current secret. Copy it again with `/alert-invites webhook secret` (it changes after a `reset-secret`). InviteCount may keep sending the old one for up to a minute after a reset. |
| The test returns `404` | The URL given to InviteCount must end with `WEBHOOK_PATH` (`/webhook` by default). |
| The test works, but nobody gets a role | No InviteCount alert at that number (`/alert-invites list`), the server is no longer Premium, the reward is missing (`/rewards list`), or the invite was counted as fake. A new alert can take up to a minute to be used. |
| Log: `move the bot's role above it` | Drag the bot's role above the reward role in **Server Settings → Roles**. |
| Log: `the bot needs Manage Roles` | Give the bot's role the **Manage Roles** permission. |
| Log: `the bot is not in that server` | The alert comes from a server the bot was not added to. |
| Slash commands do not show up | A global sync can take a few minutes: set `DEV_GUILD_ID` for an instant sync, and check that the bot was invited with `applications.commands`. |

## Development

```bash
pip install -e ".[dev]"
ruff check . && ruff format --check .
pytest
```

The tests cover the secret check, the payload parsing (with the exact body InviteCount sends), the reward storage and
the HTTP endpoint.

| File | Role |
| --- | --- |
| `reward_bot/webhook.py` | Secret check, payload parsing, aiohttp endpoint. |
| `reward_bot/bot.py` | Discord client, `/rewards` commands, role granting. |
| `reward_bot/db.py` | SQLite storage. |
| `reward_bot/config.py` | Environment variables. |

## Support

Questions about InviteCount, alerts or Premium: [InviteCount support server](https://invite-count.xyz/support).
