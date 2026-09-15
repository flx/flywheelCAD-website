#!/usr/bin/env python3
"""Import the parts of flywheelcad.com that are built in the app repository.

    python3 scripts/import_app.py --app ~/Documents/Programming/swift/FlyWheelCADV3

Writes these, then stamps the pages with scripts/chrome.py:

    public/manual/index.html                     FlywheelCAD_manual.html (User Manual)
    public/manual/component-library/index.html   scripts/library_guide/gen_guide.py
    public/downloads/FlywheelCAD-AI-Scripting-Guide.md   scripts/publish-ai-guide.py
    public/downloads/FlywheelCAD-Samples.zip     scripts/package-sample-zips.py
    public/downloads/FlywheelCAD-Showcase.zip    scripts/package-sample-zips.py

The app's own scripts are loaded as modules and only their OUTPUT paths are
redirected, so their assembly rules and self-checks run unchanged. The site
pulls from the app; the app never writes into the site.

The component-library images are not rendered here (that needs a Release build;
see the app's scripts/library_guide/regenerate.sh). They live in
public/manual/component-library/images/ and this script refuses to write the
page if one it references is missing.

    python3 scripts/import_app.py --port-dh SRC.html DEST.html /url/path/

converts one digitalhandstand.com page to the site shell. It was used once to
move the hand-written manual pages here; they are edited in place since.
"""
import importlib.util
import os
import re
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUBLIC = os.path.join(ROOT, "public")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import chrome  # noqa: E402

# Old digitalhandstand URL -> new URL. Also the redirect map on that site.
URL_MAP = [
    ("/flywheelcad/manual/", "/manual/"),
    ("/flywheelcad/ui-interactions/", "/manual/ui/"),
    ("/flywheelcad/python-script-backend/", "/manual/python-backend/"),
    ("/flywheelcad/python-syntax/", "/manual/python-syntax/"),
    ("/flywheelcad/component-library/", "/manual/component-library/"),
    ("/flywheelcad/", "/"),
]

# The User Manual keeps its own stylesheet; this re-points its accent at the
# site's, mirroring all four of the manual's own token selectors so it wins in
# every theme (same specificity, later in the document).
MANUAL_ACCENT = """<style id="fw-accent">
  :root { --accent: #1f5f4f; --accent-soft: #e6f0ec; }
  @media (prefers-color-scheme: dark) { :root { --accent: #5fd6b4; --accent-soft: #14302a; } }
  :root[data-theme="dark"] { --accent: #5fd6b4; --accent-soft: #14302a; }
  :root[data-theme="light"] { --accent: #1f5f4f; --accent-soft: #e6f0ec; }
  /* Long inline identifiers must wrap on a phone rather than widen the page. */
  .wrap :not(pre) > code { overflow-wrap: anywhere; }
</style>"""


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    print("wrote", os.path.relpath(path, ROOT))


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def require(cond, msg):
    if not cond:
        sys.exit("import_app: " + msg)


def text_of(fragment):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", fragment)).strip()


# ---------------------------------------------------------------- User Manual
def import_manual(app):
    html = read(os.path.join(app, "FlywheelCAD_manual.html"))
    require(html.count("<style>") == 1 and html.count("</style>") == 1,
            "the manual no longer has exactly one <style> block")
    require('<div class="wrap">' in html, "the manual has no .wrap container")
    lead = re.search(r'<p class="lead">(.*?)</p>', html, re.S)
    require(lead, "the manual has no .lead paragraph to describe it")
    description = text_of(lead.group(1)).replace('"', "&quot;")

    html = re.sub(r"<title>.*?</title>", "<title>User Manual — FlywheelCAD</title>", html, count=1, flags=re.S)
    html = html.replace("</head>",
                        f'<meta name="description" content="{description}">\n'
                        '<link rel="canonical" href="https://flywheelcad.com/manual/">\n'
                        "<!-- chrome:head-standalone --><!-- /chrome:head-standalone -->\n"
                        f"{MANUAL_ACCENT}\n</head>", 1)
    html = re.sub(r"<body>", "<body>\n<!-- chrome:header --><!-- /chrome:header -->\n"
                  "<!-- chrome:manual-nav --><!-- /chrome:manual-nav -->", html, count=1)
    html = html.replace('<div class="wrap">', '<div class="wrap" id="main">', 1)
    html = html.replace("</body>", "<!-- chrome:footer --><!-- /chrome:footer -->\n</body>", 1)

    css = html[html.index("<style>"):html.index("</style>")]
    used = set(re.findall(r"var\(\s*(--[a-zA-Z0-9-]+)", css))
    defined = set(re.findall(r"(--[a-zA-Z0-9-]+)\s*:", css))
    require(used <= defined, f"the manual uses undefined custom properties {sorted(used - defined)}")

    out = os.path.join(PUBLIC, "manual", "index.html")
    write(out, html)
    chrome.main(["--file", out])


# ------------------------------------------------- digitalhandstand shell
def rewrite_urls(html):
    html = re.sub(r'((?:href|src)="[^"?]*)\?v=[^"]*"', r'\1"', html)
    for old, new in URL_MAP:
        html = html.replace(f'href="{old}', f'href="{new}')
    # Screenshots a page shows travel with it, in its own images/ folder.
    html = re.sub(r'((?:href|src)=")/assets/images/flywheelcad/examples/', r'\1images/', html)
    return html


def dh_to_page(src_html, url_path, extra_head=""):
    """One digitalhandstand.com FlywheelCAD page -> a flywheelcad.com manual page."""
    title = re.search(r"<title>(.*?)</title>", src_html, re.S).group(1)
    title = re.sub(r"\s*\|\s*Digital Handstand\s*$", "", title).replace("FlywheelCAD ", "").strip()
    desc = re.search(r'<meta\s+name="description"\s+content="([^"]*)"', src_html, re.S)
    require(desc, f"{url_path}: source page has no meta description")
    styles = "\n".join(re.findall(r"<style>.*?</style>", src_html, re.S))

    body = re.search(r'<main class="site-shell">(.*)</main>', src_html, re.S)
    require(body, f"{url_path}: no <main class=\"site-shell\">")
    body = body.group(1)
    body = re.sub(r'\s*<header class="topbar[^"]*">.*?</header>', "", body, count=1, flags=re.S)
    body = re.sub(r'\s*<a class="back-link"[^>]*>.*?</a>', "", body, count=1, flags=re.S)
    body = re.sub(r'\s*<nav class="doc-tabs".*?</nav>', "", body, flags=re.S)
    body = re.sub(r'\s*<script[^>]*lightbox\.js[^>]*></script>', "", body)
    body = re.sub(r'\s*animate-(?:rise|delay-\d)', "", body)

    hero = re.search(r'<section class="hero">(.*?)</section>', body, re.S)
    require(hero, f"{url_path}: no hero section")
    head_html = hero.group(1)
    head_html = re.sub(r'<span class="eyebrow">(.*?)</span>', r'<p class="eyebrow">\1</p>', head_html)
    head_html = re.sub(
        r'<div class="app-head">\s*<img[^>]*>\s*<div>\s*(<h1>.*?</h1>)\s*<p class="muted">(.*?)</p>\s*</div>\s*</div>',
        r'\1\n<p class="lede">\2</p>', head_html, flags=re.S)
    require('class="app-head"' not in head_html, f"{url_path}: unexpected hero layout")
    rest = body[hero.end():]

    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{title} — FlywheelCAD manual</title>
<meta name="description" content="{desc.group(1).strip()}">
<link rel="canonical" href="https://flywheelcad.com{url_path}">
<!-- chrome:head --><!-- /chrome:head -->
{styles}{extra_head}
</head>
<body>
<!-- chrome:header --><!-- /chrome:header -->
<!-- chrome:manual-nav --><!-- /chrome:manual-nav -->
<main id="main" class="doc">
<header class="doc-head">
{head_html.strip()}
</header>
<div class="doc-body">
{rest.strip()}
</div>
</main>
<!-- chrome:footer --><!-- /chrome:footer -->
</body>
</html>
"""
    return rewrite_urls(page)


# ---------------------------------------------------------- component library
def import_library(app):
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["SITE_DIR"] = tmp
        gen = load(os.path.join(app, "scripts", "library_guide", "gen_guide.py"), "fw_gen_guide")
        gen.build()
        src = read(gen.OUT)
    page = dh_to_page(src, "/manual/component-library/")
    images = os.path.join(PUBLIC, "manual", "component-library", "images")
    missing = [m for m in re.findall(r'src="images/([^"]+)"', page)
               if not os.path.isfile(os.path.join(images, m))]
    require(not missing, f"component-library images missing: {missing} "
                         "(render them with the app's scripts/library_guide/regenerate.sh)")
    out = os.path.join(PUBLIC, "manual", "component-library", "index.html")
    write(out, page)
    chrome.main(["--file", out])


# ------------------------------------------------------------------ downloads
def import_downloads(app):
    guide = load(os.path.join(app, "scripts", "publish-ai-guide.py"), "fw_publish_ai_guide")
    guide.OUT = os.path.join(PUBLIC, "downloads", "FlywheelCAD-AI-Scripting-Guide.md")
    guide.main()
    zips = load(os.path.join(app, "scripts", "package-sample-zips.py"), "fw_package_sample_zips")
    zips.DL = os.path.join(PUBLIC, "downloads")
    os.makedirs(zips.DL, exist_ok=True)
    zips.main()


def main(argv):
    if "--port-dh" in argv:
        i = argv.index("--port-dh")
        src, dest, url = argv[i + 1:i + 4]
        write(dest, dh_to_page(read(src), url))
        chrome.main(["--file", dest])
        return 0
    require("--app" in argv, "usage: import_app.py --app PATH_TO_APP_CHECKOUT")
    app = os.path.abspath(os.path.expanduser(argv[argv.index("--app") + 1]))
    require(os.path.isfile(os.path.join(app, "FlywheelCAD_manual.html")), f"{app} is not the app checkout")
    import_manual(app)
    import_library(app)
    import_downloads(app)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
