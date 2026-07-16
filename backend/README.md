# Nudgement — Optional Backend

This Flask backend is optional. The extension runs fully offline using local scoring.

## Purpose

- Provide a local `/analyze` endpoint for experimentation
- Store analysis history in `storage/` for debugging or training data collection
- All processing stays on your machine; binds to `127.0.0.1` only

## Run

```bash
pip install -r requirements.txt
python app.py
```

## Note on ML dependencies

`torch` and `transformers` have been removed. They were listed as potential future dependencies in the hackathon build but were never used.

Future ML improvements should use **WASM-based models** (ONNX Runtime Web, TensorFlow.js) that run inside the browser extension itself — no backend required, no gigabyte installs, works offline. This is the correct direction for a local-first privacy-preserving tool.

## API

- `GET /health` — engine version and status
- `POST /analyze` — score content, same interface as `scorer.js`

Required fields: `hash` (string) + at least one of `headline` / `snippet`.
