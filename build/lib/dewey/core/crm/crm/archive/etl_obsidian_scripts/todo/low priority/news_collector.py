import requests
from bs4 import BeautifulSoup
from typing import Dict, List, Any
from datetime import datetime, timedelta
from collections import defaultdict
import re
import feedparser
from urllib.parse import urlparse
import dateutil.parser
import os
import duckdb
from pathlib import Path

class NewsCollector:
    def __init__(self):
        self.current_date = datetime(2024, 12, 1)  # Simulation date
        self.cutoff_date = self.current_date - timedelta(days=60)
        self.session = requests.Session()
        
        # Try to get DuckDB API config from environment
        self.duckdb_url = os.getenv('DUCKDB_API_URL', 'http://localhost:3000')
        self.duckdb_user = os.getenv('DUCKDB_USER', 'admin')
        self.duckdb_pass = os.getenv('DUCKDB_PASS', 'xK9#mP2$vL5nQ8@jR3')
        
        # Local data paths
        self.data_dir = Path('/Users/srvo/lc/performance/data')
    
    def get_company_news(self, company: Dict) -> List[Dict]:
        """Get news from company IR pages and RSS feeds"""
        news_items = []
        
        # IR page mappings
        ir_urls = {
            'NYCB': 'https://ir.flagstar.com/news-and-events/news-releases/default.aspx',
            'AGM': 'https://www.farmermac.com/news-events/press-releases/',
            'BMI': 'https://investors.badgermeter.com/news/'
        }
        
        # Try IR page
        if company['ticker'] in ir_urls:
            try:
                response = self.session.get(
                    ir_urls[company['ticker']],
                    headers={'User-Agent': 'Mozilla/5.0'},
                    timeout=10
                )
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Common news item selectors
                    for selector in ['.news-item', '.press-release', 'article.release']:
                        items = soup.select(selector)
                        if items:
                            for item in items[:5]:  # Get latest 5
                                date = item.select_one('.date, .news-date')
                                title = item.select_one('.title, .news-headline')
                                if date and title:
                                    news_items.append({
                                        'date': date.text.strip(),
                                        'title': title.text.strip(),
                                        'source': f"{company['ticker']} IR"
                                    })
                            break  # Found items with one selector
            
            except Exception as e:
                print(f"IR page error for {company['ticker']}: {str(e)}")
        
        # Try RSS feeds
        rss_patterns = [
            f"https://ir.{company['ticker'].lower()}.com/rss/news-releases.xml",
            f"https://investors.{company['ticker'].lower()}.com/rss/news.xml"
        ]
        
        for url in rss_patterns:
            try:
                feed = feedparser.parse(url)
                if feed.entries:
                    for entry in feed.entries[:5]:
                        news_items.append({
                            'date': entry.get('published', 'Recent'),
                            'title': entry.title,
                            'source': f"{company['ticker']} RSS"
                        })
                    break  # Found working feed
            except:
                continue
        
        return sorted(
            news_items,
            key=lambda x: dateutil.parser.parse(x['date']) if x['date'] != 'Recent' else self.current_date,
            reverse=True
        )[:10]  # Return 10 most recent items

    def get_historical_data(self, company: Dict) -> Dict[str, Any]:
        """Get historical data from DuckDB API or local files"""
        try:
            # Try API first
            api_url = f"{self.duckdb_url}/query"
            auth = (self.duckdb_user, self.duckdb_pass)
            
            try:
                # Test API connection
                response = requests.get(
                    self.duckdb_url,
                    auth=auth,
                    timeout=5
                )
                if response.status_code == 200:
                    return self._get_data_from_api(company, api_url, auth)
            except:
                print("DuckDB API not available, falling back to local files")
            
            # Fall back to local files
            return self._get_data_from_files(company)
            
        except Exception as e:
            print(f"Data access error for {company['ticker']}: {str(e)}")
            return {'success': False}
            
    def _get_data_from_files(self, company: Dict) -> Dict[str, Any]:
        """Get data from local parquet files"""
        try:
            # Connect to local DuckDB
            con = duckdb.connect(':memory:')
            
            # Price data
            price_query = """
            SELECT 
                date,
                close,
                volume,
                LAG(close, 60) OVER (ORDER BY date) as price_60d_ago
            FROM read_parquet('*.parquet')
            WHERE ticker = ?
            ORDER BY date DESC
            LIMIT 1
            """
            
            prices_path = self.data_dir / 'market' / 'prices'
            price_df = con.execute(price_query, [company['ticker']], prices_path).df()
            
            # Process results
            market_data = {}
            if not price_df.empty:
                row = price_df.iloc[0]
                current_price = row['close']
                price_60d_ago = row['price_60d_ago']
                if price_60d_ago:
                    price_change = ((current_price - price_60d_ago) / price_60d_ago) * 100
                else:
                    price_change = None
                market_data = {
                    'current_price': current_price,
                    'price_change_60d': price_change,
                    'avg_daily_volume': row['volume']
                }
            
            return {
                'market_data': market_data,
                'filings': [],  # Could add local filings data if available
                'news': [],     # Could add local news data if available
                'success': True
            }
            
        except Exception as e:
            print(f"Local data access error for {company['ticker']}: {str(e)}")
            return {'success': False}
            
    def _get_data_from_api(self, company: Dict, api_url: str, auth: tuple) -> Dict[str, Any]:
        """Get data from DuckDB API"""
        # Original API query logic here
        price_query = {
            "query": """
            SELECT 
                date,
                close,
                volume,
                LAG(close, 60) OVER (ORDER BY date) as price_60d_ago
            FROM read_parquet('s3://decisive-market-data/prices/*.parquet')
            WHERE ticker = ?
            ORDER BY date DESC
            LIMIT 1
            """,
            "parameters": [company['ticker']]
        }
        
        price_response = requests.post(
            api_url, 
            json=price_query,
            auth=auth,
            timeout=30
        )
        
        if price_response.status_code != 200:
            raise Exception(f"API returned status {price_response.status_code}: {price_response.text}")
            
        price_data = price_response.json()
        
        # Process results (same as before)
        market_data = {}
        if price_data.get('data'):
            row = price_data['data'][0]
            current_price = row[1]
            price_60d_ago = row[3]
            if price_60d_ago:
                price_change = ((current_price - price_60d_ago) / price_60d_ago) * 100
            else:
                price_change = None
            market_data = {
                'current_price': current_price,
                'price_change_60d': price_change,
                'avg_daily_volume': row[2]
            }
            
        return {
            'market_data': market_data,
            'filings': [],  # Add filings if needed
            'news': [],     # Add news if needed
            'success': True
        }

    def generate_company_report(self, company_info: Dict[str, str], findings: List[Dict], max_words: int = 750) -> str:
        """Generate report with DuckDB API data"""
        
        # Get historical data from DuckDB API
        historical_data = self.get_historical_data(company_info)
        
        # Get IR and other news
        news_items = self.get_company_news(company_info)
        
        report_lines = [
            "## {} Analysis Report".format(company_info['ticker']),
            "*Generated: {}*\n".format(self.current_date.strftime('%B %d, %Y')),
            "### Market Overview"
        ]
        
        # Add market data
        if historical_data.get('success') and historical_data.get('market_data'):
            market_data = historical_data['market_data']
            if market_data.get('current_price'):
                report_lines.extend([
                    "Current Price: ${:.2f}".format(market_data['current_price']),
                    "60-Day Change: {:+.1f}%".format(market_data['price_change_60d']),
                    "Avg Daily Volume: {:,d}\n".format(int(market_data['avg_daily_volume']))
                ])
        
        # Add recent filings
        if historical_data.get('filings'):
            report_lines.append("### Recent SEC Filings")
            for filing in historical_data['filings'][:3]:
                report_lines.append(
                    f"- {filing[0]}: {filing[1]} - {filing[2]}"  # date, form_type, description
                )
            report_lines.append("")
        
        # Add news coverage
        if historical_data.get('news') or news_items:
            report_lines.append("### Recent Coverage")
            
            # Add data lake news
            if historical_data.get('news'):
                report_lines.append("\n#### News Analysis")
                for item in historical_data['news'][:3]:
                    sentiment = "[+]" if item[3] > 0 else "[-]" if item[3] < 0 else "[o]"
                    report_lines.append(
                        f"- {sentiment} {item[0]}: {item[1]} ({item[2]})"  # date, headline, source
                    )
            
            # Add IR and other gathered news
            if news_items:
                report_lines.append("\n#### Company Announcements")
                for item in news_items[:5]:
                    report_lines.append(f"- {item['date']}: {item['title']} ({item['source']})")
        
        return '\n'.join(report_lines)

def main():
    """Main function to process companies and generate reports"""
    collector = NewsCollector()
    
    # Define companies to analyze
    companies = [
        {'ticker': 'NYCB', 'security_name': 'New York Community Bank'},
        {'ticker': 'AGM', 'security_name': 'Federal Agricultural Mortgage Corp'},
        {'ticker': 'BMI', 'security_name': 'Badger Meter Inc'}
    ]
    
    reports = {}
    for company in companies:
        print(f"\nProcessing {company['ticker']}...")
        
        # Get historical data and generate report
        historical_data = collector.get_historical_data(company)
        report = collector.generate_company_report(company, [], max_words=750)
        reports[company['ticker']] = report
        
        # Print report
        print(f"\n{'='*50}")
        print(report)
        print(f"{'='*50}\n")
    
    return reports

if __name__ == "__main__":
    main()
