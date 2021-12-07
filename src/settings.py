import os

from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

DEBUG = os.environ.get('DEBUG', False)

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.join(ROOT_DIR, '..')
LOGGING_CONF_PATH = os.path.join(PROJECT_DIR, 'logging.conf')
META_DIR = os.path.join(PROJECT_DIR, 'meta')

DB_HOST = os.environ.get("DB_HOST", '127.0.0.1')
DB_NAME = os.environ.get("DB_NAME", 'linkedin')
DB_PORT = int(os.environ.get("DB_PORT", "5432"))
DB_USERNAME = os.environ.get("DB_USERNAME", 'postgres')
DB_PASSWORD = os.environ.get("DB_PASSWORD", 'linkedin123')

CHROMEDRIVER_PATH = "/usr/local/bin/chromedriver"
ANTICAPTCHA_KEY = "52072a12b31d437f42f0c1825bda9fa5"

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) " \
             "Chrome/74.0.3729.169 Safari/537.36"
