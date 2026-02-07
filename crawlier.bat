@echo off
REM Crawlier CLI wrapper for Windows CMD

python -c "from crawlier.cli import main; main()" %*
