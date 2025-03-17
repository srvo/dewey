import pandas as pd
from pathlib import Path

class SimpleComposite:
    def __init__(self, debug=False):
        """Initialize with specific transactions directory"""
        self.accounts = {}
        self.data_dir = Path('/Users/srvo/lc/performance/data')
        self.debug = debug
        self.load_transactions()
    
    def process_transactions(self, df, account_number=None):
        """Process transactions to calculate current holdings"""
        df['Date'] = pd.to_datetime(df['Date'], format='%m/%d/%Y')
        
        # Filter by account if specified
        if account_number:
            df = df[df['Account'] == account_number]
        
        # Process all transaction types that might affect quantity
        quantity_txns = df[df['Type'].isin([
            'Buy', 'Sell', 
            'Dividend Reinvestment',
            'Split', 'Position',
            'Transfer In', 'Transfer Out'
        ])].copy()
        
        # Skip zero-quantity dividend reinvestments and zero-quantity positions
        quantity_txns = quantity_txns[
            ~((quantity_txns['Type'] == 'Dividend Reinvestment') & (quantity_txns['Quantity'] == 0)) &
            ~((quantity_txns['Type'] == 'Position') & (quantity_txns['Quantity'] == 0))
        ]
        
        quantity_txns = quantity_txns.sort_values('Date')
        
        # Clean quantity column and standardize signs
        quantity_txns['Quantity'] = pd.to_numeric(quantity_txns['Quantity'], errors='coerce').fillna(0)
        quantity_txns.loc[quantity_txns['Type'].isin(['Sell', 'Transfer Out']), 'Quantity'] = \
            -abs(quantity_txns.loc[quantity_txns['Type'].isin(['Sell', 'Transfer Out']), 'Quantity'])
        
        positions = {}
        closed_positions = set()
        
        # Process transactions
        for _, txn in quantity_txns.iterrows():
            symbol = str(txn['Symbol']).strip()
            if not symbol or pd.isna(symbol):
                continue
                
            txn_type = txn['Type']
            quantity = txn['Quantity']
            
            # Handle Position transfers directly, but only non-zero quantities
            if txn_type == 'Position' and quantity != 0:
                positions[symbol] = float(quantity)
                if self.debug:
                    print(f"Debug: {symbol} position set to {quantity} via {txn_type}")
                continue
                
            old_position = positions.get(symbol, 0)
            new_position = old_position + quantity
            
            if new_position < -0.001:
                if symbol in positions:
                    del positions[symbol]
                closed_positions.add(symbol)
                continue
                
            if symbol not in closed_positions:
                positions[symbol] = new_position
        
        # Remove positions with zero or very small quantities
        positions = {k: v for k, v in positions.items() if abs(v) > 0.001}
        
        # Sort positions by symbol
        positions = dict(sorted(positions.items()))
        
        return positions

    def load_transactions(self):
        """Load and process all transaction files"""
        try:
            # Get all CSV files in the data directory
            transaction_files = list(self.data_dir.glob('*.csv'))
            if not transaction_files:
                raise FileNotFoundError(f"No transaction files found in: {self.data_dir}")
            
            # Combine all transaction files
            dfs = []
            for file in transaction_files:
                if self.debug:
                    print(f"Loading transactions from {file.name}")
                df = pd.read_csv(file)
                dfs.append(df)
            
            combined_df = pd.concat(dfs, ignore_index=True)
            
            # First process and show composite view
            composite_positions = self.process_transactions(combined_df)
            print("\nAGGREGATE PORTFOLIO HOLDINGS")
            print("===========================")
            print(f"Total Accounts Found: {len(combined_df['Account'].unique())}")
            print(f"Accounts: {', '.join(sorted(combined_df['Account'].unique().astype(str)))}\n")
            
            print(f"{'Symbol':<8} {'Shares':>12}")
            print("-" * 25)
            for symbol, quantity in composite_positions.items():
                print(f"{symbol:<8} {quantity:>12.3f}")
                
            # Then process individual accounts
            print("\nBREAKDOWN BY ACCOUNT")
            print("===================")
            
            for account in sorted(combined_df['Account'].unique()):
                account_str = str(account)
                print(f"\nProcessing Account {account_str}...")
                
                account_df = combined_df[combined_df['Account'] == account].copy()
                account_positions = self.process_transactions(account_df)
                
                self.accounts[account_str] = {
                    'positions': account_positions
                }
                
                # Print individual account views if they have positions
                if account_positions:
                    print(f"\nAccount {account_str}: ({len(account_positions)} positions)")
                    print(f"{'Symbol':<8} {'Shares':>12}")
                    print("-" * 25)
                    for symbol, quantity in account_positions.items():
                        print(f"{symbol:<8} {quantity:>12.3f}")
                else:
                    print(f"No positions found for Account {account_str}")
                
                print("-" * 40)  # Visual separator between accounts
            
        except Exception as e:
            print(f"Error processing transactions: {str(e)}")
            raise

if __name__ == "__main__":
    print("Loading portfolio data from transactions...")
    composite = SimpleComposite(debug=True)  # Set to True to see individual account holdings
