#!/usr/bin/env python3
"""Check that every code excerpt on the site still matches its source.

    python3 scripts/check_excerpts.py --app ~/Documents/Programming/swift/FlyWheelCADV3

An excerpt is a <pre data-src="path/in/app:10-20,30-31">. Its text must equal
the cited lines of that file, with ranges joined by one blank line. Run it
after the app's samples change; it exits 1 on the first page that drifted.
"""
import html
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUBLIC = os.path.join(ROOT, "public")


def expected(app, spec):
    path, _, ranges = spec.partition(":")
    lines = open(os.path.join(app, path), encoding="utf-8").read().split("\n")
    parts = []
    for r in ranges.split(","):
        a, _, b = r.partition("-")
        parts.append("\n".join(lines[int(a) - 1:int(b or a)]))
    return "\n\n".join(parts)


def main(argv):
    if "--app" not in argv:
        sys.exit("usage: check_excerpts.py --app PATH_TO_APP_CHECKOUT")
    app = os.path.abspath(os.path.expanduser(argv[argv.index("--app") + 1]))
    bad = checked = 0
    for dirpath, _, files in os.walk(PUBLIC):
        for fn in files:
            if not fn.endswith(".html"):
                continue
            page = os.path.join(dirpath, fn)
            text = open(page, encoding="utf-8").read()
            for spec, body in re.findall(r'<pre data-src="([^"]+)"><code>(.*?)</code></pre>', text, re.S):
                checked += 1
                if html.unescape(body) != expected(app, spec):
                    bad += 1
                    print(f"{os.path.relpath(page, ROOT)}: excerpt no longer matches {spec}")
    print(f"checked {checked} excerpt(s): {'OK' if not bad else f'{bad} drifted'}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
