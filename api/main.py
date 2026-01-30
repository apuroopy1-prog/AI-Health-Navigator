"""
FastAPI Backend for AI Health Navigator
RESTful API for patient assessments, chat, and agent orchestration
"""
import logging
from datetime import datetime
from typing import List, Optional
from contextlib import asynccontextmanager

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from database.mongodb_client import patient_repo, mongo_client
from database.pinecone_client import pinecone_rag
from api.routes import patients, assessments, chat, appointments, medications, followups

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - startup and shutdown"""
    # Startup
    logger.info("Starting AI Health Navigator API...")

    # Connect to MongoDB
    mongo_client.connect()

    # Initialize Pinecone (optional - will use fallback if not configured)
    pinecone_rag.initialize_index()

    yield

    # Shutdown
    logger.info("Shutting down API...")
    mongo_client.close()


# Create FastAPI app
app = FastAPI(
    title="AI Health Navigator API",
    description="Enterprise AI-powered patient assessment system with multi-agent collaboration",
    version="2.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(patients.router, prefix="/api/v1/patients", tags=["Patients"])
app.include_router(assessments.router, prefix="/api/v1/assessments", tags=["Assessments"])
app.include_router(chat.router, prefix="/api/v1/chat", tags=["Chat"])
app.include_router(appointments.router, prefix="/api/v1/appointments", tags=["Appointments"])
app.include_router(medications.router, prefix="/api/v1/medications", tags=["Medications"])
app.include_router(followups.router, prefix="/api/v1/followups", tags=["Follow-ups"])


# ==================== Health Check ====================

@app.get("/health")
async def health_check():
    """API health check endpoint"""
    return {
        "status": "healthy",
        "service": "AI Health Navigator",
        "version": "2.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/")
async def root():
    """Root endpoint with API info"""
    return {
        "name": "AI Health Navigator API",
        "version": "2.0.0",
        "description": "Enterprise AI-powered patient assessment system",
        "docs": "/docs",
        "endpoints": {
            "patients": "/api/v1/patients",
            "assessments": "/api/v1/assessments",
            "chat": "/api/v1/chat",
            "appointments": "/api/v1/appointments",
            "medications": "/api/v1/medications",
            "followups": "/api/v1/followups"
        }
    }


# ==================== Run with Uvicorn ====================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
