import json
import logging
import os
import time
import zipfile
from random import randrange

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from python3_anticaptcha import FunCaptchaTaskProxyless

from db import Account, Proxy
from settings import ROOT_DIR, CHROMEDRIVER_PATH, PROJECT_DIR, ANTICAPTCHA_KEY, DEBUG


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

        for ip in proxy_info.get('addresses'):
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
    options = webdriver.ChromeOptions()
    options.add_argument("window-size=1280,800")
    options.add_argument('--start-maximized')
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_experimental_option("prefs", {
        "credentials_enable_service": False,
        "profile.password_manager_enabled": False
    })

    if not DEBUG:
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--no-sandbox")

    if use_proxy and account.proxy:
        proxy: Proxy = account.proxy

        if proxy.need_auth:
            plugin_file = 'proxy_auth_plugin_%s.zip' % str(randrange(10000))
            plugin_file = os.path.join(os.path.join(PROJECT_DIR, 'plugins'), plugin_file)

            with zipfile.ZipFile(plugin_file, 'w') as zp:
                zp.writestr("manifest.json", get_manifest())
                zp.writestr(
                    "background.js", get_background_js(proxy.protocol, proxy.ip,
                                                       proxy.port, proxy.login, proxy.password)
                )

            options.add_extension(plugin_file)
        else:
            options.add_argument('--proxy-server=%s://%s:%s' % (proxy.protocol, proxy.ip, proxy.port))

    if user_agent:
        options.add_argument('--user-agent=%s' % user_agent)

    return webdriver.Chrome(
        service=service,
        chrome_options=options
    )


def solve_captcha(url, key) -> str:
    logger = logging.getLogger('linkedin.service.solve_captcha')
    fun_captcha = FunCaptchaTaskProxyless.FunCaptchaTaskProxyless(anticaptcha_key=ANTICAPTCHA_KEY)

    i = 0
    while i < 5:
        result = fun_captcha.captcha_handler(websiteURL=url, websitePublicKey=key, data='')
        error_id = result.get('errorId', -1)

        if error_id == 0:
            break

        logger.info('captcha task, result: %s' % result)
        time.sleep(20)
        i += 1

    status = result.get('status', None)
    if status and status == 'ready':
        solution = result.get('solution', None)
        if solution:
            token = solution.get('token', None)
            if token:
                return token

    raise Exception('Exception in solve captcha: %s' % result)
