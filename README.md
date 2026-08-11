# Formspree MCP Server

MCP server for working with 43 Formspree forms from Claude Desktop.

## Configuration

The server has no `.env` file. Form IDs, names, and API keys are stored in
`forms.json`, which Docker mounts read-only at `/app/forms.json`.

## Run

```powershell
docker compose up -d --build
docker compose ps
```

SSE is available locally at `http://127.0.0.1:9090/sse`.

Claude Desktop connects to the running container over stdio:

```json
{
  "mcpServers": {
    "formspree": {
      "command": "C:\\Program Files\\Docker\\Docker\\resources\\bin\\docker.exe",
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
- `submit_form`

## Tests

```powershell
python -m pip install -r requirements-dev.txt
pytest -q
```
