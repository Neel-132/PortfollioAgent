import logging
import json
import asyncio
from typing import List, Dict
from datetime import datetime
from pathlib import Path
import requests
import time
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from backend.utils.market_utils import fetch_news_data, fetch_sec_filings
import backend.constant as constant

CACHE_FILE = constant.CACHE_MARKETDATA_FILE


logger = logging.getLogger(__name__)


class SECFilingsIntegration:
    """Integrated SEC filings fetcher with scraping capability."""
    
    def __init__(self, user_agent: str = "YourCompany yourname@email.com"):
        self.headers = {
            'User-Agent': user_agent,
            'Accept-Encoding': 'gzip, deflate'
        }
        self._cik_cache = {}  # Cache CIK lookups
    
    def fetch_and_scrape_filings(
        self,
        ticker: str,
        max_filings: int = 5,
        scrape_content: bool = True
    ) -> List[Dict]:
        """
        Fetch and optionally scrape SEC filings for a single ticker.
        
        Args:
            ticker: Stock ticker symbol
            max_filings: Maximum number of filings to fetch
            scrape_content: Whether to scrape the filing content
        
        Returns:
            List of filing dictionaries with optional scraped content
        """
        ticker = ticker.upper()
        
        try:
            # Step 1: Get CIK
            cik = self._get_cik(ticker)
            if not cik:
                logger.warning(f"Could not find CIK for {ticker}")
                return []
            
            # Step 2: Fetch filing metadata
            filings = self._fetch_filing_metadata(ticker, cik, max_filings)
            if not filings:
                logger.warning(f"No filings found for {ticker}")
                return []
            
            # Step 3: Optionally scrape content
            if scrape_content:
                filings = self._scrape_filings_sync(filings)
            
            return filings
            
        except Exception as e:
            logger.error(f"Error fetching filings for {ticker}: {e}", exc_info=True)
            return []
    
    def _get_cik(self, ticker: str) -> str:
        """Get CIK for ticker with caching."""
        if ticker in self._cik_cache:
            return self._cik_cache[ticker]
        
        try:
            url = "https://www.sec.gov/files/company_tickers.json"
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            for item in data.values():
                if item.get('ticker', '').upper() == ticker:
                    cik = str(item['cik_str']).zfill(10)
                    self._cik_cache[ticker] = cik
                    return cik
            
            return ""
        except Exception as e:
            logger.error(f"Error fetching CIK for {ticker}: {e}")
            return ""
    
    def _fetch_filing_metadata(self, ticker: str, cik: str, max_filings: int) -> List[Dict]:
        """Fetch filing metadata from EDGAR."""
        try:
            url = f"https://data.sec.gov/submissions/CIK{cik}.json"
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            recent = data.get('filings', {}).get('recent', {})
            
            forms = recent.get('form', [])
            dates = recent.get('filingDate', [])
            accessions = recent.get('accessionNumber', [])
            primary_docs = recent.get('primaryDocument', [])
            
            filings = []
            for i in range(min(len(forms), max_filings)):
                accession = accessions[i].replace('-', '')
                
                filings.append({
                    "type": forms[i],
                    "title": f"{forms[i]} filing for {ticker}",
                    "date": dates[i],
                    "url": f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession}/{primary_docs[i]}",
                    "accession_number": accessions[i],
                    "scraped": False
                })
            
            time.sleep(0.1)  # SEC rate limit
            return filings
            
        except Exception as e:
            logger.error(f"Error fetching filing metadata for {ticker}: {e}")
            return []
    
    def _scrape_filings_sync(self, filings: List[Dict]) -> List[Dict]:
        """Scrape filings synchronously (wrapper for async)."""
        try:
            return asyncio.run(self._scrape_filings_async(filings))
        except Exception as e:
            logger.error(f"Error scraping filings: {e}")
            # Return filings without content on error
            for filing in filings:
                filing["content"] = {
                    "success": False,
                    "error": "Scraping failed"
                }
            return filings
    
    async def _scrape_filings_async(self, filings: List[Dict]) -> List[Dict]:
        """Scrape multiple filings asynchronously."""
        semaphore = asyncio.Semaphore(3)  # Max 3 concurrent
        
        async def scrape_one(filing):
            async with semaphore:
                try:
                    content = await self._scrape_filing(filing["url"])
                    filing["content"] = content
                    filing["scraped"] = content.get("success", False)
                except Exception as e:
                    logger.error(f"Error scraping {filing['url']}: {e}")
                    filing["content"] = {"success": False, "error": str(e)}
                    filing["scraped"] = False
                return filing
        
        tasks = [scrape_one(filing) for filing in filings]
        return await asyncio.gather(*tasks)
    
    async def _scrape_filing(self, url: str) -> Dict:
        """Scrape a single filing URL."""
        try:
            browser_config = BrowserConfig(
                headless=True,
                verbose=False,
                extra_args=["--disable-gpu", "--disable-dev-shm-usage", "--no-sandbox"]
            )
            
            crawler_config = CrawlerRunConfig(
                cache_mode=CacheMode.BYPASS,
                wait_for_images=False,
                process_iframes=True,
                excluded_tags=['nav', 'footer', 'header'],
                word_count_threshold=10,
            )
            
            async with AsyncWebCrawler(config=browser_config) as crawler:
                result = await crawler.arun(url=url, config=crawler_config)
                
                if not result.success:
                    return {"success": False, "error": result.error_message or "Unknown error"}
                
                return {
                    "success": True,
                    "markdown": result.markdown[:50000] if result.markdown else "",  # Limit size
                    "word_count": len(result.markdown.split()) if result.markdown else 0,
                    "has_content": bool(result.markdown)
                }
        except Exception as e:
            return {"success": False, "error": str(e)}


# Global instance for reuse
_sec_integration = None

def get_sec_integration(user_agent: str = "YourCompany yourname@email.com"):
    """Get or create SEC integration instance."""
    global _sec_integration
    if _sec_integration is None:
        _sec_integration = SECFilingsIntegration(user_agent=user_agent)
    return _sec_integration


def fetch_sec_filings(
    tickers: List[str],
    max_filings: int = 5,
    scrape_content: bool = True
) -> Dict[str, List[Dict]]:
    """
    Fetch SEC filings for multiple tickers.
    Drop-in replacement for your original function.
    
    Args:
        tickers: List of ticker symbols
        max_filings: Maximum filings per ticker
        scrape_content: Whether to scrape filing content
    
    Returns:
        Dictionary mapping ticker to list of filings
    """
    integration = get_sec_integration()
    results = {}
    
    for ticker in tickers:
        try:
            filings = integration.fetch_and_scrape_filings(
                ticker,
                max_filings=max_filings,
                scrape_content=scrape_content
            )
            results[ticker] = filings
        except Exception as e:
            logger.error(f"Error processing {ticker}: {e}")
            results[ticker] = []
    
    return results


def _load_existing_cache() -> Dict:
    """Load existing cache from file."""
    cache_file = Path("market_data_cache.json")
    if cache_file.exists():
        try:
            with open(cache_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading cache: {e}")
    return {}


def _save_cache(cache: Dict):
    """Save cache to file."""
    try:
        with open("market_data_cache.json", 'w') as f:
            json.dump(cache, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving cache: {e}")


def fetch_news_data(tickers: List[str]) -> Dict[str, List]:
    """Placeholder for your news fetching function."""
    # Replace with your actual implementation
    return {ticker: [] for ticker in tickers}


def prefetch_market_data(
    tickers: List[str],
    scrape_filings: bool = True,
    max_filings: int = 5
):
    """
    Prefetch news and filings for all tickers.
    This should run at startup or on client login.
    
    Args:
        tickers: List of ticker symbols
        scrape_filings: Whether to scrape filing content (slower but more data)
        max_filings: Maximum filings to fetch per ticker
    """
    logger.info(f"Starting prefetch for {len(tickers)} tickers")

    cache = _load_existing_cache()
    updated_cache = {}

    for ticker in tickers:
        ticker = ticker.upper()
        logger.info(f"Fetching news and filings for {ticker}")

        # 📰 News
        try:
            news_data = fetch_news_data([ticker])
        except Exception as e:
            logger.error(f"Failed to fetch news for {ticker}: {e}")
            news_data = {}

        # 📑 SEC Filings with Scraping
        try:
            filings_data = fetch_sec_filings(
                [ticker],
                max_filings=max_filings,
                scrape_content=scrape_filings
            )
            logger.info(f"Fetched {len(filings_data.get(ticker, []))} filings for {ticker}")
        except Exception as e:
            logger.error(f"Failed to fetch filings for {ticker}: {e}", exc_info=True)
            filings_data = {}

        updated_cache[ticker] = {
            "timestamp": datetime.utcnow().isoformat(),
            "news": news_data.get(ticker, []),
            "filings": filings_data.get(ticker, []),
            "filings_scraped": scrape_filings
        }
        
        # Save after each ticker to prevent data loss
        _save_cache(updated_cache)
        logger.info(f"Saved data for {ticker} to cache")

    logger.info(f"Prefetch complete for {len(tickers)} tickers")
    return updated_cache


# Alternative: Lightweight version (metadata only, no scraping)
def prefetch_market_data_lightweight(tickers: List[str]):
    """
    Faster prefetch that only gets filing metadata without scraping.
    Use this for quick startup, then scrape on-demand.
    """
    return prefetch_market_data(
        tickers=tickers,
        scrape_filings=False,  # Just metadata
        max_filings=5
    )


# On-demand scraping function
def scrape_filing_on_demand(ticker: str, filing_url: str) -> Dict:
    """
    Scrape a specific filing on-demand.
    Useful if you prefetch metadata only.
    """
    integration = get_sec_integration()
    try:
        return asyncio.run(integration._scrape_filing(filing_url))
    except Exception as e:
        logger.error(f"Error scraping filing for {ticker}: {e}")
        return {"success": False, "error": str(e)}


# Example usage
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Option 1: Full prefetch with scraping (slower, complete data)
    tickers = ["AAPL", "MSFT", "GOOGL"]
    cache = prefetch_market_data(tickers, scrape_filings=True, max_filings=3)
    
    # Option 2: Lightweight prefetch (faster, metadata only)
    # cache = prefetch_market_data_lightweight(tickers)
    
    # Print results
    for ticker, data in cache.items():
        print(f"\n{ticker}:")
        print(f"  Filings: {len(data['filings'])}")
        for filing in data['filings']:
            print(f"    {filing['type']} - {filing['date']} - Scraped: {filing.get('scraped', False)}")