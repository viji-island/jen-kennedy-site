# Jen Kennedy — Costume Design

Static portfolio site. One `index.html`, one `assets/` folder, no build step, no dependencies,
no third-party requests (fonts are self-hosted; YouTube loads only when a trailer is opened).

## Local preview
    python3 -m http.server 8080     # then open http://localhost:8080

## Deploy
- **Vercel** (recommended): import this repo at vercel.com, framework preset "Other". `vercel.json`
  already sets caching + security headers.
- **Netlify**: `netlify.toml` is equivalent; or drag the folder to app.netlify.com/drop.
- **Domain**: jenkennedycostumedesign.com is registered with Squarespace Domains (paid through
  May 2027). Going live = pointing its A / CNAME records at the host. No transfer needed.
  Cancel the Squarespace *website* subscription afterwards; the domain registration is separate.

## Conventions
- Every project row has a stable id, so `/#his-and-hers` opens that project directly — handy for
  sending a producer straight to one credit.
- `?flat` renders without motion and with a fixed hero height, for clean screenshots.
- Below-hero images carry `data-src` and are swapped in on row open, row hover, or page idle.
  Only the hero image is on the critical path.
- Preview hosts (github.io etc.) inject `noindex` at runtime so they can never outrank the real
  domain. The allowlist lives in the head script — update it if the production domain changes.

## Content still owed by Jen
- Confirm The Rivals of Amziah King release year (site says 2027; public sources said Aug 2026).
- Parachute cast: names for the two portraits, and whether the casting may be shown publicly.
- Tell Me a Secret: the two cast portraits.
- About: a portrait of Jen and two lines of bio.
- Verify the IMDb profile linked in the footer is hers.
