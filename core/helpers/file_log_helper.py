import sys
from pathlib import Path
from datetime import datetime


def get_log_file_path() -> Path:
    """Determines the correct path for the log file."""
    if getattr(sys, "frozen", False):
        # If the application is run as a bundle (PyInstaller)
        application_path = Path(sys.executable).parent
    else:
        # If run as a script, use the project root (parent of helpers folder)
        application_path = Path(__file__).parent.parent

    return application_path / "app.log"


def write_on_file(message: str, correlation_id: str = "") -> None:
    """Writes a message directly to a log file."""
    date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_path = get_log_file_path()
    try:
        with open(log_path, "a") as log_file:
            log_file.write(f"{date} | {correlation_id} | {message}\n")
    except IOError as e:
        print(f"Failed to write to log file: {e}")


def clear_log_file() -> None:
    """Clears the log file."""
    log_path = get_log_file_path()
    try:
        open(log_path, "w").close()
    except IOError as e:
        print(f"Failed to clear log file: {e}")
