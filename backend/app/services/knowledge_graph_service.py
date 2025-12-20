"""
AURA Service - Knowledge Graph
Neo4j knowledge graph operations for fact inference
"""

from typing import Optional, List, Dict, Any
from datetime import datetime

from app.core.logging import logger
from app.db.neo4j_db import (
    create_node, create_relationship, find_node,
    find_related_entities, query_fact_relationships, get_fact_chain,
    NodeLabels, RelationshipTypes
)


class KnowledgeGraphService:
    """Service for managing the knowledge graph in Neo4j."""
    
    async def add_entity(
        self,
        name: str,
        entity_type: str,
        properties: Dict[str, Any] = None
    ) -> Optional[str]:
        """
        Add an entity to the knowledge graph.
        
        Args:
            name: Entity name
            entity_type: Type (Person, Organization, Location, etc.)
            properties: Additional properties
            
        Returns:
            Node ID if created
        """
        props = properties or {}
        props["name"] = name
        props["type"] = entity_type
        props["created_at"] = datetime.utcnow().isoformat()
        
        # Determine labels
        labels = [NodeLabels.ENTITY]
        if entity_type == "person":
            labels.append(NodeLabels.PERSON)
        elif entity_type == "organization":
            labels.append(NodeLabels.ORGANIZATION)
        elif entity_type == "location":
            labels.append(NodeLabels.LOCATION)
        elif entity_type == "event":
            labels.append(NodeLabels.EVENT)
        
        node_id = await create_node(labels, props)
        
        if node_id:
            logger.info(f"Created entity node: {name} ({entity_type})")
        
        return node_id
    
    async def add_fact(
        self,
        claim: str,
        verdict: str,
        evidence: str,
        source: str,
        entities: List[str] = None,
        fact_id: str = None
    ) -> Optional[str]:
        """
        Add a verified fact to the knowledge graph.
        
        Args:
            claim: The claim text
            verdict: Verification verdict
            evidence: Evidence summary
            source: Source of verification
            entities: Related entities
            fact_id: Optional fact ID
            
        Returns:
            Node ID if created
        """
        props = {
            "fact_id": fact_id,
            "claim": claim,
            "verdict": verdict,
            "evidence": evidence,
            "source": source,
            "verified": True,
            "created_at": datetime.utcnow().isoformat()
        }
        
        node_id = await create_node([NodeLabels.FACT], props)
        
        if node_id and entities:
            # Link fact to entities
            for entity_name in entities:
                entity_node = await find_node(
                    labels=[NodeLabels.ENTITY],
                    properties={"name": entity_name}
                )
                
                if entity_node:
                    await create_relationship(
                        node_id,
                        entity_node.id,
                        RelationshipTypes.RELATED_TO,
                        {"created_at": datetime.utcnow().isoformat()}
                    )
        
        if node_id:
            logger.info(f"Created fact node: {fact_id or claim[:50]}")
        
        return node_id
    
    async def add_claim(
        self,
        claim_id: str,
        claim_text: str,
        language: str = "en"
    ) -> Optional[str]:
        """
        Add a claim to the knowledge graph.
        
        Args:
            claim_id: Unique claim identifier
            claim_text: The claim text
            language: Language code
            
        Returns:
            Node ID if created
        """
        props = {
            "claim_id": claim_id,
            "claim": claim_text,
            "language": language,
            "verified": False,
            "created_at": datetime.utcnow().isoformat()
        }
        
        return await create_node([NodeLabels.CLAIM], props)
    
    async def link_claim_to_fact(
        self,
        claim_id: str,
        fact_id: str,
        relationship_type: str = "MATCHES"
    ) -> Optional[str]:
        """
        Link a claim to a matching fact.
        
        Args:
            claim_id: Claim identifier
            fact_id: Fact identifier
            relationship_type: Type of relationship
            
        Returns:
            Relationship ID if created
        """
        claim_node = await find_node(
            labels=[NodeLabels.CLAIM],
            properties={"claim_id": claim_id}
        )
        
        fact_node = await find_node(
            labels=[NodeLabels.FACT],
            properties={"fact_id": fact_id}
        )
        
        if claim_node and fact_node:
            return await create_relationship(
                claim_node.id,
                fact_node.id,
                relationship_type,
                {"created_at": datetime.utcnow().isoformat()}
            )
        
        return None
    
    async def find_related_facts(
        self,
        entities: List[str],
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Find facts related to given entities.
        
        Args:
            entities: List of entity names
            limit: Maximum results
            
        Returns:
            List of related facts
        """
        all_facts = []
        
        for entity in entities[:5]:  # Limit entities
            relationships = await query_fact_relationships([entity])
            all_facts.extend(relationships)
        
        # Deduplicate
        seen = set()
        unique_facts = []
        for fact in all_facts:
            key = str(fact)
            if key not in seen:
                seen.add(key)
                unique_facts.append(fact)
        
        return unique_facts[:limit]
    
    async def get_inference_chain(
        self,
        start_entity: str,
        end_entity: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get the inference chain between two entities.
        
        Useful for understanding how two concepts are connected.
        
        Args:
            start_entity: Starting entity name
            end_entity: Ending entity name
            
        Returns:
            Chain of relationships
        """
        path = await get_fact_chain(start_entity, end_entity, max_depth=5)
        
        if path:
            return {
                "start": start_entity,
                "end": end_entity,
                "nodes": [
                    {"id": n.id, "labels": n.labels, "name": n.properties.get("name")}
                    for n in path.nodes
                ],
                "relationships": [
                    {"type": r.type, "from": r.start_node, "to": r.end_node}
                    for r in path.relationships
                ],
                "path_length": len(path.relationships)
            }
        
        return None
    
    async def build_claim_context(
        self,
        claim: str,
        entities: List[str]
    ) -> Dict[str, Any]:
        """
        Build context for a claim using the knowledge graph.
        
        Args:
            claim: The claim text
            entities: Extracted entities
            
        Returns:
            Context with related facts and relationships
        """
        context = {
            "entities": entities,
            "related_facts": [],
            "entity_relationships": [],
            "inference_paths": []
        }
        
        # Find related facts
        related_facts = await self.find_related_facts(entities)
        context["related_facts"] = related_facts
        
        # Find relationships between entities
        if len(entities) >= 2:
            relationships = await query_fact_relationships(entities)
            context["entity_relationships"] = relationships
            
            # Try to find inference chains between entity pairs
            for i in range(min(len(entities) - 1, 3)):
                chain = await self.get_inference_chain(entities[i], entities[i + 1])
                if chain:
                    context["inference_paths"].append(chain)
        
        return context


# Global service instance
knowledge_graph_service = KnowledgeGraphService()
