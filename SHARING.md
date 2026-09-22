# Sharing the app with someone (e.g. your supervisor)

The app is one program: a small server that hosts both the website and the
analysis engine. To let someone else open it in their browser you just need to
give that server a public web address. Two ways, easiest first.

---

## Option A — a temporary link (no accounts, ~2 minutes)

Best for "try it while we're on a call" or a quick review.

1. Open **PowerShell** in this folder (`C:\dev\dr-danquah`).
2. Run:

   ```powershell
   powershell -ExecutionPolicy Bypass -File share.ps1
   ```

3. The first run installs a small tool called **cloudflared** and builds the app
   (a few minutes). After that it's fast.
4. Watch the window for a line like:

   ```
   https://something-random-words.trycloudflare.com
   ```

   That is the link. Copy it and send it to the person.
5. **Keep the PowerShell window open** and your computer awake the whole time
   they're using it. Closing the window takes the link down.
   Each time you run `share.ps1` the link is different.

If the cloudflared install is blocked on your machine, the script automatically
falls back to a no-install method (it may ask you to type `yes` once) and prints
a `https://….lhr.life` link instead.

### Limitations of Option A
- The link only works while `share.ps1` is running on your computer.
- It's meant for demos, not for many people or long-term use.
- Data (projects, uploads) lives on your computer as usual.

---

## Option B — a permanent link (one free account, always online)

Best for "here's a link, poke at it whenever". The app runs on a free hosting
service instead of your laptop. Recommended: **Hugging Face Spaces** (free, no
credit card).

1. Create a free account at <https://huggingface.co/join>.
2. Go to <https://huggingface.co/new-space>:
   - **Space name**: e.g. `research-analysis-agent`
   - **License**: any (e.g. MIT)
   - **Space SDK**: choose **Docker** → **Blank**
   - **Hardware**: the free **CPU basic** is enough
   - Visibility: **Private** if you only want to share by link with your account,
     or **Public**.
3. On the new Space page, open the **Files** tab → **Add file** → **Upload files**,
   and drag in **everything from this folder** *except* these (they're large and
   rebuilt automatically): `backend\.venv`, `backend\app.db`, `backend\uploads`,
   `frontend\node_modules`, `frontend\dist`, `.git`.
   (The `Dockerfile` in this folder tells the Space how to build itself.)
4. Add one small file so the Space knows which port to use. **Add file → Create a
   new file**, name it `README.md`, paste this and commit:

   ```
   ---
   title: Research Data Analysis Agent
   sdk: docker
   app_port: 8000
   ---
   ```

5. The Space builds automatically (5–10 minutes the first time). When it says
   **Running**, the address at the top of the page (e.g.
   `https://your-name-research-analysis-agent.hf.space`) is your permanent link.

### Turning on the AI features (optional)
The app works without it (rule-based recommendations, simple chat). To enable the
smarter AI recommendations and chat:
- In the Space, go to **Settings → Variables and secrets → New secret**
- Name: `ANTHROPIC_API_KEY`, Value: your key from <https://console.anthropic.com>
- The Space restarts and AI features switch on. (This costs money per use.)

### Note on saved data
On the free tier the Space's storage resets when it restarts or sleeps (after
~48h idle). Fine for a demo. For durable storage, upgrade the Space to add a
persistent disk, or point `DATABASE_URL` at a hosted database.

---

## Other hosts

The same `Dockerfile` also works on **Render**, **Railway**, and **Fly.io**
(each needs an account and, usually, the code pushed to GitHub first). Render and
Railway inject a `PORT` variable, which the `Dockerfile` already handles.

---

## Making it a desktop or mobile app (later)

This is a web app, so the realistic paths are:
- **Desktop**: wrap it with **Tauri** or **Electron** — the same web UI in a
  window, with the Python server bundled alongside. Meaningful extra work.
- **Mobile**: the web app is already responsive; "install to home screen" from a
  phone browser gives an app-like icon with no code changes. A true native app
  (React Native / Flutter) would be a separate front-end project talking to this
  same server.

For now, a hosted web link (Option B) is the fastest way to put it in someone's
hands on any device.
