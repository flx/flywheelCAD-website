# flywheelcad-website

Static site for [flywheelcad.com](https://flywheelcad.com), deployed on Cloudflare Pages.

## Deployment

Cloudflare Pages is connected to this repository and deploys `main` automatically.

- Framework preset: **None**
- Build command: *(empty)*
- Build output directory: **`public`**

Pushing to `main` deploys production; every pushed branch gets a public preview
URL. The repository is public too — keep plans and drafts out of it (`plans/`
and `drafts/` are gitignored for that).

## Layout

| Path | Purpose |
|---|---|
| `public/` | Everything the site serves |
| `public/assets/site.css` | Content styles (pages, docs layer), light and dark |
| `public/assets/chrome.css` | Header, footer, manual navigation — self-contained |
| `public/assets/site.js` | Video play-when-visible, reduced motion, lightbox |
| `public/downloads/` | AI guide, sample zips (imported from the app repo) |
| `public/video/` | Loops. Cached for a year: give every re-cut a new file name |
| `partials/` | The shared head, header, footer, manual nav and `version.txt` |
| `scripts/chrome.py` | Stamps `partials/` into every page; `--check`, `--links` |
| `scripts/import_app.py` | Pulls the User Manual, component library, AI guide and zips from the app repo |
| `scripts/check_excerpts.py` | Checks that example code excerpts still match the app's samples |
| `.githooks/pre-push` | Runs `chrome.py --check --links` before `main` is pushed |

The DMG is not here: it is about 30 MB, over Pages' 25 MiB asset limit. The
download buttons point at
`https://github.com/flx/flywheelcad-releases/releases/latest/download/FlywheelCAD.dmg`.

## Working on the site

```sh
git config core.hooksPath .githooks          # once per clone
python3 -m http.server -d public 4173        # preview at http://localhost:4173
python3 scripts/chrome.py                    # after editing anything in partials/
python3 scripts/chrome.py --check --links    # before pushing
```

Pages are complete HTML files. The blocks between `<!-- chrome:NAME -->` markers
are written only by `scripts/chrome.py`; edit the partial, not the page.

## After a release

From the app checkout that was released:

```sh
python3 scripts/import_app.py --app ~/Documents/Programming/swift/FlyWheelCADV3
python3 scripts/check_excerpts.py --app ~/Documents/Programming/swift/FlyWheelCADV3
```

Then update `partials/version.txt`, run `python3 scripts/chrome.py`, add a post
under `public/news/` (and to `news/index.html`, `news/feed.xml` and the home
page's news list), and push. The component-library images come from the app's
`scripts/library_guide/regenerate.sh`; copy them into
`public/manual/component-library/images/` when the library changes.

Example renders come from the installed app's headless renderer, for example:

```sh
/Applications/FlywheelCAD.app/Contents/MacOS/FlywheelCAD snapshot Glider.fwcad \
  -o glider.png --view 3d --quality high --size 1600 --bg "#eef0f2" \
  --look-at 1025,0,120 --look-radius 1700 --view-dir -0.75,-1.0,0.85
```

cropped to 4:3 with ffmpeg (`-vf crop=1600:1200:0:<y>`).
