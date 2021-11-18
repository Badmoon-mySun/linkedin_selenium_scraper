from multiprocessing import Pool

from db import Account
from parser import LinkedInParsing
from services import bcolors, load_accounts


def worker(account: Account):
    print(f'{bcolors.OKGREEN}Starting parsing with {account.email} account{bcolors.ENDC}')
    LinkedInParsing(account, proxy).start()


if __name__ == "__main__":
    load_accounts()

    accounts = Account.select().filter(banned=False)
    proxy = "socks5://127.0.0.1:9150"

    pools_count = 5

    with Pool(pools_count) as pool:
        pool.map(worker, accounts)
