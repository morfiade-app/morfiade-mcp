# Ready-made client configs

All four say the same thing in the dialect of a different client: run
`Morfiade.exe` with `--mcp` and talk to it over stdio. Replace the path with
your own if you installed elsewhere — or use
[`launcher_config.json`](launcher_config.json), which lets the launcher find it.

| File | For | Where its contents go |
|---|---|---|
| [`claude_desktop_config.json`](claude_desktop_config.json) | Claude Desktop | `claude_desktop_config.json` (Settings → Developer → Edit Config) |
| [`cursor_mcp.json`](cursor_mcp.json) | Cursor | `.cursor/mcp.json` in the project, or the global one |
| [`vscode_mcp.json`](vscode_mcp.json) | VS Code | `.vscode/mcp.json` — note that it says `servers`, not `mcpServers`, and wants an explicit `"type": "stdio"` |
| [`launcher_config.json`](launcher_config.json) | anything, without a hardcoded path | the same place as the config for your client |

Claude Code needs no file at all:

```
claude mcp add morfiade -- "C:\Program Files\Morfiade\Morfiade.exe" --mcp
```

Gemini CLI and other clients keep their own format and their own location, and
those move more often than this folder — check the client's own documentation and
copy the `command` / `args` pair across.

To turn on one of the tools that are off by default, add the flag to `args`:

```json
"args": ["--mcp", "--mcp-allow-cdp"]
```

Read what that one actually grants before you do —
[README](../README.md#dangerous-flags-off-by-default).
