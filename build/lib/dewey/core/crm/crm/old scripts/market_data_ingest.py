#!pip pandas pyarrow s3fs pyEX supabase requests wmill
from typing import List, Dict, Optional, Tuple
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import s3fs
import wmill
from datetime import datetime, timedelta
import yfinance as yf
from supabase import create_client, Client
import re
import traceback
from collections import defaultdict

# Hardcoded configs for debugging
SUPABASE_CONFIG = {
    "url": "https://avyxazyiaibtahuciggx.supabase.co",
    "service_role_key": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImF2eXhhenlpYWlidGFodWNpZ2d4Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTczMjEwMDEwOCwiZXhwIjoyMDQ3Njc2MTA4fQ.x3k96ILT2b-wzThVZ67o3coJhvBw1Of_tPuhdKAZnGk"
}

def validate_ticker(ticker: str) -> Tuple[bool, str]:
    """Validate ticker symbol format"""
    if not ticker:
        return False, ""
    
    # Remove whitespace and convert to uppercase
    cleaned = ticker.strip().upper()
    
    # Skip mutual funds and certain patterns
    if any([
        cleaned.endswith('X'),  # Mutual funds
        cleaned.startswith(('A0', 'US')),  # Foreign listings
        len(cleaned) > 5,  # Most US tickers are 1-5 chars
        not cleaned.isalpha()  # Only letters for now
    ]):
        return False, cleaned
        
    return True, cleaned

def update_company_status(client: Client, ticker: str, status: str, note: str, metadata: Dict = None) -> None:
    """Update company status and metadata in Supabase"""
    try:
        update_data = {
            'workflow_status': status,
            'notes': note,
            'last_updated': datetime.now().isoformat()
        }
        
        if metadata:
            update_data['metadata'] = metadata
            
        client.table('companies')\
            .update(update_data)\
            .eq('ticker', ticker)\
            .execute()
            
    except Exception as e:
        print(f"⚠️ Failed to update {ticker}: {str(e)}")

def get_max_history(symbol: str) -> Tuple[str, int, Dict]:
    """Get maximum available history for a symbol
    Returns: (start_date, years_of_history, metadata)
    """
    try:
        # Create Ticker object
        ticker = yf.Ticker(symbol)
        
        # Get all available info
        info = ticker.info
        
        # Try to get first listed date from info
        start_date = None
        if 'firstTradeDateEpochUtc' in info:
            start_date = datetime.fromtimestamp(info['firstTradeDateEpochUtc'])
        
        # If no listing date found, try downloading max history
        if not start_date:
            hist = ticker.history(period='max')
            if not hist.empty:
                start_date = hist.index[0].to_pydatetime()
        
        if start_date:
            years = (datetime.now() - start_date).days / 365.25
            metadata = {
                'start_date': start_date.strftime('%Y-%m-%d'),
                'years': round(years, 1),
                'exchange': info.get('exchange', 'Unknown'),
                'type': info.get('quoteType', 'Unknown'),
                'currency': info.get('currency', 'Unknown')
            }
            return start_date.strftime('%Y-%m-%d'), years, metadata
            
    except Exception as e:
        print(f"Error getting history for {symbol}: {str(e)}")
    
    return None, 0, {}

def get_all_companies(client: Client) -> List[dict]:
    """Get all companies with pagination"""
    all_companies = []
    page = 0
    page_size = 1000
    
    while True:
        print(f"\nFetching page {page + 1}...")
        result = client.table('companies')\
            .select('ticker, excluded, workflow_status')\
            .neq('ticker', None)\
            .eq('excluded', False)\
            .range(page * page_size, (page + 1) * page_size - 1)\
            .execute()
            
        if not result.data:
            break
            
        all_companies.extend(result.data)
        print(f"Found {len(result.data)} companies on page {page + 1}")
        
        if len(result.data) < page_size:
            break
            
        page += 1
    
    print(f"\nTotal companies found: {len(all_companies)}")
    return all_companies

def get_portfolio_tickers() -> List[str]:
    """Get all unique tickers from companies table"""
    try:
        print("Connecting to Supabase...")
        client: Client = create_client(
            SUPABASE_CONFIG['url'],
            SUPABASE_CONFIG['service_role_key']
        )
        print("Connected successfully")
        
        # Get all companies with pagination
        companies = get_all_companies(client)
        
        # Track statistics
        stats = {
            'total': len(companies),
            'valid': 0,
            'invalid': 0,
            'skipped': 0,
            'delisted': 0,
            'reasons': {}
        }
        
        # Validate and clean tickers
        valid_tickers = set()
        invalid_tickers = []
        skipped = []
        
        for record in companies:
            if ticker := record.get('ticker'):
                # Skip certain patterns
                skip_reason = None
                if ' ' in ticker:
                    skip_reason = 'contains_space'
                elif 'PRG' in ticker:
                    skip_reason = 'preferred_share'
                elif '.' in ticker:
                    skip_reason = 'dot_notation'
                elif '-' in ticker:
                    skip_reason = 'contains_dash'
                elif len(ticker) > 5:
                    skip_reason = 'too_long'
                elif not ticker.replace('-','').isalnum():
                    skip_reason = 'invalid_chars'
                    
                if skip_reason:
                    skipped.append(ticker)
                    stats['skipped'] += 1
                    stats['reasons'][skip_reason] = stats['reasons'].get(skip_reason, 0) + 1
                    continue
                    
                # Check if ticker is active
                try:
                    start_date, years, period = get_max_history(ticker)
                    if start_date:
                        valid_tickers.add(ticker)
                        stats['valid'] += 1
                        print(f"✓ Valid ticker: {ticker} (history: {years}y)")
                        
                        # Update Supabase with history info
                        note = f"Active ticker with {years} years of history (since {start_date})"
                        update_company_status(client, ticker, 'active', note)
                    else:
                        stats['delisted'] += 1
                        print(f"✗ No data for: {ticker}")
                        update_company_status(client, ticker, 'delisted', 'No price data available')
                except Exception as e:
                    invalid_tickers.append(ticker)
                    stats['invalid'] += 1
                    print(f"✗ Error checking {ticker}: {str(e)}")
        
        # Log results
        print("\n=== Ticker Statistics ===")
        print(f"Total companies: {stats['total']}")
        print(f"Valid tickers: {stats['valid']}")
        print(f"Invalid tickers: {stats['invalid']}")
        print(f"Delisted tickers: {stats['delisted']}")
        print(f"Skipped tickers: {stats['skipped']}")
        print("\nSkip reasons:")
        for reason, count in stats['reasons'].items():
            print(f"- {reason}: {count}")
        
        # Always include major indices
        indices = ['SPY', 'QQQ', 'IWM', 'DIA']
        valid_tickers.update(indices)
        
        tickers = sorted(list(valid_tickers))
        print(f"\nFinal ticker list ({len(tickers)} total):")
        for t in tickers:
            print(f"- {t}")
            
        return tickers
        
    except Exception as e:
        print(f"\nSupabase error: {str(e)}")
        print(f"Error type: {type(e)}")
        import traceback
        traceback.print_exc()
        # Return default tickers for now
        defaults = ['SPY', 'QQQ', 'IWM', 'DIA']
        print(f"\nUsing default tickers due to error: {defaults}")
        return defaults

def verify_yf_ticker(symbol: str) -> bool:
    """Verify ticker exists in Yahoo Finance"""
    try:
        print(f"Verifying {symbol} with YF...")
        ticker = yf.Ticker(symbol)
        # Just try to get basic history - more reliable than info
        df = ticker.history(period="1d")
        is_valid = not df.empty
        print(f"{'✓' if is_valid else '✗'} {symbol}: {'Valid' if is_valid else 'Invalid'}")
        return is_valid
    except Exception as e:
        print(f"YF error for {symbol}: {str(e)}")
        return False

def write_parquet_batch(
    data: Dict[str, pd.DataFrame],
    frequency: str = '1d',
    s3_config: Dict = None
) -> Dict:
    """Batch write market data to partitioned parquet
    """
    s3_config = s3_config or DEFAULT_S3_CONFIG
    results = {}
    
    fs = s3fs.S3FileSystem(
        endpoint_url=f"https://{s3_config['endpoint']}",
        key=s3_config['access_key'],
        secret=s3_config['secret_key'],
        client_kwargs={
            'region_name': s3_config['region']
        }
    )
    
    for symbol, df in data.items():
        try:
            # Add partition columns
            df['symbol'] = symbol
            df['year'] = pd.to_datetime(df.index).year
            df['month'] = pd.to_datetime(df.index).month
            
            # Write to S3
            base_path = f"{s3_config['bucket']}/market_data/{frequency}"
            
            table = pa.Table.from_pandas(df)
            pq.write_to_dataset(
                table,
                base_path,
                partition_cols=['symbol', 'year', 'month'],
                filesystem=fs
            )
            
            results[symbol] = {
                'success': True,
                'rows': len(df),
                'years': df['year'].nunique(),
                'months': df['month'].nunique()
            }
            
        except Exception as e:
            print(f"Error writing {symbol}: {str(e)}")
            results[symbol] = {
                'success': False,
                'error': str(e)
            }
    
    return results

def validate_companies(client: Client) -> Dict[str, List[str]]:
    """Phase 1: Validate all companies and return categorized tickers"""
    print("\nPhase 1: Validating Companies")
    
    categories = {
        'valid': [],
        'invalid': [],
        'skipped': [],
        'reasons': defaultdict(list)
    }
    
    companies = get_all_companies(client)
    total = len(companies)
    
    print(f"\nValidating {total} companies...")
    for i, record in enumerate(companies, 1):
        if i % 100 == 0:
            print(f"Progress: {i}/{total}")
            
        if ticker := record.get('ticker'):
            # Basic validation checks
            skip_reason = None
            if ' ' in ticker:
                skip_reason = 'contains_space'
            elif 'PRG' in ticker:
                skip_reason = 'preferred_share'
            elif '.' in ticker:
                skip_reason = 'dot_notation'
            elif '-' in ticker:
                skip_reason = 'contains_dash'
            elif len(ticker) > 5:
                skip_reason = 'too_long'
            elif not ticker.replace('-','').isalnum():
                skip_reason = 'invalid_chars'
                
            if skip_reason:
                categories['skipped'].append(ticker)
                categories['reasons'][skip_reason].append(ticker)
                update_company_status(client, ticker, 'skipped', f"Skipped: {skip_reason}")
                continue
                
            # Basic format is valid
            categories['valid'].append(ticker)
    
    print("\n=== Validation Results ===")
    print(f"Total companies: {total}")
    print(f"Valid format: {len(categories['valid'])}")
    print(f"Skipped: {len(categories['skipped'])}")
    print("\nSkip reasons:")
    for reason, tickers in categories['reasons'].items():
        print(f"- {reason}: {len(tickers)}")
    
    return categories

def main(months_lookback: int = 0):
    """
    Main entry point for market data ingestion
    Args:
        months_lookback: Number of months to look back (0 = maximum history)
    """
    print(f"Starting market data update (lookback: {months_lookback} months)...")
    
    def get_start_date(months: int) -> Optional[str]:
        """Calculate start date based on lookback months"""
        if months <= 0:
            return None  # Get all history
        
        start = datetime.now() - timedelta(days=months * 30)
        return start.strftime('%Y-%m-%d')

    def fetch_market_data(client: Client, tickers: List[str]) -> Dict[str, pd.DataFrame]:
        print("\nPhase 2: Fetching Market Data History")
        
        lookback_start = get_start_date(months_lookback)
        if lookback_start:
            print(f"Fetching data from {lookback_start} to present")
        else:
            print("Fetching complete price history")
        
        results = {
            'active': [],
            'delisted': [],
            'error': [],
            'data': {}
        }
        
        total = len(tickers)
        print(f"\nProcessing {total} tickers...")
        
        for i, ticker in enumerate(tickers, 1):
            if i % 10 == 0:
                print(f"Progress: {i}/{total}")
                
            try:
                max_start, years, metadata = get_max_history(ticker)
                
                if max_start:
                    start_date = lookback_start if lookback_start else max_start
                    
                    data = yf.download(
                        ticker,
                        start=start_date,
                        progress=False,
                        actions=True,
                        auto_adjust=True
                    )
                    
                    if not data.empty:
                        results['active'].append(ticker)
                        results['data'][ticker] = data
                        
                        date_range = f"{data.index[0]} to {data.index[-1]}"
                        metadata['date_range'] = date_range
                        
                        note = (
                            f"Active ticker with {len(data)} days of data\n"
                            f"Date range: {date_range}\n"
                            f"Exchange: {metadata['exchange']}\n"
                            f"Type: {metadata['type']}\n"
                            f"Currency: {metadata['currency']}"
                        )
                        
                        update_company_status(
                            client, 
                            ticker, 
                            'active',
                            note,
                            metadata=metadata
                        )
                        
                        print(f"✓ {ticker}: {len(data)} days ({date_range})")
                    else:
                        results['delisted'].append(ticker)
                        update_company_status(
                            client, 
                            ticker, 
                            'delisted',
                            'No price data available'
                        )
                else:
                    results['delisted'].append(ticker)
                    update_company_status(
                        client, 
                        ticker, 
                        'delisted',
                        'Could not determine listing date'
                    )
                    
            except Exception as e:
                results['error'].append(ticker)
                error_msg = f"Error fetching data: {str(e)}"
                update_company_status(client, ticker, 'error', error_msg)
                print(f"✗ Error with {ticker}: {error_msg}")
        
        return results

    client = create_client(
        SUPABASE_CONFIG['url'],
        SUPABASE_CONFIG['service_role_key']
    )
    
    categories = validate_companies(client)
    results = fetch_market_data(client, categories['valid'])
    
    indices = ['SPY', 'QQQ', 'IWM', 'DIA']
    final_tickers = set(results['active']) | set(indices)
    
    return sorted(list(final_tickers))