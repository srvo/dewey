from typing import Dict, List, Optional
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def calculate_macd(
    duck: DuckDBAPI,
    symbol: str,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
    timeframe: str = 'weekly'
) -> pd.DataFrame:
    """Calculate MACD using DuckDB window functions
    """
    query = f"""
    WITH price_data AS (
        SELECT 
            symbol,
            timestamp,
            close,
            CASE 
                WHEN '{timeframe}' = 'weekly' 
                THEN date_trunc('week', timestamp)
                ELSE timestamp 
            END as period
        FROM read_parquet('s3://fort/market_data/1d/*/*/*.parquet')
        WHERE symbol = '{symbol}'
    ),
    weekly_data AS (
        SELECT 
            period,
            last(close) as close
        FROM price_data
        GROUP BY period
        ORDER BY period
    ),
    macd_calc AS (
        SELECT 
            period,
            close,
            exp(sum(ln(close) * (1-alpha)) OVER (
                ORDER BY period ROWS BETWEEN {fast-1} PRECEDING AND CURRENT ROW
            )) as ema_fast,
            exp(sum(ln(close) * (1-alpha)) OVER (
                ORDER BY period ROWS BETWEEN {slow-1} PRECEDING AND CURRENT ROW
            )) as ema_slow
        FROM weekly_data
        CROSS JOIN (SELECT 2.0/({fast}+1) as alpha) params
    )
    SELECT 
        period,
        close,
        ema_fast - ema_slow as macd_line,
        exp(sum(ln(ema_fast - ema_slow) * (1-alpha)) OVER (
            ORDER BY period ROWS BETWEEN {signal-1} PRECEDING AND CURRENT ROW
        )) as signal_line
    FROM macd_calc
    CROSS JOIN (SELECT 2.0/({signal}+1) as alpha) params
    ORDER BY period
    """
    
    return duck.query(query)

def get_sec_events(
    duck: DuckDBAPI,
    symbol: str,
    start_date: str,
    end_date: str
) -> pd.DataFrame:
    """Get SEC filing events and insider transactions
    """
    query = f"""
    WITH filings AS (
        SELECT 
            filing_date as event_date,
            'SEC_FILING' as event_type,
            form_type as event_detail
        FROM read_parquet('s3://fort/sec/filings/*/*/*.parquet')
        WHERE symbol = '{symbol}'
        AND filing_date BETWEEN '{start_date}' AND '{end_date}'
    ),
    insider_trades AS (
        SELECT 
            transaction_date as event_date,
            'INSIDER_TRADE' as event_type,
            concat(
                transaction_type, 
                ' by ', 
                insider_name,
                ' (', 
                cast(shares as varchar),
                ' shares)'
            ) as event_detail
        FROM read_parquet('s3://fort/sec/insider/*/*/*.parquet')
        WHERE symbol = '{symbol}'
        AND transaction_date BETWEEN '{start_date}' AND '{end_date}'
    )
    SELECT * FROM filings
    UNION ALL
    SELECT * FROM insider_trades
    ORDER BY event_date
    """
    
    return duck.query(query)

def analyze_technical_events(
    symbol: str,
    lookback_days: int = 365,
    duck: Optional[DuckDBAPI] = None
) -> Dict:
    """Analyze MACD signals and SEC events
    """
    duck = duck or DuckDBAPI()
    end_date = datetime.now()
    start_date = end_date - timedelta(days=lookback_days)
    
    # Get MACD data
    macd_data = calculate_macd(duck, symbol)
    
    # Get SEC events
    events = get_sec_events(
        duck, 
        symbol, 
        start_date.strftime('%Y-%m-%d'),
        end_date.strftime('%Y-%m-%d')
    )
    
    # Find MACD signals
    macd_data['signal'] = np.where(
        (macd_data['macd_line'] > macd_data['signal_line']) & 
        (macd_data['macd_line'].shift(1) <= macd_data['signal_line'].shift(1)),
        'BULLISH_CROSS',
        np.where(
            (macd_data['macd_line'] < macd_data['signal_line']) & 
            (macd_data['macd_line'].shift(1) >= macd_data['signal_line'].shift(1)),
            'BEARISH_CROSS',
            None
        )
    )
    
    # Combine events with MACD signals
    signals = pd.DataFrame({
        'date': macd_data[macd_data['signal'].notna()]['period'],
        'event_type': 'MACD_SIGNAL',
        'event_detail': macd_data[macd_data['signal'].notna()]['signal']
    })
    
    all_events = pd.concat([events, signals]).sort_values('date')
    
    return {
        'symbol': symbol,
        'period': {
            'start': start_date.strftime('%Y-%m-%d'),
            'end': end_date.strftime('%Y-%m-%d')
        },
        'macd_status': {
            'current_macd': float(macd_data['macd_line'].iloc[-1]),
            'current_signal': float(macd_data['signal_line'].iloc[-1]),
            'histogram': float(macd_data['macd_line'].iloc[-1] - macd_data['signal_line'].iloc[-1]),
            'trend': 'BULLISH' if macd_data['macd_line'].iloc[-1] > macd_data['signal_line'].iloc[-1] else 'BEARISH'
        },
        'events': all_events.to_dict('records'),
        'summary': {
            'total_events': len(all_events),
            'sec_filings': len(events[events['event_type'] == 'SEC_FILING']),
            'insider_trades': len(events[events['event_type'] == 'INSIDER_TRADE']),
            'macd_signals': len(signals)
        }
    } 