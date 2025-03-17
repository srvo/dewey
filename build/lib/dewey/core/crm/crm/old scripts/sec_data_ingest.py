#!pip requests boto3 beautifulsoup4 pandas
from typing import Optional, Dict, List
import requests
from bs4 import BeautifulSoup
import json
import time
from datetime import datetime
import zipfile
import pandas as pd
from io import BytesIO, StringIO
import boto3
from botocore.config import Config

def get_partition_info(filename: str, dataset_type: str) -> Dict:
    """Extract partition information from filename
    """
    try:
        if dataset_type == "mutual_fund":
            # Format: 2024q3_rr1.zip
            year = filename[0:4]
            quarter = filename[5:6]
            return {
                'partition': f"{year}/Q{quarter}",
                'year': year,
                'quarter': quarter
            }
        elif dataset_type == "fails_deliver":
            # Format: cnsfails202411a.zip
            year = filename[8:12]
            month = filename[12:14]
            half = "1" if filename.endswith("a.zip") else "2"
            return {
                'partition': f"{year}/{month}/{half}",
                'year': year,
                'month': month,
                'half': half
            }
        else:
            return {'partition': 'unknown'}
    except Exception as e:
        print(f"Error parsing partition from {filename}: {e}")
        return {'partition': 'error'}

def parse_mutual_fund(content: Dict[str, bytes]) -> Dict:
    """Parse mutual fund data files and extract key information
    """
    results = {
        'tickers': set(),
        'fund_count': 0,
        'summary': {}
    }
    
    # Parse submission file for fund info
    if 'sub.tsv' in content:
        df = pd.read_csv(BytesIO(content['sub.tsv']), sep='\t', low_memory=False)
        results['fund_count'] = len(df)
        
        # Get date columns (might be different names)
        date_cols = [col for col in df.columns if 'date' in col.lower() or 'period' in col.lower()]
        if date_cols:
            results['summary']['submissions'] = {
                'total_funds': len(df),
                'date_columns': date_cols,
                'date_ranges': {
                    col: {
                        'min': df[col].min(),
                        'max': df[col].max()
                    } for col in date_cols
                }
            }
    
    # Parse numeric data
    if 'num.tsv' in content:
        df = pd.read_csv(BytesIO(content['num.tsv']), sep='\t', low_memory=False)
        results['summary']['numeric_data'] = {
            'total_entries': len(df),
            'metric_types': df['tag'].nunique() if 'tag' in df.columns else 0,
            'columns': list(df.columns)
        }
    
    return results

def parse_fails_deliver(content: bytes) -> Dict:
    """Parse fails-to-deliver data and extract ticker information
    """
    # Read with proper data types and handle missing/bad values
    df = pd.read_csv(BytesIO(content), sep='|', dtype={
        'SETTLEMENT DATE': str,
        'CUSIP': str,
        'SYMBOL': str,
        'QUANTITY (FAILS)': str,  # Read as string first
        'PRICE': str  # Read as string first
    })
    
    # Clean and convert numeric columns
    df['QUANTITY (FAILS)'] = pd.to_numeric(df['QUANTITY (FAILS)'].str.replace('.', ''), errors='coerce')
    df['PRICE'] = pd.to_numeric(df['PRICE'], errors='coerce')
    
    # Fill NaN values with 0 for calculations
    df['QUANTITY (FAILS)'] = df['QUANTITY (FAILS)'].fillna(0)
    df['PRICE'] = df['PRICE'].fillna(0)
    
    results = {
        'tickers': list(df['SYMBOL'].dropna().unique()),
        'summary': {
            'total_records': len(df),
            'unique_symbols': df['SYMBOL'].nunique(),
            'date_range': {
                'start': df['SETTLEMENT DATE'].min(),
                'end': df['SETTLEMENT DATE'].max()
            },
            'total_fails': df['QUANTITY (FAILS)'].sum(),
            'total_value': (df['PRICE'] * df['QUANTITY (FAILS)']).sum()
        }
    }
    
    # Get top fails by value
    df['total_value'] = df['PRICE'] * df['QUANTITY (FAILS)']
    top_fails = df.groupby('SYMBOL', as_index=False).agg({
        'QUANTITY (FAILS)': 'sum',
        'PRICE': 'mean',
        'total_value': 'sum'
    })
    top_fails = top_fails.sort_values('total_value', ascending=False)
    
    results['top_fails'] = top_fails.head(10).to_dict('records')
    
    return results

def process_dataset(
    content: bytes,
    dataset_type: str,
    filename: str
) -> Dict:
    """Process dataset content based on type
    """
    try:
        if dataset_type == "mutual_fund":
            # Extract all files from zip
            with zipfile.ZipFile(BytesIO(content)) as zf:
                print(f"Found files in zip: {zf.namelist()}")
                files = {
                    name: zf.read(name)
                    for name in zf.namelist()
                    if name.endswith('.tsv')
                }
                return parse_mutual_fund(files)
        
        elif dataset_type == "fails_deliver":
            # Single CSV file in zip
            with zipfile.ZipFile(BytesIO(content)) as zf:
                first_file = zf.namelist()[0]
                print(f"Processing fails-to-deliver file: {first_file}")
                return parse_fails_deliver(zf.read(first_file))
        
        return {"error": "Unsupported dataset type"}
        
    except Exception as e:
        print(f"Error processing {dataset_type}: {str(e)}")
        return {
            "error": str(e),
            "dataset_type": dataset_type,
            "filename": filename
        }

def save_to_s3(
    s3_client,
    bucket: str,
    content: bytes,
    parsed_data: Dict,
    dataset_info: Dict
) -> Dict:
    """Save raw and processed data with proper partitioning
    """
    timestamp = datetime.now()
    dataset_type = dataset_info['category']
    filename = dataset_info['sample_file']['filename']
    
    # Get partition information
    partition_info = get_partition_info(filename, dataset_type)
    partition = partition_info['partition']
    
    # Save raw data
    raw_key = f"sec/{dataset_type}/raw/{partition}/{filename}"
    s3_client.put_object(
        Bucket=bucket,
        Key=raw_key,
        Body=content,
        ContentType='application/zip',
        Metadata={
            'source_url': dataset_info['url'],
            'description': dataset_info['description'],
            'frequency': dataset_info['frequency'],
            'processed_at': timestamp.isoformat(),
            **partition_info  # Include partition info in metadata
        }
    )
    
    # Save parsed data
    parsed_key = f"sec/{dataset_type}/processed/{partition}/data.json"
    s3_client.put_object(
        Bucket=bucket,
        Key=parsed_key,
        Body=json.dumps(parsed_data, default=str),
        ContentType='application/json'
    )
    
    # Update latest metadata
    metadata_key = f"sec/metadata/{dataset_type}/latest.json"
    metadata = {
        'last_update': timestamp.isoformat(),
        'latest_file': raw_key,
        'latest_data': parsed_key,
        'dataset_info': dataset_info,
        'partition_info': partition_info,
        'summary': parsed_data.get('summary', {})
    }
    s3_client.put_object(
        Bucket=bucket,
        Key=metadata_key,
        Body=json.dumps(metadata, default=str),
        ContentType='application/json'
    )
    
    return {
        'raw_key': raw_key,
        'parsed_key': parsed_key,
        'metadata_key': metadata_key,
        'partition_info': partition_info
    }

def get_all_available_files(dataset_type: str) -> List[Dict]:
    """Get ALL available files for a dataset
    """
    base_urls = {
        "mutual_fund": "https://www.sec.gov/data-research/sec-markets-data/mutual-fund-prospectus-riskreturn-summary-data-sets",
        "fails_deliver": "https://www.sec.gov/data-research/sec-markets-data/fails-deliver-data",
        "edgar_logs": "https://www.sec.gov/data-research/sec-markets-data/edgar-log-file-data-sets",
        "insider_trades": "https://www.sec.gov/data-research/sec-markets-data/insider-transactions-data-sets",
        "financial_notes": "https://www.sec.gov/data-research/financial-statement-notes-data-sets",
        "closed_end": "https://www.sec.gov/about/opendatasetsshtmlclosed-end-investment_company",
        "investment_company": "https://www.sec.gov/about/opendatasetsshtmlinvestment_company"
    }

    headers = {
        'User-Agent': 'sloan@ethicic.com'
    }

    url = base_urls[dataset_type]
    print(f"Scraping directory: {url}")
    
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    
    soup = BeautifulSoup(response.text, 'html.parser')
    files = []
    
    # Find all links that look like data files
    for link in soup.find_all('a'):
        href = link.get('href', '')
        if href.endswith('.zip'):
            files.append({
                'url': href if href.startswith('http') else f"https://www.sec.gov{href}",
                'filename': href.split('/')[-1],
                'text': link.text.strip(),
                'parent_text': link.parent.text.strip() if link.parent else None
            })
    
    return files

def main(
    s3_config: Optional[Dict] = None,
    max_workers: int = 3,
    sleep_time: float = 0.3,
    datasets: Optional[List[str]] = None
) -> Dict:
    """Download ALL available SEC datasets
    
    Args:
        s3_config: S3 configuration
        max_workers: Maximum concurrent downloads
        sleep_time: Time to sleep between requests (be nice to SEC)
        datasets: Optional list of specific datasets to download
    """
    if not s3_config:
        s3_config = {
            "endPoint": "fort.fsn1.your-objectstorage.com",
            "bucket": "fort",
            "region": "eu-central-1",
            "accessKey": "8WV9AU74GN9WVS5TD88Z",
            "secretKey": "S03DI67F75gJVECAUuHKDwRBErdEidPKWYf5YjWl"
        }
    
    # Use all datasets if none specified
    if not datasets:
        datasets = [
            "mutual_fund",
            "fails_deliver",
            "edgar_logs",
            "insider_trades",
            "financial_notes",
            "closed_end",
            "investment_company"
        ]
    
    results = {}
    total_files = 0
    processed_files = 0
    
    # Process each dataset
    for dataset_type in datasets:
        try:
            print(f"\nProcessing {dataset_type}...")
            
            # Get all available files
            available_files = get_all_available_files(dataset_type)
            total_files += len(available_files)
            
            dataset_results = []
            
            # Process each file
            for file_info in available_files:
                try:
                    print(f"Downloading {file_info['filename']}...")
                    time.sleep(sleep_time)  # Be nice to SEC servers
                    
                    # Download file
                    response = requests.get(
                        file_info['url'],
                        headers={'User-Agent': 'sloan@ethicic.com'}
                    )
                    response.raise_for_status()
                    
                    # Parse content
                    parsed_data = process_dataset(
                        response.content,
                        dataset_type,
                        file_info['filename']
                    )
                    
                    # Save to S3
                    s3_client = boto3.client(
                        's3',
                        endpoint_url=f"https://{s3_config['endPoint']}",
                        aws_access_key_id=s3_config['accessKey'],
                        aws_secret_access_key=s3_config['secretKey'],
                        region_name=s3_config['region'],
                        config=Config(s3={'addressing_style': 'path'}, signature_version='s3v4')
                    )
                    
                    saved_paths = save_to_s3(
                        s3_client,
                        s3_config['bucket'],
                        response.content,
                        parsed_data,
                        {
                            'url': file_info['url'],
                            'category': dataset_type,
                            'sample_file': file_info,
                            'description': f"{dataset_type} data",
                            'frequency': 'unknown'  # Could be determined from filename
                        }
                    )
                    
                    dataset_results.append({
                        'filename': file_info['filename'],
                        'success': True,
                        'parsed_data': parsed_data,
                        'saved_paths': saved_paths
                    })
                    
                    processed_files += 1
                    print(f"✓ {file_info['filename']} ({processed_files}/{total_files})")
                    
                except Exception as e:
                    print(f"✗ Error processing {file_info['filename']}: {e}")
                    dataset_results.append({
                        'filename': file_info['filename'],
                        'success': False,
                        'error': str(e)
                    })
            
            results[dataset_type] = {
                'total_files': len(available_files),
                'successful': len([r for r in dataset_results if r['success']]),
                'failed': len([r for r in dataset_results if not r['success']]),
                'results': dataset_results
            }
            
        except Exception as e:
            print(f"Error processing dataset {dataset_type}: {e}")
            results[dataset_type] = {
                'error': str(e),
                'success': False
            }
    
    return {
        'success': True,
        'timestamp': datetime.utcnow().isoformat(),
        'total_files': total_files,
        'processed_files': processed_files,
        'results': results
    }
