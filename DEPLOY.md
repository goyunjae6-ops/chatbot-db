# Render deployment repair

Use the current `goyunjae6-ops/chatbot-db` repository, branch `main`, for both services.
The old deployed frontend calls localhost and uses an outdated message endpoint.

## Backend (Web Service)

- Root Directory: `backend`
- Build Command: `pip install -r requirements.txt`
- Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- Environment: `CHAT_MODE=basic` (default; free offline replies, no API token needed)
- Optional AI mode: `CHAT_MODE=huggingface`, valid `HF_TOKEN`, supported `HF_MODEL` and inference credits
- Environment: `FRONTEND_ORIGINS=https://two026-chatbot-frontend.onrender.com`
- Deploy latest commit, then confirm `<backend URL>/health` returns JSON containing `"status":"ok"` and `"mode":"basic"`.

## Frontend (Static Site)

- Root Directory: `frontend`
- Build Command: `npm ci && npm run build`
- Publish Directory: `dist`
- Environment: `VITE_API_URL=<actual HTTPS backend URL>`
- Deploy latest commit after setting the variable; it is embedded at build time.

Confirm the frontend loads, creates a new conversation and receives a basic reply (or an AI reply if explicitly configured).
Use `/sessions/{id}/messages` (plural) for message requests.
The production build now rejects missing, non-HTTPS and localhost API URLs.

Local development remains available through `start.bat`; VS Code is optional.
