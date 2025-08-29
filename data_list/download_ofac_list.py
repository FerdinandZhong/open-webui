#!/usr/bin/env python3
"""
Download OFAC Consolidated Sanctions List in XML format
"""

import requests
import logging
from pathlib import Path
from datetime import datetime
import hashlib
from typing import Optional

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class OFACDownloader:
    """Download and manage OFAC consolidated sanctions list"""
    
    # Direct XML download URLs from OFAC Sanctions List Service
    # SDN List - The main OFAC Specially Designated Nationals list
    SDN_XML_URL = "https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/SDN_ADVANCED.XML"
    # Alternative formats available:
    # SDN_XML_URL = "https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/sdn.xml"  # Simple format
    # SDN_CSV_URL = "https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/sdn.csv"
    
    # Consolidated list (non-SDN sanctions programs)
    CONSOLIDATED_XML_URL = "https://sanctionslistservice.ofac.treas.gov/api/publicationpreview/exports/consolidated.xml"
    
    # Default to SDN list (the main sanctions list)
    OFAC_XML_URL = SDN_XML_URL
    
    def __init__(self, data_dir: str = "data_list"):
        """Initialize the downloader
        
        Args:
            data_dir: Directory to store downloaded files
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
    def get_file_hash(self, filepath: Path) -> Optional[str]:
        """Calculate SHA256 hash of a file
        
        Args:
            filepath: Path to the file
            
        Returns:
            SHA256 hash string or None if file doesn't exist
        """
        if not filepath.exists():
            return None
            
        sha256_hash = hashlib.sha256()
        with open(filepath, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    def download_xml(self, force: bool = False) -> Path:
        """Download the OFAC consolidated list in XML format
        
        Args:
            force: Force download even if file exists
            
        Returns:
            Path to the downloaded XML file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        xml_filename = f"ofac_consolidated_{timestamp}.xml"
        xml_path = self.data_dir / xml_filename
        latest_path = self.data_dir / "ofac_consolidated_latest.xml"
        
        try:
            logger.info(f"Downloading OFAC consolidated list from {self.OFAC_XML_URL}")
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(self.OFAC_XML_URL, headers=headers, timeout=60)
            response.raise_for_status()
            
            # Check if content is actually XML
            content_type = response.headers.get('Content-Type', '')
            if 'xml' not in content_type.lower() and not response.text.strip().startswith('<?xml'):
                logger.warning(f"Response may not be XML. Content-Type: {content_type}")
                logger.info("Attempting to parse response anyway...")
            
            # Save the downloaded content
            with open(xml_path, 'wb') as f:
                f.write(response.content)
            
            file_size = xml_path.stat().st_size
            logger.info(f"Downloaded {file_size:,} bytes to {xml_path}")
            
            # Check if content has changed
            new_hash = self.get_file_hash(xml_path)
            old_hash = self.get_file_hash(latest_path) if latest_path.exists() else None
            
            if new_hash != old_hash:
                # Update the latest symlink
                if latest_path.exists():
                    latest_path.unlink()
                latest_path.symlink_to(xml_path.name)
                logger.info(f"Updated latest link to {xml_filename}")
                logger.info("New content detected - file has been updated")
            else:
                logger.info("Downloaded content is identical to the latest version")
                # Remove duplicate file
                xml_path.unlink()
                xml_path = latest_path
            
            return xml_path
            
        except requests.RequestException as e:
            logger.error(f"Failed to download OFAC list: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during download: {e}")
            raise
    
    def cleanup_old_files(self, keep_last: int = 5):
        """Remove old downloaded files, keeping the most recent ones
        
        Args:
            keep_last: Number of recent files to keep
        """
        pattern = "ofac_consolidated_*.xml"
        files = sorted(self.data_dir.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
        
        if len(files) > keep_last:
            for old_file in files[keep_last:]:
                logger.info(f"Removing old file: {old_file.name}")
                old_file.unlink()
    
    def get_latest_file(self) -> Optional[Path]:
        """Get the path to the latest downloaded file
        
        Returns:
            Path to the latest XML file or None if no files exist
        """
        latest_path = self.data_dir / "ofac_consolidated_latest.xml"
        if latest_path.exists():
            return latest_path
            
        # Fallback to finding the most recent file
        pattern = "ofac_consolidated_*.xml"
        files = sorted(self.data_dir.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
        return files[0] if files else None


def main():
    """Main function to download OFAC list"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Download OFAC sanctions lists")
    parser.add_argument(
        "--list-type",
        choices=["consolidated", "sdn"],
        default="consolidated",
        help="Which list to download (default: consolidated)"
    )
    parser.add_argument(
        "--data-dir",
        default="data_list",
        help="Directory to store downloaded files (default: data_list)"
    )
    args = parser.parse_args()
    
    downloader = OFACDownloader(data_dir=args.data_dir)
    
    # Set the URL based on list type
    if args.list_type == "sdn":
        downloader.OFAC_XML_URL = downloader.SDN_XML_URL
        logger.info("Downloading SDN list")
    else:
        logger.info("Downloading Consolidated list")
    
    try:
        # Download the latest XML file
        xml_path = downloader.download_xml()
        logger.info(f"Successfully downloaded OFAC list to: {xml_path}")
        
        # Clean up old files
        downloader.cleanup_old_files(keep_last=5)
        
        # Get latest file info
        latest = downloader.get_latest_file()
        if latest:
            size = latest.stat().st_size
            logger.info(f"Latest file: {latest.name} ({size:,} bytes)")
            
    except Exception as e:
        logger.error(f"Failed to download OFAC list: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())