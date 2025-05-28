"""
Lambda handler for Text-to-SQL Chatbot AWS deployment
"""

import json
import os
import boto3
import base64
from flask import Flask, request, jsonify, send_from_directory
import sys

# Add the current directory to the path so that we can import our modules
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Import our modules
from src.models.llm_provider import get_provider
from src.models.s3_data_access import S3DataAccess

# Initialize Flask app
app = Flask(__name__)

# Global configuration
CONFIG = {
    'default_provider': 'bedrock',
    'default_model': 'anthropic.claude-3-sonnet-20240229-v1:0',
    'bucket_name': None,
    'api_keys': {}
}

def get_secrets():
    """Get secrets from AWS Secrets Manager"""
    secret_name = os.environ.get('SECRET_NAME', 'text-to-sql-chatbot-secret-key')
    region_name = os.environ.get('AWS_REGION', 'ap-south-1')
    
    # Create a Secrets Manager client
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )
    
    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
    except Exception as e:
        print(f"Error getting secret: {str(e)}")
        return {}
    
    # Decode the secret
    if 'SecretString' in get_secret_value_response:
        secret = get_secret_value_response['SecretString']
        return json.loads(secret)
    else:
        decoded_binary_secret = base64.b64decode(get_secret_value_response['SecretBinary'])
        return json.loads(decoded_binary_secret)

# Load secrets on startup
secrets = get_secrets()
if 'S3_BUCKET_NAME' in secrets:
    CONFIG['bucket_name'] = secrets['S3_BUCKET_NAME']
if 'OPENAI_API_KEY' in secrets:
    CONFIG['api_keys']['openai'] = secrets['OPENAI_API_KEY']
if 'GEMINI_API_KEY' in secrets:
    CONFIG['api_keys']['gemini'] = secrets['GEMINI_API_KEY']

# Import routes
from src.routes.api import api_bp
app.register_blueprint(api_bp, url_prefix='/api')

# Serve static files
@app.route('/', defaults={'path': 'index.html'})
@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('src/static', path)

def lambda_handler(event, context):
    """AWS Lambda handler function"""
    # Get HTTP method and path from the event
    http_method = event['httpMethod']
    path = event['path']
    
    # Process API Gateway event into Flask format
    environ = {
        'REQUEST_METHOD': http_method,
        'PATH_INFO': path,
        'QUERY_STRING': event.get('queryStringParameters', {}) or '',
        'CONTENT_LENGTH': str(len(event.get('body', '') or '')),
        'CONTENT_TYPE': event.get('headers', {}).get('Content-Type', ''),
        'SERVER_NAME': 'lambda',
        'SERVER_PORT': '80',
        'SERVER_PROTOCOL': 'HTTP/1.1',
        'wsgi.version': (1, 0),
        'wsgi.url_scheme': 'http',
        'wsgi.input': event.get('body', '') or '',
        'wsgi.errors': sys.stderr,
        'wsgi.multithread': False,
        'wsgi.multiprocess': False,
        'wsgi.run_once': False,
    }
    
    # Handle request with Flask
    response = app.handle_request(environ)
    
    # Convert Flask response to Lambda response format
    return {
        'statusCode': response.status_code,
        'headers': dict(response.headers),
        'body': response.get_data(as_text=True)
    }

if __name__ == '__main__':
    # For local development
    app.run(host='0.0.0.0', port=5000, debug=True)
