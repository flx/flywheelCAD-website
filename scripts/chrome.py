#!/usr/bin/env python3
"""Stamp the shared chrome into every page, and check the site.

Pages are complete HTML files. The parts every page shares sit between
markers and are written ONLY by this script, from partials/:

    <!-- chrome:head --> ... <!-- /chrome:head -->                 partials/head.html
    <!-- chrome:head-standalone --> ... <!-- /chrome:head-standalone -->
                                        partials/head-standalone.html (User Manual)
    <!-- chrome:header --> ... <!-- /chrome:header -->             partials/header.html
    <!-- chrome:manual-nav --> ... <!-- /chrome:manual-nav -->     partials/manual-nav.html
    <!-- chrome:footer --> ... <!-- /chrome:footer -->             partials/footer.html
    <!-- chrome:version -->0.35<!-- /chrome:version -->            partials/version.txt

Usage:
    python3 scripts/chrome.py                 stamp every page under public/
    python3 scripts/chrome.py --file PATH     stamp one page (used by import_app.py)
    python3 scripts/chrome.py --check         exit 1 if any page is out of date or malformed
    python3 scripts/chrome.py --check --links also resolve every internal link and #anchor

It is an author-time include, not a generator: nothing runs at deploy time.
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUBLIC = os.path.join(ROOT, "public")
PARTIALS = os.path.join(ROOT, "partials")
BLOCKS = ["head", "head-standalone", "header", "manual-nav", "footer"]
MARKER = re.compile(r"(<!-- chrome:([a-z-]+) -->)(.*?)(<!-- /chrome:\2 -->)", re.S)
# The version marker also sits INSIDE the footer partial, where a block-level
# pass never looks (a match does not descend into its own text), so it is
# filled by its own pass over the whole page after the blocks are stamped.
VERSION = re.compile(r"(<!-- chrome:version -->)(.*?)(<!-- /chrome:version -->)", re.S)
FORBIDDEN = ["digitalhandstand.com/flywheelcad", "?v="]


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def page_path(file):
    """URL path a file is served at: public/manual/ui/index.html -> /manual/ui/."""
    rel = os.path.relpath(file, PUBLIC).replace(os.sep, "/")
    if rel == "index.html":
        return "/"
    if rel.endswith("/index.html"):
        return "/" + rel[: -len("index.html")]
    return None  # 404.html and other non-directory pages: no current link


def mark_current(html, path, section_links):
    """aria-current="page" on the exact link; "true" on a section link that
    prefixes the page (e.g. Manual on /manual/ui/)."""
    if path is None:
        return html

    def repl(m):
        tag, href = m.group(0), m.group(1)
        if href == path:
            return tag[:-1] + ' aria-current="page">'
        if section_links and href != "/" and href.endswith("/") and path.startswith(href):
            return tag[:-1] + ' aria-current="true">'
        return tag
    return re.sub(r'<a\b[^>]*\bhref="(/[^"#?]*)"[^>]*>', repl, html)


def stamp(html, file):
    partials = {name: read(os.path.join(PARTIALS, name + ".html")) for name in BLOCKS}
    version = read(os.path.join(PARTIALS, "version.txt")).strip()
    path = page_path(file)

    def fill(m):
        start, name, _, end = m.groups()
        if name == "version":
            return start + version + end
        if name not in partials:
            raise SystemExit(f"{file}: unknown chrome block '{name}'")
        body = partials[name]
        if name == "header":
            body = mark_current(body, path, section_links=True)
        elif name == "manual-nav":
            body = mark_current(body, path, section_links=False)
        return start + "\n" + body.strip("\n") + "\n" + end

    out = MARKER.sub(fill, html)
    return VERSION.sub(lambda m: m.group(1) + version + m.group(3), out)


def pages():
    for dirpath, _, files in os.walk(PUBLIC):
        for fn in sorted(files):
            if fn.endswith(".html"):
                yield os.path.join(dirpath, fn)


def check_head(html, file):
    problems = []
    if os.path.basename(file) == "404.html":
        return problems
    if not re.search(r"<title>[^<]+</title>", html):
        problems.append("no <title>")
    if not re.search(r'<meta name="description" content="[^"]+"', html):
        problems.append("no meta description")
    if not re.search(r'<link rel="canonical" href="https://flywheelcad\.com/[^"]*"', html):
        problems.append("no canonical")
    return problems


def resolve(target, file):
    """Filesystem path an internal URL serves, or None."""
    if target.startswith("/"):
        base = os.path.join(PUBLIC, target.lstrip("/"))
    else:
        base = os.path.normpath(os.path.join(os.path.dirname(file), target))
    candidates = [os.path.join(base, "index.html")] if target.endswith("/") or target == "" else [
        base, base + ".html", os.path.join(base, "index.html")]
    return next((c for c in candidates if os.path.isfile(c)), None)


def check_links(html, file):
    problems = []
    # (?<![\w-]) so that data-src="…" (an excerpt's source note) is not a link.
    for attr, url in re.findall(r'(?<![\w-])(href|src|poster)="([^"]+)"', html):
        if re.match(r"^(https?:|mailto:|data:|//)", url):
            continue
        target, _, frag = url.partition("#")
        target = target.split("?")[0]
        if target == "":
            dest = file
        else:
            dest = resolve(target, file)
            if dest is None:
                problems.append(f"broken {attr}: {url}")
                continue
        if frag and dest.endswith(".html"):
            if not re.search(r'\b(id|name)="%s"' % re.escape(frag), read(dest)):
                problems.append(f"missing anchor: {url}")
    return problems


def check_css_vars():
    css = read(os.path.join(PUBLIC, "assets", "chrome.css"))
    used = set(re.findall(r"var\(\s*(--[a-zA-Z0-9-]+)", css))
    defined = set(re.findall(r"(--[a-zA-Z0-9-]+)\s*:", css))
    return sorted(used - defined)


def main(argv):
    check = "--check" in argv
    links = "--links" in argv
    files = [os.path.abspath(argv[argv.index("--file") + 1])] if "--file" in argv else list(pages())

    failures = 0
    for file in files:
        html = read(file)
        stamped = stamp(html, file)
        rel = os.path.relpath(file, ROOT)
        if not check:
            if stamped != html:
                with open(file, "w", encoding="utf-8") as f:
                    f.write(stamped)
                print(f"stamped {rel}")
            continue
        problems = []
        if stamped != html:
            problems.append("chrome out of date (run scripts/chrome.py)")
        for m in list(MARKER.finditer(html)) + list(VERSION.finditer(html)):
            if not m.group(m.lastindex - 1).strip():
                problems.append(f"empty chrome block '{m.group(1)}'")
        problems += check_head(html, file)
        problems += [f"contains '{s}'" for s in FORBIDDEN if s in html]
        if links:
            problems += check_links(html, file)
        for p in problems:
            print(f"{rel}: {p}")
        failures += bool(problems)

    if check:
        undefined = check_css_vars()
        if undefined:
            print(f"public/assets/chrome.css: undefined custom properties {undefined}")
            failures += 1
        print(f"checked {len(files)} page(s): {'OK' if not failures else f'{failures} with problems'}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
