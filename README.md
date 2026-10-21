# TikTok LIVE Messi vs Ronaldo — Pro Version

This version is designed for a TikTok LIVE vote overlay.

## Rules
- A comment exactly equal to `messi` => Messi +1
- A comment exactly equal to `ronaldo` => Ronaldo +1
- `ronsldo` is also accepted for Ronaldo
- `I vote Messi` is ignored.
- Every matching comment counts, including multiple comments from the same user.

## Features
- Real-time TikTok LIVE comment reader
- Automatic reconnect loop when the LIVE is offline/disconnected
- SQLite vote history
- Reset button
- Clean OBS/browser overlay at `/overlay`
- Dashboard at `/`
- Scores survive browser refresh and app restart

## Start
Python 3.10+ recommended.

    python -m venv .venv
    # Windows:
    .venv\Scripts\activate
    # macOS/Linux:
    source .venv/bin/activate

    pip install -r requirements.txt
    uvicorn app:app --host 0.0.0.0 --port 8000

Open:
    http://localhost:8000

OBS Browser Source:
    http://YOUR-PC-IP:8000/overlay

For a public hosted version, deploy this Python app on a server with HTTPS/WSS and use its `/overlay` URL in OBS.

## Important
TikTokLive is an unofficial third-party reverse-engineered connector to TikTok LIVE's internal Webcast service. TikTok can change its internal protocol, so the connector may require updates. It does not use a TikTok Developer API key for ordinary public LIVE streams.

## Production note
For a permanent public service, a managed TikTok LIVE WebSocket/API provider is preferable to relying on a reverse-engineered connector. Keep the vote logic and overlay exactly as-is.
