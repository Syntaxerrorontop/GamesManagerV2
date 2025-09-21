import os
import logging
import subprocess
import hashlib

logging.basicConfig(level=logging.DEBUG, format='[%(asctime)s][%(levelname)s] Root/Setup: %(message)s')

repo_url = "https://github.com/FlareSolverr/FlareSolverr"

def git_setup():
    logging.debug("Starting Git installation...")
    os.system("winget install --id Git.Git -e --source winget")
    logging.debug("Git installation completed.")

if __name__ == "__main__":
    git_setup()
    logging.debug("All setup steps completed successfully.")