# Jen Kennedy — Costume Design

Static portfolio site. One `index.html`, one `assets/` folder, no build step, no dependencies,
no third-party requests (fonts are self-hosted; YouTube loads only when a trailer is opened).

## Local preview
    python3 -m http.server 8080     # then open http://localhost:8080

## Live preview
https://viji-island.github.io/jen-kennedy-site/ — shareable anywhere, auto-updates on push.
Preview hosts inject `noindex` at runtime so they can never outrank the real domain.

## Deploy
- **Netlify Free** (recommended): `netlify.toml` sets caching + security headers. Netlify's Free
  plan permits commercial use and lists portfolios explicitly.
- **Vercel**: `vercel.json` is equivalent, but the free **Hobby plan is non-commercial only** and
  this site promotes a working designer and routes enquiries to her agency — use Vercel Pro if you
  prefer Vercel.
- **GitHub Pages** (already running, zero extra accounts): add a `CNAME` file with the domain,
  then point DNS at GitHub. Free HTTPS. Trade-off: Pages ignores `vercel.json`, so no CSP or
  cache headers, and the repo must stay public.

**Domain**: jenkennedycostumedesign.com is registered with Squarespace Domains, paid through
May 2027. Going live = repointing its A / CNAME records at the chosen host. No transfer, no
repurchase, existing links keep working. Cancel the Squarespace *website* subscription
afterwards — the domain registration is a separate product and survives.

## Conventions
- Every project row has a stable id, so `/#his-and-hers` opens that project directly — handy for
  sending a producer straight to one credit.
- `?flat` renders without motion and with a fixed hero height, for clean screenshots.
- Below-hero images carry `data-src` and are swapped in on row open, row hover, or page idle.
  Only the hero image is on the critical path.
- Preview hosts (github.io etc.) inject `noindex` at runtime so they can never outrank the real
  domain. The allowlist lives in the head script — update it if the production domain changes.

## Before DNS cutover
1. Release year settled: The Rivals of Amziah King opens August 14, 2026 (official site,
   Wikipedia, exhibitor listings) — the site now says August 2026 everywhere.
2. Parachute cast portraits are back in, per Viji's decision (Jen's own asset). Named cast
   portraits on Rivals / God of the Woods are Wikimedia Commons photos (CC-licensed:
   McConaughey TIFF 2025, Russell by Gage Skidmore, Hawke, Condon TIFF 2025) — replace with
   Jen's or studio-supplied portraits when available.
3. Disable GitHub Pages for this repo, so the preview cannot be indexed or linger.
4. When repointing DNS, change only the web A / CNAME records. Leave MX and TXT records alone or
   Jen's email breaks.
5. Smoke-test on a real iPhone in portrait *and* landscape before announcing.

## Content still owed by Jen
- Parachute: names for the two cast portraits, and the director once announced.
- Tell Me a Secret: cast portraits + names (nothing public/verifiable exists yet), and director.
- About: a portrait of Jen and two lines of bio.
- Verify the IMDb profile linked in the footer is hers.
