import os
import logging
import subprocess
import hashlib

logging.basicConfig(level=logging.DEBUG, format='[%(asctime)s][%(levelname)s] Root/Setup: %(message)s')

repo_url = "https://github.com/FlareSolverr/FlareSolverr"

def powershell(cmd, popen=False):
    if popen:
        return subprocess.Popen(["powershell", "-Command", cmd], text=True)
    else:
        return subprocess.run(["powershell", "-Command", cmd], text=True)

def git_setup():
    logging.debug("Starting Git installation...")
    os.system("winget install --id Git.Git -e --source winget")
    logging.debug("Git installation completed.")

def clone_repo(name):
    logging.debug("Cloning repository...")
    if not os.path.exists("Server"):
        os.system(f"git clone {repo_url} {name}")
        logging.debug("Repository cloned successfully.")
    else:
        logging.debug("Repository already exists. Skipping clone.")
    logging.debug("Repository setup completed.")

if __name__ == "__main__":
    git_setup()
    logging.debug("All setup steps completed successfully.")