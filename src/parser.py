import logging
import random
import sys
import time
import traceback

import peewee

from db import Link, Account, LinkedInUser
from helpers import NavigationHelper, LoginHelper, VerificationHelper, UserProfileHelper
from imap import MailRuImap
from services import get_chromedriver


def random_sleep(min_time=7, max_time=15):
    delay = random.randint(min_time, max_time)
    time.sleep(delay)


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

    def __login(self):
        self.navigation_helper.goto_login_page()
        self.login_helper.do_login()

        while self.navigation_helper.is_verification_page():
            time.sleep(5)
            code = self.mail.get_last_email_verification_code()
            self.verification_helper.do_verification(code)

        if self.navigation_helper.is_identity_verification_page():
            logger = logging.getLogger('linkedin.parser.LinkedInParsing.__login')
            logger.warning(f'Account {self.account.email} has been banned, exit...')

            self.account.banned = True
            self.account.save()

        elif self.navigation_helper.is_add_phone_page():
            self.verification_helper.skip_add_phone_page()

        self.navigation_helper.goto_feed_page()
        if not self.navigation_helper.is_feed_page():
            raise Exception('Attempt to login failed')

        self.user_profile_helper.close_msg_tab()

    def __start_parsing_iteration(self):
        logger = logging.getLogger('linkedin.parser.LinkedInParsing.__start_parsing_iteration')
        profile_helper = self.user_profile_helper
        driver = self.driver

        link = Link.select().filter(is_checked=False).first()
        link.is_checked = True
        link.save()

        driver.get(link.url)
        random_sleep()

        city = profile_helper.get_city()
        logger.info('Parsing user: %s has city: %s' % (link.url, city.name))
        if city and city.name and 'moscow' in city.name:
            link.is_moscow_location = True
            link.save()

            profile_helper.save_also_vied()

            random_sleep()

            self.save_user_info(city)

        random_sleep(2, 6)

    def save_user_info(self, city):
        helper = self.user_profile_helper

        user = LinkedInUser.create(
            fullname=helper.get_fullname(),
            about=helper.get_about(),
            avatar=helper.get_avatar(),
            following=helper.get_following_count(),
            city=city.id if city else None,
            position=helper.get_position(),
            url=self.driver.current_url
        )

        helper.save_experience(user)
        helper.save_activity(user)
        helper.save_education(user)
        helper.save_user_contacts(user)

    def do_random_actions(self):
        driver = self.driver

        urls = [
            "https://www.linkedin.com/feed/",
            "https://www.linkedin.com/premium/survey/?destRedirectURL=https%3A%2F%2Fwww.linkedin.com%2Ffeed%2F%3FshowPremiumWelcomeBanner%3Dtrue&upsellOrderOrigin=premium_homepage_identity_upsell",
            "https://www.linkedin.com/jobs/",
            "https://www.linkedin.com/mynetwork/",
            "https://www.linkedin.com/feed/following/?filterType=member",
            "https://www.linkedin.com/mynetwork/discover-hub/",
            "https://linkedin.com/mynetwork/network-manager/newsletters/",
            "https://www.linkedin.com/notifications/",
            "https://www.linkedin.com/company/exxonmobil/mycompany/verification/",
            "https://www.linkedin.com/messaging/thread/new/",
            "https://www.linkedin.com/company/capgemini/",
            "https://www.linkedin.com/showcase/capgemini-fs/",
            "https://www.linkedin.com/company/bearingpoint/",
            "https://www.linkedin.com/feed/following/?filterType=channel&focused=true",
            "https://www.linkedin.com/company/hihk/?isFollowingPage=true",
            "https://www.linkedin.com/mynetwork/import-contacts/saved-contacts/",
            "https://www.linkedin.com/feed/following/?filterType=company",
            "https://www.linkedin.com/feed/followers/",
            "https://www.linkedin.com/learning/?trk=nav_neptune_learning",
            "https://www.linkedin.com/salary?trk=d_flagship3_nav",
            "https://www.linkedin.com/salary/software-engineer-salaries-in-san-francisco-bay-area",
            "https://www.linkedin.com/groups/",
            "https://www.linkedin.com/talent/post-a-job?trk=nav_app_launcher_job_post_nept",
            "https://www.linkedin.com/insights?trk=nav_app_launcher_insights_nept&src=li-nav",
        ]

        url = random.choice(urls)
        for i in range(random.randint(1, 4)):
            driver.get(url)
            random_sleep(9, 20)

    def start(self):
        logger = logging.getLogger('linkedin.parser.LinkedInParsing.start')
        is_login_in = False
        i = 0

        while not self.account.banned:
            try:
                if self.navigation_helper.is_auth_page():
                    is_login_in = False

                if not is_login_in:
                    self.driver.delete_all_cookies()
                    self.__login()
                    if self.account.banned:
                        break

                    is_login_in = True

                if i < 7:
                    self.__start_parsing_iteration()
                else:
                    self.do_random_actions()
                    i = -1

            except Exception as ex:
                logger.error(ex, exc_info=True)

                self.driver.refresh()

            i += 1

    def stop(self):
        self.driver.quit()
