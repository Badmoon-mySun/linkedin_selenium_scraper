import os
import random
import time


from db import Link, Account
from helpers import NavigationHelper, LoginHelper, VerificationHelper, ProfileHelper
from imap import MailRuImap
from services import bcolors, get_chromedriver


class LinkedInParsing:
    account: Account
    proxy: str

    def __init__(self, account: Account, use_proxy=False):
        self.driver = get_chromedriver(account, use_proxy=use_proxy)
        self.driver.implicitly_wait(30)

        self.base_url = "https://www.linkedin.com/"
        self.accept_next_alert = True

        self.account = account
        self.navigation_helper = NavigationHelper(self.driver, self.base_url)
        self.login_helper = LoginHelper(self.driver, account.email, account.linkedin_password)
        self.verification_helper = VerificationHelper(self.driver)
        self.mail = MailRuImap(account.email, account.email_password)
        self.profile_helper = ProfileHelper(self.driver)

    def __login(self):
        self.navigation_helper.goto_login_page()
        self.login_helper.do_login()

        if self.navigation_helper.is_email_verification_page():
            time.sleep(5)
            code = self.mail.get_last_email_verification_code()
            self.verification_helper.do_verification(code)

        elif self.navigation_helper.is_identity_verification_page():
            print(f'{bcolors.WARNING}Account {self.account.email} has been banned, exit...{bcolors.ENDC}')
            self.account.banned = True
            self.account.save()

        elif self.navigation_helper.is_add_phone_page():
            self.verification_helper.skip_add_phone_page()

    def __start_parsing_iteration(self):
        profile_helper = self.profile_helper
        driver = self.driver

        link = Link.select().filter(is_checked=False).first()
        link.is_checked = True
        link.save()

        driver.get(link.url)
        delay = random.randint(2, 6)
        time.sleep(delay)

        location = profile_helper.get_location()
        if location and 'moscow' in location.text.lower():
            link.is_moscow_location = True
            link.save()

            more_button = profile_helper.get_more_also_viewed_button()
            if more_button:
                try:
                    more_button.click()
                except Exception as ex:
                    print(f'{bcolors.FAIL}{ex}{bcolors.ENDC}')

            viewers = profile_helper.get_also_viewed_members()
            links_data = map(
                lambda el: {'url': el.get_attribute('href')},
                viewers
            )

            Link.insert_many(links_data).on_conflict_ignore().execute()
            delay = random.randint(2, 4)
            time.sleep(delay)

    def start(self):
        is_login_in = False

        while True:
            try:
                if self.account.banned:
                    break

                if self.navigation_helper.is_auth_page():
                    is_login_in = False

                if not is_login_in:
                    self.driver.delete_all_cookies()
                    self.__login()
                    is_login_in = True

                self.__start_parsing_iteration()
            except Exception as ex:
                print(f'{bcolors.FAIL}{ex}{bcolors.ENDC}')

    def stop(self):
        self.driver.quit()
