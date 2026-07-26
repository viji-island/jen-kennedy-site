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
1. Settle the release year for The Rivals of Amziah King. The site says 2027 (as instructed);
   Jen's current live site and public sources say 2026. One of them is wrong in public.
2. Parachute cast portraits were removed pending written clearance — re-add only once cleared.
3. Disable GitHub Pages for this repo, so the preview cannot be indexed or linger.
4. When repointing DNS, change only the web A / CNAME records. Leave MX and TXT records alone or
   Jen's email breaks.
5. Smoke-test on a real iPhone in portrait *and* landscape before announcing.

## Content still owed by Jen
- Confirm The Rivals of Amziah King release year (site says 2027; public sources said Aug 2026).
- Parachute cast: names for the two portraits, and whether the casting may be shown publicly.
- Tell Me a Secret: the two cast portraits.
- About: a portrait of Jen and two lines of bio.
- Verify the IMDb profile linked in the footer is hers.
