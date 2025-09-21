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
    logging.info(f"Version Mutation Detected: {current_version} -> {online_version}")

<<<<<<< HEAD
    exceptions = "autoupdater.py","setup.py","setup.bat", "Games"
=======
    exceptions = "autoupdater.py","setup.py","setup.bat"
>>>>>>> 066cd7baa352e11cc4d2ae0aa7688a843b40a490

    # PowerShell-Befehl bauen
    ps_command = f'''
    $folder = "{os.getcwd()}";
    $exceptions = @({",".join(f'"{e}"' for e in exceptions)});
    Get-ChildItem -Path $folder -File -Recurse | Where-Object {{
        $exceptions -notcontains $_.Name
    }} | Remove-Item -Force
    '''

    # PowerShell über Python ausführen
    subprocess.run(["powershell", "-Command", ps_command], check=True)
        
    name = hashlib.md5(repo_url.encode('utf-8')).hexdigest()
    clone_repo(name)
    
    os.system(f'robocopy {os.path.join(os.getcwd(), name)} {os.getcwd()} /E /XF autoupdater.py setup.py setup.bat /R:0 /W:0')

    py = sys.executable
    os.system(f'{py} -m pip install -r requirements.txt')
    
    ps_command = f'Remove-Item -Path "{os.path.join(os.getcwd(), name)}" -Recurse -Force'

    subprocess.run(["powershell", "-Command", ps_command], check=True)