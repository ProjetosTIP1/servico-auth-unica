from core.config.settings import settings
from core.utils.context import get_correlation_id

from core.helpers.file_log_helper import write_on_file

# Define ANSI escape codes for colors and reset
RED = "\033[91m"
GREEN = "\033[92m"
BLUE = "\033[94m"
YELLOW = "\033[93m"
MAGENTA = "\033[95m"
RESET = "\033[0m"


class AppLogHelper:
    """
    Simple logger class for console output with color coding.

    Attributes:
        is_debug (bool): Whether debug mode is enabled.
        is_development (bool): Whether the environment is development.

    Methods:
        info(message: str, correlation_id: str = "") -> None: Logs an informational message.
        success(message: str, correlation_id: str = "") -> None: Logs a success message.
        warning(message: str, correlation_id: str = "") -> None: Logs a warning message.
        error(message: str, correlation_id: str = "") -> None: Logs an error message.
        debug(message: str, correlation_id: str = "") -> None: Logs a debug message if debug mode is enabled.
        spacer() -> None: Prints a spacer line for better readability in logs.
    """

    def __init__(self):
        self.is_debug = settings.DEBUG
        self.is_development = settings.DEVELOPMENT_ENV

    def info(self, message: str, correlation_id: str = "") -> None:
        """
        Logs an informational message.
            message (str): The message to log.
            correlation_id (str): An optional correlation ID for tracking requests.
        """
        if not correlation_id:
            correlation_id = get_correlation_id()
        if self.is_development:
            print(f"{BLUE}INFO {correlation_id} {RESET}{message}")
        else:
            print(f"INFO {correlation_id} {message}")

    def success(self, message: str, correlation_id: str = "") -> None:
        """
        Logs a success message.
            message (str): The success message to log.
            correlation_id (str): An optional correlation ID for tracking requests.
        """
        if not correlation_id:
            correlation_id = get_correlation_id()
        if self.is_development:
            print(f"{GREEN}SUCCESS {correlation_id} {RESET}{message}")
        else:
            print(f"SUCCESS {correlation_id} {message}")

    def warning(self, message: str, correlation_id: str = "") -> None:
        """
        Logs a warning message.
            message (str): The warning message to log.
            correlation_id (str): An optional correlation ID for tracking requests.
        """
        if not correlation_id:
            correlation_id = get_correlation_id()
        if self.is_development:
            print(f"{YELLOW}WARNING {correlation_id} {RESET}{message}")
        else:
            print(f"WARNING {correlation_id} {message}")
            write_on_file(f"WARNING {correlation_id} {message}", correlation_id)

    def error(self, message: str, correlation_id: str = "") -> None:
        """
        Logs an error message.
            message (str): The error message to log.
            correlation_id (str): An optional correlation ID for tracking requests.
        """
        if not correlation_id:
            correlation_id = get_correlation_id()
        if self.is_development:
            print(f"{RED}ERROR {correlation_id} {RESET}{message}")
        else:
            print(f"ERROR {correlation_id} {message}")
            write_on_file(f"ERROR {correlation_id} {message}", correlation_id)

    def debug(self, message: str, correlation_id: str = "") -> None:
        """
        Logs a debug message if debug mode is enabled.
            message (str): The debug message to log.
            correlation_id (str): An optional correlation ID for tracking requests.
        """
        if not correlation_id:
            correlation_id = get_correlation_id()
        if self.is_debug:
            if self.is_development:
                print(f"{MAGENTA}DEBUG {correlation_id} {RESET}{message}")
            else:
                print(f"DEBUG {correlation_id} {message}")

    def spacer(self) -> None:
        """
        Prints a spacer line for better readability in logs.
        """
        if self.is_development:
            print(f"{MAGENTA}{'-' * 50}{RESET}")
        else:
            print("-" * 50)


class ProgressBar:
    """
    Simple progress bar for console output.
    """

    def __init__(self, total: int):
        self.total = total
        self.current = 0
        self.is_development = settings.environment == "development"

    def update(self):
        self.current += 1
        percent = (self.current / self.total) * 100
        bar_length = 40
        filled_length = int(bar_length * self.current // self.total)
        if self.is_development:
            bar = f"{MAGENTA}█{RESET}" * filled_length + "-" * (
                bar_length - filled_length
            )
            print(f"\r{BLUE}PROGRESS{RESET} |{bar}| {percent:.1f}%", end="\r")

        else:
            bar = "█" * filled_length + "-" * (bar_length - filled_length)
            print(f"\rPROGRESS |{bar}| {percent:.1f}%", end="\r")
        if self.current == self.total:
            print()  # New line on complete

    def reset(self):
        self.current = 0
        if self.is_development:
            print(f"\r{BLUE}PROGRESS{RESET} |{'-' * 40}| 0.0%{RESET}", end="\r")
        else:
            print(f"\rPROGRESS |{'-' * 40}| 0.0%", end="\r")


logger = AppLogHelper()