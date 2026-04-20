from flask import Flask, render_template, request, jsonify
import requests
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

API_GATEWAY_URL = os.environ.get('API_GATEWAY_URL', 'your-endpoint')


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        data = request.get_json(silent=True) or {}
        query = data.get('query', '').strip()
        session_id = data.get('session_id', '').strip()

        if not query:
            return jsonify({'error': 'Query is required'}), 400

        payload = {'query': query}
        if session_id:
            payload['session_id'] = session_id

        response = requests.post(
            API_GATEWAY_URL,
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=130
        )

        if response.status_code == 200:
            return jsonify(response.json())

        logger.error(f"API Gateway {response.status_code}: {response.text}")
        return jsonify({'error': 'Failed to get recommendations. Please try again.'}), 500

    except requests.Timeout:
        return jsonify({'error': 'Request timed out. Please try again.'}), 504
    except Exception as e:
        logger.error(f"Chat error: {e}")
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)
