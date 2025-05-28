#!/bin/bash

# Create deployment directory
mkdir -p deployment

# Copy application files
rsync -av --exclude 'venv/' app/ deployment/

# Install dependencies
cd deployment
pip install -r requirements.txt -t .

# Create zip file
zip -r ../text-to-sql-chatbot.zip .

# Upload zip to S3
aws s3 cp ../text-to-sql-chatbot.zip s3://lambda-deployment-$(aws sts get-caller-identity --query Account --output text)-ap-south-1/ --region ap-south-1

cd ..
