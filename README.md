# Formspree MCP Server

Read-only analytics over all Formspree forms of the navsi100 tour sites: lead lists,
per-form analytics with a chart, and a cross-form leaderboard.

## Tools

| Tool | What it does |
|---|---|
| `list_all_forms` | List connected forms, search by word (`карпаты`, `italy`, …) |
| `compare_forms_leaderboard` | Leaderboard of all forms for a period, with growth/decline vs the previous period |
| `get_form_analytics` | Analytics and a text chart for one form |
| `list_submissions` | Table of the latest leads of one form |
| `submit_form` | Send a submission to a form — **disabled** unless `ENABLE_SUBMIT_FORM=true` |

## How to connect

The server runs at `https://formspree-mcp.navsi100.travel`. Access is protected by a
**secret URL**: `https://formspree-mcp.navsi100.travel/mcp/<secret-code>`.
Whoever has the URL has access — share it only privately. Get the current URL from the
server admin (`mcp-link show` on the server).

**Claude (Desktop, web, mobile)** — nothing to install:

1. Settings → Connectors → **Add custom connector**.
2. Name: `Formspree`, URL: the secret URL.
3. Authentication: **No sign-in**. Leave request headers empty. Add.

**Claude Code:**

```bash
claude mcp add --transport http formspree https://formspree-mcp.navsi100.travel/mcp/<secret-code>
```

Health check (no secret needed): `https://formspree-mcp.navsi100.travel/health`.

## Server deployment

Every push to `main` runs GitHub Actions: tests → build image `ghcr.io/domitori19/mcp-formspree`
→ deploy to the server over SSH (`deploy/docker-compose.yml` is copied to `/opt/mcp/formspree`).

Files that live **only on the server** (not in git):

| File | Contents |
|---|---|
| `/opt/mcp/formspree/.env` | `MCP_PATH=/mcp/<secret-code>` |
| `/opt/mcp/formspree/forms.json` | form IDs, names and Formspree API keys |

The container has no public port: Caddy of the bot project proxies
`formspree-mcp.navsi100.travel` to `mcp-formspree:9090` over the `telegrambotnew_default` network.

Rotate the secret URL (the old one stops working immediately):

```bash
mcp-link rotate formspree
```

Add a form: append it to `/opt/mcp/formspree/forms.json`, then `docker restart mcp-formspree`.

Repository secrets used by the workflow: `SERVER_HOST`, `SERVER_USER`, `SERVER_SSH_KEY`.

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `MCP_PATH` | `/mcp` | Endpoint path. On a server use a secret path `/mcp/<code>` (`openssl rand -hex 24`) |
| `ENABLE_SUBMIT_FORM` | `false` | Expose the `submit_form` tool |
| `HOST` / `PORT` | `0.0.0.0` / `9090` | Listen address in HTTP mode |
| `TRANSPORT` | `stdio` | `streamable-http` (or the `--http` flag) for network mode |

`forms.json` format — see `forms.example.json` (same structure, empty `api_key`).

## Local run

```powershell
docker compose up -d --build
```

Starts the HTTP server at `http://127.0.0.1:9090/mcp` (path `/mcp`, no secret — local use only).
The same container can also be used over stdio:

```json
{
  "mcpServers": {
    "formspree": {
      "command": "docker",
      "args": ["exec", "-i", "mcp-formspree-server", "python", "-m", "src.server"]
    }
  }
}
```

## Tests

```powershell
python -m pip install -r requirements-dev.txt
pytest -q
```

Tests need a `forms.json`; without the real one, copy `forms.example.json` to `forms.json`.
