import subprocess
import sys
import os
import shutil

VENV_DIR = "venv"

def create_virtual_env():
    """Creates a virtual environment."""
    if not os.path.exists(VENV_DIR):
        print(f"Creating virtual environment in ./{VENV_DIR}...")
        try:
            subprocess.check_call([sys.executable, "-m", "venv", VENV_DIR])
            print("Virtual environment created successfully.")
        except subprocess.CalledProcessError as e:
            print(f"Error creating virtual environment: {e}")
            sys.exit(1)
    else:
        print("Virtual environment already exists.")

def get_pip_executable():
    """Returns the path to the pip executable in the virtual environment."""
    if sys.platform == "win32":
        return os.path.join(VENV_DIR, "Scripts", "pip.exe")
    else:
        return os.path.join(VENV_DIR, "bin", "pip")

def get_python_executable():
    """Returns the path to the python executable in the virtual environment."""
    if sys.platform == "win32":
        return os.path.join(VENV_DIR, "Scripts", "python.exe")
    else:
        return os.path.join(VENV_DIR, "bin", "python")

def install_dependencies():
    """Install dependencies from requirements.txt into the virtual environment."""
    print("Installing dependencies into virtual environment...")
    pip_executable = get_pip_executable()
    try:
        subprocess.check_call([pip_executable, "install", "-r", "requirements.txt"])
        print("Dependencies installed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Error installing dependencies: {e}")
        sys.exit(1)

def setup_tools_folder():
    """Ensure the Tools folder exists and contains necessary executables."""
    tools_path = os.path.join(os.getcwd(), "Tools")
    os.makedirs(tools_path, exist_ok=True)
    
    unrar_exe_path = os.path.join(tools_path, "UnRAR.exe")
    if not os.path.exists(unrar_exe_path):
        print(f"Warning: {unrar_exe_path} not found.")
        print("Please place UnRAR.exe into the 'Tools' folder for unpacking functionality.")

def run_application():
    """Run the main application using the virtual environment's python."""
    print("Starting the application from virtual environment...")
    python_executable = get_python_executable()
    try:
        subprocess.check_call([python_executable, "main.py"])
    except subprocess.CalledProcessError as e:
        print(f"Application exited with an error: {e}")
    except FileNotFoundError:
        print(f"Error: Could not find '{python_executable}'. Has the virtual environment been created and dependencies installed?")


def clean_cache():
    """Removes the DownloadCache, Games, and Config folders."""
    print("Cleaning cache and configuration folders...")
    folders_to_clean = ["DownloadCache", "Games", "Config", VENV_DIR]
    for folder in folders_to_clean:
        path = os.path.join(os.getcwd(), folder)
        if os.path.exists(path):
            try:
                shutil.rmtree(path)
                print(f"Removed: {folder}")
            except OSError as e:
                print(f"Error removing {folder}: {e}")
        else:
            print(f"Skipped {folder}: Not found.")

if __name__ == "__main__":
    print("Gemini CLI Project Setup Script")
    
    action = input("Choose action: (1) Install/Setup, (2) Run, (3) Clean, (4) Exit: ")

    if action == "1":
        create_virtual_env()
        install_dependencies()
        setup_tools_folder()
        print("\nSetup complete. You can now run the application by choosing option (2).")
    elif action == "2":
        run_application()
    elif action == "3":
        clean_cache()
        print("\nCleanup complete.")
    elif action == "4":
        print("Exiting.")
        sys.exit(0)
    else:
        print("Invalid action. Please choose 1, 2, 3, or 4.")
    
    print("\nScript finished.")
