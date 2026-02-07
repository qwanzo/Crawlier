#!/usr/bin/env python3
"""
Post-installation script for Crawlier.
Automatically adds Python Scripts directory to Windows PATH.
This runs automatically when installed via pip.
"""

import os
import sys
import pathlib


def setup_path():
    """Add Python Scripts directory to Windows PATH if on Windows"""
    if sys.platform != "win32":
        return
    
    try:
        python_path = pathlib.Path(sys.executable).parent
        scripts_path = python_path / "Scripts"
        
        if not scripts_path.exists():
            print(f"⚠️  Scripts directory not found: {scripts_path}")
            return
        
        # Try to add to Windows registry (requires permissions)
        try:
            from winreg import ConnectRegistry, OpenKey, SetValueEx, REG_EXPAND_SZ, HKEY_CURRENT_USER
            
            registry = ConnectRegistry(None, HKEY_CURRENT_USER)
            key = OpenKey(registry, r"Environment", 0, 2)
            
            current_path = os.environ.get("PATH", "")
            scripts_str = str(scripts_path)
            
            if scripts_str not in current_path:
                new_path = f"{current_path};{scripts_str}" if current_path else scripts_str
                SetValueEx(key, "PATH", 0, REG_EXPAND_SZ, new_path)
                print(f"✅ Added {scripts_path} to system PATH")
                print("   Restart your terminal to use 'crawlier' command directly")
            else:
                print(f"✅ {scripts_path} already in PATH")
            
            key.Close()
        
        except ImportError:
            print("⚠️  Could not import Windows registry module (not on Windows)")
        
        except PermissionError:
            print(f"⚠️  Insufficient permissions to modify PATH")
            print(f"   Please manually add to PATH: {scripts_path}")
    
    except Exception as e:
        print(f"⚠️  Error during PATH setup: {e}")
        print(f"   You can manually add: {sys.executable.rsplit(chr(92), 1)[0]}\\Scripts to PATH")


if __name__ == "__main__":
    setup_path()
