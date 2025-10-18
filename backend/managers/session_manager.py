# managers/session_manager.py
from typing import Dict, Tuple, Any
from threading import Lock

class SessionManager:
    """
    SessionManager is responsible for:
    - Storing and retrieving per-client sessions
    - Caching portfolio data, chat history, intermediate results
    - Ensuring thread-safe access (important for concurrent requests)
    """

    _instance = None
    _lock = Lock()

    def __init__(self):
        self._sessions: Dict[Tuple[str, str], Dict[str, Any]] = {}

    @classmethod
    def get_instance(cls):
        """Singleton pattern to ensure a single global session manager."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = SessionManager()
        return cls._instance

    def get_session(self, client_id: str, session_id: str) -> Dict[str, Any]:
        """Return session data for client_id and session_id, or None if not exists."""
        return self._sessions.get((client_id, session_id))

    def get_or_create_session(self, client_id: str, session_id: str) -> Dict[str, Any]:
        """
        Retrieve session if it exists, or initialize a new session structure if not.
        """
        if (client_id, session_id) not in self._sessions:
            self._sessions[(client_id, session_id)] = {
                "portfolio": None,
                "chat_history": [],
                "intermediate_results": {},
                "metadata": {}
            }
        return self._sessions[(client_id, session_id)]

    def update_portfolio(self, client_id: str, session_id: str, portfolio: Any):
        """Cache the client's portfolio data in the session."""
        session = self.get_or_create_session(client_id, session_id)
        session["portfolio"] = portfolio

    def get_portfolio(self, client_id: str, session_id: str) -> Any:
        """Retrieve cached portfolio data if exists."""
        session = self.get_session(client_id, session_id)
        return session["portfolio"] if session else None

    def append_chat(self, client_id: str, session_id: str, query: str, response: str):
        """Append query-response pair to session chat history."""
        session = self.get_or_create_session(client_id, session_id)
        session["chat_history"].append({"query": query, "response": response})

    def get_chat_history(self, client_id: str, session_id: str):
        """Return session chat history."""
        session = self.get_session(client_id, session_id)
        return session["chat_history"] if session else []

    def update_intermediate(self, client_id: str, session_id: str, key: str, value: Any):
        """Cache intermediate computed result (e.g. portfolio value, sector allocations)."""
        session = self.get_or_create_session(client_id, session_id)
        session["intermediate_results"][key] = value

    def get_intermediate(self, client_id: str, session_id: str, key: str):
        """Retrieve a previously stored intermediate result."""
        session = self.get_session(client_id, session_id)
        if session:
            return session["intermediate_results"].get(key)
        return None

    def clear_session(self, client_id: str, session_id: str):
        """Completely remove a session (e.g., logout or session timeout)."""
        self._sessions.pop((client_id, session_id), None)

    def clear_all(self):
        """Dangerous: clears all sessions."""
        self._sessions.clear()
