"""
Pinecone Vector Database Client for Medical Knowledge RAG
"""
import os
import logging
from typing import List, Dict, Any, Optional
import json

from pinecone import Pinecone, ServerlessSpec
import boto3

logger = logging.getLogger(__name__)


class PineconeRAG:
    """
    Pinecone-powered RAG for medical knowledge retrieval.
    Uses AWS Bedrock for embeddings.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        index_name: str = "medical-knowledge",
        dimension: int = 1024,  # Titan embedding dimension
        region: str = "us-east-1"
    ):
        """
        Initialize Pinecone RAG client.

        Args:
            api_key: Pinecone API key (or from PINECONE_API_KEY env)
            index_name: Name of the Pinecone index
            dimension: Embedding dimension
            region: AWS region for Bedrock
        """
        self.api_key = api_key or os.getenv("PINECONE_API_KEY")
        self.index_name = index_name
        self.dimension = dimension
        self.region = region

        self._pc: Optional[Pinecone] = None
        self._index = None
        self._bedrock = None

        # Medical knowledge base for seeding
        self.medical_knowledge = self._load_medical_knowledge()

    def _get_pinecone(self) -> Pinecone:
        """Get or create Pinecone client"""
        if self._pc is None:
            if not self.api_key:
                logger.warning("Pinecone API key not set, using fallback mode")
                return None
            self._pc = Pinecone(api_key=self.api_key)
        return self._pc

    def _get_bedrock(self):
        """Get Bedrock client for embeddings"""
        if self._bedrock is None:
            self._bedrock = boto3.client(
                "bedrock-runtime",
                region_name=self.region
            )
        return self._bedrock

    def _get_embedding(self, text: str) -> List[float]:
        """
        Get embedding for text using AWS Bedrock Titan.

        Args:
            text: Text to embed

        Returns:
            Embedding vector
        """
        try:
            bedrock = self._get_bedrock()
            response = bedrock.invoke_model(
                modelId="amazon.titan-embed-text-v1",
                body=json.dumps({"inputText": text}),
                contentType="application/json",
                accept="application/json"
            )
            result = json.loads(response["body"].read())
            return result["embedding"]
        except Exception as e:
            logger.error(f"Embedding error: {e}")
            # Return zero vector as fallback
            return [0.0] * self.dimension

    def initialize_index(self) -> bool:
        """
        Initialize Pinecone index, create if not exists.

        Returns:
            True if successful
        """
        try:
            pc = self._get_pinecone()
            if pc is None:
                return False

            # Check if index exists
            existing_indexes = pc.list_indexes().names()

            if self.index_name not in existing_indexes:
                logger.info(f"Creating Pinecone index: {self.index_name}")
                pc.create_index(
                    name=self.index_name,
                    dimension=self.dimension,
                    metric="cosine",
                    spec=ServerlessSpec(
                        cloud="aws",
                        region="us-east-1"
                    )
                )

            self._index = pc.Index(self.index_name)
            logger.info(f"Connected to Pinecone index: {self.index_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize Pinecone: {e}")
            return False

    def seed_medical_knowledge(self) -> int:
        """
        Seed the index with medical knowledge base.

        Returns:
            Number of vectors upserted
        """
        if self._index is None:
            if not self.initialize_index():
                return 0

        vectors = []
        for i, (topic, facts) in enumerate(self.medical_knowledge.items()):
            for j, fact in enumerate(facts):
                vector_id = f"{topic}_{j}"
                embedding = self._get_embedding(fact)
                vectors.append({
                    "id": vector_id,
                    "values": embedding,
                    "metadata": {
                        "topic": topic,
                        "content": fact,
                        "type": "medical_fact"
                    }
                })

        # Upsert in batches
        batch_size = 100
        total_upserted = 0

        for i in range(0, len(vectors), batch_size):
            batch = vectors[i:i + batch_size]
            self._index.upsert(vectors=batch)
            total_upserted += len(batch)

        logger.info(f"Seeded {total_upserted} medical knowledge vectors")
        return total_upserted

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        filter_dict: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant medical knowledge for a query.

        Args:
            query: Search query (symptoms, conditions, etc.)
            top_k: Number of results to return
            filter_dict: Optional metadata filters

        Returns:
            List of relevant knowledge items with scores
        """
        # Fallback if Pinecone not configured
        if self._index is None:
            return self._fallback_retrieve(query, top_k)

        try:
            query_embedding = self._get_embedding(query)

            results = self._index.query(
                vector=query_embedding,
                top_k=top_k,
                include_metadata=True,
                filter=filter_dict
            )

            return [
                {
                    "id": match.id,
                    "score": match.score,
                    "content": match.metadata.get("content", ""),
                    "topic": match.metadata.get("topic", ""),
                }
                for match in results.matches
            ]

        except Exception as e:
            logger.error(f"Pinecone query error: {e}")
            return self._fallback_retrieve(query, top_k)

    def _fallback_retrieve(
        self,
        query: str,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Fallback keyword-based retrieval when Pinecone unavailable.
        """
        query_lower = query.lower()
        results = []

        for topic, facts in self.medical_knowledge.items():
            if topic in query_lower:
                for fact in facts:
                    results.append({
                        "id": f"{topic}_fallback",
                        "score": 0.8,
                        "content": fact,
                        "topic": topic
                    })

        # If no topic match, return general knowledge
        if not results:
            for topic, facts in self.medical_knowledge.items():
                for fact in facts:
                    if any(word in fact.lower() for word in query_lower.split()):
                        results.append({
                            "id": f"{topic}_keyword",
                            "score": 0.5,
                            "content": fact,
                            "topic": topic
                        })

        return results[:top_k]

    def _load_medical_knowledge(self) -> Dict[str, List[str]]:
        """Load comprehensive medical knowledge base"""
        return {
            "headache": [
                "Headaches are classified as primary (migraine, tension-type, cluster) or secondary to underlying conditions.",
                "Red flags for headaches include sudden severe onset (thunderclap), fever, neck stiffness, neurological deficits, or papilledema.",
                "Migraine headaches are characterized by unilateral pulsating pain, photophobia, phonophobia, and may have aura.",
                "Tension-type headaches present as bilateral, pressing/tightening quality, mild-moderate intensity.",
                "Cluster headaches are severe unilateral orbital/supraorbital pain with autonomic features.",
                "Initial headache workup includes neurological examination and consideration of imaging if red flags present.",
                "Medication overuse headache occurs with frequent use of acute headache medications (>10-15 days/month)."
            ],
            "chest_pain": [
                "Chest pain requires urgent evaluation to rule out acute coronary syndrome (ACS).",
                "Typical angina: substernal pressure/squeezing, provoked by exertion, relieved by rest or nitroglycerin.",
                "Atypical presentations more common in women, elderly, and diabetics - may present as dyspnea or fatigue.",
                "HEART score helps risk stratify chest pain: History, ECG, Age, Risk factors, Troponin.",
                "Aortic dissection presents with sudden severe tearing chest/back pain, may have unequal pulses.",
                "Pulmonary embolism presents with pleuritic chest pain, dyspnea, tachycardia, and risk factors for DVT.",
                "Initial ACS workup: ECG within 10 minutes, serial troponins, chest X-ray.",
                "STEMI requires immediate reperfusion therapy - PCI preferred if available within 120 minutes."
            ],
            "shortness_of_breath": [
                "Dyspnea differential includes cardiac, pulmonary, hematologic, and psychogenic causes.",
                "Heart failure presents with orthopnea, PND, peripheral edema, elevated JVP.",
                "COPD exacerbation: increased dyspnea, sputum volume, and sputum purulence.",
                "Asthma: episodic wheezing, cough, chest tightness, often with triggers.",
                "Pulmonary embolism: sudden dyspnea, pleuritic pain, tachycardia, hypoxia.",
                "Pneumonia: fever, productive cough, dyspnea, focal lung findings.",
                "Anxiety can cause hyperventilation syndrome with perioral/extremity paresthesias.",
                "BNP/NT-proBNP helpful in distinguishing cardiac from pulmonary causes."
            ],
            "abdominal_pain": [
                "Abdominal pain location helps localize pathology: RUQ (biliary), epigastric (gastric/pancreatic), RLQ (appendix).",
                "Peritoneal signs (rebound, guarding, rigidity) suggest surgical abdomen.",
                "Appendicitis: periumbilical pain migrating to RLQ, anorexia, fever, leukocytosis.",
                "Cholecystitis: RUQ pain after fatty meals, positive Murphy's sign, fever.",
                "Pancreatitis: epigastric pain radiating to back, nausea, elevated lipase.",
                "Small bowel obstruction: colicky pain, distension, vomiting, obstipation.",
                "Ectopic pregnancy must be considered in reproductive-age women with abdominal pain.",
                "AAA rupture: sudden severe abdominal/back pain, hypotension, pulsatile mass."
            ],
            "dizziness": [
                "Dizziness categories: vertigo (spinning), presyncope (lightheaded), disequilibrium (unsteady).",
                "BPPV: brief episodes triggered by head position changes, positive Dix-Hallpike.",
                "Vestibular neuritis: acute severe vertigo, nausea, nystagmus, no hearing loss.",
                "Meniere's disease: episodic vertigo with hearing loss, tinnitus, aural fullness.",
                "Central vertigo red flags: vertical nystagmus, direction-changing nystagmus, neurological deficits.",
                "Orthostatic hypotension: BP drop >20/10 mmHg on standing, causes presyncope.",
                "HINTS exam helps distinguish central from peripheral causes of acute vertigo.",
                "Posterior stroke can present with isolated vertigo - high clinical suspicion needed."
            ],
            "fatigue": [
                "Fatigue differential is broad: anemia, thyroid, depression, sleep disorders, chronic disease.",
                "Initial fatigue workup: CBC, CMP, TSH, glucose, consider ferritin and vitamin D.",
                "Hypothyroidism: fatigue, weight gain, cold intolerance, constipation, dry skin.",
                "Anemia symptoms: fatigue, dyspnea on exertion, pallor, tachycardia.",
                "Depression screening important - fatigue is a core symptom of major depression.",
                "Sleep apnea: snoring, witnessed apneas, daytime somnolence, morning headaches.",
                "Chronic fatigue syndrome: severe fatigue >6 months with PEM, unrefreshing sleep.",
                "Cancer-related fatigue is common and often multifactorial."
            ],
            "hypertension": [
                "Hypertension defined as BP ≥130/80 mmHg on repeated measurements.",
                "Essential hypertension accounts for 90-95% of cases.",
                "Secondary causes: renal disease, endocrine disorders, OSA, medications.",
                "Target organ damage: LVH, retinopathy, nephropathy, stroke, CAD.",
                "First-line medications: ACE inhibitors, ARBs, CCBs, thiazide diuretics.",
                "Hypertensive urgency: severely elevated BP without acute organ damage.",
                "Hypertensive emergency: severely elevated BP WITH acute organ damage.",
                "Lifestyle modifications: DASH diet, sodium restriction, weight loss, exercise."
            ],
            "diabetes": [
                "Type 2 DM: insulin resistance progressing to beta cell failure.",
                "Diagnosis: A1C ≥6.5%, fasting glucose ≥126, random glucose ≥200 with symptoms.",
                "Microvascular complications: retinopathy, nephropathy, neuropathy.",
                "Macrovascular complications: CAD, stroke, peripheral arterial disease.",
                "Metformin is first-line therapy for type 2 diabetes.",
                "SGLT2 inhibitors and GLP-1 agonists have cardiovascular and renal benefits.",
                "Annual screening: dilated eye exam, foot exam, urine albumin, lipids.",
                "Hypoglycemia symptoms: tremor, sweating, confusion, palpitations."
            ]
        }


# Global instance
pinecone_rag = PineconeRAG()
