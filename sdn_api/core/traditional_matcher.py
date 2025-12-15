"""
Traditional rule-based name screening with feature extraction.
Uses multiple distance metrics and features to calculate risk scores.
"""
import re
from typing import List, Dict, Optional, Tuple
from difflib import SequenceMatcher
from collections import Counter

from ..models.sdn import SDNEntry
from ..utils.logger import setup_logger

logger = setup_logger(__name__)


class TraditionalMatcher:
    """
    Traditional name screening using 20+ extracted features.
    No LLM - pure algorithmic matching.
    """

    def __init__(self, threshold: float = 0.3):
        self.threshold = threshold
        # Feature weights for final score calculation
        self.feature_weights = {
            # Name similarity features (0-1 scores)
            'exact_match': 1.0,
            'case_insensitive_match': 0.95,
            'levenshtein_similarity': 0.7,
            'jaro_winkler_similarity': 0.7,
            'soundex_match': 0.5,
            'metaphone_match': 0.5,
            'ngram_similarity': 0.6,
            'token_set_ratio': 0.65,
            'partial_ratio': 0.5,
            'first_name_match': 0.4,
            'last_name_match': 0.5,
            'initials_match': 0.3,
            'name_length_similarity': 0.2,
            'common_prefix': 0.3,
            'common_suffix': 0.3,
            # Alias features
            'alias_exact_match': 0.9,
            'alias_similarity': 0.6,
            # Context features
            'dob_exact_match': 0.8,
            'dob_partial_match': 0.4,
            'nationality_match': 0.5,
            'country_in_remarks': 0.3,
        }

    def screen(self, query: str, entries: List[SDNEntry], max_results: int = 10) -> Dict:
        """
        Screen query against all entries using traditional feature extraction.
        Returns results and detailed feature breakdown.
        """
        logger.info(f"Traditional screening for query: '{query}'")

        # Parse query
        query_info = self._parse_query(query)
        query_name = query_info['name'].lower().strip()

        results = []

        for entry in entries:
            # Extract all features
            features = self._extract_features(query_info, entry)

            # Calculate weighted score
            score = self._calculate_score(features)

            if score >= self.threshold:
                results.append({
                    'entry': entry,
                    'score': score,
                    'features': features,
                    'confidence': self._score_to_confidence(score),
                    'matched_features': [k for k, v in features.items() if v > 0],
                    'feature_count': sum(1 for v in features.values() if v > 0)
                })

        # Sort by score descending
        results.sort(key=lambda x: x['score'], reverse=True)
        results = results[:max_results]

        logger.info(f"Traditional screening found {len(results)} matches")

        # Build step details
        step_details = {
            'method': 'Traditional Feature-Based',
            'total_features': len(self.feature_weights),
            'query_parsed': query_info,
            'matches_found': len(results),
            'feature_weights': self.feature_weights,
            'results_detail': [
                {
                    'name': r['entry'].name,
                    'score': round(r['score'], 3),
                    'confidence': r['confidence'],
                    'feature_count': r['feature_count'],
                    'features': {k: round(v, 3) for k, v in r['features'].items() if v > 0}
                }
                for r in results
            ]
        }

        return {
            'results': results,
            'step_details': step_details
        }

    def _parse_query(self, query: str) -> Dict[str, Optional[str]]:
        """Parse query to extract name, DOB, and nationality."""
        parts = [p.strip() for p in query.split(',')]

        result = {
            'name': parts[0] if parts else query,
            'dob': None,
            'nationality': None,
            'raw_query': query
        }

        for part in parts[1:]:
            part_lower = part.lower()
            # Check for date pattern
            if re.search(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}', part):
                result['dob'] = part
            elif re.search(r'\d{4}', part) and len(part) <= 10:
                result['dob'] = part
            else:
                result['nationality'] = part

        return result

    def _extract_features(self, query_info: Dict, entry: SDNEntry) -> Dict[str, float]:
        """Extract all 20+ features for a query-entry pair."""
        query_name = query_info['name'].lower().strip()
        entry_name = entry.name.lower().strip()

        features = {}

        # === NAME SIMILARITY FEATURES ===

        # 1. Exact match
        features['exact_match'] = 1.0 if query_name == entry_name else 0.0

        # 2. Case insensitive match (already lower, so same as exact here)
        features['case_insensitive_match'] = 1.0 if query_name == entry_name else 0.0

        # 3. Levenshtein similarity
        features['levenshtein_similarity'] = self._levenshtein_similarity(query_name, entry_name)

        # 4. Jaro-Winkler similarity
        features['jaro_winkler_similarity'] = self._jaro_winkler(query_name, entry_name)

        # 5. Soundex match
        features['soundex_match'] = 1.0 if self._soundex(query_name) == self._soundex(entry_name) else 0.0

        # 6. Metaphone match
        features['metaphone_match'] = 1.0 if self._metaphone(query_name) == self._metaphone(entry_name) else 0.0

        # 7. N-gram similarity (bigrams)
        features['ngram_similarity'] = self._ngram_similarity(query_name, entry_name, n=2)

        # 8. Token set ratio (handles word order)
        features['token_set_ratio'] = self._token_set_ratio(query_name, entry_name)

        # 9. Partial ratio (best partial match)
        features['partial_ratio'] = self._partial_ratio(query_name, entry_name)

        # 10. First name match
        query_parts = query_name.split()
        entry_parts = entry_name.split()
        if query_parts and entry_parts:
            features['first_name_match'] = self._levenshtein_similarity(query_parts[0], entry_parts[0])
        else:
            features['first_name_match'] = 0.0

        # 11. Last name match
        if query_parts and entry_parts:
            features['last_name_match'] = self._levenshtein_similarity(query_parts[-1], entry_parts[-1])
        else:
            features['last_name_match'] = 0.0

        # 12. Initials match
        query_initials = ''.join(p[0] for p in query_parts if p)
        entry_initials = ''.join(p[0] for p in entry_parts if p)
        features['initials_match'] = 1.0 if query_initials == entry_initials else (
            0.5 if set(query_initials) == set(entry_initials) else 0.0
        )

        # 13. Name length similarity
        max_len = max(len(query_name), len(entry_name))
        if max_len > 0:
            features['name_length_similarity'] = 1.0 - abs(len(query_name) - len(entry_name)) / max_len
        else:
            features['name_length_similarity'] = 0.0

        # 14. Common prefix length
        common_prefix = self._common_prefix_length(query_name, entry_name)
        features['common_prefix'] = common_prefix / max(len(query_name), 1)

        # 15. Common suffix length
        common_suffix = self._common_suffix_length(query_name, entry_name)
        features['common_suffix'] = common_suffix / max(len(query_name), 1)

        # === ALIAS FEATURES ===

        # 16. Alias exact match
        alias_exact = 0.0
        for alias in entry.aliases:
            if query_name == alias.lower():
                alias_exact = 1.0
                break
        features['alias_exact_match'] = alias_exact

        # 17. Best alias similarity
        alias_sim = 0.0
        for alias in entry.aliases:
            sim = self._jaro_winkler(query_name, alias.lower())
            alias_sim = max(alias_sim, sim)
        features['alias_similarity'] = alias_sim

        # === CONTEXT FEATURES ===

        # 18. DOB exact match
        query_dob = query_info.get('dob', '')
        if query_dob and entry.dob:
            query_dob_clean = re.sub(r'[^0-9]', '', query_dob)
            entry_dob_clean = re.sub(r'[^0-9]', '', entry.dob)
            features['dob_exact_match'] = 1.0 if query_dob_clean == entry_dob_clean else 0.0
        else:
            features['dob_exact_match'] = 0.0

        # 19. DOB partial match (year or month/day)
        if query_dob and entry.dob:
            query_dob_clean = re.sub(r'[^0-9]', '', query_dob)
            entry_dob_clean = re.sub(r'[^0-9]', '', entry.dob)
            # Check if any 4-digit year matches or if partial date matches
            if len(query_dob_clean) >= 4 and len(entry_dob_clean) >= 4:
                if query_dob_clean[-4:] == entry_dob_clean[-4:]:  # Year match
                    features['dob_partial_match'] = 0.7
                elif query_dob_clean[:4] in entry_dob_clean or entry_dob_clean[:4] in query_dob_clean:
                    features['dob_partial_match'] = 0.5
                else:
                    features['dob_partial_match'] = 0.0
            else:
                features['dob_partial_match'] = 0.0
        else:
            features['dob_partial_match'] = 0.0

        # 20. Nationality match
        query_nat = (query_info.get('nationality') or '').lower()
        entry_nat = (entry.nationality or '').lower()
        if query_nat and entry_nat:
            features['nationality_match'] = self._jaro_winkler(query_nat, entry_nat)
        else:
            features['nationality_match'] = 0.0

        # 21. Country mentioned in remarks
        if query_nat and entry.remarks:
            features['country_in_remarks'] = 1.0 if query_nat in entry.remarks.lower() else 0.0
        else:
            features['country_in_remarks'] = 0.0

        return features

    def _calculate_score(self, features: Dict[str, float]) -> float:
        """Calculate weighted score from features."""
        total_weight = 0.0
        weighted_sum = 0.0

        for feature_name, feature_value in features.items():
            weight = self.feature_weights.get(feature_name, 0.5)
            weighted_sum += feature_value * weight
            total_weight += weight

        if total_weight == 0:
            return 0.0

        # Normalize to 0-1 range
        return weighted_sum / total_weight

    def _score_to_confidence(self, score: float) -> str:
        """Convert score to confidence level."""
        if score >= 0.8:
            return 'HIGH'
        elif score >= 0.6:
            return 'MEDIUM-HIGH'
        elif score >= 0.4:
            return 'MEDIUM'
        elif score >= 0.2:
            return 'LOW-MEDIUM'
        else:
            return 'LOW'

    # === STRING DISTANCE ALGORITHMS ===

    def _levenshtein_similarity(self, s1: str, s2: str) -> float:
        """Calculate Levenshtein similarity (1 - normalized distance)."""
        if not s1 or not s2:
            return 0.0 if s1 != s2 else 1.0

        len1, len2 = len(s1), len(s2)

        # Create distance matrix
        dp = [[0] * (len2 + 1) for _ in range(len1 + 1)]

        for i in range(len1 + 1):
            dp[i][0] = i
        for j in range(len2 + 1):
            dp[0][j] = j

        for i in range(1, len1 + 1):
            for j in range(1, len2 + 1):
                cost = 0 if s1[i-1] == s2[j-1] else 1
                dp[i][j] = min(
                    dp[i-1][j] + 1,      # deletion
                    dp[i][j-1] + 1,      # insertion
                    dp[i-1][j-1] + cost  # substitution
                )

        distance = dp[len1][len2]
        max_len = max(len1, len2)
        return 1.0 - (distance / max_len) if max_len > 0 else 1.0

    def _jaro_winkler(self, s1: str, s2: str, winkler_prefix: float = 0.1) -> float:
        """Calculate Jaro-Winkler similarity."""
        if not s1 or not s2:
            return 0.0 if s1 != s2 else 1.0

        if s1 == s2:
            return 1.0

        len1, len2 = len(s1), len(s2)
        match_distance = max(len1, len2) // 2 - 1
        match_distance = max(0, match_distance)

        s1_matches = [False] * len1
        s2_matches = [False] * len2

        matches = 0
        transpositions = 0

        # Find matches
        for i in range(len1):
            start = max(0, i - match_distance)
            end = min(i + match_distance + 1, len2)

            for j in range(start, end):
                if s2_matches[j] or s1[i] != s2[j]:
                    continue
                s1_matches[i] = True
                s2_matches[j] = True
                matches += 1
                break

        if matches == 0:
            return 0.0

        # Count transpositions
        k = 0
        for i in range(len1):
            if not s1_matches[i]:
                continue
            while not s2_matches[k]:
                k += 1
            if s1[i] != s2[k]:
                transpositions += 1
            k += 1

        jaro = (matches / len1 + matches / len2 + (matches - transpositions / 2) / matches) / 3

        # Winkler modification
        prefix_len = 0
        for i in range(min(4, len1, len2)):
            if s1[i] == s2[i]:
                prefix_len += 1
            else:
                break

        return jaro + prefix_len * winkler_prefix * (1 - jaro)

    def _soundex(self, s: str) -> str:
        """Generate Soundex code for a string."""
        if not s:
            return ''

        s = s.upper()
        soundex = s[0]

        mapping = {
            'B': '1', 'F': '1', 'P': '1', 'V': '1',
            'C': '2', 'G': '2', 'J': '2', 'K': '2', 'Q': '2', 'S': '2', 'X': '2', 'Z': '2',
            'D': '3', 'T': '3',
            'L': '4',
            'M': '5', 'N': '5',
            'R': '6'
        }

        for char in s[1:]:
            code = mapping.get(char, '')
            if code and code != soundex[-1]:
                soundex += code
            if len(soundex) == 4:
                break

        return soundex.ljust(4, '0')

    def _metaphone(self, s: str) -> str:
        """Generate simplified Metaphone code."""
        if not s:
            return ''

        s = s.upper()
        result = ''

        # Simplified metaphone - just remove vowels and double letters
        prev = ''
        for char in s:
            if char not in 'AEIOU' and char != prev:
                result += char
                prev = char

        return result[:6]

    def _ngram_similarity(self, s1: str, s2: str, n: int = 2) -> float:
        """Calculate n-gram (character) similarity."""
        if len(s1) < n or len(s2) < n:
            return 0.0

        ngrams1 = set(s1[i:i+n] for i in range(len(s1) - n + 1))
        ngrams2 = set(s2[i:i+n] for i in range(len(s2) - n + 1))

        intersection = len(ngrams1 & ngrams2)
        union = len(ngrams1 | ngrams2)

        return intersection / union if union > 0 else 0.0

    def _token_set_ratio(self, s1: str, s2: str) -> float:
        """Calculate token set ratio (handles word order differences)."""
        tokens1 = set(s1.split())
        tokens2 = set(s2.split())

        if not tokens1 or not tokens2:
            return 0.0

        intersection = tokens1 & tokens2

        # Calculate ratio based on intersection vs union
        union = tokens1 | tokens2
        base_ratio = len(intersection) / len(union) if union else 0.0

        # Also check sequence match on sorted tokens
        sorted1 = ' '.join(sorted(tokens1))
        sorted2 = ' '.join(sorted(tokens2))
        seq_ratio = SequenceMatcher(None, sorted1, sorted2).ratio()

        return max(base_ratio, seq_ratio)

    def _partial_ratio(self, s1: str, s2: str) -> float:
        """Calculate best partial match ratio."""
        if len(s1) == 0 or len(s2) == 0:
            return 0.0

        # Make s1 the shorter string
        if len(s1) > len(s2):
            s1, s2 = s2, s1

        # Find best substring match
        best = 0.0
        for i in range(len(s2) - len(s1) + 1):
            substr = s2[i:i + len(s1)]
            ratio = SequenceMatcher(None, s1, substr).ratio()
            best = max(best, ratio)

        return best

    def _common_prefix_length(self, s1: str, s2: str) -> int:
        """Find length of common prefix."""
        length = 0
        for c1, c2 in zip(s1, s2):
            if c1 == c2:
                length += 1
            else:
                break
        return length

    def _common_suffix_length(self, s1: str, s2: str) -> int:
        """Find length of common suffix."""
        return self._common_prefix_length(s1[::-1], s2[::-1])
