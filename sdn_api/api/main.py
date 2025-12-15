from flask import Flask, request, jsonify
from flask_cors import CORS
from pathlib import Path
import traceback

from ..models.sdn import SearchQuery, SearchResponse, MatchResult
from ..core.search_service import SDNSearchService
from ..config import settings
from ..utils.logger import setup_logger

logger = setup_logger(__name__)


def _make_json_safe(obj):
    """Recursively convert objects to JSON-serializable format."""
    if isinstance(obj, dict):
        return {k: _make_json_safe(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_make_json_safe(item) for item in obj]
    elif hasattr(obj, 'value'):  # Enum
        return obj.value
    elif hasattr(obj, 'model_dump'):  # Pydantic v2
        return obj.model_dump()
    elif hasattr(obj, 'dict'):  # Pydantic v1
        return obj.dict()
    elif hasattr(obj, '__dict__'):  # Other objects
        return str(obj)
    else:
        return obj


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
            try:
                if hasattr(result, 'model_dump'):
                    # Use mode='json' for Pydantic v2 to ensure JSON-serializable output
                    results_dicts.append(result.model_dump(mode='json'))
                elif hasattr(result, 'dict'):
                    results_dicts.append(result.dict())
                else:
                    logger.error(f"Result {i} is not a Pydantic model: {type(result)} - {result}")
                    continue
            except Exception as convert_err:
                logger.error(f"Error converting result {i}: {convert_err}")
                logger.error(f"Result type: {type(result)}, Result: {result}")
                logger.error(f"Traceback: {traceback.format_exc()}")
                continue

        # Serialize step_details - convert any non-serializable objects
        try:
            import json
            json.dumps(step_details)  # Test if serializable
        except (TypeError, ValueError) as e:
            logger.error(f"step_details not JSON serializable: {e}")
            # Make step_details JSON-safe
            step_details = _make_json_safe(step_details)

        return jsonify({
            "query": query_text,
            "total_matches": len(results_dicts),
            "results": results_dicts,
            "step_details": step_details
        })
    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
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