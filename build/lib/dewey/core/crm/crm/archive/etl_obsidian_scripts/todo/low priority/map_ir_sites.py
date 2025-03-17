import wmill
from supabase import create_client
import pandas as pd
from edgar import *
import time
from bs4 import BeautifulSoup
import requests
from urllib.parse import urljoin

def get_company_info(ticker: str) -> dict:
    """Get company information from EDGAR and extract IR website"""
    try:
        # Initialize company
        company = Company(ticker)
        
        # Get latest 10-K for best IR website info
        latest_10k = company.latest("10-K")
        if latest_10k:
            tenk = latest_10k.obj()
            
            # Try to extract IR website from business section
            business = tenk.business if hasattr(tenk, 'business') else ''
            if business:
                soup = BeautifulSoup(business, 'html.parser')
                text = soup.get_text().lower()
                
                # Common IR website patterns
                ir_indicators = [
                    'investor relations website',
                    'investor website',
                    'company\'s website',
                    'corporate website',
                    'investor information'
                ]
                
                for indicator in ir_indicators:
                    if indicator in text:
                        # Extract URL near the indicator
                        idx = text.find(indicator)
                        surrounding = text[max(0, idx-100):idx+100]
                        urls = [word for word in surrounding.split() 
                               if 'http' in word or 'www.' in word]
                        if urls:
                            return {
                                'ticker': ticker,
                                'name': company.name,
                                'cik': company.cik,
                                'ir_website': urls[0].strip('.,()<>'),
                                'source': '10-K',
                                'filing_date': latest_10k.date
                            }
        
        # Fallback: Try company facts
        facts = company.get_facts()
        if facts:
            company_info = {
                'ticker': ticker,
                'name': company.name,
                'cik': company.cik,
                'ir_website': None,
                'source': 'EDGAR',
                'filing_date': None
            }
            return company_info
            
    except Exception as e:
        print(f"Error processing {ticker}: {str(e)}")
    
    return None

def main(limit: int = 10):
    """Map IR sites for companies in our database"""
    print("Fetching companies from database...")
    supabase_creds = wmill.get_resource("u/sloane/decisive_supabase")
    supabase = create_client(supabase_creds['url'], supabase_creds['key'])
    
    # Set EDGAR identity
    set_identity("YourName your.email@domain.com")
    
    result = supabase.from_('companies').select('*').limit(limit).execute()
    df = pd.DataFrame(result.data)
    print(f"\nTesting with {len(df)} companies")
    
    results = []
    for idx, row in df.iterrows():
        print(f"\nProcessing {idx+1}/{len(df)}: {row['ticker']} - {row['security_name']}")
        
        try:
            company_info = get_company_info(row['ticker'])
            if company_info:
                results.append(company_info)
                print(f"Results for {row['ticker']}: {company_info}")
            else:
                results.append({
                    'ticker': row['ticker'],
                    'name': row['security_name'],
                    'ir_website': None,
                    'source': None,
                    'filing_date': None
                })
            
        except Exception as e:
            print(f"Error processing {row['ticker']}: {str(e)}")
            results.append({
                'ticker': row['ticker'],
                'name': row['security_name'],
                'ir_website': None,
                'source': None,
                'filing_date': None
            })
        
        time.sleep(0.1)  # SEC rate limit compliance
    
    results_df = pd.DataFrame(results)
    print("\nFinal Results:")
    print(f"Total companies processed: {len(results_df)}")
    print(f"IR sites found: {results_df['ir_website'].notna().sum()}")
    
    return results_df

if __name__ == "__main__":
    results = main(limit=10)