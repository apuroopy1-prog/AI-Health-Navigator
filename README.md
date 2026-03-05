# AI Health Navigator

> **Clinical decision support system with RAG, LangGraph workflows, and voice interface** — deployed on AWS with Google Vertex AI vector search.

[![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)](https://python.org)
[![LangGraph](https://img.shields.io/badge/LangGraph-Workflow_Orchestration-FF6B35)](https://langchain-ai.github.io/langgraph/)
[![Vertex AI](https://img.shields.io/badge/Google_Vertex_AI-Vector_Search-4285F4?logo=google-cloud)](https://cloud.google.com/vertex-ai)
[![AWS](https://img.shields.io/badge/AWS-App_Runner_+_EC2-FF9900?logo=amazon-aws)](https://aws.amazon.com)
[![Streamlit](https://img.shields.io/badge/Streamlit-UI-FF4B4B?logo=streamlit)](https://streamlit.io)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker)](https://docker.com)

---

## What It Does

AI Health Navigator helps patients navigate health symptoms with AI-assisted triage. A **LangGraph multi-step workflow** assesses symptoms, retrieves relevant medical knowledge via RAG, and recommends care pathways — from self-care to emergency referral.

Built for production: Docker Compose locally, deployed to **AWS App Runner** with CI/CD.

---

## Architecture

```
User (Streamlit UI)
        │
        ▼
┌───────────────────────────────────┐
│        LangGraph Workflow         │
│  Symptom Intake → Triage Engine   │
│         → RAG Retrieval           │
│         → Care Recommendation     │
└───────────────────────────────────┘
        │
        ▼
   Vertex AI Matching Engine
   (medical knowledge base)
```

---

## RAG Pipeline

| Component | Details |
|---|---|
| **Embedding Model** | Google `text-embedding-004` via Vertex AI |
| **Vector Store** | Vertex AI Matching Engine (ANN search) |
| **Chunking** | 512-token chunks, 50-token overlap |
| **Retrieval** | Top-k semantic search over indexed medical corpus |

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Orchestration** | LangGraph (multi-step workflow) |
| **Embeddings** | Google `text-embedding-004` (Vertex AI) |
| **Vector Search** | Vertex AI Matching Engine |
| **UI** | Streamlit |
| **Backend** | FastAPI |
| **Infra** | Docker Compose, AWS App Runner, EC2 |
| **CI/CD** | GitHub Actions |

---

## Quick Start

```bash
git clone https://github.com/apuroopy1-prog/AI-Health-Navigator.git
cd AI-Health-Navigator

# Local mode (no GCP required)
python streamlit_langgraph.py --mode local

# Or with Docker
cp .env.example .env
docker compose up -d --build
```

### Environment Variables (Production)

```env
GOOGLE_APPLICATION_CREDENTIALS=path/to/service-account.json
GCP_PROJECT_ID=your_project_id
GCP_REGION=us-central1
VECTOR_ENDPOINT_ID=your_endpoint_id
DEPLOYED_INDEX_ID=your_deployed_index_id
VECTOR_INDEX_ID=your_index_id
```

---

## Built By

**Apuroop Yarabarla** — AI/ML Engineer & AI Product Owner

[![LinkedIn](https://img.shields.io/badge/LinkedIn-apuroopyarabarla-0077B5?logo=linkedin)](https://linkedin.com/in/apuroopyarabarla)
[![GitHub](https://img.shields.io/badge/GitHub-apuroopy1--prog-181717?logo=github)](https://github.com/apuroopy1-prog)
