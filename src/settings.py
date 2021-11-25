import os

from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.join(ROOT_DIR, '..')

DB_HOST = os.environ.get("DB_HOST", '127.0.0.1')
DB_NAME = os.environ.get("DB_NAME", 'linkedin')
DB_PORT = int(os.environ.get("DB_PORT", "5432"))
DB_USERNAME = os.environ.get("DB_USERNAME", 'postgres')
DB_PASSWORD = os.environ.get("DB_PASSWORD", 'linkedin')

CHROMEDRIVER_PATH = "/usr/local/bin/chromedriver"
ANTICAPTCHA_KEY = "52072a12b31d437f42f0c1825bda9fa5"
