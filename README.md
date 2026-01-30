# AI Health Navigator

This repository contains `streamlit_langgraph.py`, an example health assessment workflow that uses LangGraph/Vertex AI in production, and local fallbacks for development.

Quick start (local dev):

1. Activate the project virtualenv (created for you in the workspace):

```bash
source .venv/bin/activate
```

2. Install minimal dependencies (already installed in the workspace used here):

```bash
pip install -r requirements.txt
```

3. Run the script in local mode (uses safe fallbacks, no GCP required):

```bash
python streamlit_langgraph.py --mode local
```

4. Optionally run the included pytest to validate the local run:

```bash
pytest -q
```

Production mode:

To run in production (real Vertex AI / Matching Engine), install the real SDKs and supply GCP credentials and environment variables. See the script `--mode production` checks and log messages for guidance.

Environment variables required for production:

- `GOOGLE_APPLICATION_CREDENTIALS` (path to service account JSON)
- `GCP_PROJECT_ID`
- `GCP_REGION`
- `VECTOR_ENDPOINT_ID`
- `DEPLOYED_INDEX_ID`
- `VECTOR_INDEX_ID`

If you want, I can help wire production credentials or add a configuration file.

Continuous Integration
----------------------

This repository includes a basic GitHub Actions workflow (`.github/workflows/ci.yml`) that runs tests on push and pull requests. The workflow installs the packages from `requirements.txt` and runs `pytest`.

To enable CI, push this repository to GitHub and open a pull request — the workflow will run automatically.
