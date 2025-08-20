# # logging_setup.py - Modular Spider Logging System

# import logging
# from logging.handlers import RotatingFileHandler
# import os
# import json
# from datetime import datetime
# from pathlib import Path
# from colorama import init, Fore, Style
# from typing import Dict, List, Optional, Any, Union

# # Initialize colorama for Windows color support
# init()

# class ColorConsole:
#     @staticmethod
#     def success_message(message: str) -> str:
#         return f"{Fore.GREEN}✓ {message}{Style.RESET_ALL}"

#     @staticmethod
#     def error_message(message: str) -> str:
#         return f"{Fore.RED}✗ {message}{Style.RESET_ALL}"

#     @staticmethod
#     def warning_message(message: str) -> str:
#         return f"{Fore.YELLOW}⚠️ {message}{Style.RESET_ALL}"

#     @staticmethod
#     def info_message(message: str) -> str:
#         return f"{Fore.BLUE}ℹ️ {message}{Style.RESET_ALL}"

#     @staticmethod
#     def progress_message(message: str) -> str:
#         return f"{Fore.CYAN}📊 {message}{Style.RESET_ALL}"

#     @staticmethod
#     def header_message(message: str) -> str:
#         return f"{Fore.CYAN}{'='*60}\n{message}\n{'='*60}{Style.RESET_ALL}"

# class ProgressTracker:
#     def __init__(self, target_pages: Union[int, str]):
#         self.target_pages = target_pages
#         self.pages_completed = 0
#         self.grants_found = 0
#         self.grants_successful = 0
#         self.grants_failed = 0
#         self.start_time = datetime.now()

#     def track_page_completed(self): self.pages_completed += 1
#     def track_grants_found(self, count: int): self.grants_found += count
#     def track_successful_extraction(self): self.grants_successful += 1
#     def track_failed_extraction(self): self.grants_failed += 1

#     def get_progress_percentage(self): 
#         if isinstance(self.target_pages, int) and self.target_pages > 0:
#             return (self.pages_completed / self.target_pages) * 100
#         return 0

#     def get_current_stats(self) -> Dict[str, Any]:
#         return {
#             "pages_completed": self.pages_completed,
#             "target_pages": self.target_pages,
#             "progress_percentage": self.get_progress_percentage(),
#             "grants_found": self.grants_found,
#             "grants_successful": self.grants_successful,
#             "grants_failed": self.grants_failed,
#             "elapsed_time": str(datetime.now() - self.start_time)
#         }

#     def get_final_summary(self) -> Dict[str, Any]:
#         total_time = datetime.now() - self.start_time
#         return {
#             "total_pages_completed": self.pages_completed,
#             "target_pages": self.target_pages,
#             "total_grants_found": self.grants_found,
#             "total_grants_successful": self.grants_successful,
#             "total_grants_failed": self.grants_failed,
#             "success_rate": (self.grants_successful / self.grants_found * 100) if self.grants_found else 0,
#             "total_time": str(total_time),
#             "completion_time": datetime.now().isoformat()
#         }

# class FailedURLTracker:
#     def __init__(self, log_folder: Path):
#         self.log_folder = log_folder
#         self.failed_urls: List[Dict[str, Any]] = []
#         self.failed_urls_file = log_folder / "failed_urls.json"

#     def record_failed_url(self, url: str, error: str, page_number: Union[int, str]):
#         failed_entry = {
#             "url": url,
#             "error": error,
#             "page_number": page_number,
#             "timestamp": datetime.now().isoformat()
#         }
#         self.failed_urls.append(failed_entry)
#         self._save_failed_urls_to_file()

#     def _save_failed_urls_to_file(self):
#         data = {
#             "failed_urls": self.failed_urls,
#             "total_failed": len(self.failed_urls),
#             "last_updated": datetime.now().isoformat()
#         }
#         with open(self.failed_urls_file, 'w', encoding='utf-8') as f:
#             json.dump(data, f, indent=2, ensure_ascii=False)

#     def get_failure_analysis(self):
#         error_types = {}
#         for entry in self.failed_urls:
#             error_type = entry["error"].split(":")[0] if ":" in entry["error"] else "Unknown"
#             error_types[error_type] = error_types.get(error_type, 0) + 1

#         return {
#             "total_failed": len(self.failed_urls),
#             "error_types": error_types,
#             "failed_urls_file": str(self.failed_urls_file)
#         }

# def setup_logger(name: str, log_file: str, level: int = logging.INFO):
#     formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
#     handler = RotatingFileHandler(log_file, maxBytes=2*1024*1024, backupCount=5)
#     handler.setFormatter(formatter)
#     logger = logging.getLogger(name)
#     logger.setLevel(level)
#     logger.addHandler(handler)
#     return logger

# class SpiderLogger:
#     def __init__(self, spider_name: str, target_pages: Union[int, str], log_level: int = logging.INFO):
#         self.spider_name = spider_name
#         self.target_pages = target_pages
#         self.log_folder = self._create_log_folder()
#         self.console = ColorConsole()
#         self.progress_tracker = ProgressTracker(target_pages)
#         self.failed_tracker = FailedURLTracker(self.log_folder)
#         self.logger = self._setup_logger(log_level)
#         self._log_startup()

#     def _create_log_folder(self) -> Path:
#         logs_dir = Path("logs")
#         logs_dir.mkdir(exist_ok=True)
#         log_folder = logs_dir / f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
#         log_folder.mkdir(exist_ok=True)
#         return log_folder

#     def _setup_logger(self, level: int) -> logging.Logger:
#         logger = logging.getLogger(self.spider_name)
#         logger.setLevel(level)
#         if logger.hasHandlers():
#             return logger
#         formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
#         file_handler = RotatingFileHandler(self.log_folder / "spider.log", maxBytes=2 * 1024 * 1024, backupCount=5)
#         file_handler.setFormatter(formatter)
#         logger.addHandler(file_handler)
#         return logger

#     def _log_startup(self):
#         print(self.console.header_message(f"🚀 Starting {self.spider_name}"))
#         print(self.console.info_message(f"📁 Log folder: {self.log_folder}"))
#         self.logger.info(f"Spider started. Target pages: {self.target_pages}")

#     def log_page_progress(self, page_number: int, grants_found: int, grants_failed: int = 0):
#         self.progress_tracker.track_page_completed()
#         self.progress_tracker.track_grants_found(grants_found)
#         msg = f"Page {page_number}/{self.target_pages} | Grants: {grants_found}, Failed: {grants_failed}"
#         print(self.console.progress_message(msg))
#         self.logger.info(msg)

#     def log_grant_success(self, title: str, url: str, page_number: Union[int, str]):
#         self.progress_tracker.track_successful_extraction()
#         print(self.console.success_message(f"✓ {title[:60]}..."))
#         self.logger.info(f"SUCCESS - Page {page_number} - {title} - {url}")

#     def log_grant_failure(self, url: str, error: str, page_number: Union[int, str]):
#         self.progress_tracker.track_failed_extraction()
#         self.failed_tracker.record_failed_url(url, error, page_number)
#         print(self.console.error_message(f"✗ {url} - {error}"))
#         self.logger.error(f"FAIL - Page {page_number} - {url} - {error}")

#     def log_final_summary(self):
#         summary = self.progress_tracker.get_final_summary()
#         failures = self.failed_tracker.get_failure_analysis()

#         print(self.console.header_message("📊 FINAL SUMMARY"))
#         print(self.console.success_message(f"✓ Grants Success: {summary['total_grants_successful']}"))
#         print(self.console.error_message(f"✗ Grants Failed: {summary['total_grants_failed']}"))
#         print(self.console.info_message(f"⏱ Time Taken: {summary['total_time']}"))

#         if failures["total_failed"]:
#             print(self.console.warning_message(f"⚠️ Failed URLs logged at {failures['failed_urls_file']}"))

#         self.logger.info(f"FINAL SUMMARY:\n{json.dumps(summary, indent=2)}")
#         with open(self.log_folder / "summary.json", "w") as f:
#             json.dump(summary, f, indent=2)

# logging_setup.py - Modular Spider Logging System

import logging
from logging.handlers import RotatingFileHandler
import os
import json
from datetime import datetime
from pathlib import Path
from colorama import init, Fore, Style
from typing import Dict, List, Optional, Any, Union

# Initialize colorama for Windows color support
init()

class ColorConsole:
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
        return f"{Fore.CYAN}{'='*60}\n{message}\n{'='*60}{Style.RESET_ALL}"

class ProgressTracker:
    def __init__(self, target_pages: Union[int, str]):
        self.target_pages = target_pages
        self.pages_completed = 0
        self.grants_found = 0
        self.grants_successful = 0
        self.grants_failed = 0
        self.start_time = datetime.now()

    def track_page_completed(self): self.pages_completed += 1
    def track_grants_found(self, count: int): self.grants_found += count
    def track_successful_extraction(self): self.grants_successful += 1
    def track_failed_extraction(self): self.grants_failed += 1

    def get_progress_percentage(self): 
        if isinstance(self.target_pages, int) and self.target_pages > 0:
            return (self.pages_completed / self.target_pages) * 100
        return 0

    def get_current_stats(self) -> Dict[str, Any]:
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
        total_time = datetime.now() - self.start_time
        return {
            "total_pages_completed": self.pages_completed,
            "target_pages": self.target_pages,
            "total_grants_found": self.grants_found,
            "total_grants_successful": self.grants_successful,
            "total_grants_failed": self.grants_failed,
            "success_rate": (self.grants_successful / self.grants_found * 100) if self.grants_found else 0,
            "total_time": str(total_time),
            "completion_time": datetime.now().isoformat()
        }

class FailedURLTracker:
    def __init__(self, log_folder: Path):
        self.log_folder = log_folder
        self.failed_urls: List[Dict[str, Any]] = []
        self.failed_urls_file = log_folder / "failed_urls.json"

    def record_failed_url(self, url: str, error: str, page_number: Union[int, str]):
        failed_entry = {
            "url": url,
            "error": error,
            "page_number": page_number,
            "timestamp": datetime.now().isoformat()
        }
        self.failed_urls.append(failed_entry)
        self._save_failed_urls_to_file()

    def get_failure_analysis(self):
        error_types = {}
        for entry in self.failed_urls:
            error_type = entry["error"].split(":")[0] if ":" in entry["error"] else "Unknown"
            error_types[error_type] = error_types.get(error_type, 0) + 1

        return {
            "total_failed": len(self.failed_urls),
            "error_types": error_types,
            "failed_urls_file": str(self.failed_urls_file)
        }

def setup_logger(name: str, log_file: str, level: int = logging.INFO):
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    # Use 'utf-8' encoding to prevent Unicode errors
    handler = RotatingFileHandler(log_file, maxBytes=2*1024*1024, backupCount=5, encoding='utf-8')
    handler.setFormatter(formatter)
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)
    return logger

class SpiderLogger:
    def __init__(self, spider_name: str, target_pages: Union[int, str], log_level: int = logging.INFO):
        self.spider_name = spider_name
        self.target_pages = target_pages
        self.log_folder = self._create_log_folder()
        self.console = ColorConsole()
        self.progress_tracker = ProgressTracker(target_pages)
        self.failed_tracker = FailedURLTracker(self.log_folder)
        self.logger = self._setup_logger(log_level)
        self._log_startup()

    def _create_log_folder(self) -> Path:
        logs_dir = Path("logs")
        logs_dir.mkdir(exist_ok=True)
        log_folder = logs_dir / f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        log_folder.mkdir(exist_ok=True)
        return log_folder

    def _setup_logger(self, level: int) -> logging.Logger:
        logger = logging.getLogger(self.spider_name)
        logger.setLevel(level)
        if logger.hasHandlers():
            return logger
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler = RotatingFileHandler(self.log_folder / "spider.log", maxBytes=2 * 1024 * 1024, backupCount=5)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        return logger

    def _log_startup(self):
        print(self.console.header_message(f"🚀 Starting {self.spider_name}"))
        print(self.console.info_message(f"📁 Log folder: {self.log_folder}"))
        self.logger.info(f"Spider started. Target pages: {self.target_pages}")

    def log_page_progress(self, page_number: int, grants_found: int, grants_failed: int = 0):
        self.progress_tracker.track_page_completed()
        self.progress_tracker.track_grants_found(grants_found)
        msg = f"Page {page_number}/{self.target_pages} | Grants: {grants_found}, Failed: {grants_failed}"
        print(self.console.progress_message(msg))
        self.logger.info(msg)
    
    def log_processing_success(self, title: str, url: str):
        """Logs successful processing of a single grant's HTML content."""
        self.progress_tracker.track_successful_extraction()
        print(self.console.success_message(f"✅ Filtered and processed HTML for: {title}"))
        self.logger.info(f"SUCCESS - Processed HTML for grant: {title} - {url}")

    def log_grant_success(self, title: str, url: str, page_number: Union[int, str]):
        self.progress_tracker.track_successful_extraction()
        print(self.console.success_message(f"✓ {title[:60]}..."))
        self.logger.info(f"SUCCESS - Page {page_number} - {title} - {url}")

    def log_grant_failure(self, url: str, error: str, page_number: Union[int, str]):
        self.progress_tracker.track_failed_extraction()
        self.failed_tracker.record_failed_url(url, error, page_number)
        print(self.console.error_message(f"✗ {url} - {error}"))
        self.logger.error(f"FAIL - Page {page_number} - {url} - {error}")

    def log_final_summary(self):
        summary = self.progress_tracker.get_final_summary()
        failures = self.failed_tracker.get_failure_analysis()

        print(self.console.header_message("📊 FINAL SUMMARY"))
        print(self.console.success_message(f"✓ Grants Success: {summary['total_grants_successful']}"))
        print(self.console.error_message(f"✗ Grants Failed: {summary['total_grants_failed']}"))
        print(self.console.info_message(f"⏱ Time Taken: {summary['total_time']}"))

        if failures["total_failed"]:
            print(self.console.warning_message(f"⚠️ Failed URLs logged at {failures['failed_urls_file']}"))

        self.logger.info(f"FINAL SUMMARY:\n{json.dumps(summary, indent=2)}")
        with open(self.log_folder / "summary.json", "w") as f:
            json.dump(summary, f, indent=2)