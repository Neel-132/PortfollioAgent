import logging
# Configure logging format
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logging.basicConfig(format='%(asctime)s: %(levelname)s: %(message)s')
from .calculator import CalculatorTool
class PortfolioFunctions:
    """
    High-level functions exposed to LLM.
    Takes price_cache as input to avoid redundant API calls.
    """

    def __init__(self, portfolio_df, price_cache):
        self.calculator = CalculatorTool(portfolio_df, price_cache)

    def get_returns(self, entities=None):
        return self.calculator.get_returns(entities)

    def compare_performance(self, entities):
        return self.calculator.compare_performance(entities)

    def get_allocation(self, type="sector"):
        return self.calculator.get_allocation(type)

    def get_best_performers(self, limit=3):
        return self.calculator.get_best_performers(limit)

    def get_worst_performers(self, limit=3):
        return self.calculator.get_worst_performers(limit)

    def get_weight_in_portfolio(self, ticker):
        return self.calculator.get_weight_in_portfolio(ticker)
    
    def get_holdings(self, include_details=False):
        return self.calculator.get_holdings(include_details = include_details)
    
    def get_market_cap_allocation(self):
        return self.calculator.get_market_cap_allocation()
