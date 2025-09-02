import os
from . import secure_backup, manager, models

def _init_secure_data():
    secure_backup.generate_key()
    data_dir = secure_backup.DATA_DIR
    csvs = [f for f in os.listdir(data_dir) if f.endswith(".csv")]
    if csvs: secure_backup.backup_data()
_init_secure_data()