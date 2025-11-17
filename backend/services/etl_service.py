import logging
import time
from typing import List, Tuple
from database.supabase_client import SupabaseClient
from database.sage100_client import Sage100Client
from models.bom_models import BOMPart, SyncResult

logger = logging.getLogger(__name__)


class ETLService:
    """
    Core ETL Pipeline for BOM-ERP synchronization
    
    Key responsibilities:
    1. Extract hierarchical BOM from S1000D (Supabase)
    2. Transform data structure for ERP compatibility
    3. Validate data quality (part numbers, prices, descriptions)
    4. Load validated data into Sage 100 article master
    5. Track versions for audit trail and comparison
    """
    
    def __init__(self):
        self.source = SupabaseClient()
        self.target = Sage100Client()
        logger.info("ETL Service initialized")
    
    # ================================================================
    # EXTRACT Phase
    # ================================================================
    def extract(self) -> List[BOMPart]:
        """
        Extract BOM data from S1000D source system
        Returns flattened list of all parts
        """
        logger.info("EXTRACT: Fetching BOM from S1000D...")
        
        # Flatten hierarchical BOM for processing
        parts = self.source.flatten_bom()
        
        logger.info(f"EXTRACT: Retrieved {len(parts)} parts")
        return parts
    
    # ================================================================
    # TRANSFORM Phase (Validation)
    # ================================================================
    def validate_part(self, part: BOMPart) -> Tuple[bool, List[str]]:
        """
        Validate part data against business rules
        
        Business Rules:
        - Part number must be at least 3 characters
        - Description must be at least 5 characters
        - Unit price cannot be negative
        - Components (leaf parts) should have a supplier
        """
        errors = []
        
        # Part number validation
        if not part.part_number or len(part.part_number) < 3:
            errors.append(f"Invalid part number: '{part.part_number}'")
        
        # Description validation
        if not part.description or len(part.description) < 5:
            errors.append(f"Description too short: '{part.description}'")
        
        # Price validation
        if part.unit_price < 0:
            errors.append(f"Negative price: {part.unit_price}")
        
        # Supplier validation (only for leaf components)
        if not part.is_assembly and not part.supplier and part.unit_price > 0:
            # This is a warning, not error - component should have supplier
            logger.warning(f"Component {part.part_number} has no supplier defined")
        
        is_valid = len(errors) == 0
        return is_valid, errors
    
    def transform(self, parts: List[BOMPart]) -> Tuple[List[BOMPart], List[str]]:
        """
        Transform and validate extracted parts
        Returns valid parts and error messages
        """
        logger.info("TRANSFORM: Validating data quality...")
        
        valid_parts = []
        all_errors = []
        
        for part in parts:
            is_valid, errors = self.validate_part(part)
            
            if is_valid:
                valid_parts.append(part)
            else:
                error_msg = f"{part.part_number}: {', '.join(errors)}"
                all_errors.append(error_msg)
                logger.error(f"TRANSFORM: Validation failed - {error_msg}")
        
        logger.info(f"TRANSFORM: {len(valid_parts)} valid, {len(all_errors)} errors")
        return valid_parts, all_errors
    
    # ================================================================
    # LOAD Phase
    # ================================================================
    def load(self, parts: List[BOMPart], version: str) -> Tuple[int, int, int]:
        """
        Load validated parts into Sage 100 ERP
        Uses smart upsert: INSERT new, UPDATE existing
        
        Returns: (inserted_count, updated_count, error_count)
        """
        logger.info("LOAD: Writing to Sage 100...")
        
        inserted = 0
        updated = 0
        errors = 0
        
        for part in parts:
            try:
                if self.target.article_exists(part.part_number):
                    # Update existing article
                    success = self.target.update_article(part, version)
                    if success:
                        updated += 1
                        logger.debug(f"LOAD: Updated {part.part_number}")
                    else:
                        errors += 1
                else:
                    # Insert new article
                    success = self.target.insert_article(part, version)
                    if success:
                        inserted += 1
                        logger.debug(f"LOAD: Inserted {part.part_number}")
                    else:
                        errors += 1
            except Exception as e:
                logger.error(f"LOAD: Failed {part.part_number} - {e}")
                errors += 1
        
        logger.info(f"LOAD: Inserted={inserted}, Updated={updated}, Errors={errors}")
        return inserted, updated, errors
    
    # ================================================================
    # Main Sync Pipeline
    # ================================================================
    def run_sync(self) -> SyncResult:
        """
        Execute complete ETL pipeline
        
        Process Flow:
        1. Extract BOM from S1000D
        2. Validate data quality
        3. Load into Sage 100
        4. Log sync result for audit
        """
        logger.info("=" * 60)
        logger.info("SYNC STARTED: S1000D -> Sage 100")
        logger.info("=" * 60)
        
        start_time = time.time()
        version = f"SYNC-{int(start_time)}"
        
        try:
            # EXTRACT
            parts = self.extract()
            
            # TRANSFORM (Validate)
            valid_parts, validation_errors = self.transform(parts)
            
            # LOAD
            inserted, updated, load_errors = self.load(valid_parts, version)
            
            # Calculate duration
            duration = time.time() - start_time
            
            # Create result
            result = SyncResult(
                version=version,
                total_parts=len(parts),
                inserted=inserted,
                updated=updated,
                errors=len(validation_errors) + load_errors,
                error_messages=validation_errors,
                duration_seconds=duration,
                status="completed" if load_errors == 0 else "completed_with_errors"
            )
            
            # Log to database
            self.target.log_sync_result(result)
            
            logger.info("=" * 60)
            logger.info(f"SYNC COMPLETED")
            logger.info(f"Total: {result.total_parts} | Inserted: {inserted} | Updated: {updated}")
            logger.info(f"Duration: {duration:.3f}s")
            logger.info("=" * 60)
            
            return result
            
        except Exception as e:
            logger.error(f"SYNC FAILED: {e}", exc_info=True)
            duration = time.time() - start_time
            
            return SyncResult(
                version="ERROR",
                total_parts=0,
                errors=1,
                error_messages=[str(e)],
                duration_seconds=duration,
                status="failed"
            )
    
    # ================================================================
    # Data Access Methods
    # ================================================================
    def get_source_bom_tree(self):
        """Get hierarchical BOM tree from S1000D"""
        return self.source.build_bom_tree()
    
    def get_target_articles(self):
        """Get all articles from Sage 100"""
        return self.target.get_all_articles()
    
    def get_bom_statistics(self):
        """Get BOM statistics from source system"""
        return self.source.get_bom_statistics()
    
    def get_sync_history(self, limit=10):
        """Get recent sync operations"""
        return self.target.get_sync_history(limit)
    
    def clear_target_database(self):
        """Clear Sage 100 articles (for testing)"""
        self.target.clear_articles()
        logger.info("Target database cleared")