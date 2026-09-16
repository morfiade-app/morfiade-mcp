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

Requires Python 3.7+ and nothing else. MIT, like the rest of this repository.
"""

import os
import shutil
import subprocess
import sys

EXE_NAME = "Morfiade.exe"

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


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if os.name != "nt":
        _fail("Morfiade is a Windows program, so this launcher only makes "
              "sense on Windows.")
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
