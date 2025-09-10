import csv
import re
from typing import List, Optional
from pathlib import Path

from ..models.sdn import SDNEntry


class SDNDataLoader:
    """Handles loading and parsing of SDN CSV data."""
    
    def __init__(self, sdn_file_path: str):
        self.sdn_file_path = Path(sdn_file_path)
        if not self.sdn_file_path.exists():
            raise FileNotFoundError(f"SDN file not found: {sdn_file_path}")
    
    def load_entries(self) -> List[SDNEntry]:
        """Load and parse all SDN entries from CSV file."""
        from ..utils.logger import setup_logger
        logger = setup_logger(__name__)
        
        entries = []
        row_count = 0
        
        with open(self.sdn_file_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row_idx, row in enumerate(reader):
                row_count += 1
                logger.info(f"DEBUG: Row {row_idx}: {len(row)} columns - {row[:3] if row else 'empty'}")
                
                if row_idx == 0:  # Skip header
                    continue
                    
                if len(row) >= 3:  # Adjust for our CSV format: uid, name, details
                    try:
                        # Parse the details field to extract type and aliases
                        details = row[2] if len(row) > 2 else ""
                        entry_type = ""
                        aliases = []
                        
                        if "Type:" in details:
                            type_match = re.search(r'Type:\s*([^|]+)', details)
                            if type_match:
                                entry_type = type_match.group(1).strip()
                        
                        if "Aliases:" in details:
                            alias_match = re.search(r'Aliases:\s*(.+)', details)
                            if alias_match:
                                aliases = [alias.strip() for alias in alias_match.group(1).split(';')]
                        
                        entry_dict = {
                            'id': row[0],
                            'name': row[1].strip(),
                            'type': entry_type,
                            'program': 'SDN',  # Default program
                            'title': '',
                            'remarks': details,
                            'dob': None,
                            'nationality': None,
                            'pob': None,
                            'aliases': aliases
                        }
                        
                        entries.append(SDNEntry(**entry_dict))
                        logger.debug(f"DEBUG: Created entry for {entry_dict['name']}")
                    except Exception as e:
                        logger.error(f"DEBUG: Error creating entry from row {row_idx}: {e}")
                else:
                    logger.warning(f"DEBUG: Skipping row {row_idx} - only {len(row)} columns")
                    
                if row_idx >= 10:  # Limit debug output
                    break
        
        logger.info(f"DEBUG: Processed {row_count} rows, created {len(entries)} entries")
        return entries
    
    @staticmethod
    def _extract_dob(remarks: str) -> Optional[str]:
        """Extract date of birth from remarks."""
        dob_match = re.search(r'DOB\s+([^;]+)', remarks)
        if dob_match:
            return dob_match.group(1).strip()
        return None
    
    @staticmethod
    def _extract_nationality(remarks: str) -> Optional[str]:
        """Extract nationality from remarks."""
        nat_match = re.search(r'nationality\s+([^;]+)', remarks, re.IGNORECASE)
        if nat_match:
            return nat_match.group(1).strip()
        return None
    
    @staticmethod
    def _extract_pob(remarks: str) -> Optional[str]:
        """Extract place of birth from remarks."""
        pob_match = re.search(r'POB\s+([^;]+)', remarks)
        if pob_match:
            return pob_match.group(1).strip()
        return None
    
    @staticmethod
    def _extract_aliases(remarks: str) -> List[str]:
        """Extract aliases from remarks."""
        aliases = []
        aka_matches = re.findall(r"a\.k\.a\.\s+'([^']+)'", remarks)
        aliases.extend(aka_matches)
        alt_matches = re.findall(r"alt\.\s+([^;]+)", remarks)
        aliases.extend(alt_matches)
        return aliases