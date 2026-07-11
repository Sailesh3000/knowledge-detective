import json
import logging
from typing import List, Dict, Any
from app.config import settings
from app.llm_client import llm_client

logger = logging.getLogger(__name__)

class EvidenceVerifier:
    """
    Validates retrieved evidence chunks against the user's question,
    filtering out irrelevant or redundant chunks to prevent LLM hallucination.
    """

    def __init__(self):
        pass

    def verify_evidence(self, question: str, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Queries Fireworks AI to filter and verify the factual relevance of retrieved chunks.
        """
        if not chunks:
            return []

        # Prepare text representation of retrieved chunks for the prompt
        evidence_list = []
        for i, c in enumerate(chunks):
            evidence_list.append(
                f"ID: {c.get('chunk_id', f'chunk_{i}')}\n"
                f"Title: {c.get('title', 'Unknown')}\n"
                f"Author: {c.get('author', 'Unknown')}\n"
                f"Content:\n{c.get('content', '')}\n"
                f"---"
            )
        evidence_text = "\n".join(evidence_list)

        prompt = f"""You are a precise Fact-Checking and Evidence Verification assistant.
Analyze the user's question and determine which of the retrieved document chunks contain relevant facts to answer the question.

User Question:
\"\"\"
{question}
\"\"\"

Retrieved Evidence Chunks:
\"\"\"
{evidence_text}
\"\"\"

Task:
For each chunk ID, determine if the chunk contains information directly relevant to the user's question.
Output your evaluation as a JSON object containing a list of verified chunk IDs.

Output format MUST be valid JSON only. Do not include markdown code block formatting (such as ```json) or explanation.

Expected Output Format:
{{
  "verified_chunk_ids": ["chunk_id_1", "chunk_id_2"]
}}
"""
        # Fallback: if verifier fails, keep all chunks rather than returning nothing
        fallback_result = chunks
        response_text = ""

        try:
            logger.info(f"Verifying {len(chunks)} evidence chunks using Fireworks AI...")
            response_text = llm_client.generate(
                prompt=prompt,
                system_instruction="You are a precise Fact-Checking and Evidence Verification assistant.",
                json_format=True,
                temperature=0.0
            )
            
            if not response_text:
                logger.warning("Fireworks AI returned an empty verification response. Falling back to all chunks.")
                return fallback_result

            # Clean potential markdown packaging if present
            if response_text.startswith("```"):
                lines = response_text.splitlines()
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].startswith("```"):
                    lines = lines[:-1]
                response_text = "\n".join(lines).strip()

            data = json.loads(response_text)
            verified_ids = data.get("verified_chunk_ids", [])
            
            if not verified_ids:
                logger.warning("Fireworks AI verified 0 chunks. Using all retrieved chunks to be safe.")
                return chunks

            verified_chunks = [c for c in chunks if c.get("chunk_id") in verified_ids]
            
            # If verifier filtered out everything, default to original list to avoid empty context
            if not verified_chunks:
                logger.warning("Verification filtered out all chunks. Reverting to original chunks.")
                return chunks
                
            logger.info(f"Verified {len(verified_chunks)} / {len(chunks)} chunks as factually relevant.")
            return verified_chunks

        except Exception as e:
            logger.error(f"Failed to verify evidence via Fireworks AI: {str(e)}. Proceeding with all chunks.")
            if response_text:
                logger.error(f"Response text was: {response_text}")
            return fallback_result

