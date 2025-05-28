# Text-to-SQL Chatbot Deployment Guide

This comprehensive guide will walk you through deploying the Text-to-SQL Chatbot on AWS using GitHub integration. No coding knowledge is required - just follow these step-by-step instructions.

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Setting Up GitHub Repository](#setting-up-github-repository)
3. [AWS Account Setup](#aws-account-setup)
4. [Configuring AWS Services](#configuring-aws-services)
5. [Deploying the Application](#deploying-the-application)
6. [Testing and Verification](#testing-and-verification)
7. [Troubleshooting](#troubleshooting)

## Prerequisites

Before you begin, make sure you have:

- A GitHub account (free tier is sufficient)
- An AWS account
- Access to your S3 bucket containing the gzipped CSV data
- API keys for any LLM providers you want to use (OpenAI, Google Gemini)

## Setting Up GitHub Repository

### Step 1: Create a New GitHub Repository

1. Go to [GitHub](https://github.com) and sign in to your account
2. Click the "+" icon in the top-right corner and select "New repository"
3. Name your repository (e.g., "text-to-sql-chatbot")
4. Make sure it's set to "Public" (or "Private" if you have GitHub Pro)
5. Check "Add a README file"
6. Click "Create repository"

![Create GitHub Repository](images/github-create-repo.png)

### Step 2: Upload the Chatbot Code

1. In your new repository, click "Add file" > "Upload files"
2. Drag and drop all the files from the `text-to-sql-chatbot` folder you downloaded
3. Add a commit message like "Initial upload of Text-to-SQL Chatbot"
4. Click "Commit changes"

![Upload Files to GitHub](images/github-upload-files.png)

## AWS Account Setup

### Step 1: Create an IAM User for Deployment

1. Sign in to the [AWS Management Console](https://aws.amazon.com/console/)
2. Search for "IAM" in the services search bar and select it
3. In the left sidebar, click "Users" > "Add users"
4. Enter a username (e.g., "github-deployment-user")
5. Select "Access key - Programmatic access" as the access type
6. Click "Next: Permissions"

![Create IAM User](images/aws-create-iam-user.png)

### Step 2: Attach Required Permissions

1. Click "Attach existing policies directly"
2. Search for and select the following policies:
   - AmazonS3FullAccess
   - AWSLambdaFullAccess
   - AmazonAPIGatewayAdministrator
   - AWSCloudFormationFullAccess
   - IAMFullAccess
3. Click "Next: Tags" (no tags needed)
4. Click "Next: Review"
5. Click "Create user"
6. **IMPORTANT**: Download the CSV file with the access key and secret key or copy them somewhere safe. You will need these later.

![Attach IAM Policies](images/aws-attach-policies.png)

## Configuring AWS Services

### Step 1: Set Up AWS Secrets Manager for API Keys

1. In the AWS Management Console, search for "Secrets Manager" and select it
2. Click "Store a new secret"
3. Select "Other type of secret"
4. Add the following key-value pairs:
   - `OPENAI_API_KEY`: Your OpenAI API key (if using)
   - `GEMINI_API_KEY`: Your Google Gemini API key (if using)
   - `S3_BUCKET_NAME`: Your S3 bucket name containing the data
5. Click "Next"
6. Name your secret "text-to-sql-chatbot-secrets"
7. Add a description like "API keys for Text-to-SQL Chatbot"
8. Click "Next" > "Next" > "Store"

![AWS Secrets Manager](images/aws-secrets-manager.png)

### Step 2: Configure S3 Bucket Permissions

1. In the AWS Management Console, search for "S3" and select it
2. Find and click on your data bucket
3. Go to the "Permissions" tab
4. Under "Bucket policy", click "Edit"
5. Add the following policy (replace `YOUR-BUCKET-NAME` with your actual bucket name):

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Service": "lambda.amazonaws.com"
            },
            "Action": [
                "s3:GetObject",
                "s3:ListBucket"
            ],
            "Resource": [
                "arn:aws:s3:::YOUR-BUCKET-NAME",
                "arn:aws:s3:::YOUR-BUCKET-NAME/*"
            ]
        }
    ]
}
```

6. Click "Save changes"

![S3 Bucket Policy](images/aws-s3-policy.png)

## Deploying the Application

### Step 1: Set Up GitHub Actions for Deployment

1. In your GitHub repository, click on the "Actions" tab
2. Click "set up a workflow yourself"
3. Replace the default content with the following:

```yaml
name: Deploy to AWS

on:
  push:
    branches: [ main ]
  workflow_dispatch:

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v1
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1
      
      - name: Deploy CloudFormation stack
        run: |
          aws cloudformation deploy \
            --template-file cloudformation.yaml \
            --stack-name text-to-sql-chatbot \
            --capabilities CAPABILITY_IAM \
            --parameter-overrides \
              SecretName=text-to-sql-chatbot-secrets
      
      - name: Get deployment outputs
        run: |
          aws cloudformation describe-stacks \
            --stack-name text-to-sql-chatbot \
            --query "Stacks[0].Outputs" \
            --output table
```

4. Click "Start commit" > "Commit new file"

![GitHub Actions Workflow](images/github-actions-workflow.png)

### Step 2: Add AWS Credentials to GitHub Secrets

1. In your GitHub repository, go to "Settings" > "Secrets and variables" > "Actions"
2. Click "New repository secret"
3. Add the following secrets:
   - Name: `AWS_ACCESS_KEY_ID`, Value: Your IAM user access key
   - Name: `AWS_SECRET_ACCESS_KEY`, Value: Your IAM user secret key
4. Click "Add secret" for each

![GitHub Secrets](images/github-secrets.png)

### Step 3: Create CloudFormation Template

1. In your GitHub repository, click "Add file" > "Create new file"
2. Name the file `cloudformation.yaml`
3. Add the following content:

```yaml
AWSTemplateFormatVersion: '2010-09-09'
Description: 'Text-to-SQL Chatbot Deployment'

Parameters:
  SecretName:
    Type: String
    Description: Name of the secret in AWS Secrets Manager
    Default: text-to-sql-chatbot-secrets

Resources:
  # Lambda Function Role
  LambdaExecutionRole:
    Type: AWS::IAM::Role
    Properties:
      AssumeRolePolicyDocument:
        Version: '2012-10-17'
        Statement:
          - Effect: Allow
            Principal:
              Service: lambda.amazonaws.com
            Action: sts:AssumeRole
      ManagedPolicyArns:
        - arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
        - arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess
      Policies:
        - PolicyName: SecretsManagerAccess
          PolicyDocument:
            Version: '2012-10-17'
            Statement:
              - Effect: Allow
                Action:
                  - secretsmanager:GetSecretValue
                Resource: !Sub arn:aws:secretsmanager:${AWS::Region}:${AWS::AccountId}:secret:${SecretName}-*

  # Lambda Function
  ChatbotFunction:
    Type: AWS::Lambda::Function
    Properties:
      FunctionName: text-to-sql-chatbot
      Handler: src.main.lambda_handler
      Role: !GetAtt LambdaExecutionRole.Arn
      Runtime: python3.9
      Timeout: 30
      MemorySize: 512
      Environment:
        Variables:
          SECRET_NAME: !Ref SecretName
      Code:
        S3Bucket: !Sub lambda-deployment-${AWS::AccountId}
        S3Key: text-to-sql-chatbot.zip

  # API Gateway
  ChatbotAPI:
    Type: AWS::ApiGateway::RestApi
    Properties:
      Name: text-to-sql-chatbot-api
      Description: API for Text-to-SQL Chatbot

  # API Gateway Resource
  ChatbotResource:
    Type: AWS::ApiGateway::Resource
    Properties:
      RestApiId: !Ref ChatbotAPI
      ParentId: !GetAtt ChatbotAPI.RootResourceId
      PathPart: 'api'

  # API Gateway Method
  ChatbotMethod:
    Type: AWS::ApiGateway::Method
    Properties:
      RestApiId: !Ref ChatbotAPI
      ResourceId: !Ref ChatbotResource
      HttpMethod: ANY
      AuthorizationType: NONE
      Integration:
        Type: AWS_PROXY
        IntegrationHttpMethod: POST
        Uri: !Sub arn:aws:apigateway:${AWS::Region}:lambda:path/2015-03-31/functions/${ChatbotFunction.Arn}/invocations

  # API Gateway Deployment
  ChatbotDeployment:
    Type: AWS::ApiGateway::Deployment
    DependsOn: ChatbotMethod
    Properties:
      RestApiId: !Ref ChatbotAPI
      StageName: prod

  # Lambda Permission
  ChatbotPermission:
    Type: AWS::Lambda::Permission
    Properties:
      Action: lambda:InvokeFunction
      FunctionName: !Ref ChatbotFunction
      Principal: apigateway.amazonaws.com
      SourceArn: !Sub arn:aws:execute-api:${AWS::Region}:${AWS::AccountId}:${ChatbotAPI}/*/ANY/api

Outputs:
  ApiEndpoint:
    Description: API Gateway endpoint URL
    Value: !Sub https://${ChatbotAPI}.execute-api.${AWS::Region}.amazonaws.com/prod/api
```

4. Click "Commit new file"

![CloudFormation Template](images/github-cloudformation.png)

### Step 4: Prepare Lambda Deployment Package

1. In your GitHub repository, click "Add file" > "Create new file"
2. Name the file `prepare-lambda.sh`
3. Add the following content:

```bash
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
```

4. Click "Commit new file"

### Step 5: Update GitHub Actions Workflow

1. Go to the `.github/workflows` directory in your repository
2. Edit the workflow file you created earlier
3. Update it to include the Lambda preparation step:

```yaml
name: Deploy to AWS

on:
  push:
    branches: [ main ]
  workflow_dispatch:

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v1
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1
      
      - name: Prepare Lambda package
        run: |
          chmod +x prepare-lambda.sh
          ./prepare-lambda.sh
      
      - name: Deploy CloudFormation stack
        run: |
          aws cloudformation deploy \
            --template-file cloudformation.yaml \
            --stack-name text-to-sql-chatbot \
            --capabilities CAPABILITY_IAM \
            --parameter-overrides \
              SecretName=text-to-sql-chatbot-secrets
      
      - name: Get deployment outputs
        run: |
          aws cloudformation describe-stacks \
            --stack-name text-to-sql-chatbot \
            --query "Stacks[0].Outputs" \
            --output table
```

4. Commit the changes

### Step 6: Trigger Deployment

1. In your GitHub repository, go to the "Actions" tab
2. Click on the "Deploy to AWS" workflow
3. Click "Run workflow" > "Run workflow"
4. Wait for the workflow to complete (this may take a few minutes)

![Run GitHub Actions](images/github-run-action.png)

### Step 7: Get the API Endpoint

1. Once the workflow completes successfully, check the workflow logs
2. Find the "Get deployment outputs" step
3. Copy the API endpoint URL (it will look like `https://abc123def.execute-api.us-east-1.amazonaws.com/prod/api`)

![Deployment Outputs](images/github-deployment-outputs.png)

## Testing and Verification

### Step 1: Access the Chatbot

1. Open a web browser and navigate to the API endpoint URL you copied
2. You should see the Text-to-SQL Chatbot interface

### Step 2: Configure the Chatbot

1. Enter your S3 bucket name in the "S3 Bucket Name" field
2. Select your preferred LLM provider (AWS Bedrock Claude is the default)
3. If using OpenAI or Google Gemini, enter your API key
4. Set the date range for your queries
5. Click "Save Settings"

![Chatbot Configuration](images/chatbot-config.png)

### Step 3: Test a Query

1. Type a natural language question about your data in the input field
2. Click the send button or press Enter
3. Wait for the chatbot to process your query and display the results

![Chatbot Query](images/chatbot-query.png)

## Troubleshooting

### Common Issues and Solutions

#### Deployment Failed

**Issue**: The GitHub Actions workflow fails during deployment.

**Solution**:
1. Check the workflow logs for specific error messages
2. Verify that your AWS credentials are correct
3. Make sure your IAM user has the necessary permissions
4. Try running the workflow again

#### API Key Issues

**Issue**: The chatbot returns an error about invalid API keys.

**Solution**:
1. Double-check that you've entered the correct API keys
2. Verify that your API keys are active and have sufficient quota
3. Try using a different LLM provider

#### S3 Access Issues

**Issue**: The chatbot cannot access your S3 data.

**Solution**:
1. Verify that your S3 bucket name is correct
2. Check that your bucket policy allows access from the Lambda function
3. Make sure your data follows the expected directory structure

#### Query Processing Errors

**Issue**: The chatbot returns errors when processing queries.

**Solution**:
1. Start with simple queries to test functionality
2. Check that your data is in the expected format
3. Try specifying a narrower date range
4. Use a different LLM provider to see if the issue persists

For any other issues, please refer to the AWS CloudWatch logs for the Lambda function, which can provide more detailed error information.
