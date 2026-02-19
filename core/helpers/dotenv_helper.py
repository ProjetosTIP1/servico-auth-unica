"""
PyInstaller configuration and utilities
"""
import sys
from pathlib import Path
from typing import Optional

def get_executable_directory() -> Path:
    """
    Get the directory where the executable is located.
    This works both for development and PyInstaller bundled executables.
    
    Returns:
        Path: The directory containing the executable or script
    """
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        # Running in PyInstaller bundle
        return Path(sys.executable).parent
    else:
        # Running in development
        return Path(__file__).parent.parent

def get_config_directory() -> Path:
    """
    Get the configuration directory for the application.
    This should be where .env and other config files are located.
    
    Returns:
        Path: The configuration directory path
    """
    exe_dir = get_executable_directory()
    
    # Look for config directory in the same folder as executable
    config_dir = exe_dir / "core/config"
    if not config_dir.exists():
        config_dir.mkdir(exist_ok=True)
        
    return config_dir

def find_env_file() -> Optional[Path]:
    """
    Find the .env file in the expected locations.
    Follows the order: executable_dir/config/.env -> executable_dir/.env -> None
    
    Returns:
        Optional[Path]: Path to .env file if found, None otherwise
    """
    exe_dir = get_executable_directory()
    
    # Priority order for .env file locations
    env_locations = [
        exe_dir / "config" / ".env",
        exe_dir / ".env",
        exe_dir / "core/config" / ".env"  # Fallback for development
    ]
    
    for env_path in env_locations:
        if env_path.exists():
            return env_path
            
    return None

def create_sample_env_file() -> None:
    """
    Create a sample .env file in the config directory for user reference.
    This helps users understand what configuration is needed.
    """
    config_dir = get_config_directory()
    sample_env_path = config_dir / ".env.sample"
    
    if not sample_env_path.exists():
        sample_content = """
# Copy this file to .env and fill in your actual values

DEVELOPMENT_ENV=<your_value_here>
DEBUG=<your_value_here>
API_URL=<your_value_here>
AUTH_TOKEN=<your_value_here>

EMBEDDING_CHUNK_SIZE=<your_value_here>

ALLOWED_ORIGINS=<your_value_here>

SECRET_KEY=<your_value_here>
ALGORITHM=<your_value_here>

MAX_CONCURRENT_REQUESTS=<your_value_here>
TASK_POLL_INTERVAL=<your_value_here>
ACCESS_TOKEN_EXPIRE_MINUTES=<your_value_here>

POSTGRES_USER=<your_value_here>
POSTGRES_PASSWORD=<your_value_here>
POSTGRES_DB=<your_value_here>
POSTGRES_HOST=<your_value_here>
POSTGRES_PORT=<your_value_here>

REDIS_HOST=<your_value_here>
REDIS_PORT=<your_value_here>
REDIS_DB=<your_value_here>
REDIS_PASSWORD=<your_value_here>

SQLSERVER_USER=<your_value_here>
SQLSERVER_PASSWORD=<your_value_here>
SQLSERVER_DB=<your_value_here>
SQLSERVER_HOST=<your_value_here>
SQLSERVER_PORT=<your_value_here>
SQLSERVER_DRIVER=<your_value_here>
SQLSERVER_TRUST_SERVER_CERTIFICATE=<your_value_here>
SQLSERVER_ENCRYPT=<your_value_here>

WHATSAPP_API_URL=<your_value_here>
WHATSAPP_API_TOKEN=<your_value_here>
"""
        
        with open(sample_env_path, 'w', encoding='utf-8') as f:
            f.write(sample_content)
        
        print(f"Sample configuration file created at: {sample_env_path}")
        print("Please copy it to .env and configure your actual values.")
