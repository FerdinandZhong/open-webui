from typing import List, Tuple, Dict, Optional
from difflib import SequenceMatcher

from ..models.sdn import SDNEntry
from .llm_service import LLMService
from ..utils.logger import setup_logger

logger = setup_logger(__name__)


class NameMatcher:
    """Step 1: Flexible name matching for initial filtering."""
    
    def __init__(self, threshold: float = 0.7, use_llm: bool = True):
        self.threshold = threshold
        self.use_llm = use_llm
        self.llm_service = LLMService() if use_llm else None
    
    def generate_query_variations(self, query_name: str) -> List[str]:
        """Generate name variations for the query once."""
        return self._generate_name_variations(query_name)
    
    def filter_matches(self, query_variations: List[str], entries: List[SDNEntry]) -> List[Dict]:
        """Filter entries based on flexible name matching using pre-generated variations."""
        matches = []
        
        for entry in entries:
            # Flexible name matching using pre-generated query variations
            name_score, match_type = self._flexible_name_match_with_variations(
                query_variations, entry.name, entry.aliases
            )
            
            if name_score > self.threshold:
                logger.debug(f"Match: '{entry.name}' -> score: {name_score:.3f} ({match_type})")
                matches.append({
                    'entry': entry,
                    'score': name_score,  # Keep for backward compatibility
                    'name_match_score': name_score,  # Store the initial name matching score
                    'match_reasons': [f"{match_type} match: {name_score:.2f}"]
                })
        
        # Sort by score
        matches.sort(key=lambda x: x['score'], reverse=True)
        logger.info(f"Filtered to {len(matches)} matches above threshold {self.threshold}")
        return matches[:20]  # Return top 20 matches for ranking analysis
    
    def _flexible_name_match_with_variations(self, query_variations: List[str], target_name: str, aliases: List[str]) -> Tuple[float, str]:
        """Perform flexible name matching using pre-generated query variations."""
        best_score = 0.0
        best_match_type = ""
        
        # Check main name against all query variations
        target_name_lower = target_name.lower().strip()
        for q_var in query_variations:
            score = self._fuzzy_match_score(q_var, target_name_lower)
            if score > best_score:
                best_score = score
                best_match_type = "name"
        
        # Check aliases against all query variations
        for alias in aliases:
            alias_lower = alias.lower().strip()
            for q_var in query_variations:
                score = self._fuzzy_match_score(q_var, alias_lower)
                if score > best_score:
                    best_score = score
                    best_match_type = "alias"
        
        return best_score, best_match_type
    
    def _generate_name_variations(self, name: str) -> List[str]:
        """Generate name variations for flexible matching."""
        if self.use_llm and self.llm_service:
            try:
                # Use LLM to generate sophisticated name variations
                llm_variations = self.llm_service.generate_name_variations(name)
                # Convert to lowercase for matching
                return [var.lower().strip() for var in llm_variations]
            except Exception as e:
                logger.warning(f"LLM name generation failed, falling back to rule-based: {e}")
        
        # Fallback to rule-based variations
        variations = [name.lower().strip()]
        
        # Split name into parts
        parts = name.lower().split()
        
        # Add variations with different orders
        if len(parts) >= 2:
            # Last name, first name
            variations.append(f"{parts[-1]}, {' '.join(parts[:-1])}")
            # First + last only
            variations.append(f"{parts[0]} {parts[-1]}")
        
        # Remove common prefixes/suffixes
        cleaned_parts = []
        for part in parts:
            # Remove common titles and suffixes
            if part not in ['mr', 'mrs', 'ms', 'dr', 'prof', 'sir', 'jr', 'sr', 'ii', 'iii']:
                cleaned_parts.append(part)
        
        if cleaned_parts and cleaned_parts != parts:
            variations.append(' '.join(cleaned_parts))
        
        # Add partial matches (useful for typos)
        for part in parts:
            if len(part) > 3:  # Only for longer names
                variations.append(part)
        
        return list(set(variations))  # Remove duplicates
    
    @staticmethod
    def _fuzzy_match_score(str1: str, str2: str) -> float:
        """Calculate fuzzy match score between two strings."""
        return SequenceMatcher(None, str1.lower(), str2.lower()).ratio()