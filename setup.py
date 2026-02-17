import os
import sys
from setuptools import setup, find_packages
from setuptools.command.install import install


class PostInstallCommand(install):
    """Post-installation hook to add Scripts directory to PATH on Windows"""
    
    def run(self):
        install.run(self)
        
        # Only run on Windows
        if sys.platform == "win32":
            try:
                import pathlib
                python_path = pathlib.Path(sys.executable).parent
                scripts_path = python_path / "Scripts"
                
                if scripts_path.exists():
                    # Add to Windows PATH
                    from winreg import ConnectRegistry, OpenKey, SetValueEx, REG_EXPAND_SZ, HKEY_CURRENT_USER
                    
                    registry = ConnectRegistry(None, HKEY_CURRENT_USER)
                    key = OpenKey(registry, r"Environment", 0, 2)
                    
                    try:
                        current_path = pathlib.os.environ.get("PATH", "")
                        scripts_str = str(scripts_path)
                        
                        if scripts_str not in current_path:
                            new_path = f"{current_path};{scripts_str}" if current_path else scripts_str
                            SetValueEx(key, "PATH", 0, REG_EXPAND_SZ, new_path)
                            print(f"\n✅ Added {scripts_path} to system PATH")
                            print("   Restart your terminal for changes to take effect")
                        else:
                            print(f"\n✅ {scripts_path} already in PATH")
                    finally:
                        key.Close()
            except Exception as e:
                # Don't fail installation if PATH update fails
                print(f"\n⚠️  Could not automatically update PATH: {e}")
                print(f"   Please manually add: {sys.executable.rsplit(chr(92), 1)[0]}\\Scripts to your PATH")


setup(
    name="crawlier",
    version="1.0.1",
    author="Pansilu Chethiya (yoohoo-dev)",
    author_email="pansiluco@gmail.com",
    description="A modern Crawling library built completely from Python",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/Qwanzo/Crawlier",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Intended Audience :: Developers",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires=">=3.10",
    install_requires=[
        "requests>=2.28.0",
        "beautifulsoup4>=4.11.0",
        "lxml>=4.9.0",
        "dnspython>=2.2.0",
        "tqdm>=4.64.0",
        "gradio>=3.20.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.2.0",
            "pytest-cov>=4.0.0",
            "black>=22.0.0",
            "flake8>=5.0.0",
            "mypy>=0.991",
        ],
    },
    entry_points={
        "console_scripts": [
            "crawlier=crawlier.cli:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
    cmdclass={
        "install": PostInstallCommand,
    },
)
