# cf_ai_ideabank

An AI-powered idea management app built entirely on Cloudflare's developer platform. Chat with an AI assistant to brainstorm, save, refine, update, and delete ideas — all stored persistently per user via Durable Objects.

**Live demo:** https://cf_ai_ideabank.darellbarnes450.workers.dev/app

---

## What it does

- **Chat interface** — Have a natural conversation with an AI assistant about your ideas
- **Idea bank** — The AI can save, list, refine, update, and delete your ideas on command
- **Persistent memory** — Your ideas and chat history are stored per user via Cloudflare Durable Objects
- **Ideas page** — Browse, search, and delete all your saved ideas in a dedicated view
- **Multi-turn context** — The AI always knows your current saved ideas, so you can refer to them naturally ("refine the scrolling app idea")

---

## Architecture

| Component | Cloudflare Technology | Role |
|---|---|---|
| LLM | Workers AI — `@cf/meta/llama-3.1-8b-instruct` | Conversational AI, tool routing, idea refinement |
| State & coordination | Durable Objects | Per-user chat history and idea storage |
| Backend API | Workers (Python) | REST API — `/chat`, `/ideas` endpoints |
| Frontend | Static Assets binding | Serves `app.html` and `ideas-page.html` |

### Request flow

```
Browser → Cloudflare Worker (entry.py)
             ├── /app, /ideas-page  → Static Assets (HTML)
             ├── GET  /chat         → Durable Object → get history
             ├── POST /chat         → Durable Object → run LLM → execute tool → store
             ├── GET  /ideas        → Durable Object → list ideas
             └── DELETE /ideas      → Durable Object → delete idea
```

### AI tool system

The LLM responds in structured JSON with an optional `tool` field. The backend routes the tool to the appropriate Durable Object method:

```
add_idea      → stores idea with generated UUID
list_ideas    → returns all saved ideas
delete_idea   → removes idea and updates index
refine_idea   → runs a second LLM call to rewrite title + description
update_idea   → patches specific fields
```

The live idea list (IDs, titles, descriptions) is injected into the system prompt on every request so the model always operates on real data, never hallucinated state.

---

## Project structure

```
cf_ai_ideabank/
├── wrangler.jsonc          # Cloudflare Worker config
├── src/
│   ├── entry.py            # Worker entrypoint + Durable Object class
│   └── utils.py            # UUID generators, URL parsing helpers
└── static/
    ├── app.html            # Chat UI
    └── ideas-page.html     # Ideas browser UI
```

---

## Running locally

### Prerequisites

- [Node.js](https://nodejs.org/) (for Wrangler)
- [Wrangler CLI](https://developers.cloudflare.com/workers/wrangler/install-and-update/)
- A Cloudflare account with Workers AI enabled

```bash
npm install -g wrangler
wrangler login
```

### Deploy to Cloudflare

```bash
git clone https://github.com/darellbarnes450/cf_ai_ideabank
cd cf_ai_ideabank
wrangler deploy
```

Wrangler will output your deployed URL, e.g.:
```
https://cf_ai_ideabank.<your-subdomain>.workers.dev
```

Visit `/app` to start chatting.

### Local development

```bash
wrangler dev
```

Then open `http://localhost:8787/app`.

> Note: Workers AI bindings require a Cloudflare account even in local dev. `wrangler dev` proxies AI calls to Cloudflare remotely.

---

## Usage

### Chat page (`/app`)

1. Open the app — a unique user ID is generated and stored in your browser's `localStorage` on first visit
2. Type a message in the chat input to start brainstorming
3. When you're ready to save an idea, say something like **"add this to my idea bank"**
4. Ask the AI to **refine**, **update**, or **delete** any saved idea by referring to it naturally
5. Previous chats appear in the sidebar — click to resume any conversation

### Ideas page (`/ideas-page`)

- Displays all your saved ideas as cards
- Use the search bar to filter by title
- Click **✕** on any card to delete an idea

### Example prompts

```
"Help me brainstorm an app idea for tracking habits"
"Add this to my idea bank"
"Refine the habit tracker idea to be more specific"
"Show me all my ideas"
"Delete the habit tracker idea"
"Update the title to Daily Habit Tracker"
```

---

## API reference

All endpoints return `application/json`. CORS is enabled for all origins.

### `GET /chat`
Returns chat history for a user.

| Query param | Required | Description |
|---|---|---|
| `user_id` | No | Omit on first visit; server generates and returns one |
| `chat_id` | No | If provided, returns messages for that specific chat |

**Response:**
```json
{ "user_id": "user{uuid}", "history": { "chat:{uuid}": { "title": "...", "messages": [...] } } }
```

### `POST /chat`
Send a message and get an AI reply.

| Query param | Optional | Description |
|---|---|---|
| `chat_id` | Yes | Continue an existing chat |

**Body:**
```json
{ "message": "your message", "user_id": "user{uuid}" }
```

**Response:**
```json
{ "reply": "AI response", "uuid": "chat:{uuid}", "user_id": "...", "title": "...", "tool": "add_idea" }
```

### `DELETE /chat`
Delete a chat.

| Query param | Required |
|---|---|
| `user_id` | Yes |
| `chat_id` | Yes |

### `GET /ideas`
List all saved ideas (or search by title).

| Query param | Optional | Description |
|---|---|---|
| `user_id` | Yes | Required |
| `search` | No | Keyword search against idea titles |
| `idea_id` | No | Fetch a single idea by ID |

### `DELETE /ideas`
Delete a saved idea.

| Query param | Required |
|---|---|
| `user_id` | Yes |
| `idea_id` | Yes |

---

## Key design decisions

**Python Workers** — The backend is written in Python using Cloudflare's Python Workers runtime (Pyodide). This required specific workarounds: Python lists passed directly to JS AI bindings are destroyed by Pyodide's proxy system, so all AI inputs are serialized via `js.JSON.parse(json.dumps(...))` before being passed to the binding, and results are converted back with `.to_py()`.

**Single Durable Object per user** — All of a user's chats and ideas live in one Durable Object instance keyed by `user_id`. Keys are namespaced (`chat:uuid`, `idea:uuid`) to coexist in the same storage namespace.

**Stateless AI with injected context** — Rather than giving the model memory tools, the backend fetches the live idea index on every request and injects it into the system prompt. This is more reliable than asking the model to call `list_ideas` first.

**No authentication** — User identity is a UUID generated on first visit and stored in `localStorage`. This is intentional for simplicity — the app is a demo, not a multi-tenant production service.