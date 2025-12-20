"""
AURA Pinecone Vector Database Connection
Vector similarity search for fact retrieval
"""

from typing import Optional, List, Dict, Any
from dataclasses import dataclass
import hashlib

from app.core.config import settings
from app.core.logging import logger

# Global Pinecone index
pinecone_index = None


@dataclass
class VectorSearchResult:
    """Result from vector similarity search."""
    id: str
    score: float
    metadata: Dict[str, Any]


async def connect_pinecone() -> None:
    """
    Connect to Pinecone and initialize index.
    """
    global pinecone_index
    
    if not settings.PINECONE_API_KEY:
        logger.warning("⚠️ Pinecone API key not configured")
        return
    
    try:
        from pinecone import Pinecone
        
        logger.info("Connecting to Pinecone...")
        
        pc = Pinecone(api_key=settings.PINECONE_API_KEY)
        
        # Check if index exists
        existing_indexes = pc.list_indexes()
        index_names = [idx.name for idx in existing_indexes]
        
        if settings.PINECONE_INDEX_NAME not in index_names:
            logger.info(f"Creating Pinecone index: {settings.PINECONE_INDEX_NAME}")
            pc.create_index(
                name=settings.PINECONE_INDEX_NAME,
                dimension=settings.EMBEDDING_MODEL_DIMENSION,
                metric="cosine",
                spec={
                    "serverless": {
                        "cloud": "aws",
                        "region": "us-east-1"
                    }
                }
            )
        
        pinecone_index = pc.Index(settings.PINECONE_INDEX_NAME)
        
        # Get index stats
        stats = pinecone_index.describe_index_stats()
        logger.info(f"✅ Connected to Pinecone index: {settings.PINECONE_INDEX_NAME}")
        logger.info(f"   Total vectors: {stats.total_vector_count}")
        
    except ImportError:
        logger.error("❌ Pinecone library not installed")
    except Exception as e:
        logger.error(f"❌ Failed to connect to Pinecone: {e}")
        pinecone_index = None


async def close_pinecone() -> None:
    """Close Pinecone connection."""
    global pinecone_index
    pinecone_index = None
    logger.info("Pinecone connection closed")


def get_pinecone_index():
    """
    Get the Pinecone index instance.
    
    Returns:
        Pinecone Index instance
        
    Raises:
        RuntimeError if not connected
    """
    if pinecone_index is None:
        raise RuntimeError("Pinecone is not connected. Call connect_pinecone() first.")
    return pinecone_index


def generate_vector_id(text: str) -> str:
    """Generate a unique ID for a vector based on text content."""
    return hashlib.md5(text.encode()).hexdigest()[:16]


async def upsert_vectors(
    vectors: List[Dict[str, Any]],
    namespace: str = ""
) -> int:
    """
    Upsert vectors to Pinecone.
    
    Args:
        vectors: List of dicts with 'id', 'values', 'metadata'
        namespace: Optional namespace for organization
        
    Returns:
        Number of vectors upserted
    """
    try:
        index = get_pinecone_index()
        
        # Batch upsert (max 100 at a time)
        batch_size = 100
        total_upserted = 0
        
        for i in range(0, len(vectors), batch_size):
            batch = vectors[i:i + batch_size]
            index.upsert(vectors=batch, namespace=namespace)
            total_upserted += len(batch)
        
        return total_upserted
    except Exception as e:
        logger.error(f"Failed to upsert vectors: {e}")
        return 0


async def search_vectors(
    query_vector: List[float],
    top_k: int = 10,
    namespace: str = "",
    filter_dict: Optional[Dict] = None,
    include_metadata: bool = True
) -> List[VectorSearchResult]:
    """
    Search for similar vectors.
    
    Args:
        query_vector: Query embedding vector
        top_k: Number of results to return
        namespace: Optional namespace to search in
        filter_dict: Optional metadata filters
        include_metadata: Whether to include metadata in results
        
    Returns:
        List of VectorSearchResult objects
    """
    try:
        index = get_pinecone_index()
        
        results = index.query(
            vector=query_vector,
            top_k=top_k,
            namespace=namespace,
            filter=filter_dict,
            include_metadata=include_metadata
        )
        
        return [
            VectorSearchResult(
                id=match.id,
                score=match.score,
                metadata=match.metadata if include_metadata else {}
            )
            for match in results.matches
        ]
    except Exception as e:
        logger.error(f"Vector search failed: {e}")
        return []


async def delete_vectors(
    ids: List[str] = None,
    namespace: str = "",
    delete_all: bool = False
) -> bool:
    """
    Delete vectors from Pinecone.
    
    Args:
        ids: List of vector IDs to delete
        namespace: Namespace to delete from
        delete_all: If True, delete all vectors in namespace
        
    Returns:
        True if successful
    """
    try:
        index = get_pinecone_index()
        
        if delete_all:
            index.delete(delete_all=True, namespace=namespace)
        elif ids:
            index.delete(ids=ids, namespace=namespace)
        
        return True
    except Exception as e:
        logger.error(f"Failed to delete vectors: {e}")
        return False


async def get_index_stats() -> Dict[str, Any]:
    """Get Pinecone index statistics."""
    try:
        index = get_pinecone_index()
        stats = index.describe_index_stats()
        return {
            "total_vectors": stats.total_vector_count,
            "namespaces": dict(stats.namespaces) if stats.namespaces else {},
            "dimension": stats.dimension
        }
    except Exception as e:
        logger.error(f"Failed to get index stats: {e}")
        return {}


# ===========================================
# Embedding Generation
# ===========================================

_genai_configured = False


def _configure_genai():
    """Configure Google Generative AI for embeddings."""
    global _genai_configured
    if not _genai_configured:
        try:
            import google.generativeai as genai
            genai.configure(api_key=settings.GOOGLE_API_KEY)
            _genai_configured = True
            logger.info("✅ Google Generative AI configured for embeddings")
        except Exception as e:
            logger.error(f"Failed to configure Google Generative AI: {e}")


def generate_embedding(text: str) -> List[float]:
    """
    Generate embedding for text using Google Generative AI.
    
    Args:
        text: Text to embed
        
    Returns:
        Embedding vector (768 dimensions)
    """
    try:
        import google.generativeai as genai
        _configure_genai()
        
        result = genai.embed_content(
            model="models/embedding-001",
            content=text,
            task_type="retrieval_document"
        )
        return result['embedding']
    except Exception as e:
        logger.error(f"Embedding generation failed: {e}")
        return []


def generate_embeddings(texts: List[str]) -> List[List[float]]:
    """
    Generate embeddings for multiple texts using Google Generative AI.
    
    Args:
        texts: List of texts to embed
        
    Returns:
        List of embedding vectors
    """
    try:
        import google.generativeai as genai
        _configure_genai()
        
        embeddings = []
        for text in texts:
            result = genai.embed_content(
                model="models/embedding-001",
                content=text,
                task_type="retrieval_document"
            )
            embeddings.append(result['embedding'])
        return embeddings
    except Exception as e:
        logger.error(f"Batch embedding generation failed: {e}")
        return []


# ===========================================
# Text Chunking for RAG
# ===========================================

def chunk_text(
    text: str,
    chunk_size: int = None,
    chunk_overlap: int = None,
    strategy: str = None
) -> List[str]:
    """
    Chunk text for embedding and retrieval.
    
    Args:
        text: Text to chunk
        chunk_size: Size of each chunk (default from settings)
        chunk_overlap: Overlap between chunks (default from settings)
        strategy: Chunking strategy (recursive, semantic, fixed)
        
    Returns:
        List of text chunks
    """
    chunk_size = chunk_size or settings.CHUNK_SIZE
    chunk_overlap = chunk_overlap or settings.CHUNK_OVERLAP
    strategy = strategy or settings.CHUNK_STRATEGY
    
    if not text or len(text) <= chunk_size:
        return [text] if text else []
    
    if strategy == "recursive":
        return _recursive_chunk(text, chunk_size, chunk_overlap)
    elif strategy == "semantic":
        return _semantic_chunk(text, chunk_size)
    else:
        return _fixed_chunk(text, chunk_size, chunk_overlap)


def _recursive_chunk(
    text: str, 
    chunk_size: int, 
    chunk_overlap: int
) -> List[str]:
    """
    Recursively chunk text using multiple separators.
    Best for maintaining document structure.
    """
    separators = ["\n\n", "\n", ". ", ", ", " "]
    
    def split_text(text: str, separator_idx: int = 0) -> List[str]:
        if separator_idx >= len(separators):
            # Fallback to fixed chunking
            return _fixed_chunk(text, chunk_size, chunk_overlap)
        
        separator = separators[separator_idx]
        splits = text.split(separator)
        
        chunks = []
        current_chunk = ""
        
        for split in splits:
            if len(current_chunk) + len(split) + len(separator) <= chunk_size:
                if current_chunk:
                    current_chunk += separator + split
                else:
                    current_chunk = split
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                
                if len(split) > chunk_size:
                    # Recursively split with next separator
                    sub_chunks = split_text(split, separator_idx + 1)
                    chunks.extend(sub_chunks)
                    current_chunk = ""
                else:
                    current_chunk = split
        
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks
    
    chunks = split_text(text)
    
    # Add overlap
    if chunk_overlap > 0 and len(chunks) > 1:
        overlapped_chunks = []
        for i, chunk in enumerate(chunks):
            if i > 0:
                overlap_text = chunks[i-1][-chunk_overlap:]
                chunk = overlap_text + " " + chunk
            overlapped_chunks.append(chunk)
        return overlapped_chunks
    
    return chunks


def _fixed_chunk(
    text: str, 
    chunk_size: int, 
    chunk_overlap: int
) -> List[str]:
    """Fixed-size chunking with overlap."""
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        
        # Try to break at word boundary
        if end < len(text) and text[end] not in ' \n':
            last_space = chunk.rfind(' ')
            if last_space > chunk_size * 0.5:
                chunk = chunk[:last_space]
                end = start + last_space
        
        chunks.append(chunk.strip())
        start = end - chunk_overlap
    
    return chunks


def _semantic_chunk(text: str, chunk_size: int) -> List[str]:
    """
    Semantic chunking based on sentence boundaries.
    Best for maintaining meaning.
    """
    import re
    
    # Split into sentences
    sentences = re.split(r'(?<=[.!?])\s+', text)
    
    chunks = []
    current_chunk = ""
    
    for sentence in sentences:
        if len(current_chunk) + len(sentence) + 1 <= chunk_size:
            if current_chunk:
                current_chunk += " " + sentence
            else:
                current_chunk = sentence
        else:
            if current_chunk:
                chunks.append(current_chunk)
            current_chunk = sentence
    
    if current_chunk:
        chunks.append(current_chunk)
    
    return chunks
