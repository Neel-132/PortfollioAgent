# managers/dependency_loader.py

import pandas as pd
from typing import Dict, List
from ..managers.session_manager import SessionManager
import backend.utils.helper as helper 
import backend.constant as constant
class DependencyLoader:
    """
    Loads client-specific portfolio data and builds symbol-name mappings.
    Stores everything into the SessionManager.
    """

    def __init__(self):
        self.portfolio_file = constant.PORTFOLIO_DATA_PATH
        self.df = pd.read_excel(self.portfolio_file)
        self.session_mgr = SessionManager.get_instance()

    def load_client_dependencies(self, client_id: str, session_id: str):
        """
        Loads portfolio & keywords for the given client and stores in session.
        """
        # 1. Filter portfolio for the client
        self.df['Purchase Price'] = self.df['Purchase Price'].apply(lambda x: round(x, 2))
        client_portfolio = self.df[self.df["client_id"] == client_id]
        if client_portfolio.empty:
            raise ValueError(f"No portfolio found for client_id {client_id}")

        # 2. Convert to list of dicts
        # holdings = client_portfolio.to_dict(orient="records")
        holdings = {
            client_id: group.to_dict(orient="records")
            for client_id, group in client_portfolio.groupby("client_id", group_keys = False)
        }
        # 3. Build symbol-name map
        symbol_name_map = self._build_symbol_name_map(holdings.get(client_id, {}))

        # 4. Store in session
        session = self.session_mgr.get_or_create_session(client_id, session_id)
        session["portfolio"] = holdings
        session["symbol_name_map"] = symbol_name_map
        session["client_id"] = client_id
        session["session_id"] = session_id

        return session

    def _build_symbol_name_map(self, holdings: List[Dict]) -> Dict[str, List[str]]:
        """
        Builds a dictionary mapping ticker symbols to lowercase name variations.
        Example:
            NVDA -> ["nvidia", "nvidia corporation"]
        """
        symbol_map = helper.create_stock_mappings(holdings)
        return symbol_map


if __name__ == "__main__":
    loader = DependencyLoader()
    x = loader.load_client_dependencies("CLT-001", "session_id")
    print(x)
