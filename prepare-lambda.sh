#!/bin/bash

# Create deployment directory
mkdir -p deployment

# Copy application files
cp -r app/* deployment/

# Install dependencies
cd deployment
pip install -r requirements.txt -t .

# Create zip file
zip -r ../text-to-sql-chatbot.zip .

# Create S3 bucket for deployment if it doesn't exist
aws s3api create-bucket --bucket lambda-deployment-$(aws sts get-caller-identity --query Account --output text) --region us-east-1

# Upload zip to S3
aws s3 cp ../text-to-sql-chatbot.zip s3://lambda-deployment-$(aws sts get-caller-identity --query Account --output text)/

cd ..
