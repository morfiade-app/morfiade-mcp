#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Launcher for the Morfiade MCP server.

A client can start ``Morfiade.exe --mcp`` directly, and that is the shortest
path — see the README. This script exists for one reason: so a client config
does not have to carry an absolute path that differs on every machine.

It finds the executable, starts it in MCP mode and gets out of the way: stdin
and stdout are inherited by the child, so the JSON-RPC stream stays untouched —
nothing here parses, buffers or logs it. Diagnostics go to stderr, which the
protocol leaves free.

Search order:

1. ``MORFIADE_EXE`` — an explicit path wins over everything, and a wrong one is
   reported rather than quietly ignored;
2. the installer's uninstall key — ``InstallLocation``, written by Inno Setup,
   so a custom install directory is found too;
3. the usual install directories;
4. ``PATH``.

Extra arguments are passed through, so the flags off by default still work::

    python morfiade_mcp.py --mcp-allow-cdp

Outside Windows — or with ``MORFIADE_MCP_SCHEMA_ONLY=1`` — there is no program
to start, and the launcher answers by itself in **schema-only mode**: the
handshake and ``tools/list`` come from ``schemas/tools.json``, which is dumped
from the real server, so a directory can inspect the tools; every
``tools/call`` returns an error saying the program runs on Windows. Nothing is
pretended: no tool does anything in this mode.

Requires Python 3.7+ and nothing else. MIT, like the rest of this repository.
"""

import json
import os
import shutil
import subprocess
import sys

__version__ = "0.2.2"

EXE_NAME = "Morfiade.exe"

# What the server inside Morfiade answers to the handshake; schema-only mode
# repeats it so a client sees the same server either way.
PROTOCOL_VERSION = "2025-11-25"
SERVER_NAME = "morfiade"
SCHEMA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schemas")
SCHEMA_PACKAGE = "morfiade_mcp_schemas"

# Off by default in the real server, each behind its own flag.
FLAG_TOOLS = {"--mcp-allow-cdp": "browser_command",
              "--mcp-allow-scripts": "run_script"}

# The AppId of the installer, hence the key Inno Setup writes. Under HKLM for an
# all-user install (the default), under HKCU when installed for one user.
UNINSTALL_KEY = (r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"
                 r"\{D4DAC94F-56AD-443B-96B0-8F011DEF1918}_is1")

# Exit code 2 is what the server itself returns when it cannot start. Keeping it
# the same means a client sees one code for "not running", whichever of us said so.
EXIT_NOT_READY = 2


def _fail(message):
    sys.stderr.write(message.rstrip() + "\n")
    sys.exit(EXIT_NOT_READY)


def _from_registry():
    try:
        import winreg
    except ImportError:
        return None
    wow = UNINSTALL_KEY.replace("SOFTWARE\\", "SOFTWARE\\WOW6432Node\\", 1)
    places = ((winreg.HKEY_LOCAL_MACHINE, UNINSTALL_KEY),
              (winreg.HKEY_LOCAL_MACHINE, wow),
              (winreg.HKEY_CURRENT_USER, UNINSTALL_KEY))
    for root, path in places:
        try:
            with winreg.OpenKey(root, path) as key:
                location = winreg.QueryValueEx(key, "InstallLocation")[0]
        except OSError:
            continue
        candidate = os.path.join(location, EXE_NAME)
        if os.path.isfile(candidate):
            return candidate
    return None


def _from_known_dirs():
    for variable in ("ProgramFiles", "ProgramFiles(x86)", "LOCALAPPDATA"):
        base = os.environ.get(variable)
        if not base:
            continue
        for folder in ("Morfiade", os.path.join("Programs", "Morfiade")):
            candidate = os.path.join(base, folder, EXE_NAME)
            if os.path.isfile(candidate):
                return candidate
    return None


def find_executable():
    explicit = os.environ.get("MORFIADE_EXE")
    if explicit:
        if os.path.isfile(explicit):
            return explicit
        _fail("MORFIADE_EXE points at %s, and there is no file there. Fix the "
              "variable or unset it to let this launcher search." % explicit)
    return _from_registry() or _from_known_dirs() or shutil.which(EXE_NAME)


def _handles_available():
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        try:
            stream.fileno()
        except Exception:
            return False
    return True


def _run(command):
    """Start the server so that it really gets our stdin and stdout.

    ⚠️ Measured, not assumed. With subprocess defaults (``stdin=None``,
    ``stdout=None``) the child started and exited 0 without writing a single
    byte — which in a client looks exactly like "the MCP server closes
    immediately". Handing the handles over explicitly fixes it, and
    ``close_fds=False`` fixes it the same way when our own streams have no file
    descriptor to hand over.
    """
    if _handles_available():
        return subprocess.call(command, stdin=sys.stdin, stdout=sys.stdout,
                               stderr=sys.stderr)
    return subprocess.call(command, close_fds=False)


def _schema_dir():
    """Where the schemas are: next to this file in a clone of the repository,
    or inside the installed package (pip install morfiade-mcp)."""
    if os.path.isdir(SCHEMA_DIR):
        return SCHEMA_DIR
    try:
        import importlib.util
        spec = importlib.util.find_spec(SCHEMA_PACKAGE)
    except ImportError:
        spec = None
    for place in (spec.submodule_search_locations or []) if spec else []:
        if os.path.isdir(place):
            return place
    return SCHEMA_DIR


def _schema_tools(argv):
    """The tools the real server would list for these flags."""
    path = os.path.join(_schema_dir(), "tools-with-flags.json")
    try:
        with open(path, encoding="utf-8") as f:
            tools = json.load(f)
    except (OSError, ValueError) as error:
        _fail("Morfiade is a Windows program, and the tool schemas for "
              "schema-only mode are missing (%s): reinstall with pip "
              "install morfiade-mcp, or run from a clone of "
              "https://github.com/morfiade-app/morfiade-mcp" % error)
    hidden = {name for flag, name in FLAG_TOOLS.items() if flag not in argv}
    return [t for t in tools if t.get("name") not in hidden]


def serve_schema_only(argv, stream_in=None, stream_out=None):
    """Answer the protocol from the published schemas; call nothing.

    For machines where Morfiade cannot run — above all the Linux containers in
    which MCP directories start a server to list its tools. The answers match
    the real server: same handshake, same tool definitions. Only calling a tool
    differs, and it says why instead of failing silently.
    """
    stream_in = stream_in or sys.stdin
    stream_out = stream_out or sys.stdout
    tools = _schema_tools(argv)
    refusal = ("Morfiade is a Windows desktop program, and this server is "
               "running in schema-only mode, so no tool can act here. Install "
               "Morfiade on Windows (https://morfiade.com/en/) and point the "
               "client at it.")

    def answer(method, params):
        if method == "initialize":
            asked = params.get("protocolVersion")
            return {"protocolVersion": asked if asked == PROTOCOL_VERSION
                    else PROTOCOL_VERSION,
                    "capabilities": {"tools": {"listChanged": False}},
                    "serverInfo": {"name": SERVER_NAME, "version": __version__},
                    "instructions": (
                        "Morfiade browser profile management, schema-only "
                        "mode: tools are listed but cannot run outside "
                        "Windows.")}
        if method == "ping":
            return {}
        if method == "tools/list":
            return {"tools": tools}
        if method == "tools/call":
            return {"isError": True,
                    "content": [{"type": "text", "text": refusal}]}
        raise LookupError("method not supported: %s" % method)

    sys.stderr.write("morfiade-mcp: schema-only mode, %d tools listed, none "
                     "can run here\n" % len(tools))
    for line in stream_in:
        line = line.strip()
        if not line:
            continue
        try:
            message = json.loads(line)
        except ValueError:
            reply = {"jsonrpc": "2.0", "id": None,
                     "error": {"code": -32700, "message": "malformed JSON"}}
        else:
            ident = message.get("id")
            if ident is None:
                continue                      # a notification needs no answer
            try:
                reply = {"jsonrpc": "2.0", "id": ident,
                         "result": answer(message.get("method"),
                                          message.get("params") or {})}
            except LookupError as error:
                reply = {"jsonrpc": "2.0", "id": ident,
                         "error": {"code": -32601, "message": str(error)}}
        stream_out.write(json.dumps(reply, ensure_ascii=True) + "\n")
        stream_out.flush()
    return 0


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if os.name != "nt" or os.environ.get("MORFIADE_MCP_SCHEMA_ONLY") == "1":
        return serve_schema_only(argv)
    executable = find_executable()
    if not executable:
        _fail("%s not found. Install Morfiade (https://morfiade.com/), or set "
              "MORFIADE_EXE to the full path of the executable if it lives "
              "somewhere unusual." % EXE_NAME)
    # --mcp goes first and only once; everything the client passed follows.
    command = [executable, "--mcp"] + [a for a in argv if a != "--mcp"]
    try:
        return _run(command)
    except KeyboardInterrupt:
        return 130
    except OSError as error:
        _fail("could not start %s: %s" % (executable, error))


if __name__ == "__main__":
    sys.exit(main())
