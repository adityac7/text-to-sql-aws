"""
Main API routes for Text-to-SQL Chatbot
Handles all backend API endpoints for query processing
"""

from flask import Blueprint, request, jsonify
import json
import pandas as pd
from datetime import datetime
import os
import sys

# Import custom modules
from src.models.llm_provider import get_provider
from src.models.s3_data_access import S3DataAccess

# Create blueprint
api_bp = Blueprint('api', __name__)

# Global variables for configuration
CONFIG = {
    'default_provider': 'bedrock',
    'default_model': 'anthropic.claude-3-sonnet-20240229-v1:0',
    'bucket_name': None,
    'api_keys': {}
}

@api_bp.route('/config', methods=['GET', 'POST'])
def config():
    """Get or update configuration"""
    global CONFIG
    
    if request.method == 'POST':
        data = request.json
        
        # Update configuration
        if 'provider' in data:
            CONFIG['default_provider'] = data['provider']
        
        if 'model' in data:
            CONFIG['default_model'] = data['model']
        
        if 'bucket_name' in data:
            CONFIG['bucket_name'] = data['bucket_name']
        
        if 'api_keys' in data:
            # Merge with existing keys
            CONFIG['api_keys'].update(data['api_keys'])
        
        return jsonify({'status': 'success', 'config': CONFIG})
    
    # For GET requests, return current config (without API keys for security)
    safe_config = CONFIG.copy()
    safe_config['api_keys'] = {k: '***' for k in CONFIG['api_keys'].keys()}
    return jsonify(safe_config)

@api_bp.route('/available-dates', methods=['GET'])
def available_dates():
    """Get available date range from S3 bucket"""
    bucket_name = CONFIG.get('bucket_name')
    
    if not bucket_name:
        return jsonify({'error': 'S3 bucket not configured'}), 400
    
    # Create S3 data access object
    s3_access = S3DataAccess(bucket_name)
    
    # Get available date range
    start_date, end_date = s3_access.get_available_date_range()
    
    if not start_date or not end_date:
        return jsonify({'error': 'No data available in S3 bucket'}), 404
    
    return jsonify({
        'start_date': start_date.strftime('%Y-%m-%d'),
        'end_date': end_date.strftime('%Y-%m-%d')
    })

@api_bp.route('/query', methods=['POST'])
def query():
    """Process a natural language query and return results"""
    data = request.json
    
    # Validate request
    if 'question' not in data:
        return jsonify({'error': 'Question is required'}), 400
    
    question = data['question']
    provider_name = data.get('provider', CONFIG['default_provider'])
    model = data.get('model', CONFIG['default_model'])
    bucket_name = CONFIG.get('bucket_name')
    
    if not bucket_name:
        return jsonify({'error': 'S3 bucket not configured'}), 400
    
    # Parse date range
    try:
        if 'start_date' in data and 'end_date' in data:
            start_date = datetime.strptime(data['start_date'], '%Y-%m-%d')
            end_date = datetime.strptime(data['end_date'], '%Y-%m-%d')
        else:
            # Default to last 30 days
            end_date = datetime.now()
            start_date = end_date - pd.Timedelta(days=30)
    except ValueError:
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
    
    # Get API key for the selected provider
    api_key = None
    if provider_name.lower() != 'bedrock':  # Bedrock uses AWS credentials
        api_key = CONFIG['api_keys'].get(provider_name.lower())
        if not api_key:
            return jsonify({'error': f'API key not configured for {provider_name}'}), 400
    
    # Create S3 data access object
    s3_access = S3DataAccess(bucket_name)
    
    # Get data for the date range
    df = s3_access.get_data_for_date_range(start_date, end_date)
    
    if df.empty:
        return jsonify({'error': 'No data available for the specified date range'}), 404
    
    # Generate schema information
    schema = s3_access.get_schema_from_data(df)
    
    # Get sample data
    sample_data = s3_access.get_sample_data(df)
    
    # Create LLM provider
    try:
        llm = get_provider(provider_name, api_key, model)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    
    # Generate SQL query
    sql_query = llm.generate_sql(question, schema, sample_data)
    
    # Execute query
    results, error = s3_access.execute_query(df, sql_query)
    
    if error:
        return jsonify({'error': error}), 400
    
    # Convert results to JSON
    results_json = results.to_json(orient='records')
    
    # Generate explanation
    explanation = llm.explain_results(question, sql_query, results.to_string())
    
    return jsonify({
        'question': question,
        'sql_query': sql_query,
        'results': json.loads(results_json),
        'explanation': explanation
    })

@api_bp.route('/providers', methods=['GET'])
def providers():
    """Get available LLM providers and models"""
    return jsonify({
        'providers': [
            {
                'name': 'bedrock',
                'display_name': 'AWS Bedrock Claude',
                'models': [
                    {'id': 'anthropic.claude-3-sonnet-20240229-v1:0', 'name': 'Claude 3 Sonnet'},
                    {'id': 'anthropic.claude-3-haiku-20240307-v1:0', 'name': 'Claude 3 Haiku'}
                ],
                'requires_key': False
            },
            {
                'name': 'openai',
                'display_name': 'OpenAI',
                'models': [
                    {'id': 'gpt-4o', 'name': 'GPT-4o'},
                    {'id': 'gpt-4o-mini', 'name': 'GPT-4o Mini'}
                ],
                'requires_key': True
            },
            {
                'name': 'gemini',
                'display_name': 'Google Gemini',
                'models': [
                    {'id': 'gemini-1.5-pro', 'name': 'Gemini 1.5 Pro'},
                    {'id': 'gemini-1.5-flash', 'name': 'Gemini 1.5 Flash'}
                ],
                'requires_key': True
            }
        ]
    })
