@echo off
cls
echo =======================================================
echo            Project EXE Builder
echo =======================================================
echo.

cd /d "%~dp0"

:: --- Step 1: Check for and create the virtual environment ---
echo --- Checking for virtual environment ('venv' folder)...
if not exist "venv" (
    echo 'venv' folder not found. Creating a new virtual environment.
    echo This might take a moment...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo.
        echo ERROR: Failed to create the virtual environment.
        echo Please make sure Python is installed and in your system's PATH.
        pause
        exit /b
    )
    echo Virtual environment created successfully.
) else (
    echo Virtual environment already exists.
)
echo.

:: --- Step 2: Activate the virtual environment ---
echo --- Activating virtual environment...
call "venv\Scripts\activate.bat"
if %errorlevel% neq 0 (
    echo.
    echo ERROR: Failed to activate the virtual environment.
    pause
    exit /b
)
echo Activated. The following commands will run inside the venv.
echo.

:: --- Step 3: Upgrade pip and install wheel (BEST PRACTICE) ---
echo --- Upgrading build tools (pip, wheel)...
python -m pip install --upgrade pip wheel
echo.


:: --- Step 4: Run the Python EXE Maker script ---
echo --- Starting the exe_maker.py script...
echo.
python exe_maker.py

:: --- Step 5: Finish ---
echo.
echo =======================================================
echo Batch script has finished. Press any key to exit.
echo =======================================================
pause