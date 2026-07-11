import json
import logging
from typing import Dict, List, Any
from app.config import settings
from app.llm_client import llm_client

logger = logging.getLogger(__name__)

class MetadataExtractor:
    """
    Extracts semantic entities and relationships from text chunks using Fireworks AI.
    """

    def __init__(self):
        pass

    def extract_metadata(self, content: str, title: str, source: str, author: str) -> Dict[str, Any]:
        """
        Queries Fireworks AI to extract Person, Technology, Topic entities 
        and their relationships from a text chunk.
        """
        prompt = f"""You are a precise knowledge graph extraction system.
Analyze the following document chunk and extract entities and relationships.

Metadata:
- Title: {title}
- Source: {source}
- Author: {author}

Text Chunk Content:
\"\"\"
{content}
\"\"\"

Task:
Extract:
1. "entities": List of key entities with:
   - "name": Standardized proper noun or term (e.g., "Sailesh", "Tejas", "Abhilash", "Neo4j", "Qdrant", "OAuth", "FastAPI").
   - "type": One of: "Person", "Technology", "Topic", "Doc"
2. "relationships": List of relationships with:
   - "source": Name of source entity.
   - "target": Name of target entity.
   - "type": One of: "AUTHORED_BY", "MENTIONS", "REFERENCES", "ATTENDED_BY"

Strict Rules:
- The "Doc" type entity should be used for the current document itself ({title}) or other files/PRs/commits referenced.
- Ensure "Person" entities refer to individuals (e.g. "Sailesh", "Tejas", "Abhilash").
- Output MUST be valid JSON only. Do not include markdown code block formatting (such as ```json) or explanation.

Expected Output Format:
{{
  "entities": [
    {{"name": "Sailesh", "type": "Person"}},
    {{"name": "Neo4j", "type": "Technology"}},
    {{"name": "Graph Database Decision", "type": "Topic"}}
  ],
  "relationships": [
    {{"source": "Sailesh", "target": "Neo4j", "type": "MENTIONS"}},
    {{"source": "{title}", "target": "Neo4j", "type": "REFERENCES"}}
  ]
}}
"""
        fallback_result = {"entities": [], "relationships": []}
        response_text = ""

        try:
            logger.info("Extracting metadata using Fireworks AI...")
            response_text = llm_client.generate(
                prompt=prompt,
                system_instruction="You are a precise knowledge graph extraction system.",
                json_format=True,
                temperature=0.0
            )
            
            if not response_text:
                logger.warning("Fireworks AI returned an empty response text.")
                return fallback_result

            # Clean potential markdown packaging if present
            if response_text.startswith("```"):
                # Strip markdown block wrappers
                lines = response_text.splitlines()
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].startswith("```"):
                    lines = lines[:-1]
                response_text = "\n".join(lines).strip()

            data = json.loads(response_text)
            
            # Post-processing validation
            entities = data.get("entities", [])
            relationships = data.get("relationships", [])
            
            # Basic validation of structures
            valid_entities = []
            for e in entities:
                if isinstance(e, dict) and "name" in e and "type" in e:
                    # Strip whitespace and capitalize types properly
                    e["name"] = e["name"].strip()
                    e["type"] = e["type"].strip()
                    if e["type"] in ["Person", "Technology", "Topic", "Doc"]:
                        valid_entities.append(e)
            
            valid_relationships = []
            for r in relationships:
                if isinstance(r, dict) and "source" in r and "target" in r and "type" in r:
                    r["source"] = r["source"].strip()
                    r["target"] = r["target"].strip()
                    r["type"] = r["type"].strip()
                    if r["type"] in ["AUTHORED_BY", "MENTIONS", "REFERENCES", "ATTENDED_BY"]:
                        valid_relationships.append(r)
                        
            logger.info(f"Fireworks AI successfully extracted {len(valid_entities)} entities and {len(valid_relationships)} relationships.")
            return {
                "entities": valid_entities,
                "relationships": valid_relationships
            }

        except Exception as e:
            logger.error(f"Error in metadata extraction via Fireworks AI: {str(e)}")
            if response_text:
                logger.error(f"Response text was: {response_text}")
            return fallback_result

