# Build Instructions for Live Transcription App

## Quick Build (Recommended)

### Option 1: Using the Build Script (Easiest)
```bash
build_app.bat
```
That's it! The script handles everything.

### Option 2: Manual PyInstaller Command
```bash
pyinstaller --onefile --windowed --name "Live Transcription" --icon=icon.ico --add-data "modules;modules" --hidden-import=deepgram --hidden-import=pyaudiowpatch --hidden-import=sounddevice --hidden-import=customtkinter --hidden-import=openai --hidden-import=numpy --hidden-import=dotenv --collect-all customtkinter Live_Enhanced.py
```

## Important Flags Explained

| Flag | Purpose |
|------|---------|
| `--onefile` | Creates single .exe file (easier distribution) |
| `--windowed` | No console window (clean GUI-only app) |
| `--name "Live Transcription"` | Names the .exe file |
| `--icon=icon.ico` | Adds your app icon |
| `--add-data "modules;modules"` | Includes the modules folder |
| `--hidden-import=...` | Ensures all dependencies are included |
| `--collect-all customtkinter` | Includes all CustomTkinter assets |

## Why Not Just `--noconsole`?

- `--noconsole` is the old flag
- `--windowed` is the modern equivalent (recommended)
- They do the same thing: hide the console window

## After Building

### 1. Find Your Executable
```
dist\Live Transcription.exe
```

### 2. Create .env File
Create a file named `.env` in the **same folder** as the .exe:
```
DEEPGRAM_API_KEY=your_deepgram_key_here
OPENAI_API_KEY=your_openai_key_here
```

### 3. Folder Structure for Distribution
```
Live Transcription/
├── Live Transcription.exe
├── .env
└── output/ (created automatically on first run)
```

## Common Issues & Solutions

### Issue 1: "Module not found" errors
**Solution**: Add the module to `--hidden-import`:
```bash
--hidden-import=module_name
```

### Issue 2: CustomTkinter themes missing
**Solution**: Already handled by `--collect-all customtkinter`

### Issue 3: .env file not found
**Solution**: Place `.env` in the **same folder** as the .exe, not in the build folder.

### Issue 4: "No audio devices found"
**Solution**: Install VC++ Redistributables:
- https://aka.ms/vs/17/release/vc_redist.x64.exe

### Issue 5: Large .exe size (~200MB+)
**Cause**: PyInstaller includes entire Python + all libraries
**Solution**: This is normal. To reduce size:
```bash
# Use --onedir instead of --onefile
pyinstaller --onedir --windowed ...
```
This creates a folder with multiple files but smaller total size.

## Build Sizes

| Build Type | Size | Speed | Distribution |
|------------|------|-------|--------------|
| `--onefile` | ~200MB | Slower startup | Single file (easier) |
| `--onedir` | ~150MB | Faster startup | Multiple files (folder) |

## Advanced: Custom .spec File

If you need more control, edit `Live Transcription.spec`:
```python
# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['Live_Enhanced.py'],
    pathex=[],
    binaries=[],
    datas=[('modules', 'modules')],
    hiddenimports=[
        'deepgram',
        'pyaudiowpatch',
        'sounddevice',
        'customtkinter',
        'openai',
        'numpy',
        'dotenv'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='Live Transcription',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico'
)
```

Then build with:
```bash
pyinstaller Live Transcription.spec
```

## Distribution Checklist

### For Users Who Don't Have Python:
- ✅ Include the .exe
- ✅ Include instructions to create .env file
- ✅ Include VC++ Redistributable link
- ✅ Include README with usage instructions

### For Users With Python:
- ❌ Don't need the .exe
- ✅ Just share the source code
- ✅ Include requirements.txt
- ✅ Include .env template

## Testing Your Build

1. **Copy the .exe to a different location** (not the source folder)
2. **Create .env file** with your API keys
3. **Run the .exe**
4. **Test all features:**
   - Microphone recording
   - Computer audio recording
   - Both mode
   - Speaker diarization
   - File saving
   - Settings persistence

## Clean Build (If You Have Issues)

```bash
# Delete old build artifacts
rmdir /s /q build
rmdir /s /q dist
del Live_Enhanced.spec

# Rebuild fresh
pyinstaller --onefile --windowed --name "Live Transcription" --icon=icon.ico --add-data "modules;modules" --hidden-import=deepgram --hidden-import=pyaudiowpatch --hidden-import=sounddevice --hidden-import=customtkinter --hidden-import=openai --hidden-import=numpy --hidden-import=dotenv --collect-all customtkinter Live_Enhanced.py
```

## Build Time
- **First build**: 2-5 minutes
- **Rebuild**: 30-60 seconds

## File Locations After Build

```
Your Project/
├── build/              (temporary build files - can delete)
├── dist/               
│   └── Live Transcription.exe  ← Your final executable!
├── Live_Enhanced.spec  (build configuration - can keep)
└── ... (source files)
```

## Distributing to Others

### Option A: Single Executable
1. Copy `dist/Live Transcription.exe`
2. Create a `.env.example` file:
   ```
   DEEPGRAM_API_KEY=your_key_here
   OPENAI_API_KEY=your_key_here
   ```
3. Create a README with setup instructions
4. Share all three files

### Option B: Installer (Advanced)
Use Inno Setup to create a proper Windows installer:
1. Download Inno Setup
2. Create installer script
3. Includes .exe + auto .env setup

## Performance Notes

- **Startup Time**: 3-5 seconds (first run)
- **Subsequent Runs**: 1-2 seconds
- **Memory Usage**: ~100-200MB
- **CPU Usage**: 5-10% (while transcribing)

## Security Notes

⚠️ **NEVER distribute .exe with API keys inside!**
- Always use .env file
- User provides their own keys
- Include instructions for getting keys

## Support

### If Build Fails:
1. Check Python version (3.8+)
2. Update PyInstaller: `pip install --upgrade pyinstaller`
3. Check all dependencies installed: `pip install -r requirements.txt`
4. Try clean build (delete build/dist folders)

### If .exe Crashes:
1. Run from command line to see errors:
   ```cmd
   "Live Transcription.exe"
   ```
2. Check .env file exists and is valid
3. Check Windows Defender isn't blocking it
4. Check VC++ Redistributables installed

## One-Click Build & Test Script

Create `build_and_test.bat`:
```batch
@echo off
echo Cleaning...
rmdir /s /q build dist 2>nul
del Live_Enhanced.spec 2>nul

echo Building...
pyinstaller --onefile --windowed --name "Live Transcription" --icon=icon.ico --add-data "modules;modules" --hidden-import=deepgram --hidden-import=pyaudiowpatch --hidden-import=sounddevice --hidden-import=customtkinter --hidden-import=openai --hidden-import=numpy --hidden-import=dotenv --collect-all customtkinter Live_Enhanced.py

if exist "dist\Live Transcription.exe" (
    echo.
    echo Build successful! Running app...
    cd dist
    start "" "Live Transcription.exe"
) else (
    echo Build failed!
)
```

## Status
✅ **BUILD SCRIPT READY**
✅ **INSTRUCTIONS COMPLETE**
✅ **ALL FLAGS INCLUDED**

Run `build_app.bat` now to build your executable! 🚀

