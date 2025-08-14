# logging_setup.py - Modular Spider Logging System
import logging
from logging.handlers import RotatingFileHandler
import os
import json
from datetime import datetime
from pathlib import Path
from colorama import init, Fore, Style
from typing import Dict, List, Optional, Any

# Initialize colorama for Windows color support
init()

class ColorConsole:
    """Handles color-coded terminal output"""
    
    @staticmethod
    def success_message(message: str) -> str:
        return f"{Fore.GREEN}✓ {message}{Style.RESET_ALL}"
    
    @staticmethod
    def error_message(message: str) -> str:
        return f"{Fore.RED}✗ {message}{Style.RESET_ALL}"
    
    @staticmethod
    def warning_message(message: str) -> str:
        return f"{Fore.YELLOW}⚠️ {message}{Style.RESET_ALL}"
    
    @staticmethod
    def info_message(message: str) -> str:
        return f"{Fore.BLUE}ℹ️ {message}{Style.RESET_ALL}"
    
    @staticmethod
    def progress_message(message: str) -> str:
        return f"{Fore.CYAN}📊 {message}{Style.RESET_ALL}"
    
    @staticmethod
    def header_message(message: str) -> str:
        return f"{Fore.CYAN}{'='*60}\n{Fore.CYAN}{message}\n{Fore.CYAN}{'='*60}{Style.RESET_ALL}"

class ProgressTracker:
    """Tracks and reports progress metrics"""
    
    def __init__(self, target_pages: int):
        self.target_pages = target_pages
        self.pages_completed = 0
        self.grants_found = 0
        self.grants_successful = 0
        self.grants_failed = 0
        self.start_time = datetime.now()
    
    def track_page_completed(self) -> None:
        """Track a completed page"""
        self.pages_completed += 1
    
    def track_grants_found(self, count: int) -> None:
        """Track grants found on a page"""
        self.grants_found += count
    
    def track_successful_extraction(self) -> None:
        """Track successful grant extraction"""
        self.grants_successful += 1
    
    def track_failed_extraction(self) -> None:
        """Track failed grant extraction"""
        self.grants_failed += 1
    
    def get_progress_percentage(self) -> float:
        """Get completion percentage"""
        return (self.pages_completed / self.target_pages) * 100 if self.target_pages > 0 else 0
    
    def get_current_stats(self) -> Dict[str, Any]:
        """Get current progress statistics"""
        return {
            "pages_completed": self.pages_completed,
            "target_pages": self.target_pages,
            "progress_percentage": self.get_progress_percentage(),
            "grants_found": self.grants_found,
            "grants_successful": self.grants_successful,
            "grants_failed": self.grants_failed,
            "elapsed_time": str(datetime.now() - self.start_time)
        }
    
    def get_final_summary(self) -> Dict[str, Any]:
        """Get final summary statistics"""
        total_time = datetime.now() - self.start_time
        return {
            "total_pages_completed": self.pages_completed,
            "target_pages": self.target_pages,
            "total_grants_found": self.grants_found,
            "total_grants_successful": self.grants_successful,
            "total_grants_failed": self.grants_failed,
            "success_rate": (self.grants_successful / self.grants_found * 100) if self.grants_found > 0 else 0,
            "total_time": str(total_time),
            "completion_time": datetime.now().isoformat()
        }

class FailedURLTracker:
    """Manages failed URL tracking and analysis"""
    
    def __init__(self, log_folder: Path):
        self.log_folder = log_folder
        self.failed_urls: List[Dict[str, Any]] = []
        self.failed_urls_file = log_folder / "failed_urls.json"
    
    def record_failed_url(self, url: str, error: str, page_number: int) -> None:
        """Record a failed URL"""
        failed_entry = {
            "url": url,
            "error": error,
            "page_number": page_number,
            "timestamp": datetime.now().isoformat()
        }
        self.failed_urls.append(failed_entry)
        self._save_failed_urls_to_file()
    
    def _save_failed_urls_to_file(self) -> None:
        """Save failed URLs to JSON file"""
        data = {
            "failed_urls": self.failed_urls,
            "total_failed": len(self.failed_urls),
            "last_updated": datetime.now().isoformat()
        }
        with open(self.failed_urls_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def get_failure_analysis(self) -> Dict[str, Any]:
        """Get analysis of failures"""
        if not self.failed_urls:
            return {"total_failed": 0, "error_types": {}}
        
        error_types = {}
        for entry in self.failed_urls:
            error_type = entry["error"].split(":")[0] if ":" in entry["error"] else "Unknown"
            error_types[error_type] = error_types.get(error_type, 0) + 1
        
        return {
            "total_failed": len(self.failed_urls),
            "error_types": error_types,
            "failed_urls_file": str(self.failed_urls_file)
        }

class SpiderLogger:
    """Main logger class for spider operations"""
    
    def __init__(self, spider_name: str, target_pages: int, log_level: int = logging.INFO):
        self.spider_name = spider_name
        self.target_pages = target_pages
        self.log_level = log_level
        
        # Create log folder
        self.log_folder = self._create_log_folder()
        
        # Initialize components
        self.logger = self._setup_logger()
        self.progress_tracker = ProgressTracker(target_pages)
        self.failed_tracker = FailedURLTracker(self.log_folder)
        self.console = ColorConsole()
        
        # Log startup
        self._log_startup()
    
    def _create_log_folder(self) -> Path:
        """Create per-run log folder with timestamp"""
        logs_dir = Path("logs")
        logs_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_folder = logs_dir / f"run_{timestamp}"
        log_folder.mkdir(exist_ok=True)
        
        return log_folder
    
    def _setup_logger(self) -> logging.Logger:
        """Setup the main logger"""
        logger = logging.getLogger(self.spider_name)
        logger.setLevel(self.log_level)
        
        # Prevent duplicate handlers
        if logger.hasHandlers():
            return logger
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        
        # File handler (rotating)
        log_file = self.log_folder / "spider.log"
        file_handler = RotatingFileHandler(
            log_file, 
            maxBytes=2 * 1024 * 1024,  # 2MB
            backupCount=5
        )
        file_handler.setFormatter(formatter)
        
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)
        
        return logger
    
    def _log_startup(self) -> None:
        """Log spider startup information"""
        startup_msg = self.console.header_message(
            f"🚀 Starting {self.spider_name}\n"
            f"📊 Target: {self.target_pages} pages\n"
            f"📁 Log folder: {self.log_folder}"
        )
        print(startup_msg)
        
        self.logger.info(f"Spider started - Target pages: {self.target_pages}")
        self.logger.info(f"Log folder: {self.log_folder}")
    
    def log_page_progress(self, page_number: int, grants_found: int, grants_failed: int = 0) -> None:
        """Log page progress"""
        self.progress_tracker.track_page_completed()
        self.progress_tracker.track_grants_found(grants_found)
        
        progress_stats = self.progress_tracker.get_current_stats()
        
        # Console output
        progress_msg = self.console.progress_message(
            f"Page {page_number}/{self.target_pages} - "
            f"Found {grants_found} grants, {grants_failed} failed - "
            f"Progress: {progress_stats['progress_percentage']:.1f}%"
        )
        print(progress_msg)
        
        # File logging
        self.logger.info(f"PAGE_PROGRESS - Page {page_number}/{self.target_pages} - "
                        f"Grants found: {grants_found}, Failed: {grants_failed}")
    
    def log_grant_success(self, title: str, url: str, page_number: int) -> None:
        """Log successful grant extraction"""
        self.progress_tracker.track_successful_extraction()
        
        # Console output (brief)
        success_msg = self.console.success_message(f"Successfully extracted: {title[:50]}...")
        print(success_msg)
        
        # File logging (detailed)
        self.logger.info(f"SUCCESS - Page {page_number} - {url} - {title}")
    
    def log_grant_failure(self, url: str, error: str, page_number: int) -> None:
        """Log failed grant extraction"""
        self.progress_tracker.track_failed_extraction()
        self.failed_tracker.record_failed_url(url, error, page_number)
        
        # Console output
        error_msg = self.console.error_message(f"Failed: {url} - {error}")
        print(error_msg)
        
        # File logging
        self.logger.error(f"FAILURE - Page {page_number} - {url} - {error}")
    
    def log_final_summary(self) -> None:
        """Log final summary when spider completes"""
        summary = self.progress_tracker.get_final_summary()
        failure_analysis = self.failed_tracker.get_failure_analysis()
        
        # Console output
        summary_msg = self.console.header_message("📊 SPIDER COMPLETED - FINAL SUMMARY")
        print(summary_msg)
        
        print(self.console.success_message(f"Total grants found: {summary['total_grants_found']}"))
        print(self.console.success_message(f"Successfully extracted: {summary['total_grants_successful']}"))
        print(self.console.error_message(f"Failed extractions: {summary['total_grants_failed']}"))
        print(self.console.info_message(f"Success rate: {summary['success_rate']:.1f}%"))
        print(self.console.info_message(f"Total time: {summary['total_time']}"))
        print(self.console.info_message(f"Log folder: {self.log_folder}"))
        
        if failure_analysis['total_failed'] > 0:
            print(self.console.warning_message(f"Failed URLs saved to: {failure_analysis['failed_urls_file']}"))
        
        print(self.console.header_message(""))
        
        # File logging
        self.logger.info(f"SPIDER_COMPLETED - {json.dumps(summary, indent=2)}")
        
        # Save summary to file
        summary_file = self.log_folder / "summary.json"
        with open(summary_file, 'w') as f:
            json.dump({
                "spider_summary": summary,
                "failure_analysis": failure_analysis,
                "log_folder": str(self.log_folder)
            }, f, indent=2)
    
    def get_progress_tracker(self) -> ProgressTracker:
        """Get the progress tracker instance"""
        return self.progress_tracker
    
    def get_failed_tracker(self) -> FailedURLTracker:
        """Get the failed URL tracker instance"""
        return self.failed_tracker

# Legacy function for backward compatibility
def setup_logger(name: str, log_file: str = "app.log", level=logging.INFO) -> logging.Logger:
    """Creates and returns a logger with a rotating file handler and console output."""
    logger = logging.getLogger(name)
    logger.setLevel(level)

    if logger.hasHandlers():
        return logger  # Prevent duplicate handlers if already set

    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    # Rotating file handler
    file_handler = RotatingFileHandler(log_file, maxBytes=2 * 1024 * 1024, backupCount=5)
    file_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger