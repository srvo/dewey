"""
DuckDB Loader for Research Workflows
==================================

Handles loading company data and research results from DuckDB for analysis workflows.
"""

from typing import List, Dict, Any, Optional, Generator
import duckdb
from pathlib import Path
import os
from dataclasses import dataclass
from datetime import datetime

# Default database paths - using workspace root
WORKSPACE_ROOT = Path(os.getenv('WORKSPACE_ROOT', '/Users/srvo/ethifinx'))
DEFAULT_DB_PATH = WORKSPACE_ROOT / "data" / "research.duckdb"

@dataclass
class CompanyData:
    """Container for company data loaded from DuckDB."""
    ticker: str
    name: str
    current_tick: int
    tick_history: List[Dict[str, Any]]
    research_results: Optional[Dict[str, Any]]
    context: Optional[str]
    meta: Dict[str, Any]

class DuckDBLoader:
    """Loads company data from DuckDB for research workflows."""
    
    def __init__(self, db_path: Optional[str] = None):
        """Initialize the loader.
        
        Args:
            db_path: Optional path to DuckDB database. Defaults to workspace default.
        """
        self.db_path = db_path or str(DEFAULT_DB_PATH)
    
    def _get_connection(self) -> duckdb.DuckDBPyConnection:
        """Get a DuckDB connection.
        
        Returns:
            DuckDB connection object
        """
        return duckdb.connect(self.db_path)
    
    def load_companies_by_tick_range(
        self,
        min_tick: int,
        max_tick: int,
        limit: Optional[int] = None
    ) -> Generator[CompanyData, None, None]:
        """Load companies within a specified tick range.
        
        Args:
            min_tick: Minimum tick value (inclusive)
            max_tick: Maximum tick value (inclusive)
            limit: Optional limit on number of companies to return
        
        Yields:
            CompanyData objects for each matching company
        """
        with self._get_connection() as conn:
            # Get latest tick values for each company
            latest_ticks_query = """
            WITH latest_ticks AS (
                SELECT 
                    ticker,
                    new_tick as current_tick,
                    date as last_updated
                FROM tick_history th1
                WHERE date = (
                    SELECT MAX(date)
                    FROM tick_history th2
                    WHERE th2.ticker = th1.ticker
                )
            )
            SELECT 
                lt.ticker,
                lt.current_tick,
                lt.last_updated,
                u.name,
                u.sector,
                u.industry,
                u.description
            FROM latest_ticks lt
            JOIN universe u ON lt.ticker = u.ticker
            WHERE lt.current_tick BETWEEN ? AND ?
            """
            
            if limit:
                latest_ticks_query += f" LIMIT {limit}"
            
            companies = conn.execute(latest_ticks_query, [min_tick, max_tick]).fetchall()
            
            for company in companies:
                ticker = company[0]
                
                # Get tick history
                tick_history = conn.execute("""
                    SELECT 
                        date,
                        old_tick,
                        new_tick,
                        note,
                        updated_by
                    FROM tick_history
                    WHERE ticker = ?
                    ORDER BY date DESC
                """, [ticker]).fetchall()
                
                # Get latest research results
                research_results = conn.execute("""
                    SELECT 
                        summary,
                        risk_score,
                        confidence_score,
                        recommendation,
                        structured_data,
                        source_categories,
                        meta_info,
                        last_updated_at
                    FROM research_results
                    WHERE company_ticker = ?
                    ORDER BY last_updated_at DESC
                    LIMIT 1
                """, [ticker]).fetchone()
                
                # Get company context
                context = conn.execute("""
                    SELECT context
                    FROM company_context
                    WHERE ticker = ?
                    ORDER BY created_at DESC
                    LIMIT 1
                """, [ticker]).fetchone()
                
                yield CompanyData(
                    ticker=ticker,
                    name=company[3],
                    current_tick=company[1],
                    tick_history=[{
                        'date': th[0],
                        'old_tick': th[1],
                        'new_tick': th[2],
                        'note': th[3],
                        'updated_by': th[4]
                    } for th in tick_history],
                    research_results={
                        'summary': research_results[0],
                        'risk_score': research_results[1],
                        'confidence_score': research_results[2],
                        'recommendation': research_results[3],
                        'structured_data': research_results[4],
                        'source_categories': research_results[5],
                        'meta_info': research_results[6],
                        'last_updated_at': research_results[7]
                    } if research_results else None,
                    context=context[0] if context else None,
                    meta={
                        'sector': company[4],
                        'industry': company[5],
                        'description': company[6],
                        'last_tick_update': company[2]
                    }
                )
    
    def load_companies_by_tickers(
        self,
        tickers: List[str]
    ) -> Generator[CompanyData, None, None]:
        """Load specific companies by their tickers.
        
        Args:
            tickers: List of company tickers to load
        
        Yields:
            CompanyData objects for each ticker
        """
        placeholders = ','.join(['?' for _ in tickers])
        
        with self._get_connection() as conn:
            # Get latest tick values for specified companies
            latest_ticks_query = f"""
            WITH latest_ticks AS (
                SELECT 
                    ticker,
                    new_tick as current_tick,
                    date as last_updated
                FROM tick_history th1
                WHERE date = (
                    SELECT MAX(date)
                    FROM tick_history th2
                    WHERE th2.ticker = th1.ticker
                )
                AND ticker IN ({placeholders})
            )
            SELECT 
                lt.ticker,
                lt.current_tick,
                lt.last_updated,
                u.name,
                u.sector,
                u.industry,
                u.description
            FROM latest_ticks lt
            JOIN universe u ON lt.ticker = u.ticker
            """
            
            companies = conn.execute(latest_ticks_query, tickers).fetchall()
            
            for company in companies:
                ticker = company[0]
                
                # Get tick history
                tick_history = conn.execute("""
                    SELECT 
                        date,
                        old_tick,
                        new_tick,
                        note,
                        updated_by
                    FROM tick_history
                    WHERE ticker = ?
                    ORDER BY date DESC
                """, [ticker]).fetchall()
                
                # Get latest research results
                research_results = conn.execute("""
                    SELECT 
                        summary,
                        risk_score,
                        confidence_score,
                        recommendation,
                        structured_data,
                        source_categories,
                        meta_info,
                        last_updated_at
                    FROM research_results
                    WHERE company_ticker = ?
                    ORDER BY last_updated_at DESC
                    LIMIT 1
                """, [ticker]).fetchone()
                
                # Get company context
                context = conn.execute("""
                    SELECT context
                    FROM company_context
                    WHERE ticker = ?
                    ORDER BY created_at DESC
                    LIMIT 1
                """, [ticker]).fetchone()
                
                yield CompanyData(
                    ticker=ticker,
                    name=company[3],
                    current_tick=company[1],
                    tick_history=[{
                        'date': th[0],
                        'old_tick': th[1],
                        'new_tick': th[2],
                        'note': th[3],
                        'updated_by': th[4]
                    } for th in tick_history],
                    research_results={
                        'summary': research_results[0],
                        'risk_score': research_results[1],
                        'confidence_score': research_results[2],
                        'recommendation': research_results[3],
                        'structured_data': research_results[4],
                        'source_categories': research_results[5],
                        'meta_info': research_results[6],
                        'last_updated_at': research_results[7]
                    } if research_results else None,
                    context=context[0] if context else None,
                    meta={
                        'sector': company[4],
                        'industry': company[5],
                        'description': company[6],
                        'last_tick_update': company[2]
                    }
                )
    
    def save_research_results(
        self,
        ticker: str,
        results: Dict[str, Any]
    ) -> None:
        """Save research results back to DuckDB.
        
        Args:
            ticker: Company ticker
            results: Research results to save
        """
        with self._get_connection() as conn:
            # Check if results exist for this company
            existing = conn.execute("""
                SELECT id FROM research_results
                WHERE company_ticker = ?
            """, [ticker]).fetchone()
            
            if existing:
                # Update existing results
                conn.execute("""
                    UPDATE research_results
                    SET 
                        summary = ?,
                        risk_score = ?,
                        confidence_score = ?,
                        recommendation = ?,
                        structured_data = ?,
                        source_categories = ?,
                        meta_info = ?,
                        last_updated_at = CURRENT_TIMESTAMP
                    WHERE company_ticker = ?
                """, [
                    results.get('summary'),
                    results.get('risk_score'),
                    results.get('confidence_score'),
                    results.get('recommendation'),
                    results.get('structured_data'),
                    results.get('source_categories'),
                    results.get('meta_info'),
                    ticker
                ])
            else:
                # Insert new results
                conn.execute("""
                    INSERT INTO research_results (
                        company_ticker,
                        summary,
                        risk_score,
                        confidence_score,
                        recommendation,
                        structured_data,
                        source_categories,
                        meta_info,
                        first_analyzed_at,
                        last_updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """, [
                    ticker,
                    results.get('summary'),
                    results.get('risk_score'),
                    results.get('confidence_score'),
                    results.get('recommendation'),
                    results.get('structured_data'),
                    results.get('source_categories'),
                    results.get('meta_info')
                ]) 