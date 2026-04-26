# AURA Phone Demo (Frontend-Only)

This demo is intentionally deterministic and frontend-only.

- No backend required
- No vLLM / FastAPI / SAM2 / Depth / Whisper required
- No keyboard shortcuts
- No voice path

## 1) Run on laptop

```bash
cd client
npm install
npm run dev -- --host 0.0.0.0
```

The dev server now defaults to HTTP for reliable localhost startup.

Optional checks:

```bash
cd client
npm run typecheck
npm run build
npm run test
```

## 2) Open on phone

Find your laptop LAN IP (for example `192.168.1.25`) and open:

`http://<laptop-ip>:5173`

Example:

`http://192.168.1.25:5173`

## 3) Put the three scene images here

Drop files into:

- `client/public/demo-scenes/medical1.png`
- `client/public/demo-scenes/sustainability2.png`
- `client/public/demo-scenes/wayfinding3.png`

If images are missing, demo still runs. The "Use reference image" helper button will only work after files are added.

## 4) Phone camera note (important)

On many mobile browsers, camera works only on secure origins (HTTPS) unless using localhost.
When opening from another device over LAN, use one of:

- **Option A**: deploy frontend to Vercel/Netlify (HTTPS out of the box)
- **Option B**: use an HTTPS tunnel (ngrok or cloudflared)
- **Option C**: run Vite over HTTPS with local certificates if your environment already supports it

The app itself does not hard-require local HTTPS config in code.

## 5) Demo flow

1. Open one scenario image full-screen on laptop/tablet.
2. Open AURA on phone.
3. You start directly in the baseline camera flow with scenario pills on top.
4. Tap one of:
   - Care Safety Scan
   - Sustainability Audit
   - Wayfinding Assistant
   - Take Photo / Free Scan
5. Point phone at displayed image and fill the 4:3 guide.
6. Tap capture.
7. Scenario modes show a short deterministic analysis animation and then overlay render.
8. Free Scan preserves normal capture-first behavior and shows neutral guidance with no scenario overlays.

