from flask import Flask, render_template, request, jsonify
import requests
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configuration
API_GATEWAY_URL = os.environ.get('API_GATEWAY_URL', 'https://sdghsgfsghghj.execute-api.us-east-1.amazonaws.com/default/genai-app-may26')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/search', methods=['POST'])
def search():
    try:
        data = request.get_json()
        query = data.get('query', '')
        
        if not query:
            return jsonify({'error': 'Query is required'}), 400

        # Enhance query for better results
        enhanced_query = query
        if 'hospital' in query.lower():
            # For hospital-specific queries, ask for all available packages
            enhanced_query = f"{query} Please list all available health checkup packages with their prices and features."
        else:
            # For general queries, include budget and hospital comparison
            if 'budget' not in query.lower() and 'price' not in query.lower() and 'cost' not in query.lower():
                enhanced_query = f"{query} Please include prices and budget options."
            if 'hospital' not in query.lower() and 'clinic' not in query.lower():
                enhanced_query = f"{enhanced_query} Please compare packages from different hospitals."

        # Call API Gateway (which triggers Lambda)
        response = requests.post(
            API_GATEWAY_URL,
            json={'query': enhanced_query},
            headers={
                'Content-Type': 'application/json'
            }
        )
        
        if response.status_code == 200:
            result = response.json()
            
            # If no packages found, try a more specific query
            if not result.get('packages') or (len(result['packages']) == 1 and 
                result['packages'][0]['hospital'] == 'Information Available'):
                logger.info("No packages found, trying more specific query")
                specific_query = f"List all health checkup packages and their prices from {query}"
                response = requests.post(
                    API_GATEWAY_URL,
                    json={'query': specific_query},
                    headers={'Content-Type': 'application/json'}
                )
                if response.status_code == 200:
                    result = response.json()
            
            return jsonify(result)
        else:
            logger.error(f"API Gateway error: {response.text}")
            return jsonify({'error': 'Failed to get package recommendations'}), 500

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/hospitals', methods=['GET'])
def get_hospitals():
    """Get list of hospitals with available packages"""
    try:
        # Call Lambda function with a query to get hospital list
        response = requests.post(
            API_GATEWAY_URL,
            json={'query': 'List all hospitals with their available health checkup packages'}
        )
        
        if response.status_code == 200:
            result = response.json()
            # Extract unique hospitals from packages
            hospitals = list(set(pkg['hospital'] for pkg in result.get('packages', [])))
            return jsonify({'hospitals': hospitals})
        else:
            return jsonify({'error': 'Failed to get hospital list'}), 500

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True) 