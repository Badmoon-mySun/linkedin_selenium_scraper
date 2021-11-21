import json
import os
import zipfile
from random import randrange

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from python3_anticaptcha import FunCaptchaTaskProxyless

from db import Account, Proxy
from settings import ROOT_DIR, CHROMEDRIVER_PATH


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


def load_accounts(filename=os.path.join(ROOT_DIR, '../accounts.csv')):
    accounts = []

    with open(filename, 'r') as file:
        for line in file:
            data = line.strip().split(':')
            account_data = get_account_data(data)
            accounts.append(account_data)

    Account.insert_many(accounts).on_conflict_ignore().execute()


def load_proxy(filename=os.path.join(ROOT_DIR, '../proxy.json')):
    proxies = []

    with open(filename, 'r') as file:
        proxy_info: dict = json.loads(file.read())

        for ip in proxy_info.get('addresses', None):
            proxy = {
                "protocol": proxy_info.get('protocol'),
                "port": proxy_info.get('port'),
                "need_auth": proxy_info.get('login', None) is not None,
                "login": proxy_info.get('login', None),
                "password": proxy_info.get('password', None),
                "ip": ip
            }

            proxies.append(proxy)

    Proxy.insert_many(proxies).on_conflict_ignore().execute()


def add_proxy_to_accounts(accounts: Account):
    proxies = Proxy.select()
    proxies_count = len(proxies)

    if not proxies_count:
        return

    for i in range(len(accounts)):
        proxy = proxies[(i + 10) % proxies_count]
        account = accounts[i]

        if not account.proxy:
            account.proxy = proxy
            account.save()


def get_manifest():
    return """
        {
            "version": "1.0.0",
            "manifest_version": 2,
            "name": "Chrome Proxy",
            "permissions": [
                "proxy",
                "tabs",
                "unlimitedStorage",
                "storage",
                "<all_urls>",
                "webRequest",
                "webRequestBlocking"
            ],
            "background": {
                "scripts": ["background.js"]
            },
            "minimum_chrome_version":"22.0.0"
        }
    """


def get_background_js(protocol, host, port, user, password):
    return """
        var config = {
                mode: "fixed_servers",
                rules: {
                singleProxy: {
                    scheme: "%s",
                    host: "%s",
                    port: parseInt(%s)
                },
                bypassList: ["localhost"]
                }
            };
        
        chrome.proxy.settings.set({value: config, scope: "regular"}, function() {});
        
        function callbackFn(details) {
            return {
                authCredentials: {
                    username: "%s",
                    password: "%s"
                }
            };
        }
        
        chrome.webRequest.onAuthRequired.addListener(
                    callbackFn,
                    {urls: ["<all_urls>"]},
                    ['blocking']
        );
    """ % (protocol, host, port, user, password)


def get_chromedriver(account: Account, use_proxy=False, user_agent=None):
    service = Service(executable_path=CHROMEDRIVER_PATH)
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument('--start-maximized')

    if use_proxy and account.proxy:
        proxy: Proxy = account.proxy

        if proxy.need_auth:
            pluginfile = 'proxy_auth_plugin_%s.zip' % str(randrange(10000))

            with zipfile.ZipFile(pluginfile, 'w') as zp:
                zp.writestr("manifest.json", get_manifest())
                zp.writestr(
                    "background.js", get_background_js(proxy.protocol, proxy.ip,
                                                       proxy.port, proxy.login, proxy.password)
                )

            chrome_options.add_extension(pluginfile)
        else:
            chrome_options.add_argument('--proxy-server=%s://%s:%s' % (proxy.protocol, proxy.ip, proxy.port))

    if user_agent:
        chrome_options.add_argument('--user-agent=%s' % user_agent)

    return webdriver.Chrome(
        service=service,
        chrome_options=chrome_options
    )


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