import wmill
from supabase import create_client
import pandas as pd
import requests
from bs4 import BeautifulSoup
import json
import time
from datetime import datetime
from urllib.parse import urljoin

# Configuration
SEC_BASE_URL = "https://www.sec.gov"
COMPANY_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SUBMISSIONS_URL = "https://data.sec.gov/submissions"
USER_AGENT = "DecisiveAI contact@decisive.ai"

def get_edgar_company_info(ticker: str) -> dict:
    """Get company information from SEC EDGAR"""
    headers = {
        'User-Agent': USER_AGENT,
        'Accept-Encoding': 'gzip, deflate'
    }
    
    try:
        print(f"Fetching SEC data for {ticker}...")
        # First get CIK from ticker
        response = requests.get(COMPANY_TICKERS_URL, headers=headers)
        
        if response.status_code != 200:
            print(f"Error fetching CIK data: {response.status_code}")
            print(f"Response: {response.text[:200]}")
            return None
            
        try:
            companies = response.json()
        except json.JSONDecodeError as e:
            print(f"Error decoding CIK response: {str(e)}")
            print(f"Response text: {response.text[:200]}")
            return None
        
        # Find matching CIK
        cik = None
        for entry in companies.values():
            if str(entry['ticker']).upper() == str(ticker).upper():
                cik = str(entry['cik_str']).zfill(10)
                break
        
        if not cik:
            print(f"No CIK found for {ticker} - may be ADR or foreign listing")
            return {
                'ticker': ticker,
                'sec_registered': False,
                'last_updated': datetime.now().isoformat(),
                'notes': 'No CIK found - possible ADR or foreign listing'
            }
            
        print(f"Found CIK {cik} for {ticker}")
        
        # Get company submissions
        submissions_url = f"{SUBMISSIONS_URL}/CIK{cik}.json"
        response = requests.get(submissions_url, headers=headers)
        
        if response.status_code != 200:
            print(f"Error fetching submission data: {response.status_code}")
            print(f"Response: {response.text[:200]}")
            return None
            
        try:
            data = response.json()
        except json.JSONDecodeError as e:
            print(f"Error decoding submission response: {str(e)}")
            print(f"Response text: {response.text[:200]}")
            return None
        
        company_info = {
            'ticker': ticker,
            'sec_registered': True,
            'cik': cik,
            'sic': data.get('sic'),
            'sic_description': data.get('sicDescription'),
            'website': data.get('website'),
            'ir_website': None,
            'fiscal_year_end': data.get('fiscalYearEnd'),
            'state_of_incorporation': data.get('stateOfIncorporation'),
            'business_address': json.dumps(data.get('addresses', {}).get('business', {})),
            'mailing_address': json.dumps(data.get('addresses', {}).get('mailing', {})),
            'latest_10k': None,
            'latest_10k_date': None,
            'latest_10q': None,
            'latest_10q_date': None,
            'latest_8k': None,
            'latest_8k_date': None,
            'latest_proxy': None,
            'latest_proxy_date': None,
            'filing_count_ytd': 0,
            'filing_count_last_year': 0,
            'last_updated': datetime.now().isoformat(),
            'notes': None
        }
        
        # Process recent filings
        recent_filings = data.get('filings', {}).get('recent', {})
        if recent_filings:
            forms = recent_filings.get('form', [])
            dates = recent_filings.get('filingDate', [])
            accessions = recent_filings.get('accessionNumber', [])
            
            # Count filings
            this_year = datetime.now().year
            company_info['filing_count_ytd'] = sum(1 for d in dates if d.startswith(str(this_year)))
            company_info['filing_count_last_year'] = sum(1 for d in dates if d.startswith(str(this_year-1)))
            
            # Get latest filings by type
            for i, form in enumerate(forms):
                filing_url = f"{SEC_BASE_URL}/Archives/edgar/data/{int(cik)}/{accessions[i].replace('-', '')}"
                
                if form == '10-K' and not company_info['latest_10k']:
                    company_info['latest_10k'] = filing_url
                    company_info['latest_10k_date'] = dates[i]
                elif form == '10-Q' and not company_info['latest_10q']:
                    company_info['latest_10q'] = filing_url
                    company_info['latest_10q_date'] = dates[i]
                elif form == '8-K' and not company_info['latest_8k']:
                    company_info['latest_8k'] = filing_url
                    company_info['latest_8k_date'] = dates[i]
                elif form in ['DEF 14A', 'PRE 14A'] and not company_info['latest_proxy']:
                    company_info['latest_proxy'] = filing_url
                    company_info['latest_proxy_date'] = dates[i]
        
        print(f"Successfully processed {ticker}")
        return company_info
        
    except Exception as e:
        print(f"Error getting EDGAR data for {ticker}: {str(e)}")
        return None

def update_company_data(supabase, company_info: dict) -> None:
    """Update company data in Supabase"""
    try:
        # Update company data
        result = supabase.table('companies').update(company_info).eq('ticker', company_info['ticker']).execute()
        print(f"Updated data for {company_info['ticker']}")
    except Exception as e:
        print(f"Error updating database for {company_info['ticker']}: {str(e)}")

def main(batch_size: int = 5):
    """Process companies and update database"""
    print("Connecting to database...")
    supabase_creds = wmill.get_resource("u/sloane/decisive_supabase")
    supabase = create_client(supabase_creds['url'], supabase_creds['key'])
    
    # Get first N companies
    result = supabase.from_('companies') \
        .select('ticker, security_name') \
        .limit(batch_size) \
        .execute()
    
    companies = pd.DataFrame(result.data)
    print(f"\nProcessing batch of {len(companies)} companies...")
    
    processed_count = 0
    for _, row in companies.iterrows():
        ticker = row['ticker']
        print(f"\nProcessing {ticker} ({row['security_name']})")
        
        try:
            company_info = get_edgar_company_info(ticker)
            if company_info:
                update_company_data(supabase, company_info)
                processed_count += 1
            time.sleep(0.1)  # SEC rate limit compliance
            
        except Exception as e:
            print(f"Error processing {ticker}: {str(e)}")
    
    print(f"\nBatch processing complete. Processed {processed_count} companies.")
    return {"processed_count": processed_count}

if __name__ == "__main__":
    results = main(batch_size=5)