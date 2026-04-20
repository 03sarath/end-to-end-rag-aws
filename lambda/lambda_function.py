import json
import boto3
import os
from botocore.config import Config

bedrock_config = Config(connect_timeout=120, read_timeout=120, retries={'max_attempts': 0})
bedrock_agent_client = boto3.client("bedrock-agent-runtime", config=bedrock_config)

KB_ID = os.environ['KB_ID']
MODEL_ID = "amazon.nova-lite-v1:0"
REGION = os.environ.get('AWS_RGN', 'us-east-1')

# Placed in generationConfiguration so it never pollutes the retrieval query
PROMPT_TEMPLATE = """You are a health package advisor. Answer the user's health package question using ONLY the information in the knowledge base results below.

Knowledge Base Results:
$search_results$

User Question: $query$

Instructions:
1. Write 1-2 sentences addressing the user naturally.
2. Then output the matching packages in this EXACT format (do not change the markers):

[PACKAGES_START]
[
  {
    "hospital": "Hospital Name",
    "package_name": "Package Name",
    "price": 6500,
    "price_display": "₹6,500",
    "target": "Men / Women / Children / All",
    "tests": ["Test 1", "Test 2", "Test 3"],
    "consultations": ["Physician Consultation", "Dietician Consultation"],
    "optional_addons": [{"name": "Cardiac CT", "price": 6000}]
  }
]
[PACKAGES_END]

Rules:
- Only include packages that appear in the knowledge base results above
- "price" must be a plain integer (no ₹, no commas)
- "price_display" must be formatted like ₹6,500
- "tests" lists diagnostic tests/procedures only (not consultations)
- "consultations" lists only consultation/examination items
- "optional_addons" is [] if none exist
- If no relevant packages found, still output [PACKAGES_START][][PACKAGES_END] and explain why"""


def retrieve_and_generate(query: str, kb_id: str, session_id: str = None) -> dict:
    model_arn = f'arn:aws:bedrock:{REGION}::foundation-model/{MODEL_ID}'

    params = {
        'input': {'text': query},  # raw query → clean retrieval from KB
        'retrieveAndGenerateConfiguration': {
            'type': 'KNOWLEDGE_BASE',
            'knowledgeBaseConfiguration': {
                'knowledgeBaseId': kb_id,
                'modelArn': model_arn,
                'generationConfiguration': {
                    'promptTemplate': {
                        'textPromptTemplate': PROMPT_TEMPLATE
                    }
                }
            }
        }
    }

    if session_id:
        params['sessionId'] = session_id

    return bedrock_agent_client.retrieve_and_generate(**params)


def parse_response(response: dict) -> dict:
    try:
        text = response['output']['text']
        session_id = response.get('sessionId', '')

        message = text.strip()
        packages = []

        if '[PACKAGES_START]' in text and '[PACKAGES_END]' in text:
            before, rest = text.split('[PACKAGES_START]', 1)
            json_block, _ = rest.split('[PACKAGES_END]', 1)
            message = before.strip()

            try:
                raw = json.loads(json_block.strip())
                for pkg in raw:
                    price_val = pkg.get('price', 0)
                    try:
                        price_int = int(str(price_val).replace(',', '').replace('₹', '').strip())
                    except (ValueError, TypeError):
                        price_int = 0

                    packages.append({
                        'hospital': pkg.get('hospital', ''),
                        'package_name': pkg.get('package_name', ''),
                        'price': price_int,
                        'price_display': pkg.get('price_display', f'₹{price_int:,}'),
                        'target': pkg.get('target', ''),
                        'tests': pkg.get('tests', []),
                        'consultations': pkg.get('consultations', []),
                        'optional_addons': pkg.get('optional_addons', [])
                    })
            except (json.JSONDecodeError, ValueError) as e:
                print(f"JSON parse error: {e}")

        return {
            'message': message,
            'packages': packages,
            'session_id': session_id
        }

    except Exception as e:
        print(f"parse_response error: {e}")
        return {
            'message': 'I encountered an issue processing the results. Please try again.',
            'packages': [],
            'session_id': ''
        }


def lambda_handler(event, context):
    cors_headers = {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'POST,OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type'
    }

    if event.get('httpMethod') == 'OPTIONS':
        return {'statusCode': 200, 'headers': cors_headers, 'body': ''}

    try:
        body = event.get('body', '{}')
        if isinstance(body, str):
            body = json.loads(body)

        query = body.get('query', '').strip()
        session_id = body.get('session_id', '').strip()

        if not query:
            return {
                'statusCode': 400,
                'headers': cors_headers,
                'body': json.dumps({'error': 'Query is required'})
            }

        response = retrieve_and_generate(query, KB_ID, session_id or None)
        result = parse_response(response)

        return {
            'statusCode': 200,
            'headers': cors_headers,
            'body': json.dumps(result)
        }

    except Exception as e:
        print(f"lambda_handler error: {e}")
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'error': str(e)})
        }
