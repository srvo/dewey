"""
OpenFIGI API Integration Script

This script:
1. Reads stock data from Universe.csv
2. Looks up FIGI identifiers using OpenFIGI API
3. Filters for primary listings using basic rules
4. Writes results to CSV with listing details
"""

import requests
import pandas as pd
import os
from datetime import datetime
import time
from typing import List, Dict, Any, Optional
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class StockDataProcessor:
    def __init__(self, api_key: str):
        """Initialize the processor with API key."""
        self.api_key = api_key
        self.last_request_time = 0
        self.rate_limit_delay = 0.1  # 100ms between requests for OpenFIGI
        self.batch_size = 100  # OpenFIGI batch size limit
        self.max_retries = 3
        self.retry_delay = 5  # 5 seconds between retries
        
        # Ensure output directory exists
        os.makedirs('data/raw', exist_ok=True)
    
    def get_stock_universe(self) -> pd.DataFrame:
        """Get the current stock universe from Universe.csv."""
        try:
            df = pd.read_csv('data/raw/Universe.csv')
            
            # Map CSV columns to our required format
            df = df.rename(columns={
                'Ticker': 'ticker',
                'Security Name': 'security_name',
                'Tick': 'tick'
            })
            
            # Add entity_id if not present
            if 'entity_id' not in df.columns:
                df['entity_id'] = df.index
            
            # Select required columns
            df = df[['ticker', 'security_name', 'tick', 'entity_id']]
            
            # Filter out any rows where ticker is null or empty
            df = df.dropna(subset=['ticker'])
            df = df[df['ticker'].str.strip() != '']
            
            return df.sort_values('ticker')
            
        except Exception as e:
            logging.error(f"Error reading Universe.csv: {str(e)}")
            raise
    
    def respect_rate_limit(self):
        """Ensure we don't exceed the OpenFIGI API rate limit."""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        if time_since_last_request < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - time_since_last_request)
        self.last_request_time = time.time()
    
    def filter_primary_listing(self, figi_data_list: List[Dict]) -> Dict:
        """Filter FIGI data to get the primary listing.
        
        Prioritizes:
        1. US exchange codes
        2. Common Stock security type
        3. Primary exchange for the region
        """
        # First try to find US common stock
        for data in figi_data_list:
            if (data.get('exchCode') == 'US' and 
                data.get('securityType') == 'Common Stock' and
                data.get('marketSector') == 'Equity'):
                return data
        
        # Then try any US listing
        for data in figi_data_list:
            if data.get('exchCode') == 'US':
                return data
        
        # Then try any common stock
        for data in figi_data_list:
            if data.get('securityType') == 'Common Stock':
                return data
        
        # Finally, just take the first one
        return figi_data_list[0] if figi_data_list else None
    
    def get_figi_data(self, companies: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """Get FIGI data for a batch of companies."""
        if not companies:
            return []
        
        retries = 0
        while retries < self.max_retries:
            try:
                self.respect_rate_limit()
                
                headers = {
                    'X-OPENFIGI-APIKEY': self.api_key,
                    'Content-Type': 'application/json'
                }
                
                mapping_jobs = [{"idType": "TICKER", "idValue": company["ticker"]} for company in companies]
                
                response = requests.post(
                    'https://api.openfigi.com/v3/mapping',
                    headers=headers,
                    json=mapping_jobs
                )
                response.raise_for_status()
                results = response.json()
                
                processed_results = []
                for idx, result in enumerate(results):
                    company = companies[idx]
                    if "data" in result:
                        # Filter for primary listing
                        primary_listing = self.filter_primary_listing(result["data"])
                        
                        processed_results.append({
                            'ticker': company['ticker'],
                            'security_name': company['security_name'],
                            'tick': company['tick'],
                            'entity_id': company['entity_id'],
                            'figi': primary_listing.get('figi') if primary_listing else None,
                            'market_sector': primary_listing.get('marketSector') if primary_listing else None,
                            'security_type': primary_listing.get('securityType') if primary_listing else None,
                            'exchange_code': primary_listing.get('exchCode') if primary_listing else None,
                            'composite_figi': primary_listing.get('compositeFIGI') if primary_listing else None,
                            'security_description': primary_listing.get('securityDescription') if primary_listing else None,
                            'lookup_status': 'success',
                            'alternative_listings': str(result["data"]) if result.get("data") else '[]'
                        })
                    else:
                        processed_results.append({
                            'ticker': company['ticker'],
                            'security_name': company['security_name'],
                            'tick': company['tick'],
                            'entity_id': company['entity_id'],
                            'figi': None,
                            'market_sector': None,
                            'security_type': None,
                            'exchange_code': None,
                            'composite_figi': None,
                            'security_description': None,
                            'lookup_status': f"failed: {result.get('warning', 'unknown error')}",
                            'alternative_listings': '[]'
                        })
                
                return processed_results
                
            except Exception as e:
                logging.error(f"Error processing batch (attempt {retries + 1}): {str(e)}")
                retries += 1
                if retries < self.max_retries:
                    logging.info(f"Retrying in {self.retry_delay} seconds...")
                    time.sleep(self.retry_delay)
                    continue
                
                # Return error results after all retries
                return [{
                    'ticker': company['ticker'],
                    'security_name': company['security_name'],
                    'tick': company['tick'],
                    'entity_id': company['entity_id'],
                    'figi': None,
                    'market_sector': None,
                    'security_type': None,
                    'exchange_code': None,
                    'composite_figi': None,
                    'security_description': None,
                    'lookup_status': f"error after {retries} attempts: {str(e)}",
                    'alternative_listings': '[]'
                } for company in companies]
    
    def process_universe(self, output_file: str = 'data/raw/stock_universe_figi.csv'):
        """Process the entire stock universe and write results to CSV."""
        # Get stock universe
        df = self.get_stock_universe()
        logging.info(f"Found {len(df)} companies in universe")
        
        # Convert to list of dicts for processing
        companies = df.to_dict('records')
        
        # Process in batches
        results = []
        for i in range(0, len(companies), self.batch_size):
            batch = companies[i:i+self.batch_size]
            logging.info(f"Processing batch {i//self.batch_size + 1} of {(len(companies)-1)//self.batch_size + 1}")
            
            batch_results = self.get_figi_data(batch)
            results.extend(batch_results)
            
            # Write intermediate results
            pd.DataFrame(results).to_csv(output_file, index=False)
            logging.info(f"Written {len(results)} results to {output_file}")
        
        logging.info("Processing completed")
        return results

def main():
    """Main entry point."""
    api_key = os.getenv('OPENFIGI_API_KEY')
    if not api_key:
        raise ValueError("OPENFIGI_API_KEY environment variable not set")
    
    processor = StockDataProcessor(api_key)
    processor.process_universe()

if __name__ == "__main__":
    main()