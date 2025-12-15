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
from sdn_api.core.traditional_matcher import TraditionalMatcher
from sdn_api.config import settings
from sdn_api.utils.logger import setup_logger

load_dotenv()

app = Flask(__name__, template_folder='flask_ui/templates', static_folder='flask_ui/static')

logger = setup_logger(__name__)

# Initialize search service directly
SDN_FILE_PATH = "/home/cdsw/data_list/sdn_final.csv"

search_service = None
traditional_matcher = None

try:
    search_service = SDNSearchService(SDN_FILE_PATH, use_llm=settings.use_llm)
    logger.info(f"Initialized SDN Search Service with LLM: {settings.use_llm}")
    logger.info(f"SDN file path: {SDN_FILE_PATH}")

    # Initialize traditional matcher with the same entries
    traditional_matcher = TraditionalMatcher(threshold=0.3)
    logger.info("Initialized Traditional Matcher")
except FileNotFoundError:
    logger.error(f"SDN file not found at {SDN_FILE_PATH}")
except Exception as e:
    logger.error(f"Error loading SDN file: {e}")

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

        # === LLM-BASED METHOD (Right side) ===
        search_result = search_service.search(query, max_results)
        llm_results = search_result['results']
        llm_step_details = search_result['step_details']

        # Convert LLM results to dicts
        llm_results_dicts = []
        for result in llm_results:
            if hasattr(result, 'model_dump'):
                llm_results_dicts.append(result.model_dump(mode='json'))
            elif hasattr(result, 'dict'):
                llm_results_dicts.append(result.dict())
            else:
                logger.error(f"Result is not a Pydantic model: {type(result)}")
                continue

        # === TRADITIONAL METHOD (Left side) ===
        traditional_result = {'results': [], 'step_details': {}}
        if traditional_matcher:
            traditional_result = traditional_matcher.screen(
                query,
                search_service.entries,
                max_results
            )
            # Convert traditional results to serializable format
            traditional_results_dicts = []
            for r in traditional_result['results']:
                traditional_results_dicts.append({
                    'name': r['entry'].name,
                    'type': r['entry'].type,
                    'score': round(r['score'], 3),
                    'confidence': r['confidence'],
                    'feature_count': r['feature_count'],
                    'matched_features': r['matched_features'],
                    'features': {k: round(v, 3) for k, v in r['features'].items()},
                    'details': {
                        'id': r['entry'].id,
                        'program': r['entry'].program,
                        'nationality': r['entry'].nationality,
                        'dob': r['entry'].dob,
                        'pob': r['entry'].pob,
                        'aliases': r['entry'].aliases,
                        'remarks': r['entry'].remarks
                    }
                })
            traditional_result['results'] = traditional_results_dicts

        return jsonify({
            "query": query,
            # LLM method results (existing - right side)
            "total_matches": len(llm_results_dicts),
            "results": llm_results_dicts,
            "step_details": llm_step_details,
            # Traditional method results (new - left side)
            "traditional": {
                "total_matches": len(traditional_result['results']),
                "results": traditional_result['results'],
                "step_details": traditional_result['step_details']
            }
        })
    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
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