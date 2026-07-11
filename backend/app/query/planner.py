import json
import logging
from typing import Dict, List, Any
from app.config import settings
from app.llm_client import llm_client

logger = logging.getLogger(__name__)

class QueryPlanner:
    """
    Analyzes natural language questions, decomposes them into sub-queries,
    and determines the optimal search strategy (vector, graph, or hybrid).
    """

    def __init__(self):
        pass

    def plan_query(self, question: str) -> Dict[str, Any]:
        """
        Queries Fireworks AI to generate a structured query plan in JSON.
        """
        prompt = f"""You are the Query Planner for a hybrid knowledge retrieval system (vector + graph databases).
Your task is to analyze the user's question, identify key entities/topics, and decompose it into simple sub-queries.

User Question:
\"\"\"
{question}
\"\"\"

Guidelines:
1. Decompose the question into 1 to 3 simple sub-queries or search terms to feed into a semantic vector search.
2. Determine the optimal search strategy:
   - "graph": Use if the question is about structural relations, attendees, authorship, or trace connections (e.g. "Who attended kickoff?", "What did Sailesh write?").
   - "vector": Use if the question is conceptual, informational, or asks for specific content details (e.g. "What is our frontend architecture?").
   - "hybrid": Use for complex questions requiring both semantic context and structural relationships (e.g. "Why did Sailesh choose Neo4j?").
3. Extract key entities (names, technologies) and topics that should be queried in the graph database.

Output format MUST be valid JSON only. Do not include markdown code block formatting (such as ```json) or explanation.

Expected Output Format:
{{
  "sub_queries": ["sub query 1", "sub query 2"],
  "search_type": "vector|graph|hybrid",
  "entities": ["Name1", "TechnologyName"],
  "topics": ["TopicName"]
}}
"""
        fallback_plan = {
            "sub_queries": [question],
            "search_type": "hybrid",
            "entities": [],
            "topics": []
        }
        response_text = ""

        try:
            logger.info("Planning query using Fireworks AI...")
            response_text = llm_client.generate(
                prompt=prompt,
                system_instruction="You are the Query Planner for a hybrid knowledge retrieval system (vector + graph databases).",
                json_format=True,
                temperature=0.0
            )
            
            if not response_text:
                logger.warning("Fireworks AI returned an empty query plan.")
                return fallback_plan

            # Clean potential markdown packaging if present
            if response_text.startswith("```"):
                lines = response_text.splitlines()
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].startswith("```"):
                    lines = lines[:-1]
                response_text = "\n".join(lines).strip()

            data = json.loads(response_text)
            
            # Simple validation of plan
            plan = {
                "sub_queries": data.get("sub_queries") or [question],
                "search_type": (data.get("search_type") or "hybrid").lower(),
                "entities": data.get("entities") or [],
                "topics": data.get("topics") or []
            }
            
            if plan["search_type"] not in ["vector", "graph", "hybrid"]:
                plan["search_type"] = "hybrid"
                
            logger.info(f"Generated query plan: {plan}")
            return plan

        except Exception as e:
            logger.error(f"Failed to generate query plan via Fireworks AI: {str(e)}")
            if response_text:
                logger.error(f"Response text was: {response_text}")
            return fallback_plan

