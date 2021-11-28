import logging
import logging.config
from multiprocessing import Pool
from pyvirtualdisplay import Display

from db import Account
from parser import LinkedInParsing
from services import load_accounts, load_proxy, add_proxy_to_accounts
from settings import DEBUG, LOGGING_CONF_PATH

logging.config.fileConfig(LOGGING_CONF_PATH)


def worker(account: Account):
    logger = logging.getLogger('linkedin.main.worker')
    logger.info(f'Starting parsing with {account.email} account')

    LinkedInParsing(account, use_proxy=True).start()


def get_or_load_accounts(load_form_file=False):
    if load_form_file:
        load_proxy()
        load_accounts()

    accounts = Account.select().filter(banned=False)

    if load_form_file:
        add_proxy_to_accounts(accounts)
        
    return accounts


if __name__ == "__main__":
    if not DEBUG:
        display = Display(size=(1920, 1080))
        display.start()

    accounts = get_or_load_accounts(True)

    pools_count = 1 if DEBUG else 2

    with Pool(pools_count) as pool:
        pool.map(worker, accounts)
