import pandas as pd
from pathlib import Path
from simple_composite import SimpleComposite

class MonthlyPositions:
    def __init__(self):
        # Input directory
        self.data_dir = Path('/Users/srvo/lc/performance/data')
        self.transactions_file = self.data_dir / 'transactions.csv'
        
        # Output directory
        self.output_dir = Path('/Users/srvo/lc/performance/output')
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.output_file = self.output_dir / 'monthly_positions.csv'
    
    def generate_monthly_snapshots(self):
        """Generate end-of-month position snapshots"""
        # Read transactions
        df = pd.read_csv(self.transactions_file)
        df['Date'] = pd.to_datetime(df['Date'], format='%m/%d/%Y')
        
        # Get unique months in the data
        months = df['Date'].dt.to_period('M').unique()
        
        # Store results
        snapshots = []
        
        # For each month-end, calculate positions
        for month in months:
            month_end = month.to_timestamp('M')  # Last day of month
            month_transactions = df[df['Date'] <= month_end].copy()
            
            # Calculate positions using SimpleComposite logic
            calculator = SimpleComposite(debug=False)
            calculator.transactions_file = Path('dummy')  # Bypass file loading
            positions = calculator.process_transactions(month_transactions)
            
            # Add each position to results
            for symbol, shares in positions.items():
                snapshots.append({
                    'Date': month_end.strftime('%Y-%m-%d'),
                    'Symbol': symbol,
                    'Shares': shares
                })
        
        # Convert to DataFrame and save
        results_df = pd.DataFrame(snapshots)
        results_df = results_df.sort_values(['Date', 'Symbol'])
        results_df.to_csv(self.output_file, index=False)
        
        print(f"\nMonthly position snapshots saved to {self.output_file}")
        
        # Display most recent month
        latest_date = results_df['Date'].max()
        print(f"\nLatest positions ({latest_date}):\n")
        latest = results_df[results_df['Date'] == latest_date]
        print(latest.to_string(index=False))
        
        return results_df

if __name__ == "__main__":
    print("Generating monthly position snapshots...")
    monthly = MonthlyPositions()
    snapshots = monthly.generate_monthly_snapshots()
