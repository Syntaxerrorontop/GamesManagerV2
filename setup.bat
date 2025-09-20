@echo off
:: Install Python (latest available version)
winget install --id Python.Python.3.13 -e --source winget

:: Install WinRAR
winget install --id RARLab.WinRAR -e --source winget

:: Install PsExec
winget install --id Microsoft.Sysinternals.PsTools -e --source winget

:: Install ProcessMonitor
winget install --id Microsoft.Sysinternals.ProcessMonitor -e --source winget

:: Set path to the newly installed Python
set PYTHON_PATH=C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python313\python.exe

:: Install dependencies
echo Installing/updating pip...
"%PYTHON_PATH%" -m pip install --upgrade pip

echo Installing requirements...
"%PYTHON_PATH%" -m pip install -r requirements.txt

echo Running setup.py...
"%PYTHON_PATH%" setup.py

echo Done!
pause
