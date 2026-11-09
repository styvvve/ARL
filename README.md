# Agent Reliability Lab (ARL)

Assistant for **local** notes that searches and reads notes, answers based on them,
uses controlled tools and provides **verifiable** answers. Common thread of the course
"AI Agents: understanding, building, evaluating, securing".

The current state of the project is described in `JALON.md`.

## Installation
```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e .
arl diagnostic
```

## API
```bash
pip install -e ".[api]"
uvicorn arl.api:app
```
The configuration is loaded and the agent is built once, at startup.

- `POST /demander`: body `{"question": "..."}`, 1 to 500 characters after whitespace stripping.
  Returns the agent result: answer, status, steps, notes read, citation verification, tokens and duration.
  Returns 503 if the model service is unreachable or refuses the request.
- `GET /diagnostic`: returns `ready` and four checks: `notes`, `traces`, `ollama`, `model`.
  Returns 503 if a check fails.
