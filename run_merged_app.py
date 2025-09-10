#!/usr/bin/env python3
"""
Run the merged Flask application with integrated SDN search functionality.
No separate API server needed.
"""
from flask import Flask, render_template, request, jsonify
import os
import sys
from pathlib import Path
import traceback
from dotenv import load_dotenv

from sdn_api.core.search_service import SDNSearchService
from sdn_api.config import settings
from sdn_api.utils.logger import setup_logger

load_dotenv()

app = Flask(__name__, template_folder='flask_ui/templates', static_folder='flask_ui/static')

logger = setup_logger(__name__)

# Check environment variables
print(f"DEBUG: OPENAI_API_KEY: {'*' * 10 if os.environ.get('OPENAI_API_KEY') else 'NOT SET'}")
print(f"DEBUG: USE_LLM: {os.environ.get('USE_LLM', 'NOT SET')}")
print(f"DEBUG: SDN_FILE_PATH env: {os.environ.get('SDN_FILE_PATH', 'NOT SET')}")

# Initialize search service directly
# Use the direct path since file exists
SDN_FILE_PATH = "/home/cdsw/data_list/sdn_final.csv"
print(f"DEBUG: Using SDN file at: {SDN_FILE_PATH}")
print(f"DEBUG: File exists: {os.path.exists(SDN_FILE_PATH)}")

if os.path.exists(SDN_FILE_PATH):
    file_size = os.path.getsize(SDN_FILE_PATH)
    print(f"DEBUG: File size: {file_size} bytes")
else:
    print("DEBUG: File does not exist!")

try:
    search_service = SDNSearchService(SDN_FILE_PATH, use_llm=settings.use_llm)
    logger.info(f"Initialized SDN Search Service with LLM: {settings.use_llm}")
    logger.info(f"SDN file path: {SDN_FILE_PATH}")
except FileNotFoundError:
    logger.error(f"SDN file not found at {SDN_FILE_PATH}")
    search_service = None
except Exception as e:
    logger.error(f"Error loading SDN file: {e}")
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
    
    HOST = '0.0.0.0'
    PORT = os.getenv('CDSW_READONLY_PORT', '8090')
    # Run the Flask app
    app.run(host="127.0.0.1", port=int(PORT))