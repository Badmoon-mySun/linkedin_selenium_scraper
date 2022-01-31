import json
import logging
import os
import pickle
import random
import string
import time
import zipfile
from typing import Optional, List

import peewee
from peewee import fn
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.chrome.service import Service
from python3_anticaptcha import FunCaptchaTaskProxyless
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.command import Command

from db import Account, Proxy, SiteLink, PeopleSearchResult, LinkedInUser, UsernameSearchHistory, AlsoViewed
from settings import ROOT_DIR, CHROMEDRIVER_PATH, PROJECT_DIR, ANTICAPTCHA_KEY, DEBUG, USER_AGENT, META_DIR


def get_random_linkedin_url():
    site_link = SiteLink.select().order_by(fn.Random()).get()
    return site_link.url if site_link else None


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

    j = 0
    for i in range(len(accounts)):
        proxy = proxies[j % proxies_count]
        account = accounts[i]

        if not account.proxy:
            account.proxy = proxy
            account.save()
            j += 1


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
    email = str(account.email).replace('.', '')
    plugin_path = os.path.join(os.path.join(META_DIR, 'plugin'), f'{email}.zip')
    service = Service(executable_path=CHROMEDRIVER_PATH)
    options = webdriver.ChromeOptions()
    options.add_argument("window-size=1280,800")
    options.add_argument('--start-maximized')
    options.add_argument(f"user-agent={USER_AGENT}")
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
            if os.path.exists(plugin_path):
                os.remove(plugin_path)

            with zipfile.ZipFile(plugin_path, 'w') as zp:
                zp.writestr("manifest.json", get_manifest())
                zp.writestr(
                    "background.js", get_background_js(proxy.protocol, proxy.ip,
                                                       proxy.port, proxy.login, proxy.password)
                )

            options.add_extension(plugin_path)
        else:
            options.add_argument('--proxy-server=%s://%s:%s' % (proxy.protocol, proxy.ip, proxy.port))

    if user_agent:
        options.add_argument('--user-agent=%s' % user_agent)

    return webdriver.Chrome(service=service, chrome_options=options)


def set_browser_cookie_if_exist(driver: WebDriver, account: Account):
    email = str(account.email).replace('.', '')
    cookie_path = os.path.join(os.path.join(META_DIR, 'cookie'), email)

    if os.path.exists(cookie_path):
        with open(cookie_path, 'rb') as file:
            for cookie in pickle.load(file):
                driver.add_cookie(cookie)
            time.sleep(5)


def save_browser_cookie(driver: WebDriver, account: Account):
    email = str(account.email).replace('.', '')
    cookie_path = os.path.join(os.path.join(META_DIR, 'cookie'), email)

    try:
        driver.execute(Command.STATUS)

        with open(cookie_path, 'wb') as file:
            pickle.dump(driver.get_cookies(), file)
    finally:
        pass


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


def get_element_or_none(path, item):
    try:
        return item.find_element(By.CSS_SELECTOR, path)
    except NoSuchElementException:
        return None


def get_text_or_none(path, item) -> Optional[str]:
    elem = get_element_or_none(path, item)

    return elem.text if elem else None


def get_elem_attribute_or_none(path, attr_name, item) -> Optional[str]:
    elem = get_element_or_none(path, item)

    return elem.get_attribute(attr_name) if elem else None


def move_to_element(driver, element):
    desired_y = (element.size['height'] / 2) + element.location['y']
    current_y = (driver.execute_script('return window.innerHeight') / 2) + driver.execute_script(
        'return window.pageYOffset')
    scroll_y_by = desired_y - current_y
    driver.execute_script("window.scrollBy(0, arguments[0]);", scroll_y_by)


def get_random_string(length):
    return ''.join((random.choice(string.ascii_lowercase) for x in range(length)))


def save_search_result_that_not_parsed(result: List[PeopleSearchResult]):
    urls = list(map(lambda m: m.url, result))
    fun = lambda tpl: tpl[0]

    r = LinkedInUser.select(LinkedInUser.url).where(LinkedInUser.url << urls)
    saved_urls = list(map(fun, r.tuples()))

    r = PeopleSearchResult.select(PeopleSearchResult.url).where(PeopleSearchResult.url << urls)
    saved_urls += list(map(fun, r.tuples()))

    for item in result:
        if item.url not in saved_urls:
            item.save()


def clean_users_without_name(array: List[PeopleSearchResult]) -> List[PeopleSearchResult]:
    return list(filter(lambda x: x.fullname is not None, array))


def get_people_search_result_count() -> int:
    return (
        PeopleSearchResult
            .select(fn.Count(PeopleSearchResult.url))
            .where(PeopleSearchResult.is_checked == False)
            .scalar()
    )


def random_sleep(min_time=7, max_time=15):
    delay = random.randint(min_time, max_time)
    time.sleep(delay)


def get_random_model_record(model):
    return model.select().order_by(fn.Random()).limit(1)[0]


def get_username_to_search():
    free_names = (
        UsernameSearchHistory
            .select(fn.Count(UsernameSearchHistory.fullname))
            .where(UsernameSearchHistory.is_used == False)
            .scalar()
    )

    if free_names < 10:
        new_views = (
            AlsoViewed
                .select(AlsoViewed.fullname)
                .join(UsernameSearchHistory, peewee.JOIN.LEFT_OUTER,
                      on=(AlsoViewed.fullname == UsernameSearchHistory.fullname))
                .where(UsernameSearchHistory.id.is_null())
                .tuples()
                .execute()
        )

        new_names = list(map(lambda tpl: {'fullname': tpl[0]}, new_views))

        UsernameSearchHistory.insert_many(new_names).on_conflict_ignore().execute()

    return get_random_model_record(UsernameSearchHistory)
