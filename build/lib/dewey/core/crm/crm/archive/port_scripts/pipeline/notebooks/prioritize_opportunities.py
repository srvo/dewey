import os
import duckdb
import pandas as pd
from typing import Dict
import requests
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class OpportunityPrioritizer:
    def __init__(self):
        self.conn = duckdb.connect('md:port5')
        self.ollama_endpoint = "http://localhost:11434/api/generate"
        self._setup_database()
        
    def _setup_database(self):
        """Create necessary tables if they don't exist."""
        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS opportunity_analysis (
            analysis_id INTEGER PRIMARY KEY,
            analysis_date TIMESTAMP,
            company_name VARCHAR,
            ticker VARCHAR,
            industry VARCHAR,
            last_price DOUBLE,
            tick_rating DOUBLE,
            opportunity_score INTEGER,
            follow_up_questions VARCHAR[],
            market_analysis TEXT
        )
        """)
        
    def load_companies(self, limit: int = 50) -> pd.DataFrame:
        """Load top companies by tick rating from MotherDuck."""
        query = f"""
        SELECT 
            security_name as company_name,
            ticker,
            q4_2024_analysis,
            tick as last_price,
            tick as tick_rating,
            sector as industry
        FROM current_universe
        WHERE q4_2024_analysis IS NOT NULL
            AND tick IS NOT NULL
        ORDER BY tick DESC
        LIMIT {limit}
        """
        return self.conn.execute(query).df()
        
    def analyze_opportunity(self, row: pd.Series) -> Dict:
        """Use ollama to analyze the opportunity and generate insights."""
        prompt = f"""
        You are a financial analyst expert. Analyze the given company's Q4 2024 performance and provide structured insights.
        
        Please analyze this company and provide the following in a structured format:

        1. Opportunity Score (1-10)
        2. Three Follow-up Questions
        3. Market Analysis

        Company Details:
        Company: {row['company_name']}
        Ticker: {row['ticker']}
        Industry: {row['industry']}
        Q4 2024 Analysis: {row['q4_2024_analysis']}
        Current Price: ${row['last_price']}
        Tick Rating: {row['tick_rating']}
        
        Format your response exactly like this:
        Opportunity Score: [number 1-10]
        
        Follow-up Questions:
        Q: [question 1]
        Q: [question 2]
        Q: [question 3]
        
        Market Analysis:
        [your detailed market analysis]
        """
        
        print(f"\nAnalyzing {row['company_name']} ({row['ticker']})...")
        
        data = {
            "model": "llama3-chatqa",
            "prompt": prompt,
            "stream": False
        }
        
        try:
            response = requests.post(
                self.ollama_endpoint,
                json=data
            )
            
            print("\nAPI Response Status:", response.status_code)
            
            if response.status_code == 200:
                result = response.json()
                analysis = result['response']
                print("\nRaw Analysis:", analysis)
                
                # Parse the structured response
                lines = analysis.split('\n')
                # Handle score with or without brackets
                score_line = next((l for l in lines if 'Score:' in l), '')
                try:
                    score_text = score_line.split(':')[1].strip()
                    # Remove any brackets and convert to int
                    score = int(score_text.replace('[', '').replace(']', ''))
                except (IndexError, ValueError):
                    print(f"\nWarning: Could not parse score from '{score_line}', using default")
                    score = 5
                questions = [l.strip() for l in lines if l.strip().startswith('Q:')][:3]
                try:
                    market_analysis = '\n'.join(lines[lines.index('Market Analysis:'):])
                except ValueError:
                    market_analysis = "Market analysis section not found in response"
                
                result = {
                    'opportunity_score': score,
                    'follow_up_questions': questions,
                    'market_analysis': market_analysis
                }
                print("\nStructured Result:", result)
                return result
            else:
                print(f"\nError {response.status_code}:", response.text)
                
        except Exception as e:
            print(f"\nException occurred: {str(e)}")
        return None
        
    def save_results(self, results: list):
        """Save analysis results to MotherDuck."""
        if not results:
            return
            
        # Convert results to DataFrame
        df = pd.DataFrame(results)
        df['analysis_date'] = datetime.now()
        
        # Write to MotherDuck (append new records)
        self.conn.execute("""
        INSERT INTO opportunity_analysis (
            analysis_date,
            company_name,
            ticker,
            industry,
            last_price,
            tick_rating,
            opportunity_score,
            follow_up_questions,
            market_analysis
        )
        SELECT 
            analysis_date,
            company_name,
            ticker,
            industry,
            last_price,
            tick_rating,
            opportunity_score,
            follow_up_questions,
            market_analysis
        FROM df
        """)
        
        print(f"\nSaved {len(results)} new analysis results to database")
        
        # Show latest analysis counts by company
        self.conn.execute("""
        SELECT 
            ticker,
            COUNT(*) as analysis_count,
            MAX(analysis_date) as latest_analysis
        FROM opportunity_analysis
        GROUP BY ticker
        ORDER BY latest_analysis DESC
        LIMIT 5
        """).show()

if __name__ == "__main__":
    prioritizer = OpportunityPrioritizer()
    
    # Load top companies by tick rating
    print("\n=== Loading Top Companies by Tick Rating ===")
    companies = prioritizer.load_companies(limit=50)
    print(f"\nLoaded {len(companies)} companies for analysis")
    
    # Run analysis on each company
    results = []
    for _, company in companies.iterrows():
        analysis = prioritizer.analyze_opportunity(company)
        if analysis:
            results.append({
                'company_name': company['company_name'],
                'ticker': company['ticker'],
                'industry': company['industry'],
                'last_price': company['last_price'],
                'tick_rating': company['tick_rating'],
                'opportunity_score': analysis['opportunity_score'],
                'follow_up_questions': analysis['follow_up_questions'],
                'market_analysis': analysis['market_analysis']
            })
    
    # Save results to database
    prioritizer.save_results(results)
    
    # Display results sorted by opportunity score
    if results:
        results_df = pd.DataFrame(results)
        results_df = results_df.sort_values(['opportunity_score', 'tick_rating'], ascending=[False, False])
        
        print("\n=== Analysis Results (Sorted by Opportunity Score) ===")
        for _, row in results_df.iterrows():
            print(f"\n{row['company_name']} ({row['ticker']}) - Score: {row['opportunity_score']}/10")
            print(f"Tick Rating: {row['tick_rating']}")
            print("\nFollow-up Questions:")
            for i, q in enumerate(row['follow_up_questions'], 1):
                print(f"{i}. {q}")
            print("\nMarket Analysis:")
            print(row['market_analysis'])
            print("\n" + "="*80) 