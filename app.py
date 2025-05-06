from flask import Flask, request, render_template, jsonify
from flask_cors import CORS
from orchestrator import process_query, initialize_database
import os

app = Flask(__name__)
# Enable CORS for all routes - important for API usage from external UIs
CORS(app)

# Initialize the database when the app starts
initialize_database()

# Root route - can be used for API health check
@app.route('/')
def index():
    # For API-only usage, you might want to return API info instead of HTML
    # But we'll keep the template option for now
    if os.path.exists(os.path.join('templates', 'index.html')):
        return render_template('index.html')
    else:
        return jsonify({
            'status': 'online',
            'message': 'Scenario Search API is running',
            'endpoints': ['/api/query']
        })

# Main API endpoint for querying scenarios
@app.route('/api/query', methods=['POST'])
def handle_query():
    data = request.json
    query = data.get('query')
    
    if not query:
        return jsonify({
            'success': False,
            'message': 'No query provided',
            'count': 0,
            'results': []
        })
    
    # Process the query through the orchestrator
    result = process_query(query)
    return jsonify(result)

# Health check endpoint
@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy',
        'message': 'API is operational'
    })

if __name__ == '__main__':
    # Get port from environment variable for cloud deployment compatibility
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
