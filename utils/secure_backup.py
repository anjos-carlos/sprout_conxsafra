import os, io, zipfile
from cryptography.fernet import Fernet

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR = os.path.join(BASE_DIR, "data")
KEY_PATH = os.path.join(DATA_DIR, ".secret.key")
BACKUP_PATH = os.path.join(DATA_DIR, "backup.enc")


# ---------------- AUXILIARES ---------------- #

def generate_key():
    if not os.path.exists(KEY_PATH):
        key = Fernet.generate_key()
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(KEY_PATH, "wb") as f: f.write(key)
    return load_key()

def load_key():
    with open(KEY_PATH, "rb") as f: return f.read()

def delete_files():
    files = [os.path.join(DATA_DIR,f) for f in os.listdir(DATA_DIR) if f.endswith(".csv")]
    for f in files: os.remove(f)


# ---------------- GERENCIADOR ---------------- #

def backup_data():
    files = [os.path.join(DATA_DIR,f) for f in os.listdir(DATA_DIR) if f.endswith(".csv")]
    if not files: return  # Não há CSVs para fazer backup
    
    mem = io.BytesIO()
    with zipfile.ZipFile(mem, "w", zipfile.ZIP_DEFLATED) as z: 
        [z.write(f, os.path.basename(f)) for f in files]
    data = Fernet(load_key()).encrypt(mem.getvalue())
    with open(BACKUP_PATH, "wb") as f: f.write(data)
    delete_files()

def restore_data():
    if not os.path.exists(BACKUP_PATH): return
    data = Fernet(load_key()).decrypt(open(BACKUP_PATH,"rb").read())
    mem = io.BytesIO(data)
    with zipfile.ZipFile(mem, "r") as z: z.extractall(DATA_DIR)