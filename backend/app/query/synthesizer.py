import logging
import requests
from typing import List, Dict, Any, Tuple

from app.config import settings

logger = logging.getLogger(__name__)

class AnswerSynthesizer:
    """
    Synthesizes the final natural language answer based on verified evidence chunks,
    strictly enforcing citations and anti-hallucination instructions.
    """

    def __init__(self):
        self.ollama_url = f"{settings.OLLAMA_BASE_URL}/api/generate"
        self.model = settings.OLLAMA_MODEL

    def synthesize(self, question: str, verified_chunks: List[Dict[str, Any]]) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Queries Ollama to synthesize the final answer with inline citations.
        Returns a tuple of (synthesized_answer, unique_citations_metadata).
        """
        if not verified_chunks:
            return (
                "No relevant documents were found in the database to answer this question.",
                []
            )

        # 1. Format the verified chunks for the context window
        context_blocks = []
        citations_map: Dict[str, Dict[str, Any]] = {}
        
        for i, chunk in enumerate(verified_chunks):
            title = chunk.get("title", f"Document {i}")
            doc_id = chunk.get("document_id", f"doc_{i}")
            source = chunk.get("source", "unknown")
            author = chunk.get("author", "Unknown")
            timestamp = chunk.get("timestamp", "")
            url = chunk.get("url", "")
            
            # Record citation metadata for reference mapping
            if title not in citations_map:
                citations_map[title] = {
                    "id": doc_id,
                    "title": title,
                    "source": source,
                    "author": author,
                    "timestamp": timestamp,
                    "url": url
                }

            context_blocks.append(
                f"Document Title: {title}\n"
                f"Source System: {source}\n"
                f"Author: {author}\n"
                f"Timestamp: {timestamp}\n"
                f"Content:\n{chunk.get('content', '')}\n"
                f"================================="
            )

        context_text = "\n".join(context_blocks)

        # 2. Formulate system guidelines and user prompt
        prompt = f"""You are Knowledge Detective, an advanced enterprise RAG reasoning agent.
Synthesize a clear, direct, and helpful answer to the user's question using ONLY the provided verified document context.

User Question:
\"\"\"
{question}
\"\"\"

Verified Context:
\"\"\"
{context_text}
\"\"\"

Strict Guidelines:
1. **Fact-based Only**: Rely only on clear facts directly mentioned in the verified context. Do NOT assume, extrapolate, or hallucinate.
2. **Inline Citations**: Every claim or fact you mention MUST be followed by an inline citation to its source document title in the exact format: `[Source: Document Title]`.
3. **No Fabrication**: If the context does not contain enough information to fully answer the question, state exactly what is missing rather than making up answers.
4. **Tone**: Be professional, objective, and analytical.

Answer:
"""
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.2, # slightly low temperature for factuality
                "seed": 42
            }
        }

        try:
            logger.info("Synthesizing final answer with Ollama...")
            response = requests.post(self.ollama_url, json=payload, timeout=180.0)
            response.raise_for_status()
            
            result_json = response.json()
            answer = result_json.get("response", "").strip()
            
            # Collect list of citations that were actually mentioned in the text
            active_citations = []
            for title, meta in citations_map.items():
                if f"[Source: {title}]" in answer or title in answer:
                    active_citations.append(meta)
                    
            # Fallback: if somehow no citations detected but we had docs, attach them
            if not active_citations and citations_map:
                active_citations = list(citations_map.values())

            logger.info(f"Synthesized answer successfully. Cited {len(active_citations)} sources.")
            return answer, active_citations

        except Exception as e:
            logger.error(f"Failed to synthesize answer: {str(e)}")
            return (
                "Error: Failed to synthesize an answer due to an internal LLM connection issue.",
                []
            )
