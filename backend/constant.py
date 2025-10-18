from pathlib import Path
import yaml
from dotenv import load_dotenv
load_dotenv()


BASE_DIR = Path(__file__).resolve().parent

PORTFOLIO_DATA_PATH = BASE_DIR / "data" / "portfolios.xlsx"
PROMPTS_PATH = BASE_DIR / "prompts" / "prompts.yaml"
CACHE_MARKETDATA_FILE = BASE_DIR / "data" / "market_cache_2.json"

with open(PROMPTS_PATH, "r", encoding="utf-8") as f:
    PROMPTS = yaml.safe_load(f)

finhub_news_endpoint = "https://finnhub.io/api/v1/company-news"



query_classification_prompt = PROMPTS["query_classification"]

portfolio_functioncalling_prompt = PROMPTS["portfolio_functioncalling"]

response_generation_prompt = PROMPTS["response_generator"]

validator_prompt = PROMPTS["validation_prompt"]

COMMON_SUFFIXES = [
    "inc", "inc.", "corp", "corp.", "corporation",
    "ltd", "ltd.", "plc", "llc", "co", "co.", "company", "incorporated"
]


portfolio_keywords = [
            "portfolio", "holding", "holdings", "own", "performance", "return",
            "gain", "allocation", "value", "profit", "loss", "perform"
        ]

market_keywords = [
            "news", "impact", "deal", "filing", "event", "announcement", "market"
        ]

## Confidence Map to assign to each intent
query_confidence_map = {
    "hybrid": 0.9,
    "portfolio": 0.95,
    "market": 0.85,
    "unknown": 0.5
}

spacy_valid_labels = ["ORG", "PRODUCT", "GPE", "PERSON"]

routing_map = {
            "portfolio": ["PortfolioAgent", "CalculatorTool"],
            "market": ["MarketAgent"], 
            "hybrid": ["MarketAgent", "PortfolioAgent", "CalculatorTool"],
            "unknown": []
}

comparison_based_pattern = r"(compare|better|vs|versus)"
performance_based_pattern = r"(return|performance|gain|loss|doing)"
holding_based_pattern = r"(holding|own|position|stock|portfolio)"