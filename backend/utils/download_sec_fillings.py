import requests
import logging
import asyncio
import json
from typing import List, Dict, Optional
from datetime import datetime
from pathlib import Path
import time
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

logger = logging.getLogger(__name__)


class SECFilingsPipeline:
    """Complete pipeline for fetching and scraping SEC filings."""
    
    def __init__(self, user_agent: str = "YourCompany yourname@email.com"):
        """
        Initialize the pipeline.
        
        Args:
            user_agent: User agent string with your contact info (required by SEC)
        """
        self.headers = {
            'User-Agent': user_agent,
            'Accept-Encoding': 'gzip, deflate'
        }
        self.results = {
            "timestamp": datetime.utcnow().isoformat(),
            "tickers": {},
            "summary": {
                "total_tickers": 0,
                "successful_tickers": 0,
                "failed_tickers": 0,
                "total_filings": 0,
                "successful_scrapes": 0,
                "failed_scrapes": 0
            }
        }
    
    def process_tickers(
        self,
        tickers: List[str],
        max_filings_per_ticker: int = 5,
        ticker_batch_size: int = 5,
        scrape_batch_size: int = 3,
        output_file: Optional[str] = None,
        save_intermediate: bool = True
    ) -> Dict:
        """
        Main pipeline: Fetch filings from EDGAR and scrape with Crawl4AI.
        
        Args:
            tickers: List of ticker symbols to process
            max_filings_per_ticker: Maximum number of filings to fetch per ticker
            ticker_batch_size: Number of tickers to process before saving
            scrape_batch_size: Number of concurrent scraping tasks
            output_file: Path to save final JSON (default: sec_filings_TIMESTAMP.json)
            save_intermediate: Whether to save after each ticker batch
        
        Returns:
            Dictionary containing all results
        """
        self.results["summary"]["total_tickers"] = len(tickers)
        
        if output_file is None:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            output_file = f"sec_filings_{timestamp}.json"
        
        # Process tickers in batches
        for i in range(0, len(tickers), ticker_batch_size):
            batch = tickers[i:i + ticker_batch_size]
            logger.info(f"Processing batch {i//ticker_batch_size + 1}: {batch}")
            
            for ticker in batch:
                try:
                    self._process_single_ticker(
                        ticker,
                        max_filings_per_ticker,
                        scrape_batch_size
                    )
                except Exception as e:
                    logger.error(f"Critical error processing ticker {ticker}: {e}", exc_info=True)
                    self.results["tickers"][ticker] = {
                        "success": False,
                        "error": str(e),
                        "filings": []
                    }
                    self.results["summary"]["failed_tickers"] += 1
            
            # Save intermediate results
            if save_intermediate:
                self._save_results(output_file)
                logger.info(f"Saved intermediate results to {output_file}")
        
        # Final save
        self._save_results(output_file)
        logger.info(f"Pipeline complete. Results saved to {output_file}")
        
        return self.results
    
    def _process_single_ticker(
        self,
        ticker: str,
        max_filings: int,
        scrape_batch_size: int
    ):
        """Process a single ticker: fetch filings and scrape them."""
        ticker = ticker.upper()
        logger.info(f"Processing ticker: {ticker}")
        
        # Initialize ticker result
        self.results["tickers"][ticker] = {
            "success": False,
            "filings": [],
            "fetch_timestamp": datetime.utcnow().isoformat()
        }
        
        try:
            # Step 1: Get CIK
            cik = self._get_cik_from_ticker(ticker)
            if not cik:
                raise ValueError(f"Could not find CIK for ticker {ticker}")
            
            logger.info(f"Found CIK {cik} for {ticker}")
            
            # Step 2: Fetch filings metadata
            filings = self._fetch_filings_metadata(ticker, cik, max_filings)
            if not filings:
                raise ValueError(f"No filings found for {ticker}")
            
            logger.info(f"Found {len(filings)} filings for {ticker}")
            self.results["summary"]["total_filings"] += len(filings)
            
            # Step 3: Scrape filings content
            scraped_filings = self._scrape_filings(filings, scrape_batch_size)
            
            # Update results
            self.results["tickers"][ticker] = {
                "success": True,
                "cik": cik,
                "filings": scraped_filings,
                "fetch_timestamp": datetime.utcnow().isoformat(),
                "total_filings": len(scraped_filings),
                "successful_scrapes": sum(1 for f in scraped_filings if f.get("content", {}).get("success", False))
            }
            
            self.results["summary"]["successful_tickers"] += 1
            
        except Exception as e:
            logger.error(f"Error processing ticker {ticker}: {e}", exc_info=True)
            self.results["tickers"][ticker]["success"] = False
            self.results["tickers"][ticker]["error"] = str(e)
            self.results["summary"]["failed_tickers"] += 1
    
    def _get_cik_from_ticker(self, ticker: str) -> Optional[str]:
        """Get CIK for a ticker symbol."""
        try:
            url = "https://www.sec.gov/files/company_tickers.json"
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            for item in data.values():
                if item.get('ticker', '').upper() == ticker.upper():
                    return str(item['cik_str']).zfill(10)
            
            return None
            
        except Exception as e:
            logger.error(f"Error fetching CIK for {ticker}: {e}", exc_info=True)
            return None
    
    def _fetch_filings_metadata(
        self,
        ticker: str,
        cik: str,
        max_filings: int
    ) -> List[Dict]:
        """Fetch filings metadata from EDGAR."""
        try:
            filings_url = f"https://data.sec.gov/submissions/CIK{cik}.json"
            
            response = requests.get(filings_url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            filings = []
            
            recent = data.get('filings', {}).get('recent', {})
            forms = recent.get('form', [])
            filing_dates = recent.get('filingDate', [])
            accession_numbers = recent.get('accessionNumber', [])
            primary_documents = recent.get('primaryDocument', [])
            
            for i in range(min(len(forms), max_filings)):
                accession = accession_numbers[i].replace('-', '')
                primary_doc = primary_documents[i]
                
                doc_url = (
                    f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/"
                    f"{accession}/{primary_doc}"
                )
                
                filings.append({
                    "type": forms[i],
                    "title": f"{forms[i]} filing for {ticker}",
                    "date": filing_dates[i],
                    "url": doc_url,
                    "accession_number": accession_numbers[i]
                })
            
            # SEC rate limit
            time.sleep(0.1)
            
            return filings
            
        except Exception as e:
            logger.error(f"Error fetching filings for {ticker}: {e}", exc_info=True)
            return []
    
    def _scrape_filings(
        self,
        filings: List[Dict],
        batch_size: int
    ) -> List[Dict]:
        """Scrape content from filing URLs."""
        scraped_filings = []
        
        for i in range(0, len(filings), batch_size):
            batch = filings[i:i + batch_size]
            logger.info(f"Scraping batch of {len(batch)} filings")
            
            try:
                batch_results = asyncio.run(
                    self._scrape_batch_async(batch)
                )
                scraped_filings.extend(batch_results)
            except Exception as e:
                logger.error(f"Error scraping batch: {e}", exc_info=True)
                # Add filings with error status
                for filing in batch:
                    scraped_filings.append({
                        **filing,
                        "content": {
                            "success": False,
                            "error": f"Batch scraping failed: {str(e)}"
                        }
                    })
        
        return scraped_filings
    
    async def _scrape_batch_async(self, filings: List[Dict]) -> List[Dict]:
        """Scrape a batch of filings asynchronously."""
        semaphore = asyncio.Semaphore(len(filings))
        
        async def scrape_single(filing):
            async with semaphore:
                try:
                    content = await self._scrape_filing_async(filing["url"])
                    
                    if content["success"]:
                        self.results["summary"]["successful_scrapes"] += 1
                    else:
                        self.results["summary"]["failed_scrapes"] += 1
                    
                    return {
                        **filing,
                        "content": content,
                        "scrape_timestamp": datetime.utcnow().isoformat()
                    }
                except Exception as e:
                    logger.error(f"Error scraping {filing['url']}: {e}", exc_info=True)
                    self.results["summary"]["failed_scrapes"] += 1
                    return {
                        **filing,
                        "content": {
                            "success": False,
                            "error": str(e)
                        },
                        "scrape_timestamp": datetime.utcnow().isoformat()
                    }
        
        tasks = [scrape_single(filing) for filing in filings]
        return await asyncio.gather(*tasks, return_exceptions=False)
    
    async def _scrape_filing_async(self, url: str) -> Dict:
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
                remove_overlay_elements=True,
                excluded_tags=['nav', 'footer', 'header'],
                word_count_threshold=10,
            )
            
            async with AsyncWebCrawler(config=browser_config) as crawler:
                result = await crawler.arun(url=url, config=crawler_config)
                
                if not result.success:
                    return {
                        "success": False,
                        "error": result.error_message or "Unknown error"
                    }
                
                # Extract tables
                tables = self._extract_tables_from_markdown(result.markdown or "")
                
                return {
                    "success": True,
                    "markdown": result.markdown,
                    "text": result.cleaned_html if result.cleaned_html else "",
                    "tables": tables,
                    "metadata": {
                        "title": result.metadata.get("title", "") if result.metadata else "",
                        "word_count": len(result.markdown.split()) if result.markdown else 0,
                        "table_count": len(tables)
                    }
                }
                
        except Exception as e:
            logger.error(f"Error scraping {url}: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    def _extract_tables_from_markdown(self, markdown: str) -> List[Dict]:
        """Extract tables from markdown content."""
        tables = []
        if not markdown:
            return tables
        
        lines = markdown.split('\n')
        current_table = []
        in_table = False
        
        for line in lines:
            if '|' in line:
                if not in_table:
                    in_table = True
                    current_table = []
                current_table.append(line)
            else:
                if in_table and current_table:
                    tables.append(self._parse_markdown_table(current_table))
                    current_table = []
                    in_table = False
        
        if current_table:
            tables.append(self._parse_markdown_table(current_table))
        
        return tables
    
    def _parse_markdown_table(self, table_lines: List[str]) -> Dict:
        """Parse markdown table into structured format."""
        if len(table_lines) < 2:
            return {"headers": [], "rows": []}
        
        headers = [h.strip() for h in table_lines[0].split('|') if h.strip()]
        rows = []
        
        for line in table_lines[2:]:
            cells = [c.strip() for c in line.split('|') if c.strip()]
            if cells:
                rows.append(cells)
        
        return {"headers": headers, "rows": rows}
    
    def _save_results(self, output_file: str):
        """Save results to JSON file."""
        try:
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(self.results, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Results saved to {output_file}")
            
        except Exception as e:
            logger.error(f"Error saving results: {e}", exc_info=True)


def process_sec_filings(
    tickers: List[str],
    max_filings_per_ticker: int = 5,
    output_file: Optional[str] = None,
    user_agent: str = "YourCompany yourname@email.com"
) -> Dict:
    """
    Convenience function to process SEC filings for a list of tickers.
    
    Args:
        tickers: List of ticker symbols
        max_filings_per_ticker: Maximum filings to fetch per ticker
        output_file: Output JSON file path (auto-generated if None)
        user_agent: SEC User-Agent with contact info
    
    Returns:
        Dictionary with all results
    """
    pipeline = SECFilingsPipeline(user_agent=user_agent)
    return pipeline.process_tickers(
        tickers=tickers,
        max_filings_per_ticker=max_filings_per_ticker,
        output_file=output_file,
        ticker_batch_size=5,
        scrape_batch_size=3,
        save_intermediate=True
    )


# Example usage
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Process multiple tickers
    tickers = ["AAPL", "MSFT", "GOOGL", "TSLA", "AMZN"]
    
    results = process_sec_filings(
        tickers=tickers,
        max_filings_per_ticker=3,
        output_file="sec_filings_output.json",
        user_agent="MyCompany contact@example.com"  # Replace with your info
    )
    breakpoint()
    # Print summary
    print("\n" + "="*50)
    print("PROCESSING SUMMARY")
    print("="*50)
    print(f"Total tickers: {results['summary']['total_tickers']}")
    print(f"Successful: {results['summary']['successful_tickers']}")
    print(f"Failed: {results['summary']['failed_tickers']}")
    print(f"Total filings: {results['summary']['total_filings']}")
    print(f"Successful scrapes: {results['summary']['successful_scrapes']}")
    print(f"Failed scrapes: {results['summary']['failed_scrapes']}")
    print("="*50)