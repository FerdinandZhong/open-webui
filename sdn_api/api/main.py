from flask import Flask, request, jsonify
from flask_cors import CORS
from pathlib import Path
import traceback

from ..models.sdn import SearchQuery, SearchResponse, MatchResult
from ..core.search_service import SDNSearchService
from ..config import settings
from ..utils.logger import setup_logger

logger = setup_logger(__name__)

app = Flask(__name__)
CORS(app)  # Enable CORS


# Initialize search service
SDN_FILE_PATH = Path(__file__).parent.parent.parent / settings.sdn_file_path
try:
    search_service = SDNSearchService(str(SDN_FILE_PATH), use_llm=settings.use_llm)
    logger.info(f"Initialized SDN Search Service with LLM: {settings.use_llm}")
except FileNotFoundError:
    logger.error(f"SDN file not found at {SDN_FILE_PATH}")
    search_service = None


@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "sdn_loaded": search_service is not None,
        "entries_count": len(search_service.entries) if search_service else 0
    })


@app.route("/search", methods=["POST"])
def search_sdn():
    """
    Search the SDN list with two-step matching.

    Step 1: Flexible name matching
    Step 2: Context-based ranking (DOB, nationality, etc.)
    """
    if not search_service:
        return jsonify({"error": "SDN data not loaded"}), 503

    try:
        data = request.get_json()
        query_text = data.get("query", "")
        max_results = data.get("max_results", 10)

        search_result = search_service.search(query_text, max_results)
        results = search_result['results']
        step_details = search_result['step_details']

        # Convert results to dicts, handling both Pydantic v1 and v2
        results_dicts = []
        for i, result in enumerate(results):
            if hasattr(result, 'model_dump'):
                results_dicts.append(result.model_dump())
            elif hasattr(result, 'dict'):
                results_dicts.append(result.dict())
            else:
                logger.error(f"Result {i} is not a Pydantic model: {type(result)} - {result}")
                # Skip invalid results
                continue

        return jsonify({
            "query": query_text,
            "total_matches": len(results_dicts),
            "results": results_dicts,
            "step_details": step_details
        })
    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/stats", methods=["GET"])
def get_stats():
    """Get statistics about the loaded SDN data."""
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