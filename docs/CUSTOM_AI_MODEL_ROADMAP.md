# Custom AI Model Development Roadmap

## Overview

This document outlines the path to building a custom AI model for the AI Health Navigator, replacing the Claude API with our own trained model.

---

## Current Architecture (Using Claude API)

```
User Query → FastAPI → Claude API → Response
                         ↑
                    Cost: ~$0.01/query
```

---

## Two Approaches

| Approach | Difficulty | Cost | Time |
|----------|------------|------|------|
| **Fine-tune existing model** | Medium | $100 - $10,000 | 1-4 weeks |
| **Train from scratch** | Very Hard | $1M - $100M+ | 6-24 months |

**Recommended: Fine-tuning**

---

## Phase 1: Data Collection (Month 1-3)

### Required Data Volume
- **Minimum:** 10,000 medical Q&A pairs
- **Ideal:** 50,000 - 100,000 examples

### Data Sources

| Source | Type | Access |
|--------|------|--------|
| PubMed | Research papers | Free API |
| MIMIC-III | Clinical records | Free (apply) |
| MedQA | Q&A dataset | Free |
| UpToDate | Clinical guidelines | Subscription |
| Your app data | Patient assessments | Own data |

### Data Format
```json
{
  "instruction": "Analyze these symptoms and provide diagnosis",
  "input": "45-year-old male, chest pain radiating to left arm, shortness of breath, sweating",
  "output": "Assessment: Suspect acute coronary syndrome (ACS). The triad of chest pain with radiation, dyspnea, and diaphoresis is classic for cardiac ischemia.\n\nRisk Level: HIGH - Requires immediate evaluation\n\nRecommendations:\n1. Call 911 immediately\n2. Chew aspirin 325mg if not allergic\n3. ECG within 10 minutes of arrival\n4. Serial troponin measurements\n5. Cardiology consultation"
}
```

### Data Collection Script
```python
# Example: Collect from PubMed
import requests

def fetch_pubmed_articles(query, count=1000):
    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"

    # Search
    search_url = f"{base_url}esearch.fcgi?db=pubmed&term={query}&retmax={count}&retmode=json"
    response = requests.get(search_url)
    ids = response.json()['esearchresult']['idlist']

    # Fetch abstracts
    fetch_url = f"{base_url}efetch.fcgi?db=pubmed&id={','.join(ids)}&retmode=xml"
    return requests.get(fetch_url).text

# Collect medical articles
articles = fetch_pubmed_articles("clinical diagnosis symptoms treatment")
```

---

## Phase 2: Environment Setup (Week 1-2)

### Hardware Options

| Option | Specs | Cost |
|--------|-------|------|
| **AWS SageMaker** | ml.g5.2xlarge (A10G GPU) | $1.50/hour |
| **Google Colab Pro+** | A100 GPU | $50/month |
| **Lambda Labs** | A100 80GB | $1.10/hour |
| **RunPod** | A100 80GB | $1.50/hour |
| **Local RTX 4090** | 24GB VRAM | $2000 one-time |

### Software Stack
```bash
# Create environment
conda create -n medical-llm python=3.11
conda activate medical-llm

# Install dependencies
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
pip install transformers datasets accelerate
pip install peft bitsandbytes  # Efficient fine-tuning
pip install wandb  # Experiment tracking
pip install huggingface_hub
```

### requirements-training.txt
```
torch>=2.1.0
transformers>=4.36.0
datasets>=2.15.0
accelerate>=0.25.0
peft>=0.7.0
bitsandbytes>=0.41.0
wandb>=0.16.0
trl>=0.7.0
scipy
sentencepiece
protobuf
```

---

## Phase 3: Choose Base Model (Week 2)

### Recommended Models for Medical AI

| Model | Size | Medical Performance | License |
|-------|------|---------------------|---------|
| **BioMistral-7B** | 7B | Excellent | Apache 2.0 |
| **Meditron-70B** | 70B | Excellent | LLaMA license |
| **LLaMA-3-8B** | 8B | Good | Meta license |
| **Mistral-7B** | 7B | Good | Apache 2.0 |
| **Gemma-7B** | 7B | Good | Google license |

### Recommended: BioMistral-7B
- Already trained on medical literature
- Small enough for affordable fine-tuning
- Open source (Apache 2.0)

```python
from transformers import AutoModelForCausalLM, AutoTokenizer

model_name = "BioMistral/BioMistral-7B"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(
    model_name,
    torch_dtype=torch.float16,
    device_map="auto"
)
```

---

## Phase 4: Fine-Tuning (Week 3-4)

### Method: QLoRA (Quantized Low-Rank Adaptation)
- Trains only 1-2% of parameters
- Uses 4-bit quantization
- Fits on single GPU

### Training Script
```python
# train_medical_model.py

import torch
from datasets import load_dataset
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    TrainingArguments,
    Trainer,
    BitsAndBytesConfig
)
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training

# 1. Load base model with 4-bit quantization
bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.float16,
    bnb_4bit_use_double_quant=True
)

model = AutoModelForCausalLM.from_pretrained(
    "BioMistral/BioMistral-7B",
    quantization_config=bnb_config,
    device_map="auto"
)

tokenizer = AutoTokenizer.from_pretrained("BioMistral/BioMistral-7B")
tokenizer.pad_token = tokenizer.eos_token

# 2. Prepare for training
model = prepare_model_for_kbit_training(model)

# 3. Add LoRA adapters
lora_config = LoraConfig(
    r=16,                      # Rank
    lora_alpha=32,             # Scaling factor
    target_modules=["q_proj", "v_proj", "k_proj", "o_proj"],
    lora_dropout=0.05,
    bias="none",
    task_type="CAUSAL_LM"
)

model = get_peft_model(model, lora_config)
model.print_trainable_parameters()  # Shows ~1-2% trainable

# 4. Load your medical dataset
dataset = load_dataset("json", data_files="medical_training_data.json")

def format_prompt(example):
    return f"""### Instruction:
{example['instruction']}

### Input:
{example['input']}

### Response:
{example['output']}"""

def tokenize(example):
    prompt = format_prompt(example)
    return tokenizer(prompt, truncation=True, max_length=2048, padding="max_length")

tokenized_dataset = dataset.map(tokenize, remove_columns=dataset["train"].column_names)

# 5. Training configuration
training_args = TrainingArguments(
    output_dir="./medical-model-output",
    num_train_epochs=3,
    per_device_train_batch_size=4,
    gradient_accumulation_steps=4,
    learning_rate=2e-4,
    warmup_steps=100,
    logging_steps=10,
    save_steps=500,
    fp16=True,
    report_to="wandb"
)

# 6. Train
trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=tokenized_dataset["train"],
)

trainer.train()

# 7. Save the model
model.save_pretrained("./health-navigator-model")
tokenizer.save_pretrained("./health-navigator-model")
```

### Training Cost Estimate
| Dataset Size | Training Time | GPU Cost |
|--------------|---------------|----------|
| 10,000 examples | 2-4 hours | $5-10 |
| 50,000 examples | 10-20 hours | $25-50 |
| 100,000 examples | 20-40 hours | $50-100 |

---

## Phase 5: Evaluation (Week 4)

### Evaluation Metrics
```python
# evaluate_model.py

from datasets import load_dataset
import evaluate

# Load test data
test_data = load_dataset("json", data_files="test_data.json")

# Metrics
bleu = evaluate.load("bleu")
rouge = evaluate.load("rouge")
bertscore = evaluate.load("bertscore")

def evaluate_model(model, tokenizer, test_examples):
    predictions = []
    references = []

    for example in test_examples:
        # Generate prediction
        inputs = tokenizer(example["input"], return_tensors="pt")
        outputs = model.generate(**inputs, max_length=512)
        prediction = tokenizer.decode(outputs[0], skip_special_tokens=True)

        predictions.append(prediction)
        references.append(example["output"])

    # Calculate scores
    results = {
        "bleu": bleu.compute(predictions=predictions, references=references),
        "rouge": rouge.compute(predictions=predictions, references=references),
        "bertscore": bertscore.compute(predictions=predictions, references=references, lang="en")
    }

    return results
```

### Benchmark Against Claude
| Metric | Claude API | Our Model | Target |
|--------|------------|-----------|--------|
| Accuracy | 95% | ? | >90% |
| Response Time | 2-3s | 0.5-1s | <1s |
| Cost per Query | $0.01 | $0.001 | <$0.005 |

---

## Phase 6: Deployment (Week 5-6)

### Option A: AWS SageMaker
```python
# deploy_sagemaker.py

import sagemaker
from sagemaker.huggingface import HuggingFaceModel

role = sagemaker.get_execution_role()

huggingface_model = HuggingFaceModel(
    model_data="s3://your-bucket/health-navigator-model.tar.gz",
    role=role,
    transformers_version="4.36",
    pytorch_version="2.1",
    py_version="py310",
)

predictor = huggingface_model.deploy(
    initial_instance_count=1,
    instance_type="ml.g5.xlarge"  # GPU instance
)
```

### Option B: Self-hosted on EC2
```bash
# On EC2 GPU instance (g4dn.xlarge or g5.xlarge)

# Install dependencies
pip install vllm  # Fast inference engine

# Run inference server
python -m vllm.entrypoints.openai.api_server \
    --model ./health-navigator-model \
    --port 8000
```

### Option C: Hugging Face Inference Endpoints
```python
# One-click deployment
from huggingface_hub import InferenceClient

client = InferenceClient(
    model="your-username/health-navigator-model",
    token="your-hf-token"
)

response = client.text_generation(
    prompt="Patient symptoms: headache, fever...",
    max_new_tokens=512
)
```

---

## Phase 7: Integration (Week 6)

### Update FastAPI to Use Custom Model

```python
# api/routes/assessments.py

from vllm import LLM, SamplingParams

# Load our custom model
llm = LLM(model="./health-navigator-model")
sampling_params = SamplingParams(temperature=0.7, max_tokens=1024)

class CustomMedicalLLM:
    def __init__(self):
        self.llm = LLM(model="./health-navigator-model")
        self.sampling_params = SamplingParams(temperature=0.7, max_tokens=1024)

    def invoke(self, prompt: str) -> str:
        outputs = self.llm.generate([prompt], self.sampling_params)
        return outputs[0].outputs[0].text

# Replace BedrockClient with CustomMedicalLLM
# llm = BedrockClient()  # Old
llm = CustomMedicalLLM()   # New
```

---

## Cost Comparison Over Time

### Year 1 (1000 assessments/month)
| Approach | Monthly Cost |
|----------|--------------|
| Claude API | $10/month |
| Custom Model (hosted) | $200-500/month |
| **Winner** | Claude API |

### Year 2 (10,000 assessments/month)
| Approach | Monthly Cost |
|----------|--------------|
| Claude API | $100/month |
| Custom Model (hosted) | $200-500/month |
| **Winner** | Claude API |

### Year 3 (100,000 assessments/month)
| Approach | Monthly Cost |
|----------|--------------|
| Claude API | $1,000/month |
| Custom Model (hosted) | $200-500/month |
| **Winner** | Custom Model |

**Break-even point: ~50,000 queries/month**

---

## Timeline Summary

```
Month 1-2:   Learn PyTorch, Hugging Face, transformers
Month 3-4:   Collect and prepare medical training data
Month 5:     Fine-tune BioMistral-7B
Month 6:     Evaluate and optimize
Month 7:     Deploy and integrate
Month 8+:    Monitor, improve, collect more data
```

---

## Resources for Learning

### Courses
- [Hugging Face NLP Course](https://huggingface.co/learn/nlp-course) (Free)
- [Fast.ai Practical Deep Learning](https://course.fast.ai/) (Free)
- [DeepLearning.AI LLM Courses](https://www.deeplearning.ai/) (Paid)

### Documentation
- [Hugging Face Transformers](https://huggingface.co/docs/transformers)
- [PEFT Documentation](https://huggingface.co/docs/peft)
- [vLLM Documentation](https://docs.vllm.ai/)

### Papers
- "LLaMA: Open Foundation Models" - Meta
- "QLoRA: Efficient Finetuning" - Dettmers et al.
- "BioMistral: Medical LLM" - BioMistral team

---

## Checklist

- [ ] Collect 10,000+ medical Q&A pairs
- [ ] Set up GPU training environment
- [ ] Download BioMistral-7B base model
- [ ] Prepare training data in correct format
- [ ] Run fine-tuning with QLoRA
- [ ] Evaluate on test set
- [ ] Compare with Claude API
- [ ] Deploy inference server
- [ ] Integrate with FastAPI
- [ ] Monitor and improve

---

*Document created: January 2025*
*Last updated: January 2025*
*Project: AI Health Navigator*
