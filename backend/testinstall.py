# backend/test_installation.py

"""
Test script to verify all dependencies are installed correctly.
"""

import sys
print(f"Python version: {sys.version}")

def test_import(module_name, display_name=None):
    """Test if a module can be imported."""
    display = display_name or module_name
    try:
        module = __import__(module_name)
        version = getattr(module, '__version__', 'N/A')
        print(f"✅ {display}: {version}")
        return True
    except ImportError as e:
        print(f"❌ {display}: FAILED - {e}")
        return False

print("\n" + "="*60)
print("🔍 AURA Dependencies Check")
print("="*60 + "\n")

# Core Framework
print("📦 Core Framework:")
test_import("fastapi", "FastAPI")
test_import("uvicorn", "Uvicorn")
test_import("pydantic", "Pydantic")

# LangChain & AI
print("\n🤖 LangChain & AI:")
test_import("langchain", "LangChain")
test_import("langchain_community", "LangChain Community")
test_import("langchain_google_genai", "LangChain Google GenAI")
test_import("langgraph", "LangGraph")

# CrewAI
print("\n👥 CrewAI:")
test_import("crewai", "CrewAI")

# LLM Providers
print("\n🧠 LLM Providers:")
test_import("google.generativeai", "Google GenAI")
test_import("groq", "Groq")

# Embeddings & Vector DB
print("\n📊 Embeddings & Vector DB:")
test_import("sentence_transformers", "Sentence Transformers")
test_import("pinecone", "Pinecone")

# Databases
print("\n💾 Databases:")
test_import("neo4j", "Neo4j")
test_import("pymongo", "PyMongo")
test_import("redis", "Redis")

# Web Scraping
print("\n🌐 Web Scraping:")
test_import("serpapi", "SerpAPI")
test_import("bs4", "BeautifulSoup")
test_import("requests", "Requests")

# NLP
print("\n📝 NLP & ML:")
test_import("spacy", "spaCy")
test_import("transformers", "Transformers")
test_import("torch", "PyTorch")

# Check CUDA
print("\n🎮 GPU Check:")
try:
    import torch
    cuda_available = torch.cuda.is_available()
    if cuda_available:
        gpu_name = torch.cuda.get_device_name(0)
        print(f"✅ CUDA Available: {gpu_name}")
    else:
        print("⚠️  CUDA not available (CPU mode)")
except:
    print("❌ PyTorch GPU check failed")

# OCR
print("\n🔍 OCR:")
test_import("pytesseract", "Pytesseract")
test_import("PIL", "Pillow")

# Audio
print("\n🔊 Audio:")
test_import("elevenlabs", "ElevenLabs")

# WhatsApp
print("\n📱 WhatsApp:")
test_import("twilio", "Twilio")

# Utilities
print("\n🛠️ Utilities:")
test_import("dotenv", "Python-dotenv")
test_import("loguru", "Loguru")
test_import("langdetect", "Langdetect")

print("\n" + "="*60)
print("✅ Installation check complete!")
print("="*60)