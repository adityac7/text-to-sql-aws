"""
S3 Data Access Module for Text-to-SQL Chatbot
Handles access to gzipped CSV files stored in S3 buckets
"""

import os
import io
import gzip
import boto3
import pandas as pd
from datetime import datetime, timedelta

class S3DataAccess:
    """Class for accessing and querying data from S3 buckets"""
    
    def __init__(self, bucket_name, base_path="csv-data/"):
        """Initialize S3 data access with bucket name and base path"""
        self.bucket_name = bucket_name
        self.base_path = base_path
        self.session = boto3.Session()
        self.s3_client = self.session.client('s3')
    
    def get_available_date_range(self):
        """Get the available date range in the S3 bucket"""
        try:
            # List all objects in the bucket with the prefix
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=self.base_path
            )
            
            if 'Contents' not in response:
                return None, None
            
            # Extract dates from the object keys
            dates = []
            for obj in response.get('Contents', []):
                key = obj['Key']
                # Parse date from key format: csv-data/year=YYYY/month=MM/day=DD/
                parts = key.split('/')
                if len(parts) >= 4:
                    try:
                        year_part = parts[1]
                        month_part = parts[2]
                        day_part = parts[3]
                        
                        year = int(year_part.split('=')[1])
                        month = int(month_part.split('=')[1])
                        day = int(day_part.split('=')[1])
                        
                        dates.append(datetime(year, month, day))
                    except (IndexError, ValueError):
                        continue
            
            if not dates:
                return None, None
                
            return min(dates), max(dates)
        
        except Exception as e:
            print(f"Error getting available date range: {str(e)}")
            return None, None
    
    def get_data_for_date_range(self, start_date, end_date, limit=None):
        """
        Get data for a specific date range
        
        Args:
            start_date (datetime): Start date
            end_date (datetime): End date
            limit (int, optional): Maximum number of files to process
            
        Returns:
            pandas.DataFrame: Combined data for the date range
        """
        try:
            # Generate list of dates in the range
            date_list = []
            current_date = start_date
            while current_date <= end_date:
                date_list.append(current_date)
                current_date += timedelta(days=1)
            
            # Get data for each date
            all_data = []
            file_count = 0
            
            for date in date_list:
                year = date.year
                month = date.month
                day = date.day
                
                # Construct prefix for this date
                prefix = f"{self.base_path}year={year}/month={month:02d}/day={day:02d}/"
                
                # List objects with this prefix
                response = self.s3_client.list_objects_v2(
                    Bucket=self.bucket_name,
                    Prefix=prefix
                )
                
                # Process each file
                for obj in response.get('Contents', []):
                    key = obj['Key']
                    if key.endswith('.csv.gz'):
                        # Get the file content
                        file_obj = self.s3_client.get_object(Bucket=self.bucket_name, Key=key)
                        file_content = file_obj['Body'].read()
                        
                        # Decompress and read as CSV
                        with gzip.GzipFile(fileobj=io.BytesIO(file_content)) as gzipped:
                            df = pd.read_csv(io.BytesIO(gzipped.read()))
                            all_data.append(df)
                            
                            file_count += 1
                            if limit and file_count >= limit:
                                break
                    
                if limit and file_count >= limit:
                    break
            
            # Combine all dataframes
            if not all_data:
                return pd.DataFrame()
                
            return pd.concat(all_data, ignore_index=True)
            
        except Exception as e:
            print(f"Error getting data for date range: {str(e)}")
            return pd.DataFrame()
    
    def get_schema_from_data(self, df):
        """
        Generate schema information from a dataframe
        
        Args:
            df (pandas.DataFrame): Dataframe to generate schema from
            
        Returns:
            str: Schema information as a string
        """
        if df.empty:
            return "No data available to generate schema."
        
        schema_info = []
        schema_info.append("Table Schema:")
        
        for column in df.columns:
            dtype = df[column].dtype
            sample = df[column].iloc[0] if not df[column].isna().all() else "NULL"
            schema_info.append(f"- {column} ({dtype}): Example value: {sample}")
        
        return "\n".join(schema_info)
    
    def get_sample_data(self, df, rows=5):
        """
        Get sample data from a dataframe
        
        Args:
            df (pandas.DataFrame): Dataframe to get sample from
            rows (int): Number of rows to include in sample
            
        Returns:
            str: Sample data as a string
        """
        if df.empty:
            return "No data available for sampling."
        
        sample = df.head(rows)
        return sample.to_string()
    
    def execute_query(self, df, query):
        """
        Execute a SQL query on a dataframe
        
        Args:
            df (pandas.DataFrame): Dataframe to query
            query (str): SQL query to execute
            
        Returns:
            pandas.DataFrame: Query results
        """
        try:
            # For simplicity, we'll use pandas query capabilities
            # In a real implementation, you might want to use a SQL engine like DuckDB or SQLite
            
            # Basic parsing to extract the SELECT and WHERE parts
            query = query.strip()
            if not query.lower().startswith('select'):
                return pd.DataFrame(), "Query must start with SELECT"
            
            # Very simple query parser - this would need to be much more robust in production
            if 'where' in query.lower():
                select_part = query.lower().split('where')[0]
                where_part = query.lower().split('where')[1]
                
                # Extract columns
                columns_str = select_part.replace('select', '').strip()
                if columns_str == '*':
                    result = df.copy()
                else:
                    columns = [c.strip() for c in columns_str.split(',')]
                    result = df[columns]
                
                # Apply where condition (very simplified)
                # This is a very basic implementation and would need to be enhanced
                result = result.query(where_part)
                
            else:
                # Just select columns
                columns_str = query.lower().replace('select', '').strip()
                if columns_str == '*':
                    result = df.copy()
                else:
                    columns = [c.strip() for c in columns_str.split(',')]
                    result = df[columns]
            
            return result, None
            
        except Exception as e:
            return pd.DataFrame(), f"Error executing query: {str(e)}"
