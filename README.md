# RLM Tutorial Notebook

A from-scratch, runnable tutorial that builds a Recursive Language Model (RLM)
step by step and uses it to answer questions about CAE simulation papers under
`/home/juli/RLM/CAE-MDs`.

## Run

```bash
cd /home/juli/RLM/rlm-tutorial
cp .env.example .env       # then edit .env to put your real key
pip install "openai>=1" python-dotenv nbformat ipykernel jupyterlab
jupyter lab rlm_tutorial.ipynb
```

## What you'll build

- v1: Minimal RLM (REPL + `FINAL` + main loop)
- v2: Add async recursive `await llm_query(...)` — mirrors fast-rlm
- v3: Add a `search_kb` keyword-search tool over `/home/juli/RLM/CAE-MDs`
- Two real Q&A runs against the corpus

## Warnings

- The notebook runs LLM-generated Python via in-process `exec()`. **No sandbox.**
  Only run on your own machine; do not expose to untrusted prompts.
- `.env` holds your API key and is excluded from git via `.gitignore`.
- Default model is a DeepSeek reasoning model; iterative RLM loops may be slow
  if `thinking` cannot be disabled. The notebook auto-detects on first call.
