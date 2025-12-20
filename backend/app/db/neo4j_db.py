"""
AURA Neo4j Graph Database Connection
Knowledge graph for entity relationships and fact inference
"""

from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field

from app.core.config import settings
from app.core.logging import logger

# Global Neo4j driver
neo4j_driver = None


@dataclass
class GraphNode:
    """Represents a node in the knowledge graph."""
    id: str
    labels: List[str]
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GraphRelationship:
    """Represents a relationship in the knowledge graph."""
    id: str
    type: str
    start_node: str
    end_node: str
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GraphPath:
    """Represents a path in the knowledge graph."""
    nodes: List[GraphNode]
    relationships: List[GraphRelationship]


async def connect_neo4j() -> None:
    """
    Connect to Neo4j database.
    Creates a global driver instance.
    """
    global neo4j_driver
    
    if not settings.NEO4J_PASSWORD:
        logger.warning("⚠️ Neo4j password not configured")
        return
    
    try:
        from neo4j import AsyncGraphDatabase
        
        logger.info(f"Connecting to Neo4j at {settings.NEO4J_URI}...")
        
        neo4j_driver = AsyncGraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
            max_connection_lifetime=3600,
            max_connection_pool_size=50
        )
        
        # Verify connection
        async with neo4j_driver.session() as session:
            result = await session.run("RETURN 1")
            await result.consume()
        
        logger.info("✅ Connected to Neo4j")
        
    except ImportError:
        logger.error("❌ Neo4j library not installed")
    except Exception as e:
        logger.error(f"❌ Failed to connect to Neo4j: {e}")
        neo4j_driver = None


async def close_neo4j() -> None:
    """Close Neo4j connection."""
    global neo4j_driver
    
    if neo4j_driver:
        await neo4j_driver.close()
        neo4j_driver = None
        logger.info("Neo4j connection closed")


def get_neo4j_driver():
    """
    Get the Neo4j driver instance.
    
    Returns:
        Neo4j AsyncDriver instance
        
    Raises:
        RuntimeError if not connected
    """
    if neo4j_driver is None:
        raise RuntimeError("Neo4j is not connected. Call connect_neo4j() first.")
    return neo4j_driver


# ===========================================
# Node Operations
# ===========================================

async def create_node(
    labels: List[str],
    properties: Dict[str, Any]
) -> Optional[str]:
    """
    Create a node in the knowledge graph.
    
    Args:
        labels: List of node labels
        properties: Node properties
        
    Returns:
        Node ID if successful
    """
    try:
        driver = get_neo4j_driver()
        label_str = ":".join(labels)
        
        async with driver.session() as session:
            query = f"""
            CREATE (n:{label_str} $properties)
            RETURN elementId(n) as node_id
            """
            result = await session.run(query, properties=properties)
            record = await result.single()
            return record["node_id"] if record else None
    except Exception as e:
        logger.error(f"Failed to create node: {e}")
        return None


async def find_node(
    labels: List[str] = None,
    properties: Dict[str, Any] = None
) -> Optional[GraphNode]:
    """
    Find a node by labels and/or properties.
    
    Args:
        labels: Optional list of labels to match
        properties: Optional properties to match
        
    Returns:
        GraphNode if found
    """
    try:
        driver = get_neo4j_driver()
        
        label_str = ":".join(labels) if labels else ""
        where_clause = ""
        
        if properties:
            conditions = [f"n.{k} = ${k}" for k in properties.keys()]
            where_clause = "WHERE " + " AND ".join(conditions)
        
        query = f"""
        MATCH (n{':' + label_str if label_str else ''})
        {where_clause}
        RETURN n, labels(n) as labels, elementId(n) as id
        LIMIT 1
        """
        
        async with driver.session() as session:
            result = await session.run(query, **(properties or {}))
            record = await result.single()
            
            if record:
                return GraphNode(
                    id=record["id"],
                    labels=record["labels"],
                    properties=dict(record["n"])
                )
        return None
    except Exception as e:
        logger.error(f"Failed to find node: {e}")
        return None


async def update_node(
    node_id: str,
    properties: Dict[str, Any]
) -> bool:
    """Update node properties."""
    try:
        driver = get_neo4j_driver()
        
        query = """
        MATCH (n)
        WHERE elementId(n) = $node_id
        SET n += $properties
        RETURN n
        """
        
        async with driver.session() as session:
            result = await session.run(query, node_id=node_id, properties=properties)
            record = await result.single()
            return record is not None
    except Exception as e:
        logger.error(f"Failed to update node: {e}")
        return False


# ===========================================
# Relationship Operations
# ===========================================

async def create_relationship(
    start_node_id: str,
    end_node_id: str,
    relationship_type: str,
    properties: Dict[str, Any] = None
) -> Optional[str]:
    """
    Create a relationship between two nodes.
    
    Args:
        start_node_id: ID of the start node
        end_node_id: ID of the end node
        relationship_type: Type of relationship
        properties: Optional relationship properties
        
    Returns:
        Relationship ID if successful
    """
    try:
        driver = get_neo4j_driver()
        
        query = f"""
        MATCH (a), (b)
        WHERE elementId(a) = $start_id AND elementId(b) = $end_id
        CREATE (a)-[r:{relationship_type} $properties]->(b)
        RETURN elementId(r) as rel_id
        """
        
        async with driver.session() as session:
            result = await session.run(
                query,
                start_id=start_node_id,
                end_id=end_node_id,
                properties=properties or {}
            )
            record = await result.single()
            return record["rel_id"] if record else None
    except Exception as e:
        logger.error(f"Failed to create relationship: {e}")
        return None


# ===========================================
# Query Operations for Fact Checking
# ===========================================

async def find_related_entities(
    entity_name: str,
    relationship_depth: int = 2,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """
    Find entities related to a given entity.
    
    Args:
        entity_name: Name of the entity to search from
        relationship_depth: Max depth of relationships to traverse
        limit: Maximum number of results
        
    Returns:
        List of related entities with relationships
    """
    try:
        driver = get_neo4j_driver()
        
        query = f"""
        MATCH (start:Entity {{name: $entity_name}})
        MATCH path = (start)-[*1..{relationship_depth}]-(related)
        RETURN DISTINCT 
            related.name as entity,
            labels(related) as labels,
            [r IN relationships(path) | type(r)] as relationship_types
        LIMIT $limit
        """
        
        async with driver.session() as session:
            result = await session.run(
                query, 
                entity_name=entity_name, 
                limit=limit
            )
            records = await result.data()
            return records
    except Exception as e:
        logger.error(f"Failed to find related entities: {e}")
        return []


async def query_fact_relationships(
    entities: List[str]
) -> List[Dict[str, Any]]:
    """
    Query relationships between multiple entities for fact checking.
    
    Args:
        entities: List of entity names to query
        
    Returns:
        List of relationships between entities
    """
    try:
        driver = get_neo4j_driver()
        
        query = """
        MATCH (a:Entity)-[r]-(b:Entity)
        WHERE a.name IN $entities AND b.name IN $entities
        RETURN 
            a.name as source,
            type(r) as relationship,
            b.name as target,
            r.verified as verified,
            r.source as fact_source
        """
        
        async with driver.session() as session:
            result = await session.run(query, entities=entities)
            records = await result.data()
            return records
    except Exception as e:
        logger.error(f"Failed to query fact relationships: {e}")
        return []


async def get_fact_chain(
    start_entity: str,
    end_entity: str,
    max_depth: int = 5
) -> Optional[GraphPath]:
    """
    Find the shortest path between two entities for inference.
    
    Args:
        start_entity: Starting entity name
        end_entity: Ending entity name
        max_depth: Maximum path length
        
    Returns:
        GraphPath if path exists
    """
    try:
        driver = get_neo4j_driver()
        
        query = f"""
        MATCH path = shortestPath(
            (a:Entity {{name: $start}})-[*1..{max_depth}]-(b:Entity {{name: $end}})
        )
        RETURN path
        """
        
        async with driver.session() as session:
            result = await session.run(
                query, 
                start=start_entity, 
                end=end_entity
            )
            record = await result.single()
            
            if record and record["path"]:
                path = record["path"]
                nodes = [
                    GraphNode(
                        id=str(node.element_id),
                        labels=list(node.labels),
                        properties=dict(node)
                    )
                    for node in path.nodes
                ]
                relationships = [
                    GraphRelationship(
                        id=str(rel.element_id),
                        type=rel.type,
                        start_node=str(rel.start_node.element_id),
                        end_node=str(rel.end_node.element_id),
                        properties=dict(rel)
                    )
                    for rel in path.relationships
                ]
                return GraphPath(nodes=nodes, relationships=relationships)
        return None
    except Exception as e:
        logger.error(f"Failed to get fact chain: {e}")
        return None


# ===========================================
# Schema Initialization
# ===========================================

async def init_graph_schema() -> None:
    """
    Initialize Neo4j schema with constraints and indexes.
    Called during application startup.
    """
    try:
        driver = get_neo4j_driver()
        
        async with driver.session() as session:
            # Create constraints
            constraints = [
                "CREATE CONSTRAINT entity_name IF NOT EXISTS FOR (e:Entity) REQUIRE e.name IS UNIQUE",
                "CREATE CONSTRAINT claim_id IF NOT EXISTS FOR (c:Claim) REQUIRE c.claim_id IS UNIQUE",
                "CREATE CONSTRAINT fact_id IF NOT EXISTS FOR (f:Fact) REQUIRE f.fact_id IS UNIQUE",
            ]
            
            for constraint in constraints:
                try:
                    await session.run(constraint)
                except Exception:
                    pass  # Constraint may already exist
            
            # Create indexes
            indexes = [
                "CREATE INDEX entity_type IF NOT EXISTS FOR (e:Entity) ON (e.type)",
                "CREATE INDEX claim_status IF NOT EXISTS FOR (c:Claim) ON (c.status)",
                "CREATE INDEX fact_verified IF NOT EXISTS FOR (f:Fact) ON (f.verified)",
            ]
            
            for index in indexes:
                try:
                    await session.run(index)
                except Exception:
                    pass
        
        logger.info("✅ Neo4j schema initialized")
    except Exception as e:
        logger.error(f"Failed to initialize Neo4j schema: {e}")


# Node label constants
class NodeLabels:
    """Neo4j node labels."""
    ENTITY = "Entity"
    CLAIM = "Claim"
    FACT = "Fact"
    SOURCE = "Source"
    PERSON = "Person"
    ORGANIZATION = "Organization"
    LOCATION = "Location"
    EVENT = "Event"
    CONCEPT = "Concept"


# Relationship type constants
class RelationshipTypes:
    """Neo4j relationship types."""
    RELATED_TO = "RELATED_TO"
    CAUSES = "CAUSES"
    CAUSED_BY = "CAUSED_BY"
    SUPPORTS = "SUPPORTS"
    CONTRADICTS = "CONTRADICTS"
    VERIFIED_BY = "VERIFIED_BY"
    CLAIMS = "CLAIMS"
    SPREADS_VIA = "SPREADS_VIA"
    OPERATES_AT = "OPERATES_AT"
    CANNOT_TRANSMIT = "CANNOT_TRANSMIT"
