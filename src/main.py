from multiprocessing import Pool

from db import Account
from parser import LinkedInParsing
from services import bcolors, load_accounts, load_proxy, add_proxy_to_accounts


def worker(account: Account):
    print(f'{bcolors.OKGREEN}Starting parsing with {account.email} account{bcolors.ENDC}')
    LinkedInParsing(account, use_proxy=True).start()


if __name__ == "__main__":
    load_proxy()
    load_accounts()

    accounts = Account.select().filter(banned=False)
    add_proxy_to_accounts(accounts)

    pools_count = 2

    with Pool(pools_count) as pool:
        pool.map(worker, accounts)
