# schemas/input_schema.py
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
import uuid

class PreviousSession(BaseModel):
    portfolio: Optional[Any] = None
    chat_history: Optional[list] = []
    intermediate_results: Optional[Dict] = {}
    metadata: Optional[Dict] = {}

class QueryInput(BaseModel):
    client_id: str = Field(..., description="Unique ID of the client making the query")
    query: str = Field(..., description="Natural language query text")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    metadata: Optional[Dict] = Field(default_factory=dict)
    previous_session: Optional[PreviousSession] = Field(
        default=None, description="Optional previous session context"
    )

    class Config:
        schema_extra = {
            "example": {
                "client_id": "CLT-001",
                "query": "How have my stocks performed?",
                "timestamp": "2025-10-16T00:02:45",
                "session_id": "sess_abc123",
                "metadata": {},
                "previous_session": {
                    "portfolio": [],
                    "chat_history": [
                        {"query": "Show me my holdings", "response": "You hold 5 stocks"}
                    ],
                    "intermediate_results": {"total_value": 500000},
                    "metadata": {}
                }
            }
        }
