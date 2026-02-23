# Release Notes

Date: 2026-02-17

## v1.0.1 - Single-binary build and CLI improvements

- Added a single-file Windows executable produced with PyInstaller: `dist/crawlier.exe`.
- Added build helper script: `build/build_exe.bat` (handles installing build deps, building with PyInstaller, and embedding an icon if `icon.png` exists at project root).
- Added `build/README_BUILD.md` with quick build instructions and tips.
- CLI update: when started with no command-line arguments (e.g., double-clicking the exe), the program now opens an interactive REPL so you can see help and enter arguments without losing the console.
- The build script will attempt to stop and remove any running `crawlier.exe` in `dist/` before building to avoid lock/permission errors.

## Notes / Known issues

- The binary includes all installed requirements (including optional GUI deps like `gradio`) so the exe size can be large. To reduce size, remove unused packages from `requirements.txt` or `setup.py` before rebuilding.
- If PyInstaller reports missing imports at runtime, run the build manually and add `--hidden-import` flags for the reported modules.
- If the build fails with a permission error for `dist\crawlier.exe`, ensure no running copies are open (or run `taskkill /im crawlier.exe /f`) and rebuild.


## Next steps

- Optionally slim `requirements.txt` to reduce binary size.
- Add CI GitHub Action to produce release artifacts automatically.

If you want, I can commit and tag a release and create a GitHub release draft including the built exe (note: attaching large binaries to GitHub releases may be slower than using release assets storage). 
