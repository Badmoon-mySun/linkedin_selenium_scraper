from multiprocessing import Pool

from db import Account
from parser import LinkedInParsing
from services import bcolors, load_accounts, load_proxy, add_proxy_to_accounts


def worker(account: Account):
    print(f'{bcolors.OKGREEN}Starting parsing with {account.email} account{bcolors.ENDC}')
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
    accounts = get_or_load_accounts(True)

    pools_count = 1

    with Pool(pools_count) as pool:
        pool.map(worker, accounts)
