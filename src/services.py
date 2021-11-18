import os

from python3_anticaptcha import FunCaptchaTask, FunCaptchaTaskProxyless
from selenium.common.exceptions import NoSuchElementException

from db import Account
from settings import ROOT_DIR


class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def get_account_data(data: list) -> dict:
    return {
        'first_name': data[0],
        'second_name': data[1],
        'email': data[2],
        'linkedin_password': data[3],
        'email_password': data[4],
        'account_url': f'{data[5]}:{data[6]}',
        'banned': False
    }


def load_accounts(filename=os.path.join(ROOT_DIR, 'accounts.csv')):
    accounts = []

    with open(filename, 'r') as file:
        for line in file:
            data = line.strip().split(':')
            account_data = get_account_data(data)
            accounts.append(account_data)

    Account.insert_many(accounts).on_conflict_ignore().execute()


def captcha():
    ANTICAPTCHA_KEY = "52072a12b31d437f42f0c1825bda9fa5"

    SITE_KEY = '3117BF26-4762-4F5A-8ED9-A85E69209A46'

    PAGE_URL = 'https://www.linkedin.com/checkpoint/challenge/AgG0hwLq2DHN3wAAAX0f62b4UmWQEcdMDSRLQpCLw8Ex5koKF-X8usjX-3RRDL75IshkbQ80JCKSvwPEfDcZM-Vrc96HdQ?ut=1KPlrXmcgLiG01'

    result = FunCaptchaTaskProxyless.FunCaptchaTaskProxyless(anticaptcha_key=ANTICAPTCHA_KEY).captcha_handler(
        websiteURL=PAGE_URL, websitePublicKey=SITE_KEY, data=''
    )

    print(result)


if __name__ == '__main__':
    # load_accounts()
    captcha()