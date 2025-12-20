"""
AURA Service - Fact Ingestion
Ingest verified facts to Pinecone and Neo4j
"""

from typing import Optional, List, Dict, Any
from datetime import datetime

from app.core.logging import logger
from app.core.config import settings
from app.db.mongodb import get_collection
from app.db.pinecone_db import (
    upsert_vectors, generate_embedding, generate_vector_id, chunk_text
)
from app.db.neo4j_db import create_node, create_relationship, NodeLabels
from app.models.evidence import FactInDB, FactCreate, FactCategory
from app.utils.id_generator import generate_evidence_id


class FactIngestionService:
    """Service for ingesting verified facts to the knowledge base."""
    
    def __init__(self):
        self.facts_collection = "facts"
    
    @property
    def collection(self):
        return get_collection(self.facts_collection)
    
    async def ingest_fact(
        self,
        fact_data: FactCreate,
        entities: List[str] = None
    ) -> Optional[FactInDB]:
        """
        Ingest a verified fact to MongoDB, Pinecone, and Neo4j.
        
        Args:
            fact_data: Fact creation data
            entities: Related entities for graph
            
        Returns:
            Created fact
        """
        fact_id = generate_evidence_id()
        
        try:
            # 1. Create MongoDB document
            fact = FactInDB(
                fact_id=fact_id,
                claim=fact_data.claim,
                claim_normalized=fact_data.claim.lower().strip(),
                verdict=fact_data.verdict,
                evidence_summary=fact_data.evidence_summary,
                source=fact_data.source,
                source_url=fact_data.source_url,
                category=fact_data.category,
                entities=entities or [],
                created_at=datetime.utcnow(),
                verified_at=datetime.utcnow()
            )
            
            doc_dict = fact.model_dump(by_alias=True, exclude={"id"})
            result = await self.collection.insert_one(doc_dict)
            fact.id = str(result.inserted_id)
            
            # 2. Generate embedding and upsert to Pinecone
            await self._ingest_to_pinecone(fact)
            
            # 3. Add to Neo4j knowledge graph
            await self._ingest_to_neo4j(fact, entities)
            
            logger.info(f"Ingested fact: {fact_id}")
            return fact
            
        except Exception as e:
            logger.error(f"Fact ingestion failed: {e}")
            return None
    
    async def _ingest_to_pinecone(self, fact: FactInDB) -> bool:
        """Ingest fact to Pinecone vector database."""
        try:
            # Generate embedding for the claim
            embedding = generate_embedding(fact.claim)
            
            # Create vector with metadata
            vector_id = generate_vector_id(fact.claim)
            
            vectors = [{
                "id": vector_id,
                "values": embedding,
                "metadata": {
                    "fact_id": fact.fact_id,
                    "claim": fact.claim,
                    "verdict": fact.verdict,
                    "category": fact.category.value if hasattr(fact.category, 'value') else fact.category,
                    "source": fact.source,
                    "source_url": fact.source_url or "",
                    "content": fact.evidence_summary[:500],  # Limit content
                    "entities": fact.entities[:10],  # Limit entities
                    "verified_at": fact.verified_at.isoformat()
                }
            }]
            
            # If fact has long evidence, chunk it
            if len(fact.evidence_summary) > settings.CHUNK_SIZE:
                chunks = chunk_text(fact.evidence_summary)
                for i, chunk in enumerate(chunks[1:], start=1):  # Skip first chunk (already indexed)
                    chunk_embedding = generate_embedding(chunk)
                    chunk_id = f"{vector_id}_{i}"
                    vectors.append({
                        "id": chunk_id,
                        "values": chunk_embedding,
                        "metadata": {
                            "fact_id": fact.fact_id,
                            "claim": fact.claim,
                            "verdict": fact.verdict,
                            "content": chunk,
                            "chunk_index": i
                        }
                    })
            
            count = await upsert_vectors(vectors, namespace="facts")
            
            # Update fact with embedding ID
            await self.collection.update_one(
                {"fact_id": fact.fact_id},
                {"$set": {"embedding_id": vector_id}}
            )
            
            logger.info(f"Ingested {count} vectors to Pinecone for fact {fact.fact_id}")
            return True
            
        except Exception as e:
            logger.error(f"Pinecone ingestion failed: {e}")
            return False
    
    async def _ingest_to_neo4j(
        self, 
        fact: FactInDB, 
        entities: List[str] = None
    ) -> bool:
        """Ingest fact to Neo4j knowledge graph."""
        try:
            # Create fact node
            fact_node_id = await create_node(
                labels=[NodeLabels.FACT],
                properties={
                    "fact_id": fact.fact_id,
                    "claim": fact.claim,
                    "verdict": fact.verdict,
                    "source": fact.source,
                    "category": fact.category.value if hasattr(fact.category, 'value') else fact.category,
                    "verified": True,
                    "created_at": fact.created_at.isoformat()
                }
            )
            
            if fact_node_id and entities:
                # Create entity nodes and relationships
                for entity in entities:
                    entity_node_id = await create_node(
                        labels=[NodeLabels.ENTITY],
                        properties={
                            "name": entity,
                            "created_at": datetime.utcnow().isoformat()
                        }
                    )
                    
                    if entity_node_id:
                        await create_relationship(
                            fact_node_id,
                            entity_node_id,
                            "MENTIONS",
                            {"created_at": datetime.utcnow().isoformat()}
                        )
            
            # Update fact with Neo4j node ID
            if fact_node_id:
                await self.collection.update_one(
                    {"fact_id": fact.fact_id},
                    {"$set": {"neo4j_node_id": fact_node_id}}
                )
            
            logger.info(f"Ingested to Neo4j: {fact.fact_id}")
            return True
            
        except Exception as e:
            logger.error(f"Neo4j ingestion failed: {e}")
            return False
    
    async def bulk_ingest(
        self,
        facts: List[FactCreate],
        extract_entities: bool = True
    ) -> Dict[str, Any]:
        """
        Bulk ingest multiple facts.
        
        Args:
            facts: List of facts to ingest
            extract_entities: Whether to extract entities from claims
            
        Returns:
            Summary of ingestion
        """
        from app.services.llm_service import analyze_claim
        
        success = 0
        failed = 0
        
        for fact_data in facts:
            try:
                entities = []
                if extract_entities:
                    # Use LLM to extract entities
                    analysis = await analyze_claim(fact_data.claim)
                    entities = analysis.get("entities", [])
                
                result = await self.ingest_fact(fact_data, entities)
                if result:
                    success += 1
                else:
                    failed += 1
            except Exception as e:
                logger.error(f"Failed to ingest fact: {e}")
                failed += 1
        
        return {
            "total": len(facts),
            "success": success,
            "failed": failed
        }
    
    async def update_fact_match_count(self, fact_id: str) -> bool:
        """Increment the match count for a fact."""
        result = await self.collection.update_one(
            {"fact_id": fact_id},
            {
                "$inc": {"times_matched": 1},
                "$set": {"last_matched_at": datetime.utcnow()}
            }
        )
        return result.modified_count > 0
    
    async def get_popular_facts(self, limit: int = 10) -> List[FactInDB]:
        """Get most frequently matched facts."""
        cursor = self.collection.find(
            {"times_matched": {"$gt": 0}}
        ).sort("times_matched", -1).limit(limit)
        
        facts = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            facts.append(FactInDB(**doc))
        return facts


# Global service instance
fact_ingestion_service = FactIngestionService()
