#!/usr/bin/env python3
"""
Convert OFAC SDN_ADVANCED XML data to CSV format
"""

import xml.etree.ElementTree as ET
from pathlib import Path
import csv
import logging
import json
from typing import Dict, List, Any, Optional
from collections import defaultdict

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SDNAdvancedXMLtoCSVConverter:
    """Convert OFAC SDN Advanced XML format to CSV"""
    
    # XML namespace
    NS = {'ns': 'https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/ADVANCED_XML'}
    
    def __init__(self, xml_path: str):
        """Initialize converter with XML file path
        
        Args:
            xml_path: Path to the XML file to convert
        """
        self.xml_path = Path(xml_path)
        if not self.xml_path.exists():
            raise FileNotFoundError(f"XML file not found: {xml_path}")
        
        # Lookup tables for reference data
        self.countries = {}
        self.party_sub_types = {}
        self.party_types = {}  # Add party types lookup
        self.feature_types = {}
        self.sanctions_programs = {}
        
    def parse_reference_data(self, root):
        """Parse reference data sections (countries, types, etc.)
        
        Args:
            root: XML root element
        """
        # Parse countries/areas
        area_codes = root.find('.//ns:AreaCodeValues', self.NS)
        if area_codes is not None:
            for area in area_codes.findall('ns:AreaCode', self.NS):
                country_id = area.get('ID')
                description = area.get('Description', '')
                code = area.text if area.text else ''
                self.countries[country_id] = {
                    'description': description,
                    'code': code
                }
        
        # Parse party subtypes (Individual, Entity, Vessel, Aircraft)
        party_sub_types = root.find('.//ns:PartySubTypeValues', self.NS)
        if party_sub_types is not None:
            for pst in party_sub_types.findall('ns:PartySubType', self.NS):
                subtype_id = pst.get('ID')
                party_type_id = pst.get('PartyTypeID')
                self.party_sub_types[subtype_id] = {
                    'name': pst.text if pst.text else '',
                    'party_type_id': party_type_id
                }
        
        # Parse party types (Individual, Entity, etc.)
        party_types = root.find('.//ns:PartyTypeValues', self.NS)
        if party_types is not None:
            for pt in party_types.findall('ns:PartyType', self.NS):
                type_id = pt.get('ID')
                self.party_types[type_id] = pt.text if pt.text else ''
        
        # Parse feature types (dates of birth, nationalities, etc.)
        feature_types = root.find('.//ns:FeatureTypeValues', self.NS)
        if feature_types is not None:
            for ft in feature_types.findall('ns:FeatureType', self.NS):
                type_id = ft.get('ID')
                self.feature_types[type_id] = ft.text if ft.text else ''
        
        # Debug: Print some parsed reference data to verify parsing
        logger.info(f"Parsed {len(self.feature_types)} feature types")
        logger.info(f"Parsed {len(self.party_types)} party types")
        logger.info(f"Parsed {len(self.party_sub_types)} party subtypes")
        if '8' in self.feature_types:
            logger.info(f"Feature type 8: {self.feature_types['8']}")
        if '1' in self.party_types:
            logger.info(f"Party type 1: {self.party_types['1']}")
        if '4' in self.party_sub_types:
            subtype_info = self.party_sub_types['4']
            logger.info(f"Party subtype 4: {subtype_info['name']} -> PartyType {subtype_info['party_type_id']}")
        
        # Parse sanctions programs  
        sanctions_programs = root.find('.//ns:SanctionsProgramValues', self.NS)
        if sanctions_programs is not None:
            for sp in sanctions_programs.findall('ns:SanctionsProgram', self.NS):
                program_id = sp.get('ID')
                self.sanctions_programs[program_id] = sp.text if sp.text else ''
    
    def extract_names(self, identity_elem) -> Dict[str, Any]:
        """Extract names from an Identity element
        
        Args:
            identity_elem: Identity XML element
            
        Returns:
            Dictionary with primary and alias names
        """
        names = {
            'primary_name': '',
            'aliases': []
        }
        
        # Process each alias
        for alias in identity_elem.findall('.//ns:Alias', self.NS):
            is_primary = alias.get('Primary', 'false') == 'true'
            
            # Get all name parts
            name_parts = []
            for doc_name in alias.findall('.//ns:DocumentedName', self.NS):
                for name_part in doc_name.findall('.//ns:NamePartValue', self.NS):
                    if name_part.text:
                        name_parts.append(name_part.text)
            
            full_name = ' '.join(name_parts)
            
            if is_primary:
                names['primary_name'] = full_name
            elif full_name:
                names['aliases'].append(full_name)
        
        return names
    
    def extract_all_details(self, profile_elem) -> List[str]:
        """Extract ALL details from a Profile element as strings
        
        Args:
            profile_elem: Profile XML element
            
        Returns:
            List of detail strings
        """
        details = []
        
        # Extract all features with their types and values
        for feature in profile_elem.findall('.//ns:Feature', self.NS):
            feature_type_id = feature.get('FeatureTypeID')
            feature_type = self.feature_types.get(feature_type_id, f'Feature_{feature_type_id}')
            
            # Get all feature versions
            for version in feature.findall('.//ns:FeatureVersion', self.NS):
                values = []
                
                # Extract from DatePeriod (dates)
                date_period = version.find('.//ns:DatePeriod', self.NS)
                if date_period is not None:
                    # Get year/month/day
                    year = date_period.find('.//ns:Year', self.NS)
                    month = date_period.find('.//ns:Month', self.NS)
                    day = date_period.find('.//ns:Day', self.NS)
                    
                    date_parts = []
                    if day is not None and day.text:
                        date_parts.append(day.text)
                    if month is not None and month.text:
                        date_parts.append(month.text)
                    if year is not None and year.text:
                        date_parts.append(year.text)
                    
                    if date_parts:
                        values.append('/'.join(date_parts))
                
                # Extract from VersionLocation (countries, etc.)
                version_location = version.find('.//ns:VersionLocation', self.NS)
                if version_location is not None:
                    location_id = version_location.get('LocationID')
                    if location_id and location_id in self.countries:
                        values.append(self.countries[location_id]['description'])
                
                # Extract from Comment
                comment = version.find('.//ns:Comment', self.NS)
                if comment is not None and comment.text:
                    values.append(comment.text)
                
                # Extract any text content from the version
                if version.text and version.text.strip():
                    values.append(version.text.strip())
                
                # Add to details if we found values
                for value in values:
                    if value:
                        details.append(f"{feature_type}: {value}")
        
        # Extract sanctions programs
        for entry in profile_elem.findall('.//ns:SanctionsEntry', self.NS):
            program_id = entry.get('SanctionsProgramID')
            if program_id and program_id in self.sanctions_programs:
                details.append(f"Sanctions Program: {self.sanctions_programs[program_id]}")
        
        # Extract addresses
        for location in profile_elem.findall('.//ns:Location', self.NS):
            address_parts = []
            
            # Extract all location parts
            for part in location.findall('.//ns:LocationPart', self.NS):
                for value_elem in part.findall('.//ns:LocationPartValue', self.NS):
                    if value_elem.text:
                        address_parts.append(value_elem.text)
            
            # Get country if available
            country_id = location.get('LocationCountryID')
            if country_id and country_id in self.countries:
                address_parts.append(self.countries[country_id]['description'])
            
            if address_parts:
                details.append(f"Address: {', '.join(address_parts)}")
        
        return details
    
    def extract_sanctions_entries(self, profile_elem) -> List[str]:
        """Extract sanctions program entries
        
        Args:
            profile_elem: Profile XML element
            
        Returns:
            List of sanctions programs
        """
        programs = []
        
        for entry in profile_elem.findall('.//ns:SanctionsEntry', self.NS):
            program_id = entry.get('SanctionsProgramID')
            if program_id in self.sanctions_programs:
                programs.append(self.sanctions_programs[program_id])
        
        return programs
    
    def extract_addresses(self, profile_elem) -> List[str]:
        """Extract addresses from a Profile element
        
        Args:
            profile_elem: Profile XML element
            
        Returns:
            List of address strings
        """
        addresses = []
        
        for location in profile_elem.findall('.//ns:Location', self.NS):
            parts = []
            
            # Extract location parts
            for part in location.findall('.//ns:LocationPart', self.NS):
                value = part.find('.//ns:LocationPartValue', self.NS)
                if value is not None and value.text:
                    parts.append(value.text)
            
            # Get country if available
            country_id = location.get('LocationCountryID')
            if country_id and country_id in self.countries:
                parts.append(self.countries[country_id]['description'])
            
            if parts:
                addresses.append(', '.join(parts))
        
        return addresses
    
    def parse_distinct_party(self, party_elem) -> Dict[str, Any]:
        """Parse a single DistinctParty element
        
        Args:
            party_elem: DistinctParty XML element
            
        Returns:
            Dictionary with party data
        """
        party_data = {
            'fixed_ref': party_elem.get('FixedRef', ''),
            'party_type': '',
            'primary_name': '',
            'aliases': [],
            'all_details': []
        }
        
        # Get comment (remarks)
        comment = party_elem.find('.//ns:Comment', self.NS)
        if comment is not None and comment.text:
            party_data['all_details'].append(f"Remarks: {comment.text}")
        
        # Process profile
        profile = party_elem.find('.//ns:Profile', self.NS)
        if profile is not None:
            # Get party type - look up the actual PartyType through PartySubType
            party_sub_type_id = profile.get('PartySubTypeID')
            if party_sub_type_id and party_sub_type_id in self.party_sub_types:
                subtype_info = self.party_sub_types[party_sub_type_id]
                party_type_id = subtype_info['party_type_id']
                if party_type_id in self.party_types:
                    party_data['party_type'] = self.party_types[party_type_id]
                    party_data['all_details'].append(f"Type: {party_data['party_type']}")
                else:
                    # Fallback to subtype name if party type not found
                    party_data['party_type'] = subtype_info['name']
                    if party_data['party_type']:
                        party_data['all_details'].append(f"Type: {party_data['party_type']}")
            
            # Extract identities (names)
            for identity in profile.findall('.//ns:Identity', self.NS):
                names = self.extract_names(identity)
                if not party_data['primary_name']:
                    party_data['primary_name'] = names['primary_name']
                party_data['aliases'].extend(names['aliases'])
            
            # Add aliases to details
            if party_data['aliases']:
                aliases_str = '; '.join(party_data['aliases'])
                party_data['all_details'].append(f"Aliases: {aliases_str}")
            
            # Extract ALL other details
            all_other_details = self.extract_all_details(profile)
            party_data['all_details'].extend(all_other_details)
        
        return party_data
    
    def convert_to_csv(self, output_path: str = None) -> Path:
        """Convert XML to CSV format
        
        Args:
            output_path: Path for output CSV file
            
        Returns:
            Path to the created CSV file
        """
        if output_path is None:
            output_path = self.xml_path.with_suffix('.csv')
        else:
            output_path = Path(output_path)
        
        logger.info(f"Converting SDN Advanced XML to CSV: {self.xml_path} -> {output_path}")
        
        # Parse XML
        logger.info("Parsing XML file (this may take a moment for large files)...")
        tree = ET.parse(self.xml_path)
        root = tree.getroot()
        
        # Parse reference data first
        logger.info("Parsing reference data...")
        self.parse_reference_data(root)
        
        # Find all DistinctParty elements
        parties = root.findall('.//ns:DistinctParty', self.NS)
        logger.info(f"Found {len(parties)} entities to convert")
        
        if not parties:
            logger.warning("No entities found in XML file")
            return output_path
        
        # Convert parties to rows
        rows = []
        for i, party in enumerate(parties):
            if i % 1000 == 0:
                logger.info(f"Processing entity {i}/{len(parties)}...")
            
            try:
                party_data = self.parse_distinct_party(party)
                
                # Create simplified CSV row with comprehensive details
                name = party_data['primary_name']
                details = ' | '.join(party_data['all_details'])
                
                row = {
                    'uid': party_data['fixed_ref'],
                    'name': name,
                    'details': details
                }
                rows.append(row)
                
            except Exception as e:
                logger.error(f"Error processing party {i}: {e}")
                continue
        
        # Write to CSV
        if rows:
            fieldnames = rows[0].keys()
            
            with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)
            
            logger.info(f"Successfully converted {len(rows)} entities to CSV")
            logger.info(f"CSV file saved to: {output_path}")
        else:
            logger.error("No rows to write to CSV")
        
        return output_path


def main():
    """Main function to convert SDN Advanced XML to CSV"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Convert OFAC SDN Advanced XML to CSV")
    parser.add_argument(
        "xml_file",
        nargs="?",
        default="data_list/ofac_consolidated_latest.xml",
        help="Path to XML file (default: data_list/ofac_consolidated_latest.xml)"
    )
    parser.add_argument(
        "--output",
        default="data_list/sdn.csv",
        help="Output CSV file path (default: data_list/sdn.csv)"
    )
    args = parser.parse_args()
    
    try:
        converter = SDNAdvancedXMLtoCSVConverter(args.xml_file)
        csv_path = converter.convert_to_csv(args.output)
        
        # Display file info
        csv_size = csv_path.stat().st_size
        logger.info(f"CSV file size: {csv_size:,} bytes")
        
        # Show sample of the CSV
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            sample_row = next(reader, None)
            if sample_row:
                logger.info("Sample CSV columns:")
                for key in sample_row.keys():
                    logger.info(f"  - {key}")
        
        return 0
        
    except Exception as e:
        logger.error(f"Failed to convert XML to CSV: {e}")
        return 1


if __name__ == "__main__":
    exit(main())