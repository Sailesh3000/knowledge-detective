from datetime import datetime
from enum import Enum
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

class SourceType(str, Enum):
    GITHUB = "github"
    GMAIL = "gmail"
    CALENDAR = "calendar"
    LOCAL = "local"

class Document(BaseModel):
    id: str = Field(..., description="Unique identifier for the document")
    source: SourceType = Field(..., description="Source system name")
    title: str = Field(..., description="Title or subject of the document")
    content: str = Field(..., description="Raw text content")
    url: Optional[str] = Field(None, description="Direct URL to the source document")
    timestamp: datetime = Field(..., description="Creation/modification timestamp")
    author: str = Field(..., description="Author's name or username or email")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional source-specific metadata")

class DocumentChunk(BaseModel):
    id: str = Field(..., description="Unique identifier for the chunk")
    document_id: str = Field(..., description="Reference to the parent document ID")
    content: str = Field(..., description="Text content of this chunk")
    chunk_index: int = Field(..., description="Index of the chunk in the document")
    embedding: Optional[List[float]] = Field(None, description="Vector embedding representation")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Merged document + chunk metadata")
