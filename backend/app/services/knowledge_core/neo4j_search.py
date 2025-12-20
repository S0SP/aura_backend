"""
AURA Neo4j Search Service
Knowledge graph queries for relationship-based fact inference
"""

from typing import Dict, Any, List, Optional
from datetime import datetime

from app.core.logging import logger
from app.core.config import settings


class Neo4jSearch:
    """
    Neo4j knowledge graph search for relationship-based fact inference.
    Traverses entity relationships to validate claims.
    """
    
    def __init__(self):
        self.uri = settings.NEO4J_URI
        self.user = settings.NEO4J_USER
        self.password = settings.NEO4J_PASSWORD
        self.enabled = bool(self.uri and self.password)
        self._driver = None
    
    async def query(
        self,
        entities: List[str],
        relationship_depth: int = 3,
        include_facts: bool = True
    ) -> Dict[str, Any]:
        """
        Query knowledge graph for entity relationships.
        """
        if not self.enabled:
            logger.warning("Neo4j not configured")
            return {"nodes": [], "relationships": [], "error": "Neo4j not configured"}
        
        start_time = datetime.utcnow()
        
        try:
            driver = self._get_driver()
            
            nodes = []
            relationships = []
            related_facts = []
            
            async with driver.session() as session:
                for entity in entities[:5]:  # Limit to 5 entities
                    result = await session.run(
                        """
                        MATCH (n)-[r*1..$depth]-(m)
                        WHERE n.name CONTAINS $entity OR n.id CONTAINS $entity
                        RETURN n, r, m
                        LIMIT 50
                        """,
                        entity=entity,
                        depth=relationship_depth
                    )
                    
                    async for record in result:
                        node = record.get("n")
                        if node:
                            nodes.append(self._parse_node(node))
                        
                        related = record.get("m")
                        if related:
                            nodes.append(self._parse_node(related))
                        
                        rels = record.get("r")
                        if rels:
                            for rel in rels:
                                relationships.append(self._parse_relationship(rel))
                
                # Get related facts if requested
                if include_facts:
                    for entity in entities[:3]:
                        fact_result = await session.run(
                            """
                            MATCH (f:Fact)-[:ABOUT]->(e)
                            WHERE e.name CONTAINS $entity
                            RETURN f
                            LIMIT 5
                            """,
                            entity=entity
                        )
                        
                        async for record in fact_result:
                            fact = record.get("f")
                            if fact:
                                related_facts.append({
                                    "claim": fact.get("claim", ""),
                                    "verdict": fact.get("verdict", ""),
                                    "source": fact.get("source", "")
                                })
            
            # Deduplicate
            nodes = self._deduplicate_nodes(nodes)
            relationships = self._deduplicate_relationships(relationships)
            
            # Generate graph inference
            inference = self._generate_inference(nodes, relationships, entities)
            
            query_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            return {
                "nodes": nodes,
                "relationships": relationships,
                "related_facts": related_facts,
                "graph_inference": inference,
                "query_time_ms": round(query_time)
            }
            
        except Exception as e:
            logger.error(f"Neo4j query failed: {e}")
            return {"nodes": [], "relationships": [], "error": str(e)}
    
    def _get_driver(self):
        """Get Neo4j driver instance."""
        if not self._driver:
            from neo4j import AsyncGraphDatabase
            self._driver = AsyncGraphDatabase.driver(
                self.uri,
                auth=(self.user, self.password)
            )
        return self._driver
    
    def _parse_node(self, node) -> Dict:
        """Parse Neo4j node into dict."""
        return {
            "id": node.get("id", node.get("name", "")),
            "type": list(node.labels)[0] if hasattr(node, 'labels') else "Entity",
            "properties": dict(node)
        }
    
    def _parse_relationship(self, rel) -> Dict:
        """Parse Neo4j relationship into dict."""
        return {
            "from": rel.start_node.get("id", ""),
            "to": rel.end_node.get("id", ""),
            "type": rel.type,
            "properties": dict(rel)
        }
    
    def _deduplicate_nodes(self, nodes: List[Dict]) -> List[Dict]:
        """Remove duplicate nodes."""
        seen = set()
        unique = []
        for node in nodes:
            node_id = node.get("id", "")
            if node_id and node_id not in seen:
                seen.add(node_id)
                unique.append(node)
        return unique
    
    def _deduplicate_relationships(self, rels: List[Dict]) -> List[Dict]:
        """Remove duplicate relationships."""
        seen = set()
        unique = []
        for rel in rels:
            key = f"{rel.get('from')}_{rel.get('type')}_{rel.get('to')}"
            if key not in seen:
                seen.add(key)
                unique.append(rel)
        return unique
    
    def _generate_inference(
        self,
        nodes: List[Dict],
        relationships: List[Dict],
        entities: List[str]
    ) -> str:
        """Generate a natural language inference from graph data."""
        if not relationships:
            return f"No relationships found for entities: {', '.join(entities)}"
        
        inferences = []
        for rel in relationships[:3]:
            inferences.append(f"{rel['from']} {rel['type']} {rel['to']}")
        
        return ". ".join(inferences)
    
    async def close(self):
        """Close Neo4j driver."""
        if self._driver:
            await self._driver.close()


# Global instance
neo4j_search = Neo4jSearch()
