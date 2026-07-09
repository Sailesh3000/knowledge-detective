from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List, Dict, Any
import logging

from app.ingestion.graph_builder import GraphBuilder

logger = logging.getLogger(__name__)
router = APIRouter()

def parse_node(node) -> Dict[str, Any]:
    """
    Parses a Neo4j node object into a standard frontend node dict.
    """
    labels = list(node.labels)
    primary_label = labels[0] if labels else "Unknown"
    
    # Determine the unique ID and clean label/name
    if "Person" in labels:
        node_id = node.get("name", "Unknown")
        label = node.get("name", "Unknown")
    elif "Technology" in labels or "Topic" in labels:
        node_id = node.get("name", "Unknown")
        label = node.get("name", "Unknown")
    else: # Document types (Doc, Email, Meeting, Commit, Issue)
        node_id = node.get("id", str(node.element_id))
        label = node.get("title", node_id)
        
    return {
        "id": node_id,
        "label": label,
        "type": primary_label,
        "properties": dict(node.items())
    }

@router.get("/graph")
def get_graph(entity: Optional[str] = Query(None, description="Entity or document title to center the graph around")):
    """
    Returns nodes and relationships matching an entity search,
    formatted for standard D3/force-directed graph visualizations.
    """
    graph_builder = GraphBuilder()
    nodes: Dict[str, Dict[str, Any]] = {}
    links: List[Dict[str, Any]] = []
    seen_links = set()

    try:
        with graph_builder.driver.session() as session:
            if entity and entity.strip():
                # 1-to-2 hop query centered around entity matches
                query = """
                MATCH (n)-[r]-(m)
                WHERE toLower(n.name) CONTAINS toLower($entity) 
                   OR toLower(n.title) CONTAINS toLower($entity)
                   OR toLower(n.id) CONTAINS toLower($entity)
                RETURN n, r, m LIMIT 150
                """
                result = session.run(query, entity=entity.strip())
            else:
                # Default global summary query
                query = """
                MATCH (n)-[r]-(m)
                RETURN n, r, m LIMIT 100
                """
                result = session.run(query)

            for record in result:
                n_parsed = parse_node(record["n"])
                m_parsed = parse_node(record["m"])
                
                # Add nodes to map
                nodes[n_parsed["id"]] = n_parsed
                nodes[m_parsed["id"]] = m_parsed
                
                # Parse relationship
                rel = record["r"]
                # In Neo4j driver, relationship start/end node properties correspond to element_ids
                # We need to map them back to our custom node IDs (name/id properties)
                start_id = n_parsed["id"] if rel.start_node.element_id == record["n"].element_id else m_parsed["id"]
                end_id = m_parsed["id"] if rel.end_node.element_id == record["m"].element_id else n_parsed["id"]
                
                link_key = (start_id, end_id, rel.type)
                if link_key not in seen_links:
                    seen_links.add(link_key)
                    links.append({
                        "source": start_id,
                        "target": end_id,
                        "type": rel.type
                    })

        logger.info(f"Graph retrieved {len(nodes)} nodes and {len(links)} links for query: '{entity}'")
        return {
            "nodes": list(nodes.values()),
            "links": links
        }

    except Exception as e:
        logger.error(f"Error retrieving graph neighborhood: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve graph data: {str(e)}")
