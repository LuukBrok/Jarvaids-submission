#!/usr/bin/env python3
"""Regenerate the contrast table body between the markers in each exploration.

    <!--CONTRAST:key-->  ... generated rows ...  <!--/CONTRAST-->

Idempotent, so it can be re-run after any token change. The tables are
generated and never hand-written, for the same reason spec/accessibility.md
generates its own: a hand-maintained contrast table stops matching what it
documents and nobody notices for six weeks.
"""
import glob
import io
import os
import re
import sys

import contrast

HERE = os.path.dirname(os.path.abspath(__file__))
BLOCK = re.compile(r"(<!--CONTRAST:([a-z]+)-->).*?(<!--/CONTRAST-->)", re.S)


def rows_html(key):
    buf, old = io.StringIO(), sys.stdout
    sys.stdout = buf
    try:
        contrast.main_key(key)
    finally:
        sys.stdout = old
    return buf.getvalue().rstrip("\n")


for path in sorted(glob.glob(os.path.join(HERE, "*.html"))):
    text = open(path, encoding="utf-8").read()
    if not BLOCK.search(text):
        continue
    keys = []

    def sub(m):
        keys.append(m.group(2))
        return "%s\n%s\n%s" % (m.group(1), rows_html(m.group(2)), m.group(3))

    open(path, "w", encoding="utf-8").write(BLOCK.sub(sub, text))
    print("injected %s into %s" % (", ".join(keys), os.path.basename(path)))
