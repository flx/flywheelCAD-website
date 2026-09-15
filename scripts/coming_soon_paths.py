#!/usr/bin/env python3
"""Give every page of the full site a "coming soon" copy in coming-soon/.

    python3 scripts/coming_soon_paths.py

Why: while the Pages output directory is `coming-soon`, a URL that exists only
in the full site should show "coming soon". Cloudflare Pages kept serving old
copies of full-site pages that had been fetched before the switch (headers
`s-maxage=604800`, `age`, `x-robots-tag: noindex`), and a zone "Purge
Everything" did not clear them. A path that exists in the current deployment
is always served fresh, so each full-site page path gets the coming-soon page
here. Re-run after adding pages to public/.
"""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUBLIC = os.path.join(ROOT, "public")
SOON = os.path.join(ROOT, "coming-soon")

page = open(os.path.join(SOON, "404.html"), encoding="utf-8").read()
written = 0
for dirpath, _, files in os.walk(PUBLIC):
    if "index.html" not in files:
        continue
    rel = os.path.relpath(dirpath, PUBLIC)
    if rel == ".":
        continue  # coming-soon/index.html is the real home page
    out = os.path.join(SOON, rel, "index.html")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write(page)
    written += 1

# Files from the old stub that were served at the repo root.
with open(os.path.join(SOON, "README.md"), "w", encoding="utf-8") as f:
    f.write("# FlywheelCAD\n\nComing soon. https://flywheelcad.com/\n")
with open(os.path.join(SOON, "hero-snippet.html"), "w", encoding="utf-8") as f:
    f.write(page)
print(f"wrote {written} page copies + README.md + hero-snippet.html into coming-soon/")
