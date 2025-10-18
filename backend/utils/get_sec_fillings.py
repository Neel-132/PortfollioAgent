"""
Add this to your backend/utils/market_utils.py file
"""

import logging
import requests
import asyncio
import time
from typing import List, Dict, Optional
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

logger = logging.getLogger(__name__)

# Configuration
SEC_USER_AGENT = "YourCompany contact@yourcompany.com"  # REPLACE WITH YOUR INFO
SCRAPE_FILINGS_CONTENT = True  # Set to False for faster prefetch (metadata only)
MAX_FILINGS_PER_TICKER = 5
MAX_CONCURRENT_SCRAPES = 3


class SECFilingsClient:
    """Handles SEC EDGAR API and web scraping for filings."""
    
    def __init__(self, user_agent: str = SEC_USER_AGENT):
        self.headers = {
            'User-Agent': user_agent,
            'Accept-Encoding': 'gzip, deflate'
        }
        self._cik_cache = {}
    
    def get_cik(self, ticker: str) -> Optional[str]:
        """Get CIK for a ticker symbol with caching."""
        ticker = ticker.upper()
        
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
                    logger.info(f"Found CIK {cik} for {ticker}")
                    return cik
            
            logger.warning(f"No CIK found for ticker {ticker}")
            return None
            
        except Exception as e:
            logger.error(f"Error fetching CIK for {ticker}: {e}")
            return None
    
    def fetch_filing_metadata(
        self,
        ticker: str,
        cik: str,
        max_filings: int = 5
    ) -> List[Dict]:
        """Fetch filing metadata from SEC EDGAR."""
        try:
            url = f"https://data.sec.gov/submissions/CIK{cik}.json"
            response = requests.get(url, headers=self.headers, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            recent = data.get('filings', {}).get('recent', {})
            
            forms = recent.get('form', [])
            dates = recent.get('filingDate', [])
            accessions = recent.get('accessionNumber', [])
            primary_docs = recent.get('primaryDocument', [])
            
            if not forms:
                logger.warning(f"No filings found in EDGAR response for {ticker}")
                return []
            
            filings = []
            for i in range(min(len(forms), max_filings)):
                accession_clean = accessions[i].replace('-', '')
                doc_url = (
                    f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/"
                    f"{accession_clean}/{primary_docs[i]}"
                )
                
                filings.append({
                    "type": forms[i],
                    "title": f"{forms[i]} filing for {ticker}",
                    "date": dates[i],
                    "url": doc_url,
                    "accession_number": accessions[i],
                    "scraped": False
                })
            
            logger.info(f"Found {len(filings)} filings for {ticker}")
            
            # SEC rate limit: max 10 requests per second
            time.sleep(0.1)
            
            return filings
            
        except requests.exceptions.RequestException as e:
            logger.error(f"HTTP error fetching filings for {ticker}: {e}")
            return []
        except Exception as e:
            logger.error(f"Error fetching filings for {ticker}: {e}", exc_info=True)
            return []
    
    def scrape_filings_sync(self, filings: List[Dict]) -> List[Dict]:
        """Scrape filing content synchronously."""
        if not filings:
            return []
        
        try:
            return asyncio.run(self._scrape_filings_async(filings))
        except Exception as e:
            logger.error(f"Error in scraping batch: {e}", exc_info=True)
            # Return filings with error status
            for filing in filings:
                filing["content"] = {
                    "success": False,
                    "error": "Batch scraping failed"
                }
                filing["scraped"] = False
            return filings
    
    async def _scrape_filings_async(self, filings: List[Dict]) -> List[Dict]:
        """Scrape multiple filings concurrently."""
        semaphore = asyncio.Semaphore(MAX_CONCURRENT_SCRAPES)
        
        async def scrape_one(filing):
            async with semaphore:
                url = filing.get("url")
                if not url:
                    filing["content"] = {"success": False, "error": "No URL"}
                    filing["scraped"] = False
                    return filing
                
                try:
                    logger.info(f"Scraping {filing['type']} from {url}")
                    content = await self._scrape_single_filing(url)
                    filing["content"] = content
                    filing["scraped"] = content.get("success", False)
                    
                    if content.get("success"):
                        logger.info(
                            f"Successfully scraped {filing['type']} "
                            f"({content.get('word_count', 0)} words)"
                        )
                    else:
                        logger.warning(
                            f"Failed to scrape {filing['type']}: "
                            f"{content.get('error', 'Unknown error')}"
                        )
                    
                except Exception as e:
                    logger.error(f"Error scraping {filing['type']}: {e}")
                    filing["content"] = {"success": False, "error": str(e)}
                    filing["scraped"] = False
                
                return filing
        
        tasks = [scrape_one(filing) for filing in filings]
        return await asyncio.gather(*tasks, return_exceptions=False)
    
    async def _scrape_single_filing(self, url: str) -> Dict:
        """Scrape a single filing URL using Crawl4AI."""
        try:
            browser_config = BrowserConfig(
                headless=True,
                verbose=False,
                extra_args=[
                    "--disable-gpu",
                    "--disable-dev-shm-usage",
                    "--no-sandbox",
                    "--disable-setuid-sandbox"
                ]
            )
            
            crawler_config = CrawlerRunConfig(
                cache_mode=CacheMode.BYPASS,
                wait_for_images=False,
                process_iframes=True,
                remove_overlay_elements=True,
                excluded_tags=['nav', 'footer', 'header', 'script', 'style'],
                word_count_threshold=10,
                page_timeout=30000,  # 30 seconds
            )
            
            async with AsyncWebCrawler(config=browser_config) as crawler:
                result = await crawler.arun(url=url, config=crawler_config)
                
                if not result.success:
                    error_msg = result.error_message or "Unknown crawl error"
                    return {
                        "success": False,
                        "error": error_msg
                    }
                
                # Extract and limit content
                markdown = result.markdown or ""
                # Limit to 100K characters to prevent memory issues
                markdown = markdown[:100000] if len(markdown) > 100000 else markdown
                
                return {
                    "success": True,
                    "markdown": markdown,
                    "word_count": len(markdown.split()),
                    "has_content": bool(markdown),
                    "content_length": len(markdown)
                }
                
        except asyncio.TimeoutError:
            return {
                "success": False,
                "error": "Scraping timeout (>30s)"
            }
        except Exception as e:
            logger.error(f"Exception scraping {url}: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }


# Global client instance (reused across calls)
_sec_client = None


def _get_sec_client() -> SECFilingsClient:
    """Get or create the global SEC client."""
    global _sec_client
    if _sec_client is None:
        _sec_client = SECFilingsClient(user_agent=SEC_USER_AGENT)
    return _sec_client


def fetch_sec_filings(
    entities: List[str],
    max_filings: int = MAX_FILINGS_PER_TICKER,
    scrape_content: bool = SCRAPE_FILINGS_CONTENT
) -> Dict[str, List[Dict]]:
    """
    Fetch SEC filings for a list of ticker symbols.
    
    This is the main function called by prefetch_market_data.
    
    Args:
        entities: List of ticker symbols
        max_filings: Maximum number of filings to fetch per ticker
        scrape_content: If True, scrape full filing content (slower).
                       If False, only return metadata (faster).
    
    Returns:
        Dictionary mapping ticker symbol to list of filing dictionaries.
        Each filing has: type, title, date, url, accession_number, 
        and optionally 'content' if scrape_content=True.
    
    Example return:
        {
            "AAPL": [
                {
                    "type": "10-Q",
                    "title": "10-Q filing for AAPL",
                    "date": "2024-01-15",
                    "url": "https://www.sec.gov/Archives/...",
                    "accession_number": "0000320193-24-000001",
                    "scraped": True,
                    "content": {
                        "success": True,
                        "markdown": "Full text...",
                        "word_count": 15234
                    }
                }
            ]
        }
    """
    client = _get_sec_client()
    results = {}
    
    for ticker in entities:
        ticker = ticker.upper()
        
        try:
            # Step 1: Get CIK
            cik = client.get_cik(ticker)
            if not cik:
                logger.warning(f"Skipping {ticker}: CIK not found")
                results[ticker] = []
                continue
            
            # Step 2: Fetch filing metadata
            filings = client.fetch_filing_metadata(ticker, cik, max_filings)
            if not filings:
                logger.warning(f"No filings found for {ticker}")
                results[ticker] = []
                continue
            
            # Step 3: Optionally scrape content
            if scrape_content:
                logger.info(f"Scraping {len(filings)} filings for {ticker}")
                filings = client.scrape_filings_sync(filings)
            else:
                logger.info(f"Skipping scraping for {ticker} (metadata only)")
            
            results[ticker] = filings
            logger.info(f"Successfully processed {ticker}: {len(filings)} filings")
            
        except Exception as e:
            logger.error(f"Failed to process {ticker}: {e}", exc_info=True)
            results[ticker] = []
    
    return results


# Alternative: Mock function for testing/development
def fetch_sec_filings_mock(
    entities: List[str],
    max_filings: int = 2
) -> Dict[str, list]:
    """
    Mock SEC filings for testing (no API calls).
    Swap with fetch_sec_filings for development.
    """
    from datetime import datetime
    
    results = {}
    for symbol in entities:
        symbol = symbol.upper()
        results[symbol] = [
            {
                "type": "8-K",
                "title": f"Mock 8-K filing for {symbol}",
                "date": datetime.utcnow().strftime("%Y-%m-%d"),
                "url": f"https://www.sec.gov/mock/{symbol}/8k.html",
                "accession_number": "0000000000-24-000001",
                "scraped": False
            },
            {
                "type": "10-Q",
                "title": f"Mock quarterly filing for {symbol}",
                "date": datetime.utcnow().replace(day=1).strftime("%Y-%m-%d"),
                "url": f"https://www.sec.gov/mock/{symbol}/10q.html",
                "accession_number": "0000000000-24-000002",
                "scraped": False
            }
        ][:max_filings]
    
    return results


# Configuration helper
def configure_sec_filings(
    user_agent: str = None,
    scrape_content: bool = None,
    max_filings: int = None,
    max_concurrent: int = None
):
    """
    Update SEC filings configuration.
    Call this at app startup to customize behavior.
    
    Example:
        configure_sec_filings(
            user_agent="MyCompany contact@mycompany.com",
            scrape_content=False,  # Fast mode
            max_filings=10
        )
    """
    global SEC_USER_AGENT, SCRAPE_FILINGS_CONTENT, MAX_FILINGS_PER_TICKER, MAX_CONCURRENT_SCRAPES
    global _sec_client
    
    if user_agent:
        SEC_USER_AGENT = user_agent
        _sec_client = None  # Force recreation with new user agent
    
    if scrape_content is not None:
        SCRAPE_FILINGS_CONTENT = scrape_content
    
    if max_filings is not None:
        MAX_FILINGS_PER_TICKER = max_filings
    
    if max_concurrent is not None:
        MAX_CONCURRENT_SCRAPES = max_concurrent
    
    logger.info(
        f"SEC filings configured: scrape={SCRAPE_FILINGS_CONTENT}, "
        f"max_filings={MAX_FILINGS_PER_TICKER}, "
        f"concurrent={MAX_CONCURRENT_SCRAPES}"
    )


# For testing
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Test with a few tickers
    tickers = ["AAPL", "MSFT"]
    
    # Option 1: Full scraping (slower)
    # results = fetch_sec_filings(tickers, max_filings=2, scrape_content=True)
    
    # Option 2: Metadata only (faster)
    results = fetch_sec_filings(tickers, max_filings=2, scrape_content=False)
    
    # Print results
    for ticker, filings in results.items():
        print(f"\n{ticker}: {len(filings)} filings")
        for filing in filings:
            print(f"  {filing['type']} - {filing['date']}")
            if filing.get('content'):
                print(f"    Words: {filing['content'].get('word_count', 0)}")