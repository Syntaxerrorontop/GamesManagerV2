import os

APPDATA_CACHE_PATH = os.path.join(os.getenv('APPDATA'), "SyntaxRipper")

CONFIG_FOLDER = os.path.join(APPDATA_CACHE_PATH, "Config")
CACHE_FOLDER = os.path.join(APPDATA_CACHE_PATH, "Cached")
ASSET_FOLDER = os.path.join(APPDATA_CACHE_PATH, "Assets")