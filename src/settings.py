import os

from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

DB_HOST = os.environ.get("DB_HOST")
DB_NAME = os.environ.get("DB_NAME")
DB_PORT = int(os.environ.get("DB_PORT", "5432"))
DB_USERNAME = os.environ.get("DB_USERNAME")
DB_PASSWORD = os.environ.get("DB_PASSWORD")

CHROMEDRIVER_PATH = "/usr/local/bin/chromedriver"
