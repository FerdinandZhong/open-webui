#!/usr/bin/env python3
"""
Complete pipeline to download, convert, and import OFAC sanctions data
"""

import logging
import sys
from pathlib import Path
from datetime import datetime

# Import our modules
from download_ofac_list import OFACDownloader
from sdn_xml_to_csv import SDNAdvancedXMLtoCSVConverter
from database_manager import OFACDatabaseManager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class OFACPipeline:
    """Complete pipeline for OFAC data processing"""
    
    def __init__(self, data_dir: str = "data_list"):
        """Initialize pipeline
        
        Args:
            data_dir: Directory for data files
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
    def run(self, 
            list_type: str = "consolidated",
            skip_download: bool = False,
            skip_conversion: bool = False,
            skip_import: bool = False) -> dict:
        """Run the complete pipeline
        
        Args:
            list_type: Type of list to download ("consolidated" or "sdn")
            skip_download: Skip the download step
            skip_conversion: Skip the XML to CSV conversion
            skip_import: Skip the database import
            
        Returns:
            Dictionary with pipeline results
        """
        results = {
            'status': 'SUCCESS',
            'steps': {},
            'timestamp': datetime.now().isoformat()
        }
        
        try:
            # Step 1: Download XML
            if not skip_download:
                logger.info("=== Step 1: Downloading OFAC XML data ===")
                downloader = OFACDownloader(data_dir=str(self.data_dir))
                
                if list_type == "sdn":
                    downloader.OFAC_XML_URL = downloader.SDN_XML_URL
                    
                xml_path = downloader.download_xml()
                downloader.cleanup_old_files(keep_last=3)
                
                results['steps']['download'] = {
                    'status': 'SUCCESS',
                    'file': str(xml_path),
                    'size': xml_path.stat().st_size
                }
                logger.info(f"✓ Downloaded: {xml_path}")
            else:
                logger.info("=== Step 1: Skipping download (using existing file) ===")
                xml_path = self.data_dir / "ofac_consolidated_latest.xml"
                if not xml_path.exists():
                    raise FileNotFoundError(f"XML file not found: {xml_path}")
                results['steps']['download'] = {'status': 'SKIPPED'}
            
            # Step 2: Convert XML to CSV
            if not skip_conversion:
                logger.info("=== Step 2: Converting XML to CSV ===")
                converter = SDNAdvancedXMLtoCSVConverter(str(xml_path))
                csv_path = converter.convert_to_csv(
                    output_path=str(self.data_dir / "sdn_final.csv")
                )
                
                results['steps']['conversion'] = {
                    'status': 'SUCCESS',
                    'file': str(csv_path),
                    'size': csv_path.stat().st_size
                }
                logger.info(f"✓ Converted to CSV: {csv_path}")
            else:
                logger.info("=== Step 2: Skipping conversion (using existing CSV) ===")
                csv_path = self.data_dir / "sdn_final.csv"
                if not csv_path.exists():
                    raise FileNotFoundError(f"CSV file not found: {csv_path}")
                results['steps']['conversion'] = {'status': 'SKIPPED'}
            
            # Step 3: Import to Database
            if not skip_import:
                logger.info("=== Step 3: Importing to Database ===")
                db_path = self.data_dir / "ofac_sanctions.db"
                db = OFACDatabaseManager(str(db_path))
                
                try:
                    db.connect()
                    db.create_schema()
                    import_stats = db.import_csv(str(csv_path))
                    
                    # Get database statistics
                    db_stats = db.get_statistics()
                    
                    results['steps']['import'] = {
                        'status': 'SUCCESS',
                        'database': str(db_path),
                        'import_stats': import_stats,
                        'total_records': db_stats['total_records']
                    }
                    logger.info(f"✓ Imported to database: {import_stats}")
                finally:
                    db.disconnect()
            else:
                logger.info("=== Step 3: Skipping database import ===")
                results['steps']['import'] = {'status': 'SKIPPED'}
            
            # Summary
            logger.info("\n" + "="*50)
            logger.info("=== PIPELINE COMPLETED SUCCESSFULLY ===")
            logger.info("="*50)
            
            for step_name, step_result in results['steps'].items():
                status = step_result.get('status', 'UNKNOWN')
                logger.info(f"{step_name.capitalize()}: {status}")
                
        except Exception as e:
            logger.error(f"Pipeline failed: {e}")
            results['status'] = 'FAILED'
            results['error'] = str(e)
            raise
            
        return results
    
    def update_data(self):
        """Convenient method to update all data (download, convert, import)"""
        return self.run(skip_download=False, skip_conversion=False, skip_import=False)
    
    def quick_update(self):
        """Quick update - skip download if recent file exists"""
        xml_path = self.data_dir / "ofac_consolidated_latest.xml"
        
        # Check if file exists and is recent (less than 1 day old)
        if xml_path.exists():
            age_hours = (datetime.now().timestamp() - xml_path.stat().st_mtime) / 3600
            if age_hours < 24:
                logger.info(f"Using existing XML file (age: {age_hours:.1f} hours)")
                return self.run(skip_download=True, skip_conversion=False, skip_import=False)
        
        return self.update_data()


def main():
    """Main function to run the pipeline"""
    import argparse
    
    parser = argparse.ArgumentParser(description="OFAC Data Pipeline")
    parser.add_argument(
        "--list-type",
        choices=["consolidated", "sdn"],
        default="consolidated",
        help="Type of list to process (default: consolidated)"
    )
    parser.add_argument(
        "--data-dir",
        default="data_list",
        help="Directory for data files (default: data_list)"
    )
    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="Skip download step (use existing XML)"
    )
    parser.add_argument(
        "--skip-conversion",
        action="store_true",
        help="Skip XML to CSV conversion (use existing CSV)"
    )
    parser.add_argument(
        "--skip-import",
        action="store_true",
        help="Skip database import"
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Quick update - skip download if file is recent"
    )
    
    args = parser.parse_args()
    
    try:
        pipeline = OFACPipeline(data_dir=args.data_dir)
        
        if args.quick:
            results = pipeline.quick_update()
        else:
            results = pipeline.run(
                list_type=args.list_type,
                skip_download=args.skip_download,
                skip_conversion=args.skip_conversion,
                skip_import=args.skip_import
            )
        
        return 0 if results['status'] == 'SUCCESS' else 1
        
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        return 1


if __name__ == "__main__":
    exit(main())