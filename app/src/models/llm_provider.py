"""
LLM Provider Module for Text-to-SQL Chatbot
Handles integration with multiple LLM providers including Bedrock Claude, OpenAI, and Gemini
"""

import os
import json
import boto3
import anthropic
import openai
import google.generativeai as genai
from abc import ABC, abstractmethod

class LLMProvider(ABC):
    """Abstract base class for LLM providers"""
    
    @abstractmethod
    def generate_sql(self, question, schema, sample_data=None):
        """Generate SQL query from natural language question"""
        pass
    
    @abstractmethod
    def explain_results(self, question, sql_query, query_results):
        """Explain query results in natural language"""
        pass

class BedrockClaudeProvider(LLMProvider):
    """AWS Bedrock Claude provider implementation"""
    
    def __init__(self, api_key=None, model="anthropic.claude-3-sonnet-20240229-v1:0"):
        """Initialize Bedrock Claude provider"""
        self.model = model
        # Use provided API key or default AWS credentials
        self.session = boto3.Session()
        self.bedrock_runtime = self.session.client(
            service_name='bedrock-runtime',
            region_name=os.environ.get('AWS_REGION', 'ap-south-1')
        )
    
    def generate_sql(self, question, schema, sample_data=None):
        """Generate SQL query using Bedrock Claude"""
        prompt = self._create_sql_prompt(question, schema, sample_data)
        
        response = self.bedrock_runtime.invoke_model(
            modelId=self.model,
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 1000,
                "messages": [
                    {"role": "user", "content": prompt}
                ]
            })
        )
        
        response_body = json.loads(response.get('body').read())
        sql_query = response_body.get('content')[0].get('text')
        
        # Extract just the SQL query from the response
        return self._extract_sql(sql_query)
    
    def explain_results(self, question, sql_query, query_results):
        """Explain query results using Bedrock Claude"""
        prompt = f"""
        Question: {question}
        
        SQL Query: {sql_query}
        
        Query Results: {query_results}
        
        Please explain these results in simple terms that answer the original question.
        """
        
        response = self.bedrock_runtime.invoke_model(
            modelId=self.model,
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 1000,
                "messages": [
                    {"role": "user", "content": prompt}
                ]
            })
        )
        
        response_body = json.loads(response.get('body').read())
        explanation = response_body.get('content')[0].get('text')
        
        return explanation
    
    def _create_sql_prompt(self, question, schema, sample_data=None):
        """Create prompt for SQL generation"""
        prompt = f"""
        You are an expert SQL query generator. I need you to create a SQL query based on the following:
        
        Question: {question}
        
        Database Schema:
        {schema}
        """
        
        if sample_data:
            prompt += f"""
            Sample Data:
            {sample_data}
            """
        
        prompt += """
        Please generate a SQL query that answers the question. Return only the SQL query without any explanations.
        """
        
        return prompt
    
    def _extract_sql(self, response):
        """Extract SQL query from model response"""
        # Look for SQL between triple backticks
        import re
        sql_match = re.search(r"```sql\n(.*?)\n```", response, re.DOTALL)
        if sql_match:
            return sql_match.group(1).strip()
        
        # If no SQL code block, try to find just the SQL statement
        sql_lines = []
        capture = False
        for line in response.split('\n'):
            line = line.strip()
            if line.upper().startswith('SELECT') or line.upper().startswith('WITH'):
                capture = True
            
            if capture:
                sql_lines.append(line)
                
            if capture and line.endswith(';'):
                break
                
        if sql_lines:
            return '\n'.join(sql_lines)
        
        # If all else fails, return the whole response
        return response

class OpenAIProvider(LLMProvider):
    """OpenAI provider implementation"""
    
    def __init__(self, api_key, model="gpt-4o-mini"):
        """Initialize OpenAI provider"""
        self.model = model
        openai.api_key = api_key
    
    def generate_sql(self, question, schema, sample_data=None):
        """Generate SQL query using OpenAI"""
        prompt = self._create_sql_prompt(question, schema, sample_data)
        
        response = openai.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are an expert SQL query generator."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000
        )
        
        sql_query = response.choices[0].message.content
        
        # Extract just the SQL query from the response
        return self._extract_sql(sql_query)
    
    def explain_results(self, question, sql_query, query_results):
        """Explain query results using OpenAI"""
        prompt = f"""
        Question: {question}
        
        SQL Query: {sql_query}
        
        Query Results: {query_results}
        
        Please explain these results in simple terms that answer the original question.
        """
        
        response = openai.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are an expert at explaining SQL query results."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000
        )
        
        explanation = response.choices[0].message.content
        
        return explanation
    
    def _create_sql_prompt(self, question, schema, sample_data=None):
        """Create prompt for SQL generation"""
        prompt = f"""
        I need you to create a SQL query based on the following:
        
        Question: {question}
        
        Database Schema:
        {schema}
        """
        
        if sample_data:
            prompt += f"""
            Sample Data:
            {sample_data}
            """
        
        prompt += """
        Please generate a SQL query that answers the question. Return only the SQL query without any explanations.
        """
        
        return prompt
    
    def _extract_sql(self, response):
        """Extract SQL query from model response"""
        # Look for SQL between triple backticks
        import re
        sql_match = re.search(r"```sql\n(.*?)\n```", response, re.DOTALL)
        if sql_match:
            return sql_match.group(1).strip()
        
        # If no SQL code block, try to find just the SQL statement
        sql_lines = []
        capture = False
        for line in response.split('\n'):
            line = line.strip()
            if line.upper().startswith('SELECT') or line.upper().startswith('WITH'):
                capture = True
            
            if capture:
                sql_lines.append(line)
                
            if capture and line.endswith(';'):
                break
                
        if sql_lines:
            return '\n'.join(sql_lines)
        
        # If all else fails, return the whole response
        return response

class GeminiProvider(LLMProvider):
    """Google Gemini provider implementation"""
    
    def __init__(self, api_key, model="gemini-1.5-pro"):
        """Initialize Gemini provider"""
        self.model = model
        genai.configure(api_key=api_key)
        self.model_client = genai.GenerativeModel(self.model)
    
    def generate_sql(self, question, schema, sample_data=None):
        """Generate SQL query using Gemini"""
        prompt = self._create_sql_prompt(question, schema, sample_data)
        
        response = self.model_client.generate_content(prompt)
        sql_query = response.text
        
        # Extract just the SQL query from the response
        return self._extract_sql(sql_query)
    
    def explain_results(self, question, sql_query, query_results):
        """Explain query results using Gemini"""
        prompt = f"""
        Question: {question}
        
        SQL Query: {sql_query}
        
        Query Results: {query_results}
        
        Please explain these results in simple terms that answer the original question.
        """
        
        response = self.model_client.generate_content(prompt)
        explanation = response.text
        
        return explanation
    
    def _create_sql_prompt(self, question, schema, sample_data=None):
        """Create prompt for SQL generation"""
        prompt = f"""
        You are an expert SQL query generator. I need you to create a SQL query based on the following:
        
        Question: {question}
        
        Database Schema:
        {schema}
        """
        
        if sample_data:
            prompt += f"""
            Sample Data:
            {sample_data}
            """
        
        prompt += """
        Please generate a SQL query that answers the question. Return only the SQL query without any explanations.
        """
        
        return prompt
    
    def _extract_sql(self, response):
        """Extract SQL query from model response"""
        # Look for SQL between triple backticks
        import re
        sql_match = re.search(r"```sql\n(.*?)\n```", response, re.DOTALL)
        if sql_match:
            return sql_match.group(1).strip()
        
        # If no SQL code block, try to find just the SQL statement
        sql_lines = []
        capture = False
        for line in response.split('\n'):
            line = line.strip()
            if line.upper().startswith('SELECT') or line.upper().startswith('WITH'):
                capture = True
            
            if capture:
                sql_lines.append(line)
                
            if capture and line.endswith(';'):
                break
                
        if sql_lines:
            return '\n'.join(sql_lines)
        
        # If all else fails, return the whole response
        return response

def get_provider(provider_name, api_key=None, model=None):
    """Factory function to get the appropriate LLM provider"""
    if provider_name.lower() == "bedrock":
        model = model or "anthropic.claude-3-sonnet-20240229-v1:0"
        return BedrockClaudeProvider(api_key, model)
    elif provider_name.lower() == "openai":
        model = model or "gpt-4o-mini"
        return OpenAIProvider(api_key, model)
    elif provider_name.lower() == "gemini":
        model = model or "gemini-1.5-pro"
        return GeminiProvider(api_key, model)
    else:
        raise ValueError(f"Unsupported provider: {provider_name}")
