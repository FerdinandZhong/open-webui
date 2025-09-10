#!/usr/bin/env python3
"""
Run the merged Flask application with integrated SDN search functionality.
No separate API server needed.
"""
from flask import Flask, render_template, request, jsonify
import os
from pathlib import Path
import traceback
from dotenv import load_dotenv

from sdn_api.core.search_service import SDNSearchService
from sdn_api.config import settings
from sdn_api.utils.logger import setup_logger

load_dotenv()

app = Flask(__name__, template_folder='flask_ui/templates', static_folder='flask_ui/static')

logger = setup_logger(__name__)

# Initialize search service directly
SDN_FILE_PATH = Path(__file__).parent / settings.sdn_file_path
try:
    search_service = SDNSearchService(str(SDN_FILE_PATH), use_llm=settings.use_llm)
    logger.info(f"Initialized SDN Search Service with LLM: {settings.use_llm}")
except FileNotFoundError:
    logger.error(f"SDN file not found at {SDN_FILE_PATH}")
    search_service = None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search', methods=['POST'])
def search():
    if not search_service:
        return jsonify({"error": "SDN data not loaded"}), 503
    
    try:
        data = request.get_json()
        query = data.get('query', '')
        max_results = data.get('max_results', 10)
        
        results = search_service.search(query, max_results)
        
        return jsonify({
            "query": query,
            "total_matches": len(results),
            "results": [result.dict() for result in results]
        })
    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/health')
def health():
    return jsonify({
        "status": "healthy",
        "sdn_loaded": search_service is not None,
        "entries_count": len(search_service.entries) if search_service else 0
    })

@app.route('/stats')
def stats():
    if not search_service:
        return jsonify({"error": "SDN data not loaded"}), 503
    
    individuals = sum(1 for e in search_service.entries if 'individual' in e.type.lower())
    entities = len(search_service.entries) - individuals
    
    return jsonify({
        "total_entries": len(search_service.entries),
        "individuals": individuals,
        "entities": entities,
        "programs": len(set(e.program for e in search_service.entries if e.program))
    })

if __name__ == '__main__':
    print("Starting merged SDN Flask application...")
    
    # For CML applications, we need to bind to all interfaces
    PORT = os.getenv('CDSW_READONLY_PORT', '8090')
    HOST = '0.0.0.0'  # Bind to all interfaces for CML
    
    print(f"Starting Flask app on {HOST}:{PORT}")
    app.run(host=HOST, port=int(PORT), debug=False)