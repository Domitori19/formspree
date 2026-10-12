# Formspree MCP Server

MCP server for working with Formspree forms (56 forms) from Claude.

## Configuration

Form IDs, names, and API keys are stored in `forms.json`, which Docker mounts
read-only at `/app/forms.json`.

Optional environment variables (in `.env` or `docker-compose.yml`):

| Variable | Default | Purpose |
|---|---|---|
| `MCP_PATH` | `/mcp` | HTTP path of the MCP endpoint. On a server set a secret path (`/mcp/<long-random-code>`): the URL itself is the access key |
| `ENABLE_SUBMIT_FORM` | `false` | Expose the `submit_form` tool |

With the default `/mcp` path the server is open — use that only on
`127.0.0.1`. For deployment on a server see `../mcp-deploy/README.md`.

## Run

```powershell
docker compose up -d --build
docker compose ps
```

Streamable HTTP is available locally at `http://127.0.0.1:9090/mcp`,
health check at `http://127.0.0.1:9090/health`.

Claude Desktop can also connect to the running container over stdio:

```json
{
  "mcpServers": {
    "formspree": {
      "command": "C:\Program Files\Docker\Docker\resources\bin\docker.exe",
      "args": [
        "exec",
        "-i",
        "mcp-formspree-server",
        "python",
        "-m",
        "src.server"
      ]
    }
  }
}
```

## Tools

- `list_all_forms`
- `compare_forms_leaderboard`
- `get_form_analytics`
- `list_submissions`
- `submit_form` (only when `ENABLE_SUBMIT_FORM=true`)

## Tests

```powershell
python -m pip install -r requirements-dev.txt
pytest -q
```
