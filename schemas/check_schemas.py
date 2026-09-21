#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Check that the reference and the schemas still describe the same server.

The reference (`../docs/TOOLS.md`) is written by hand on purpose: it groups the
tools, explains what each parameter means and says which calls are slow. The
schemas are dumped from the server. Neither can be generated from the other
without losing something, so they are kept apart — and this script is what
keeps them honest.

It fails if a tool exists in one and not the other, or if a tool's parameters
disagree. It deliberately does NOT compare wording: the reference explains, the
schema states, and they are allowed to read differently.

Run:  python schemas/check_schemas.py
"""

import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REFERENCE = os.path.join(HERE, os.pardir, 'docs', 'TOOLS.md')

# `### `name`` — a tool heading. The optional *(slow)* marker is not part of it.
HEADING = re.compile(r'^###\s+`([a-z_]+)`', re.M)
# `| `param` | type | …` — a parameter row of that tool's table.
PARAM = re.compile(r'^\|\s*`([a-z_]+)`\s*\|', re.M)


def sections(text):
    """Split the reference into {tool name: its body}."""
    out, marks = {}, list(HEADING.finditer(text))
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        out[m.group(1)] = text[m.end():end]
    return out


def main():
    schemas = {}
    for name in ('tools.json', 'tools-with-flags.json'):
        path = os.path.join(HERE, name)
        for tool in json.loads(io.open(path, encoding='utf-8').read()):
            schemas[tool['name']] = tool

    reference = sections(io.open(REFERENCE, encoding='utf-8').read())

    problems = []

    only_ref = sorted(set(reference) - set(schemas))
    only_schema = sorted(set(schemas) - set(reference))
    for name in only_ref:
        problems.append('%s: in the reference, not in the schemas' % name)
    for name in only_schema:
        problems.append('%s: in the schemas, not in the reference' % name)

    for name in sorted(set(reference) & set(schemas)):
        want = set((schemas[name].get('inputSchema') or {})
                   .get('properties', {}))
        got = set(PARAM.findall(reference[name]))
        for p in sorted(want - got):
            problems.append('%s: parameter `%s` is missing from the reference'
                            % (name, p))
        for p in sorted(got - want):
            problems.append('%s: the reference documents `%s`, which the '
                            'server does not accept' % (name, p))

    print('tools in schemas: %d, in the reference: %d'
          % (len(schemas), len(reference)))
    if problems:
        print('\nthey have drifted apart:')
        for p in problems:
            print('  -', p)
        return 1
    print('names and parameters agree')
    return 0


if __name__ == '__main__':
    sys.exit(main())
