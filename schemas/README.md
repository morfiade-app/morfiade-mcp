# Machine-readable tool schemas

Exactly what the server answers to `tools/list`, as JSON.

| File | Flags | Tools |
|---|---|---|
| `tools.json` | none | 18 |
| `tools-with-flags.json` | `--mcp-allow-cdp` and `--mcp-allow-scripts` | 20 |

The two extra tools are off by default on purpose: `browser_command` gives full
Chrome DevTools access to a running profile, and `run_script` executes code on
the owner's machine. Each is enabled by its own explicit flag, so a config that
does not ask for them cannot get them.

## Where these come from

Dumped from the server, not written by hand. They match the released build —
the dump is taken from the source at the release tag, with the working tree
clean, so the code that produced them is the code that shipped.

Regenerate after any release that touches tool definitions; the procedure is in
the private repository's `RELEASE.md`.

## What they are not

They are not documentation. `../docs/TOOLS.md` is the reference a person reads:
it groups the tools, explains every parameter and says which calls are slow and
why. These files are what a machine reads, and they carry only what the protocol
carries.

Both describe the same server, and `check_schemas.py` in this directory fails if
they ever stop agreeing on tool names or parameters.
