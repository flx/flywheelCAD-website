# flywheelcad-website

Static site for [flywheelcad.com](https://flywheelcad.com), deployed on Cloudflare Pages.

## Deployment

Cloudflare Pages is connected to this repository and deploys `main` automatically.

- Framework preset: **None**
- Build command: *(empty)*
- Build output directory: `/`

Pushing to `main` triggers a production deploy. Pull requests get preview deployments.

## Files

| Path | Purpose |
|---|---|
| `index.html` | Landing page |
| `404.html` | Not-found page (served automatically by Pages) |
| `robots.txt` | Crawl policy — allow everything |
| `sitemap.xml` | Sitemap, submitted to Google Search Console |
| `_headers` | Security headers applied at the edge |
| `_redirects` | Redirect rules (add when content moves here) |
