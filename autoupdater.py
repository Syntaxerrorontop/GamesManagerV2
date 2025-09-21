import os, logging, requests, hashlib, sys, subprocess

repo_url = "https://github.com/Syntaxerrorontop/GamesManagerV2"
logging.basicConfig(level=logging.DEBUG, format='[%(asctime)s][%(levelname)s] Root/Autoupdater: %(message)s')
def clone_repo(name):
    logging.debug("Cloning repository...")
    if not os.path.exists(name):
        os.system(f"git clone {repo_url} {name}")
        logging.debug("Repository cloned successfully.")
    else:
        logging.debug("Repository already exists. Skipping clone.")
    logging.debug("Repository setup completed.")

try:
    with open(os.path.join(os.getcwd(), 'version.txt'), 'r') as f:
       current_version = str(f.read())
except:
    current_version = "0.0.0.0"

online_version = requests.get("https://raw.githubusercontent.com/Syntaxerrorontop/GamesManagerV2/master/version.txt").text

if current_version != online_version:
    logging.info(f"Version Missmatch Detected: {current_version} -> {online_version}")
    
    exceptions = "autoupdater.py","setup.py","setup.bat", "Games"
    for file in os.listdir(os.getcwd()):
        if file not in exceptions:
            try:
                ps_command = f'Remove-Item -Path "{os.path.join(os.getcwd(), file)}" -Recurse -Force'

                subprocess.run(["powershell", "-Command", ps_command], check=True)
            except Exception as e:
                logging.error(f"Error removing {file}: {e}")

    # PowerShell über Python ausführen
    subprocess.run(["powershell", "-Command", ps_command], check=True)
        
    name = hashlib.md5(repo_url.encode('utf-8')).hexdigest()
    clone_repo(name)
    
    os.system(f'robocopy {os.path.join(os.getcwd(), name)} {os.getcwd()} /E /XF autoupdater.py setup.py setup.bat /R:0 /W:0')

    py = sys.executable
    os.system(f'{py} -m pip install -r requirements.txt')
    
    ps_command = f'Remove-Item -Path "{os.path.join(os.getcwd(), name)}" -Recurse -Force'

    subprocess.run(["powershell", "-Command", ps_command], check=True)