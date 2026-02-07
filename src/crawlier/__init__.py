"""
Crawlier - A Python web crawler for desktop (PansiluBot) and mobile (MethmiBot) modes.
"""

import sys
import os

__version__ = "0.0.5-beta"
__author__ = "Pansilu Chethiya (yoohoo-dev)"
__email__ = "pansiluco@gmail.com"
__license__ = "MIT"


def _setup_windows_path():
    """Auto-configure Windows PATH for crawlier command on first import"""
    if sys.platform != "win32":
        return
    
    try:
        import pathlib
        import os.path
        
        python_path = pathlib.Path(sys.executable).parent
        scripts_path = python_path / "Scripts"
        scripts_str = str(scripts_path)
        
        # Check if already in PATH
        current_path = os.environ.get("PATH", "")
        if scripts_str in current_path:
            return
        
        # Try to add via registry (Windows environment variables)
        try:
            from winreg import ConnectRegistry, OpenKey, SetValueEx, REG_EXPAND_SZ, HKEY_CURRENT_USER
            
            registry = ConnectRegistry(None, HKEY_CURRENT_USER)
            key = OpenKey(registry, r"Environment", 0, 2)
            
            new_path = f"{current_path};{scripts_str}" if current_path else scripts_str
            SetValueEx(key, "PATH", 0, REG_EXPAND_SZ, new_path)
            key.Close()
            
            # Update current process PATH
            os.environ["PATH"] = new_path
        except Exception:
            # Silent fail - user can manually add to PATH if needed
            pass
    
    except Exception:
        # Silent fail - don't break package import
        pass


# Auto-setup PATH on first import
_setup_windows_path()

from .crawler import Crawlier, run_crawl
from .cli import main

__all__ = ["Crawlier", "run_crawl", "main"]
