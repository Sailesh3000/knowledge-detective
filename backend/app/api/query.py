from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import logging

from app.query.engine import QueryEngine

logger = logging.getLogger(__name__)
router = APIRouter()

class QueryRequest(BaseModel):
    question: str

@router.post("/query")
def ask_question(request: QueryRequest):
    """
    Exposes the hybrid vector + graph reasoning query engine.
    """
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")
    
    try:
        engine = QueryEngine()
        response = engine.ask(request.question)
        return response
    except Exception as e:
        logger.error(f"Error in ask_question API: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to process query: {str(e)}")
