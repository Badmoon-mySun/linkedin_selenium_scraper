import datetime
import logging
import random
import sys
import time
from imaplib import IMAP4

from peewee import InternalError

from db import Account, LinkedInUser, current_db, PeopleSearchResult, AlsoViewed
from helpers import NavigationHelper, LoginHelper, VerificationHelper, UserProfileHelper, PeopleSearchHelper
from imap import MailRuImap
from services import get_chromedriver, get_random_linkedin_url, save_browser_cookie, set_browser_cookie_if_exist, \
    save_search_result_that_not_parsed, get_people_search_result_count, random_sleep, \
    get_random_model_record, get_username_to_search, clean_users_without_name

MIN_USER_COUNT = 100

class LinkedInParsing:
    account: Account
    proxy: str

    def __init__(self, account: Account, use_proxy=False):
        self.driver = get_chromedriver(account, use_proxy=use_proxy)
        self.driver.implicitly_wait(2)

        self.base_url = "https://www.linkedin.com/"
        self.accept_next_alert = True

        self.account = account
        self.navigation_helper = NavigationHelper(self.driver, self.base_url)
        self.login_helper = LoginHelper(self.driver, account.email, account.linkedin_password)
        self.verification_helper = VerificationHelper(self.driver)
        self.mail = MailRuImap(account.email, account.email_password)
        self.user_profile_helper = UserProfileHelper(self.driver)
        self.people_search_helper = PeopleSearchHelper(self.driver)

    def __login(self):
        logger = logging.getLogger('linkedin.parser.LinkedInParsing.__login')
        self.navigation_helper.goto_login_page()
        self.login_helper.do_login()

        while self.navigation_helper.is_verification_page():
            time.sleep(5)
            code = self.mail.get_last_email_verification_code()
            self.verification_helper.do_verification(code, self.account)

        if self.navigation_helper.is_identity_verification_page():
            logger.warning(f'Account {self.account.email} has been banned, exit...')

            self.account.banned = True
            self.account.save()
        elif self.navigation_helper.is_add_phone_page():
            self.verification_helper.skip_add_phone_page()

        self.navigation_helper.goto_feed_page()
        if not self.navigation_helper.is_feed_page():
            raise Exception('Attempt to login failed')

    def __search_linkedin_members(self, fullname):
        logger = logging.getLogger('linkedin.parser.LinkedInParsing.__search_linkedin_members')

        self.people_search_helper.find_people_in_big_city(fullname)

        if self.navigation_helper.is_search_page():
            logger.info(f"Account: {self.account.email} -- Search linkedin members with name {fullname}")
            peoples = self.people_search_helper.get_people_from_search()

            peoples = clean_users_without_name(peoples)
            save_search_result_that_not_parsed(peoples)

            logger.info(f"Account: {self.account.email} -- Search linkedin members with "
                        f"name {fullname} complite, {len(peoples)} found")

    def save_user_info(self):
        helper = self.user_profile_helper

        user = LinkedInUser.create(
            fullname=helper.get_fullname(),
            about=helper.get_about(),
            avatar=helper.get_avatar(),
            following=helper.get_following_count(),
            city=helper.get_city(),
            position=helper.get_position(),
            url=self.driver.current_url
        )

        helper.save_experience(user)
        helper.save_activity(user)
        helper.save_education(user)
        helper.save_user_contacts(user)

    def do_random_actions(self):
        logger = logging.getLogger('linkedin.parser.LinkedInParsing.do_random_actions')
        driver = self.driver

        for i in range(random.randint(2, 5)):
            url = get_random_linkedin_url()
            driver.get(url)
            logger.info('Go to random linkedin url: %s' % url)
            random_sleep(9, 20)

    def __start_parsing_iteration(self):
        logger = logging.getLogger('linkedin.parser.LinkedInParsing.__start_parsing_iteration')
        profile_helper = self.user_profile_helper
        driver = self.driver

        user_for_parsing_count = get_people_search_result_count()
        logger.info(f'Account: {self.account.email} -- PeopleSearchResult records count = %s' % user_for_parsing_count)

        if not user_for_parsing_count < MIN_USER_COUNT:
            search_result = get_random_model_record(PeopleSearchResult)
            logger.info(f'Account: {self.account.email} -- Parsing user %s' % search_result.url)
            driver.get(search_result.url)

            self.user_profile_helper.close_msg_tab()
            profile_helper.save_also_vied()

            random_sleep()

            self.save_user_info()

            search_result.is_checked = True
            search_result.save()
        else:
            username_model = get_username_to_search()
            name = username_model.fullname

            self.__search_linkedin_members(name)

            username_model.is_used = True
            username_model.save()

        random_sleep(2, 6)

    def start(self, end_after_hour=sys.maxsize):
        logger = logging.getLogger('linkedin.parser.LinkedInParsing.start')
        start_date = datetime.datetime.now()
        now = datetime.datetime.now() - start_date
        user_count = random.randint(4, 8)
        is_login_in = False
        i = 0

        try:
            self.navigation_helper.go_base_page()
            set_browser_cookie_if_exist(self.driver, self.account)
            self.navigation_helper.goto_feed_page()
            if self.navigation_helper.is_feed_page():
                is_login_in = True
        except Exception as ex:
            logger.error(ex, exc_info=True)

        while not self.account.banned and now.seconds / 3600 < end_after_hour:
            try:
                logger.info(f'Account: {self.account.email} -- Account work: %.2f minutes %s seconds' %
                            (now.seconds / 60, now.seconds))

                if self.navigation_helper.is_auth_page():
                    is_login_in = False

                if not is_login_in:
                    self.driver.delete_all_cookies()
                    self.__login()
                    if self.account.banned:
                        break

                    is_login_in = True

                if i < user_count:
                    self.__start_parsing_iteration()
                else:
                    self.do_random_actions()
                    user_count = random.randint(4, 8)
                    i = -1

            except InternalError as ex:
                logger.error(ex, exc_info=True)
                current_db.rollback()

            except IMAP4.abort as ex:
                logger.error(ex, exc_info=True)
                self.mail.close()
                self.mail = MailRuImap(self.account.email, self.account.email_password)

            except Exception as ex:
                logger.error(ex, exc_info=True)
                self.driver.refresh()

            now = datetime.datetime.now() - start_date
            i += 1

    def stop(self):
        save_browser_cookie(self.driver, self.account)
        self.mail.close()
        self.driver.quit()
