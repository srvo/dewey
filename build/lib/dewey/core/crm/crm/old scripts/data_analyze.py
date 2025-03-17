import duckdb
import pandas as pd
from pathlib import Path
import requests
import json
import glob
import os
from datetime import datetime

class SchemaAnalyzer:
    def __init__(self, data_dir="/Users/srvo/lc/data"):
        self.data_dir = Path(data_dir)
        self.conn = duckdb.connect(":memory:")

    def analyze_duckdb(self, file_path):
        """Analyze schema of a DuckDB file"""
        try:
            # Connect to the DuckDB file
            db = duckdb.connect(str(file_path))
            # Get list of tables
            tables = db.execute("SHOW TABLES").fetchall()
            
            schemas = {}
            for table in tables:
                table_name = table[0]
                # Get schema for each table
                schema = db.execute(f"DESCRIBE {table_name}").fetchall()
                schemas[table_name] = schema
                
                # Get sample data
                sample = db.execute(f"SELECT * FROM {table_name} LIMIT 5").fetchall()
                print(f"\nTable: {table_name}")
                print("Schema:", schema)
                print("Sample:", sample)
            
            return schemas
        except Exception as e:
            print(f"Error analyzing {file_path}: {str(e)}")
            return None

    def analyze_csv(self, file_path):
        """Analyze schema of a CSV file"""
        try:
            df = pd.read_csv(file_path)
            print(f"\nCSV File: {file_path}")
            print("Columns:", df.columns.tolist())
            print("Sample:\n", df.head())
            return df.dtypes
        except Exception as e:
            print(f"Error analyzing {file_path}: {str(e)}")
            return None

    def analyze_all(self):
        """Analyze all files in the directory"""
        for file in self.data_dir.glob("*"):
            print(f"\nAnalyzing {file.name}")
            if file.suffix == '.duckdb':
                self.analyze_duckdb(file)
            elif file.suffix == '.csv':
                self.analyze_csv(file)
            elif file.suffix == '.db':
                print("SQLite file - need different handling")

class DirectusSchema:
    def __init__(self, url, token):
        self.base_url = url.rstrip('/')
        self.session = requests.Session()
        
        # Debug token
        print(f"\nInitializing with token: {token[:5]}...{token[-5:]}")
        
        self.session.headers.update({
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        })
        
        # Verify token works
        test_response = self.session.get(f"{self.base_url}/users/me")
        print(f"Auth test response: {test_response.status_code}")
        print(f"Auth test body: {test_response.text}")

    def verify_auth(self):
        """Verify authentication and permissions"""
        response = self.session.get(f"{self.base_url}/users/me")
        if response.status_code != 200:
            print(f"Auth check failed: {response.text}")
            return False
        
        try:
            user_info = response.json()
            print(f"Authenticated with static token")
            print(f"\nFull response:")
            print(json.dumps(user_info, indent=2))
            return True
        except Exception as e:
            print(f"Error parsing auth response: {str(e)}")
            print(f"Raw response: {response.text}")
            return False

    def create_collection(self, name, fields):
        """Create a collection with specified fields"""
        url = f"{self.base_url}/collections"
        
        # Debug request info
        print(f"\nCreating collection {name}")
        print(f"URL: {url}")
        print(f"Headers: {self.session.headers}")
        
        payload = {
            "collection": name,
            "fields": fields,
            "meta": {
                "icon": "box",
                "note": f"Auto-generated {name} collection"
            }
        }
        
        print(f"Payload: {json.dumps(payload, indent=2)}")
        
        response = self.session.post(url, json=payload)
        print(f"Response status: {response.status_code}")
        print(f"Response body: {response.text}")
        
        if response.status_code != 200:
            raise Exception(f"Failed to create collection {name}: {response.text}")
        
        return response.json()

    def create_schema(self):
        """Create the database schema if needed, then import data"""
        try:
            # Get admin role info
            me = self.session.get(f"{self.base_url}/users/me").json()['data']
            role_id = me['role']
            
            print(f"\nSetting up clients collection for role: {role_id}")
            
            # First make sure role has admin access
            role_update = {
                "admin_access": True,
                "app_access": True
            }
            
            role_response = self.session.patch(
                f"{self.base_url}/roles/{role_id}",
                json=role_update
            )
            print(f"Updated role permissions: {role_response.status_code}")
            
            # Create just the clients collection first
            collections = self.session.get(f"{self.base_url}/collections").json()
            existing = [c['collection'] for c in collections.get('data', [])]
            
            if 'clients' not in existing:
                print("Creating clients collection...")
                client_response = self.create_collection("clients", clients_fields)
                print(f"Create collection response: {client_response.status_code}")
                if client_response.status_code != 200:
                    print(f"Collection response: {client_response.text}")
            
            # Set permissions according to Directus docs
            permission = {
                "role": role_id,
                "collection": "clients",
                "action": "create",
                "policy": "full",
                "validation": None,
                "presets": None,
                "fields": ["*"]
            }
            
            # Try each permission type
            for action in ['create', 'read', 'update', 'delete']:
                perm = permission.copy()
                perm['action'] = action
                perm_response = self.session.post(
                    f"{self.base_url}/permissions",
                    json=perm
                )
                print(f"Setting clients {action} permission: {perm_response.status_code}")
                if perm_response.status_code != 200:
                    print(f"Permission response: {perm_response.text}")
            
            print("\nImporting clients from households file...")
            households_df = pd.read_csv("/Users/srvo/lc/data/households/Households - 20241130.csv")
            
            for _, row in households_df.iterrows():
                # Parse the Name column which is in format "Last, First" or "Last-Additional, First"
                name_parts = row['Name'].split(',', 1)
                if len(name_parts) == 2:
                    last_name = name_parts[0].strip()
                    first_name = name_parts[1].strip()
                    if '-' in last_name:  # Handle hyphenated names
                        last_name = last_name.split('-')[0].strip()
                else:
                    # Handle single name or unexpected format
                    first_name = row['Name']
                    last_name = ''
                
                client = {
                    "first_name": first_name,
                    "last_name": last_name,
                    "status": "active",
                    "balance": float(row['Balance'].replace('$', '').replace(',', '')),
                    "accounts": int(row['# of Accounts']),
                    "cash_allocation": float(row['Cash'].rstrip('%')) / 100
                }
                
                create_response = self.session.post(
                    f"{self.base_url}/items/clients",
                    json=client
                )
                print(f"Creating client {first_name} {last_name}: {create_response.status_code}")
                if create_response.status_code != 200:
                    print(f"Create response: {create_response.text}")
            
            print("\nClient import complete!")
            
        except Exception as e:
            print(f"Error setting up schema: {str(e)}")
            if hasattr(e, 'response'):
                print(f"Response: {e.response.text}")

    def import_data(self):
        """Import data from CSVs into Directus collections"""
        print("\nImporting data...")
        
        # Import holdings (required)
        holdings_files = glob.glob('/Users/srvo/lc/data/*Holdings*.csv')
        if not holdings_files:
            print("No holdings files found!")
            return
        
        for file in holdings_files:
            print(f"\nProcessing holdings file: {file}")
            try:
                df = pd.read_csv(file)
                
                # Extract client name from filename
                client_name = os.path.basename(file).split(' - ')[0]
                first_name, last_name = client_name.split(', ')
                
                # Create client record first
                client_data = {
                    "first_name": first_name,
                    "last_name": last_name,
                    "status": "active"
                }
                
                # Check if client exists
                client_response = self.session.get(
                    f"{self.base_url}/items/clients",
                    params={
                        "filter": {
                            "_and": [
                                {"first_name": {"_eq": first_name}},
                                {"last_name": {"_eq": last_name}}
                            ]
                        }
                    }
                )
                
                if client_response.status_code == 200 and client_response.json()['data']:
                    client_id = client_response.json()['data'][0]['id']
                    print(f"Found existing client: {client_name} ({client_id})")
                else:
                    create_response = self.session.post(
                        f"{self.base_url}/items/clients",
                        json=client_data
                    )
                    if create_response.status_code != 200:
                        print(f"Failed to create client {client_name}: {create_response.text}")
                        continue
                        
                    client_id = create_response.json()['data']['id']
                    print(f"Created client: {client_name} ({client_id})")
                
                # Process holdings
                for _, row in df.iterrows():
                    holding_data = {
                        "client_id": client_id,
                        "ticker": row['Ticker'],
                        "description": row['Description'],
                        "account": row['Account'],
                        "portfolio_target": float(str(row['Portfolio Target']).strip('%') or 0),
                        "effective_target": float(str(row['Effective Target']).strip('%') or 0),
                        "quantity": float(str(row['Quantity']).replace(',', '')),
                        "price": float(str(row['Price']).strip('$').replace(',', '')),
                        "amount": float(str(row['Amount']).strip('$').replace(',', '')),
                        "date": datetime.now().isoformat()
                    }
                    
                    holdings_response = self.session.post(
                        f"{self.base_url}/items/holdings",
                        json=holding_data
                    )
                    if holdings_response.status_code != 200:
                        print(f"Failed to create holding {row['Ticker']}: {holdings_response.text}")
                    else:
                        print(f"Created holding: {row['Ticker']}")
                    
            except Exception as e:
                print(f"Error processing {file}: {str(e)}")

# Run the analysis
analyzer = SchemaAnalyzer()
analyzer.analyze_all()

# Usage with static token
schema = DirectusSchema(
    url="http://directus-hs8ks4kwkk48gkw8sws4o4w0.5.78.111.69.sslip.io",
    token="GOp9bVYMC1sM1kXkJWzw2zs5tooUKIGi"
)

schema.create_schema()