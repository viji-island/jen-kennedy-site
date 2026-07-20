# Jen Kennedy — Costume Design portfolio

Self-contained static site. No build step, no dependencies: `index.html` + `assets/`.
Only external requests: Google Fonts (Fraunces, Fragment Mono) and YouTube (trailer lightbox, on demand).

## Local preview
    python3 -m http.server 8080
    # then open http://localhost:8080

## Deploy (choose one)
- **Vercel**: `npx vercel --prod` from this folder (needs a Vercel login).
- **Netlify**: drag this folder into https://app.netlify.com/drop (no CLI needed).
- **GitHub Pages**: push repo, enable Pages on main branch, root folder.

Then point the domain's A/CNAME records at the host, per its dashboard instructions.

## Content status (2026-07-20)
- Rivals of Amziah King release year set to 2027 per Jen (official sources said Aug 2026 — confirm).
- Parachute cast cards intentionally unnamed (casting unverified publicly; possible embargo).
- Tell Me a Secret cast portraits pending from Jen.
- IMDb / Instagram footer links are placeholders.
- About page, project subpages, and Jen's portrait: next phase.

## Capture mode
Append `?flat` for screenshot-friendly rendering (fixed hero height, no motion).
