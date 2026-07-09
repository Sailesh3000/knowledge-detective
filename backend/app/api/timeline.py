from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List, Dict, Any
import logging

from app.ingestion.graph_builder import GraphBuilder

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/timeline")
def get_timeline(topic: Optional[str] = Query(None, description="Topic, tech, or person to filter the timeline by")):
    """
    Returns a chronological sequence of documents (commits, emails, meetings, docs) 
    associated with a topic, technology, or person.
    """
    graph_builder = GraphBuilder()
    events = []

    try:
        with graph_builder.driver.session() as session:
            if topic and topic.strip():
                # Filtered timeline query matching topic, tech, or person
                query = """
                MATCH (d:Document)
                WHERE d.title IS NOT NULL
                WITH d
                OPTIONAL MATCH (d)-[:MENTIONS]->(t:Topic)
                OPTIONAL MATCH (d)-[:MENTIONS]->(tech:Technology)
                OPTIONAL MATCH (p:Person)-[:AUTHORED|ATTENDED]->(d)
                WHERE toLower(t.name) CONTAINS toLower($topic) 
                   OR toLower(tech.name) CONTAINS toLower($topic)
                   OR toLower(p.name) CONTAINS toLower($topic)
                   OR any(alias IN p.aliases WHERE toLower(alias) CONTAINS toLower($topic))
                   OR toLower(d.title) CONTAINS toLower($topic)
                RETURN DISTINCT 
                    d.id as id, 
                    d.title as title, 
                    d.source as source, 
                    d.timestamp as timestamp, 
                    d.author as author, 
                    d.content_snippet as snippet
                ORDER BY d.timestamp ASC
                """
                result = session.run(query, topic=topic.strip())
            else:
                # Default unfiltered timeline
                query = """
                MATCH (d:Document)
                RETURN 
                    d.id as id, 
                    d.title as title, 
                    d.source as source, 
                    d.timestamp as timestamp, 
                    d.author as author, 
                    d.content_snippet as snippet
                ORDER BY d.timestamp ASC
                LIMIT 100
                """
                result = session.run(query)

            for record in result:
                ts_val = record["timestamp"]
                iso_ts = None
                if ts_val:
                    if hasattr(ts_val, "isoformat"):
                        iso_ts = ts_val.isoformat()
                    else:
                        iso_ts = str(ts_val)

                events.append({
                    "id": record["id"],
                    "title": record["title"],
                    "source": record["source"],
                    "timestamp": iso_ts,
                    "author": record["author"],
                    "snippet": record["snippet"]
                })

        logger.info(f"Timeline retrieved {len(events)} events for topic: '{topic}'")
        return {"topic": topic, "events": events}

    except Exception as e:
        logger.error(f"Error retrieving timeline: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve timeline: {str(e)}")
