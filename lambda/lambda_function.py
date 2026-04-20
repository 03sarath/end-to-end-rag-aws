import json
import boto3
import os
from botocore.config import Config

# Initialize Bedrock client
bedrock_config = Config(connect_timeout=120, read_timeout=120, retries={'max_attempts': 0})
bedrock_client = boto3.client('bedrock-runtime', config=bedrock_config)
bedrock_agent_client = boto3.client("bedrock-agent-runtime", config=bedrock_config)

# Configuration
KB_ID = os.environ['KB_ID']
MODEL_ID = "amazon.nova-lite-v1:0"  # ✅ Changed from claude-3-haiku
REGION = os.environ['AWS_RGN']

def retrieve_and_generate(input_text, kb_id, session_id=None):
    model_arn = f'arn:aws:bedrock:{REGION}::foundation-model/{MODEL_ID}'
    
    enhanced_query = f"""Please provide detailed information about health checkup packages in the following format:
    Hospital Name: [hospital name]
    Package Name: [package name]
    Price: [price in INR]
    Description: [brief description]
    Features:
    - [feature 1]
    - [feature 2]
    - [feature 3]

    Query: {input_text}"""
    
    try:
        if session_id:
            response = bedrock_agent_client.retrieve_and_generate(
                input={'text': enhanced_query},
                retrieveAndGenerateConfiguration={
                    'type': 'KNOWLEDGE_BASE',
                    'knowledgeBaseConfiguration': {
                        'knowledgeBaseId': kb_id,
                        'modelArn': model_arn
                    }
                },
                sessionId=session_id
            )
        else:
            response = bedrock_agent_client.retrieve_and_generate(
                input={'text': enhanced_query},
                retrieveAndGenerateConfiguration={
                    'type': 'KNOWLEDGE_BASE',
                    'knowledgeBaseConfiguration': {
                        'knowledgeBaseId': kb_id,
                        'modelArn': model_arn
                    }
                }
            )
        return response
    except Exception as e:
        print(f"Error in retrieve_and_generate: {str(e)}")
        raise

def parse_bedrock_response(response):
    """Parse the Bedrock response and structure it for the frontend"""
    try:
        generated_text = response['output']['text']
        packages = []
        current_package = None
        lines = generated_text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            if line.startswith('Hospital Name:') or line.startswith('Package Name:'):
                if current_package and (current_package['hospital'] != 'Information Available' or 
                                      current_package['description'] or 
                                      current_package['features']):
                    packages.append(current_package)
                
                current_package = {
                    'hospital': 'Information Available',
                    'description': '',
                    'features': [],
                    'price': 'Contact for pricing'
                }
            
            if current_package:
                if line.startswith('Hospital Name:'):
                    current_package['hospital'] = line.replace('Hospital Name:', '').strip()
                elif line.startswith('Package Name:'):
                    current_package['description'] = line.replace('Package Name:', '').strip()
                elif line.startswith('Price:'):
                    price = line.replace('Price:', '').strip()
                    if '₹' in price:
                        price = price.split('₹')[-1].strip()
                    current_package['price'] = price
                elif line.startswith('Description:'):
                    current_package['description'] = line.replace('Description:', '').strip()
                elif line.startswith('- '):
                    feature = line.replace('- ', '').strip()
                    if feature:
                        current_package['features'].append(feature)
        
        if current_package and (current_package['hospital'] != 'Information Available' or 
                              current_package['description'] or 
                              current_package['features']):
            packages.append(current_package)
        
        if not packages:
            hospital_name = None
            for line in lines:
                if 'hospital' in line.lower() or 'medical center' in line.lower():
                    hospital_name = line.strip()
                    break
            
            packages.append({
                'hospital': hospital_name or 'Information Available',
                'description': generated_text,
                'features': ['Please contact the hospital for detailed package information'],
                'price': 'Contact for pricing'
            })
        
        return {'packages': packages}
    except Exception as e:
        print(f"Error in parse_bedrock_response: {str(e)}")
        return {'error': f'Error parsing response: {str(e)}'}

def lambda_handler(event, context):
    try:
        body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
        query = body.get('query')
        
        if not query:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Query is required'})
            }
        
        response = retrieve_and_generate(query, KB_ID)
        result = parse_bedrock_response(response)
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'POST,OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type'
            },
            'body': json.dumps(result)
        }
        
    except Exception as e:
        print(f"Error in lambda_handler: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'POST,OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type'
            },
            'body': json.dumps({'error': str(e)})
        }