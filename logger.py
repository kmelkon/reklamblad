"""Logging utilities for scrapers.

Provides consistent logging across all scraper scripts with
proper formatting and error handling.
"""

import logging
import sys
from typing import Optional


class ScraperLogger:
    """Centralized logger for scraper operations."""
    
    def __init__(self, name: str, level: int = logging.INFO):
        """Initialize logger.
        
        Args:
            name: Logger name (usually __name__)
            level: Logging level (default: INFO)
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        
        # Prevent duplicate handlers
        if not self.logger.handlers:
            # Console handler
            handler = logging.StreamHandler(sys.stdout)
            handler.setLevel(level)
            
            # Format: [2024-02-07 10:30:45] INFO: Message
            formatter = logging.Formatter(
                '[%(asctime)s] %(levelname)s: %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
    
    def info(self, message: str):
        """Log info message."""
        self.logger.info(message)
    
    def warning(self, message: str):
        """Log warning message."""
        self.logger.warning(message)
    
    def error(self, message: str, exc_info: bool = False):
        """Log error message.
        
        Args:
            message: Error message
            exc_info: Include exception traceback
        """
        self.logger.error(message, exc_info=exc_info)
    
    def debug(self, message: str):
        """Log debug message."""
        self.logger.debug(message)
    
    def section(self, title: str, char: str = '=', width: int = 60):
        """Log section divider.
        
        Args:
            title: Section title
            char: Character to use for divider
            width: Width of divider
        """
        divider = char * width
        self.logger.info(divider)
        self.logger.info(title)
        self.logger.info(divider)
    
    def success(self, message: str):
        """Log success message with checkmark."""
        self.logger.info(f"✓ {message}")
    
    def failure(self, message: str):
        """Log failure message with X."""
        self.logger.error(f"✗ {message}")
    
    def store_header(self, store_name: str):
        """Log store scraping header.
        
        Args:
            store_name: Name of the store being scraped
        """
        self.logger.info("")
        self.logger.info(f"=== Scraping {store_name} ===")
    
    def product_count(self, count: int, method: str = ""):
        """Log product count.
        
        Args:
            count: Number of products found
            method: Method used to find products
        """
        method_str = f" via {method}" if method else ""
        self.logger.info(f"  Found {count} products{method_str}")
    
    def summary(self, stats: dict):
        """Log scraping summary.
        
        Args:
            stats: Dictionary with statistics
        """
        self.section("SCRAPING SUMMARY")
        for key, value in stats.items():
            self.logger.info(f"  {key}: {value}")


class ErrorTracker:
    """Track and report errors during scraping."""
    
    def __init__(self):
        """Initialize error tracker."""
        self.errors = []
        self.warnings = []
        self.failed_stores = []
    
    def add_error(self, store: str, error: str, exception: Optional[Exception] = None):
        """Add an error.
        
        Args:
            store: Store name where error occurred
            error: Error description
            exception: Optional exception object
        """
        self.errors.append({
            'store': store,
            'error': error,
            'exception': str(exception) if exception else None
        })
        self.failed_stores.append(store)
    
    def add_warning(self, store: str, warning: str):
        """Add a warning.
        
        Args:
            store: Store name
            warning: Warning message
        """
        self.warnings.append({
            'store': store,
            'warning': warning
        })
    
    def has_errors(self) -> bool:
        """Check if any errors were recorded."""
        return len(self.errors) > 0
    
    def has_warnings(self) -> bool:
        """Check if any warnings were recorded."""
        return len(self.warnings) > 0
    
    def get_failed_stores(self) -> list[str]:
        """Get list of stores that failed."""
        return list(set(self.failed_stores))
    
    def print_summary(self, logger: ScraperLogger):
        """Print error and warning summary.
        
        Args:
            logger: Logger instance to use
        """
        if self.has_errors():
            logger.section("ERRORS")
            for error in self.errors:
                logger.error(f"  [{error['store']}] {error['error']}")
                if error['exception']:
                    logger.debug(f"    Exception: {error['exception']}")
        
        if self.has_warnings():
            logger.section("WARNINGS")
            for warning in self.warnings:
                logger.warning(f"  [{warning['store']}] {warning['warning']}")
    
    def get_stats(self) -> dict:
        """Get error/warning statistics.
        
        Returns:
            Dictionary with error and warning counts
        """
        return {
            'errors': len(self.errors),
            'warnings': len(self.warnings),
            'failed_stores': len(self.get_failed_stores())
        }


def create_logger(name: str, debug: bool = False) -> ScraperLogger:
    """Create a configured logger.
    
    Args:
        name: Logger name
        debug: Enable debug logging
        
    Returns:
        Configured ScraperLogger instance
    """
    level = logging.DEBUG if debug else logging.INFO
    return ScraperLogger(name, level)
