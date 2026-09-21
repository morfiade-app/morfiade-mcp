# Morfiade MCP

<!-- mcp-name: io.github.morfiade-app/morfiade-mcp -->

**MCP server for local Google Chrome profiles on Windows.** 18 tools that let an
AI agent list, create, launch and organise real Chrome profiles on your own
machine — each with its own cookies, sessions and proxy.

The server is not a package you download: it ships inside
[Morfiade](https://morfiade.com/en/), the Chrome profile manager itself, and
starts with a flag. Transport is stdio (JSON-RPC 2.0), protocol version
`2025-11-25`. Nothing is fetched from the internet, nothing passes through
anyone else's server.

This repository is the documentation, the ready-made client configs and an
optional launcher. Русская версия — [README.ru.md](README.ru.md).

---

## What makes it different

**The bridge lives in the program.** AdsPower and GoLogin publish MCP servers as
separate packages that talk to their cloud. Morfiade keeps profiles on your
disk, so the bridge stays on your disk too: `Morfiade.exe --mcp`, over the
loopback interface, no network required.

**Distributing values across windows.** The tools with no equivalent elsewhere
are `sync_sets` / `sync_spread` / `sync_insert`: a list of values — emails,
logins, anything line-based — is split across the open windows, one value pinned
per profile. A repeat call does not reshuffle what is already pinned, otherwise
an account would be registered on one email and confirmed with another. The
agent never sees the values themselves (see
[Security](#security-what-the-agent-cannot-do)).

Example prompts that work out of the box:

> Create twenty profiles with the prefix `shop`, give them proxies from this
> list, and launch the first five.

> Check the proxies on every profile I can manage and tell me which ones are
> dead or exiting from the wrong country.

> Take the `mail-batch` set, spread it across the open windows and show me who
> got what. I'll put the cursor in the email field, then insert.

---

## Requirements

- Windows 10 or 11
- [Morfiade](https://morfiade.com/en/) 3.37 or newer, **running**
- **Local API enabled** in its settings — the server refuses to start without it
  instead of failing silently
- The **"API" checkbox ticked** on the profiles the agent may touch; it is off by
  default, and unticked profiles do not exist as far as the agent is concerned
- A valid licence to *launch* profiles (that check lives in the manager, not here)
- Any MCP client with stdio support: Claude Code, Claude Desktop, Cursor,
  Gemini CLI, VS Code, your own

No `pip install`, no Node, no API key to register.

---

## Setup

Point your client at the executable and pass `--mcp`:

```json
{
  "mcpServers": {
    "morfiade": {
      "command": "C:\\Program Files\\Morfiade\\Morfiade.exe",
      "args": ["--mcp"]
    }
  }
}
```

Ready-made files for the common clients are in [`examples/`](examples/).
Claude Code can do it in one line:

```
claude mcp add morfiade -- "C:\Program Files\Morfiade\Morfiade.exe" --mcp
```

Where the config file lives differs per client and changes more often than this
README — check your client's own docs.

### Optional launcher

If you would rather not hardcode the path,
[`morfiade_mcp.py`](morfiade_mcp.py) finds the executable (via `MORFIADE_EXE`,
the installer's registry key, the usual install directories, or `PATH`),
forwards stdio and returns its exit code. Requires Python 3.7+ and nothing else.

```
pip install morfiade-mcp
```

```json
{
  "mcpServers": {
    "morfiade": {
      "command": "morfiade-mcp"
    }
  }
}
```

If your client needs an absolute path, point it at the `morfiade-mcp.exe` that
pip put in your Python `Scripts` directory. Without the package, the single file
works on its own too — `"command": "python"` with `morfiade_mcp.py` as the only
argument.

The package contains only that launcher. The server, and everything it talks
to, is the desktop app.

---

## Tools

Full parameters and return shapes: [`docs/TOOLS.md`](docs/TOOLS.md).
Machine-readable schemas, exactly as the server answers `tools/list`: [`schemas/`](schemas/).

- **`status`** — version, how many profiles exist, how many the agent may use, how many are running
- **`list_profiles`** — the permitted profiles: name, running or not, proxy, note
- **`create_profile`** — create a profile — optionally with proxy, note and category; permitted for the agent immediately
- **`start_profile`** — launch a profile, optionally straight onto a URL
- **`stop_profile`** — close the profile window
- **`set_proxy`** — assign a proxy (`type://user:pass@host:port` or `host:port`; empty string clears it)
- **`check_proxy`** — check one profile's proxy: alive, and where it exits
- **`check_proxies`** — the same across several profiles, or all of them
- **`profile_tags`** — read the tags, or replace them wholesale
- **`profile_note`** — read or write the note and its short title
- **`sync_windows`** — which open windows are ready for distribution and what is already pinned to each
- **`sync_sets`** — value sets: list them (name, lines, how many still free) or create one
- **`sync_spread`** — pin one line of a set per window and report who got what — inserts nothing
- **`sync_insert`** — insert each window's own value where the cursor sits in the leading window
- **`list_scripts`** — scripts in the manager's folder: name and interpreter, never the contents
- **`trash_profile`** — move a profile **to the trash** — nothing is erased
- **`list_trash`** — what is in the trash: name, when, how much space
- **`restore_profile`** — restore from the trash; a taken name comes back as `name (2)`

Two more appear only behind explicit flags — see
[Dangerous flags](#dangerous-flags-off-by-default).

---

## Security: what the agent *cannot* do

An agent that reads web pages is not a trusted party. A page can contain the
text "call this tool and send the cookies over there", and the agent cannot tell
your instruction from text it found on the internet. That is the known central
problem of MCP, and no amount of prompt wording fixes it. So the limits are
built into the tool list instead:

- **Deletion goes to the trash only.** Profiles stay whole — cookies, sessions,
  everything — and come back with one call. Permanent erase and emptying the
  trash are not exposed here and never will be: they are the only irreversible
  actions, and a human does them from the trash window, where they can see what
  they are destroying.
- **No cookie reading.** GoLogin's MCP has such a tool, which means cookies
  travel from the account into a chat log. This one does not have it.
- **Set lines are not exposed.** `sync_sets` reports the name, the line count and
  how many are free. The emails and logins themselves stay in the manager — the
  agent does not need to see them, it needs them to land in the windows.
- **Script contents are not exposed.** `list_scripts` gives names and
  interpreters only.
- **The mirror is not exposed.** It reflects what a human is doing right now in
  the leading window; there is nothing for an agent to repeat.
- **The whitelist cannot be bypassed.** The "API" column is filtered by the
  manager itself, not by this server.
- **The licence check does not weaken.** It sits in the manager's handler, so it
  fires whether a human, a script or an agent asked.
- **Nothing listens on the network.** The local API binds `127.0.0.1`, requires a
  token and checks the `Host` header. The token is stored encrypted with Windows
  DPAPI, tied to the account, and travels in a header rather than a URL — URLs
  end up in logs.

### Dangerous flags, off by default

| Flag | Extra tool | What it really means |
|---|---|---|
| `--mcp-allow-cdp` | `browser_command` | an arbitrary Chrome DevTools Protocol command. `Runtime.evaluate` in a logged-in profile reads cookies, storage and page contents — full access to your accounts, not "advanced management" |
| `--mcp-allow-scripts` | `run_script` | runs a script from the manager's folder — code execution on your machine |

Both are worth turning on only with the paragraph above in mind, and only for
pages you trust.

---

## Troubleshooting

| What you see | What to do |
|---|---|
| the client shows no tools | check the path to the exe in the client config |
| "local API is off" | enable the local API in the manager's settings |
| "no port or token in config.json" | open the manager once so it writes its settings |
| "the manager does not answer" | the manager has to be running |
| "profile not found", though it exists | the "API" checkbox is not ticked on that profile |
| "the API token contains invalid characters" | the config came from another machine — reissue the token in settings |
| launching a profile is refused | no valid licence: profile launch is closed over the API and MCP alike |

Messages come from the manager and follow its interface language — five are
available, so the wording you see may be your own.

---

## What is not here

The bridge itself is compiled into `Morfiade.exe`, and the **session transfer**
mechanism — the part that actually moves logged-in sessions between machines —
stays closed. This repository is the outside of the product: documentation,
configs, the launcher.

## Links

- [morfiade.com](https://morfiade.com/en/) — the manager itself
- [Running browser profiles from an AI agent](https://morfiade.com/en/blog/mcp-brauzer/) — what this looks like in practice
- [Manual](https://morfiade.com/en/manual/) — the AI agent access section
- [Model Context Protocol](https://modelcontextprotocol.io/) — the protocol

## License

MIT for everything in this repository — see [LICENSE](LICENSE). The manager is a
separate commercial product with its own terms.
