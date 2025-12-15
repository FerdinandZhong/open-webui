import re
import asyncio
from typing import List, Dict, Optional

from .data_loader import SDNDataLoader
from .name_matcher import NameMatcher
from .ranker import MatchRanker
from .llm_service import LLMService
from ..models.sdn import SDNEntry, MatchResult, ConfidenceLevel
from ..utils.logger import setup_logger

logger = setup_logger(__name__)


class SDNSearchService:
    """Main search service combining both steps."""
    
    def __init__(self, sdn_file_path: str, use_llm: bool = True):
        logger.info(f"Initializing SDNSearchService with LLM: {use_llm}")
        
        self.loader = SDNDataLoader(sdn_file_path)
        logger.debug("Data loader initialized")
        self.name_matcher = NameMatcher(use_llm=use_llm)
        logger.debug("Name matcher initialized")
        self.ranker = MatchRanker(use_llm=use_llm)
        logger.debug("Ranker initialized")
        self.use_llm = use_llm
        if use_llm:
            self.llm_service = LLMService()
            logger.debug("LLM service initialized for explanations")
        self.entries: List[SDNEntry] = []
        logger.info("Loading SDN data...")
        self.load_data()
        logger.info(f"Service fully initialized with {len(self.entries)} entries")
    
    def load_data(self):
        """Load SDN data into memory."""
        self.entries = self.loader.load_entries()
    
    def search(self, query: str, max_results: int = 10) -> Dict:
        """
        Main search function that combines both steps.
        Returns both results and step details for UI display.
        """
        # Parse query
        query_info = self._parse_query(query)

        # Initialize step details
        step_details = {
            'step1_name_generation': {
                'query_name': query_info['name'],
                'variations': [],
                'variation_count': 0
            },
            'step2_database_filtering': {
                'total_entries_searched': len(self.entries),
                'threshold': self.name_matcher.threshold,
                'matches_found': 0,
                'matches': []
            },
            'step3_ai_ranking': {
                'matches_ranked': 0,
                'ranking_details': []
            }
        }

        # Generate name variations once for the query
        logger.info(f"Starting search for: '{query_info['name']}'")
        logger.debug(f"Searching against {len(self.entries)} entries")
        query_variations = self.name_matcher.generate_query_variations(query_info['name'])
        logger.info(f"Generated {len(query_variations)} query variations")

        # Store step 1 details
        step_details['step1_name_generation']['variations'] = query_variations
        step_details['step1_name_generation']['variation_count'] = len(query_variations)

        # Step 1: Initial name-based filtering
        logger.info("Step 1: Filtering matches...")
        filtered = self.name_matcher.filter_matches(query_variations, self.entries)
        logger.info(f"Step 1 complete: Found {len(filtered)} initial matches")

        # Store step 2 details
        step_details['step2_database_filtering']['matches_found'] = len(filtered)
        step_details['step2_database_filtering']['matches'] = [
            {
                'name': m['entry'].name,
                'score': round(m['name_match_score'], 3),
                'match_type': m['match_reasons'][0] if m['match_reasons'] else 'name match',
                'type': m['entry'].type
            }
            for m in filtered
        ]

        if not filtered:
            return {'results': [], 'step_details': step_details}

        # Step 2: Context-based ranking
        logger.info("Step 2: Ranking matches...")
        ranked = self.ranker.rank_matches(query_info, filtered)
        logger.info(f"Step 2 complete: Ranked {len(ranked)} matches")

        # Store step 3 details
        step_details['step3_ai_ranking']['matches_ranked'] = len(ranked)
        step_details['step3_ai_ranking']['ranking_details'] = [
            {
                'name': m['entry'].name,
                'name_match_score': round(m.get('name_match_score', 0), 3),
                'final_score': round(m.get('llm_score', m.get('score', 0)), 3),
                'confidence': m['confidence'].value if hasattr(m['confidence'], 'value') else str(m['confidence']),
                'match_reasons': m['match_reasons']
            }
            for m in ranked
        ]

        # Step 3: Generate explanations for high-confidence matches
        if self.use_llm:
            logger.info("Step 3: Generating explanations for high-confidence matches...")
            for match in ranked[:max_results]:
                # Generate explanation for HIGH confidence matches
                if match['confidence'] in [ConfidenceLevel.HIGH, ConfidenceLevel.MEDIUM_HIGH]:
                    try:
                        explanation = self.llm_service.generate_explanation(query_info, match)
                        match['explanation'] = explanation
                        logger.info(f"Generated explanation for {match['entry'].name}")
                    except Exception as e:
                        logger.error(f"Error generating explanation: {e}")
                        match['explanation'] = None
                else:
                    match['explanation'] = None

        # Format results
        results = []
        for match in ranked[:max_results]:
            entry = match['entry']
            result = MatchResult(
                name=entry.name,
                type=entry.type,
                name_match_score=match['name_match_score'],
                llm_score=match['llm_score'],
                score=match['llm_score'],  # Keep for backward compatibility
                confidence=match['confidence'],
                match_reasons=match['match_reasons'],
                details={
                    'id': entry.id,
                    'program': entry.program,
                    'nationality': entry.nationality,
                    'dob': entry.dob,
                    'pob': entry.pob,
                    'aliases': entry.aliases,
                    'remarks': entry.remarks
                },
                explanation=match.get('explanation')
            )
            results.append(result)

        return {'results': results, 'step_details': step_details}
    
    @staticmethod
    def _parse_query(query: str) -> Dict[str, Optional[str]]:
        """Parse user input to extract name, DOB, and nationality."""
        parts = [p.strip() for p in query.split(',')]
        
        # First, check if any parts look like dates or nationalities
        name_parts = []
        dob = None
        nationality = None
        
        for part in parts:
            # Check if it's a date (various formats)
            if re.match(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}', part):
                dob = part
            # Check if it looks like a nationality/country (common country names)
            elif part.lower() in ['american', 'british', 'french', 'german', 'chinese', 'russian', 'iranian', 'iraqi', 'syrian', 'afghan', 'pakistan', 'usa', 'uk', 'france', 'germany', 'china', 'russia', 'iran', 'iraq', 'syria', 'afghanistan']:
                nationality = part
            else:
                # It's part of the name
                name_parts.append(part)
        
        # Reconstruct the name from remaining parts
        name = ', '.join(name_parts) if name_parts else query
        
        return {
            'name': name,
            'dob': dob,
            'nationality': nationality
        }