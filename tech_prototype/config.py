import os

# Get the directory where this config file is located (tech_prototype/)
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# Data directory is at project root level (one level up from tech_prototype/)
DATA_DIR = os.path.join(_SCRIPT_DIR, '..', 'data')
DATA_DIR = os.path.normpath(DATA_DIR)

if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

YEARS_BACK = 10