# Farming assistant (knowledge only)

A chat assistant that answers farming questions from the notes in
[`knowledge/`](../../knowledge) and the crop calendar in
[`data/crop-calendar.json`](../../data/crop-calendar.json). It has no access to
sensor data; that is the farm agent's job (`backend/agent/`, Phase 3).

```
question ──► keyword search over knowledge/ ──┐
         └─► crop calendar lookup ────────────┼─► Claude ──► answer citing [note] / [calendar]
                (country, month, crop)        │
             nothing relevant found ──────────┴─► "I don't know" (no API call)
```

- **Retrieval** is keyword scoring (BM25) with a small English/French/Arabic
  synonym list, so it runs without a vector database. Good enough for ~100
  notes; switch to embeddings if the eval shows misses.
- **Answers cite** the notes they use as `[slug]` and the calendar as
  `[calendar]`; the API returns only the cited sources.
- **"I don't know"** when search finds nothing (no model call at all), or when
  the model finds the sources do not answer the question.
- **Language:** answers in the language of the question (English, French,
  Arabic).
- **Model:** `claude-opus-5-5` at low effort, with server-side refusal
  fallback enabled. Override with `ASSISTANT_MODEL` / `ASSISTANT_EFFORT`.
  Or use NVIDIA's API (OpenAI-compatible): set `NVIDIA_API_KEY` (and
  optionally `NVIDIA_MODEL`, default `meta/llama-3.3-70b-instruct`). With only
  the NVIDIA key set it is picked automatically; `LLM_PROVIDER=anthropic|nvidia`
  forces one. See `greenloop_assistant/llm.py`.

## Run it

```bash
cd backend/assistant
python -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env            # put NVIDIA_API_KEY or ANTHROPIC_API_KEY in .env (never commit it)

python -m greenloop_assistant "When do I plant potatoes in Latvia?"   # one question
uvicorn greenloop_assistant.server:app --port 8010                    # chat page at http://localhost:8010
```

API: `POST /api/assistant/chat` with `{"question": "..."}` returns
`{"answer": "...", "sources": [{"type": "note", "slug": "...", "title": "..."}, {"type": "calendar", ...}]}`.
`GET /api/assistant/health` reports how many notes and calendar rows are loaded.

The chat page (`static/index.html`) is self-contained, so the dashboard can
embed it later; set `window.ASSISTANT_API` to the service URL when it is served
from another origin.

By default it reads `../../knowledge` and `../../data/crop-calendar.json`. Point it
elsewhere with `KNOWLEDGE_DIR` and `CROP_CALENDAR`; `sample-knowledge/` holds 5
notes for quick experiments and tests.

## Tests and evals

```bash
pytest                          # unit tests, no API key needed (the model is faked)
python evals/run_eval.py        # 22 questions: checks the right notes are retrieved
python evals/run_eval.py --live # also asks the model and checks each answer's content
```

Run the eval before each change to the notes, the search, or the prompt.
`evals/questions.jsonl` lists, per question, the sources that must be found
and the words the answer must contain. Add a line whenever the assistant gets
something wrong.

## Deploy

The assistant runs on Vercel as one serverless function; see
[docs/deploy-vercel.md](../../docs/deploy-vercel.md).
