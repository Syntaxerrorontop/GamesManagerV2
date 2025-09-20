import os
import logging
import subprocess
import time
import psutil  # pip install psutil
import shutil

logging.basicConfig(level=logging.DEBUG, format='[%(asctime)s][%(levelname)s] Root/Setup: %(message)s')

repo_url = "https://github.com/yoori/flare-bypasser"

def powershell(cmd, popen=False):
    if popen:
        return subprocess.Popen(["powershell", "-Command", cmd], text=True)
    else:
        return subprocess.run(["powershell", "-Command", cmd], text=True)

def docker_setup():
    logging.debug("Starting Docker setup...")
    logging.debug("Installing Docker Desktop via winget...")
    logging.warning("Please ensure to enable WSL 2 during Docker installation if prompted.")
    os.system("winget install --id Docker.DockerDesktop -e --source winget")
    logging.debug("Docker setup completed.")

def git_setup():
    logging.debug("Starting Git installation...")
    os.system("winget install --id Git.Git -e --source winget")
    logging.debug("Git installation completed.")

def clone_repo():
    logging.debug("Cloning repository...")
    if not os.path.exists("Server"):
        os.system(f"git clone {repo_url} Server")
        logging.debug("Repository cloned successfully.")
    else:
        logging.debug("Repository already exists. Skipping clone.")
    logging.debug("Repository setup completed.")

def start_docker():
    logging.debug("Starting Docker Desktop and managing processes...")
    processes = [
        "Docker Desktop.exe",
        "com.docker.service"
    ]

    def process_running(name: str) -> bool:
        """Check if a process with this name is running"""
        for proc in psutil.process_iter(['name']):
            if "docker" in proc.info['name'].lower():
                print(proc.info['name'])
            if proc.info['name'] and proc.info['name'].lower() == name.lower():
                return True
        return False

    def kill_process(name: str):
        """Kill a process by name"""
        logging.debug(f"Killing {name} ...")
        subprocess.run(["taskkill", "/F", "/IM", name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    if process_running("com.docker.backend.exe"):
        logging.debug("Docker Desktop Backend is already running. Skipping start.")
        return
    
    powershell('Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"', popen=True)

    logging.debug("Waiting for Docker processes...")
    while True:
        found = False
        for proc_name in processes:
            if process_running(proc_name):
                found = True
                kill_process(proc_name)
        if found:
            break
        time.sleep(2)

    logging.debug("Successfull Started")

def docker_image_setup():
    logging.debug("Setting up Docker image...")
    os.chdir("Server")
    os.system("docker compose up -d")
    logging.debug("Docker image setup completed.")
    os.chdir("..")

if __name__ == "__main__":
    docker_setup()
    git_setup()
    clone_repo()
    start_docker()
    docker_image_setup()
    powershell(r'Remove-Item -LiteralPath "D:\Coding\.Python\.BigProject\test\Server" -Recurse -Force')
    logging.debug("All setup steps completed successfully.")