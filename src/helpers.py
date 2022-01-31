import logging
import time
import urllib
from typing import Optional
from urllib.parse import urlparse

from python_anticaptcha import AnticatpchaException
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, ElementClickInterceptedException
from selenium.webdriver.common.by import By

from anticaptcha import Anticaptcha
from db import *
from services import get_element_or_none, get_text_or_none, get_elem_attribute_or_none, move_to_element, \
    get_random_string
from settings import USER_AGENT


class BaseHelper(object):
    def __init__(self, driver):
        self.driver = driver

    def is_element_present(self, how, what):
        try:
            self.driver.find_element(by=how, value=what)
        except NoSuchElementException:
            return False
        return True


class NavigationHelper(BaseHelper):
    def __init__(self, driver, base_url):
        super().__init__(driver)
        self.base_url = base_url

    def go_base_page(self):
        self.driver.get(self.base_url)

    def goto_login_page(self):
        self.driver.get(f'{self.base_url}login?fromSignIn=true&trk=guest_homepage-basic_nav-header-signin')

    def is_verification_page(self):
        return 'checkpoint/challenge/' in self.driver.current_url

    def is_identity_verification_page(self):
        return 'checkpoint/lg/login-submit' in self.driver.current_url \
               or 'checkpoint/lg/login-challenge-submit' in self.driver.current_url

    def is_add_phone_page(self):
        return 'check/add-phone' in self.driver.current_url

    def is_auth_page(self):
        return 'authwall' in self.driver.current_url

    def is_feed_page(self):
        return 'feed/' in self.driver.current_url

    def is_search_page(self):
        return 'search/' in self.driver.current_url

    def goto_feed_page(self):
        self.driver.get(f'{self.base_url}feed?trk=guest_homepage-basic_nav-header-signin')


class LoginHelper(BaseHelper):
    def __init__(self, driver, login, password):
        super().__init__(driver)
        self.login = login
        self.password = password

    def do_login(self):
        driver = self.driver
        driver.find_element_by_id("username").click()
        driver.find_element_by_id("username").clear()
        driver.find_element_by_id("username").send_keys(self.login)
        driver.find_element_by_xpath("//div[@id='organic-div']/form/div[2]").click()
        driver.find_element_by_id("password").click()
        driver.find_element_by_id("password").clear()
        driver.find_element_by_id("password").send_keys(self.password)
        driver.find_element_by_xpath("//button[@type='submit']").click()


class VerificationHelper(BaseHelper):
    driver: webdriver

    def __init__(self, driver):
        super().__init__(driver)

    def skip_add_phone_page(self):
        self.driver.find_element(By.XPATH, '//*[@id="ember455"]/button').click()

    def __email_verification(self, input_pin, code):
        input_pin.click()
        input_pin.clear()
        input_pin.send_keys(code)

        self.driver.find_element(By.XPATH, "//button[@type='submit']").click()

    def __do_captcha_challenge(self, account):
        anticaptcha = Anticaptcha(account, USER_AGENT)
        driver = self.driver
        time.sleep(20)

        url = driver.current_url
        form = driver.find_element(By.CSS_SELECTOR, 'form#captcha-challenge')
        key = form.find_element(By.NAME, 'captchaSiteKey').get_attribute('value')

        token = anticaptcha.solve_captcha(url, key)
        driver.execute_script(f"document.getElementsByName(\"captchaUserResponseToken\")[0].value = \"{token}\"")

        time.sleep(5)
        form.submit()

        time.sleep(5)

    def do_verification(self, code, account):
        logger = logging.getLogger('linkedin.helpers.VerificationHelper.do_verification')
        driver = self.driver

        try:
            element = driver.find_element(By.ID, "input__email_verification_pin")
            self.__email_verification(element, code)
            return
        except NoSuchElementException:
            pass

        try:
            self.__do_captcha_challenge(account)
            return
        except AnticatpchaException as ex:
            logger.error(ex.error_description)
            exit(1)
        except NoSuchElementException:
            pass

        try:
            banner = driver.find_element(By.CSS_SELECTOR, '.app__content h1').text
            time.sleep(4)
            if 'Something isn’t quite right' in banner:
                driver.find_element(By.CSS_SELECTOR, 'label.form__label').click()
                time.sleep(1)
                driver.find_element(By.CSS_SELECTOR, 'button.content__button--primary').click()

                return
        except NoSuchElementException:
            pass

        try:
            elem = driver.find_element(By.CSS_SELECTOR, 'main.app__content h1')
            if "We've restricted your account temporarily" == elem.text:
                logger.warning(f'Account {account.email} has been temporarily banned, exit...')

                account.banned = True
                account.temporarily_banned = True
                account.save()
                exit()
        except NoSuchElementException:
            pass


class UserProfileHelper(BaseHelper):
    driver: webdriver.Chrome

    def __init__(self, driver):
        super(UserProfileHelper, self).__init__(driver)

    def __do_click(self, element) -> bool:
        try:
            if element:
                move_to_element(self.driver, element)
                time.sleep(1)

                element.click()
                return True
        except ElementClickInterceptedException as ex:
            logger = logging.getLogger('linkedin.helpers.UserProfileHelper.__do_click')
            logger.error(ex.stacktrace)

        return False

    @staticmethod
    def __parse_also_vied(viewer) -> dict:
        return {
            'fullname': get_text_or_none('span.name', viewer),
            'position': get_text_or_none('div.inline-show-more-text', viewer),
            'avatar': get_elem_attribute_or_none('img.pv-browsemap-section__member-image', 'src', viewer),
            'url': viewer.get_attribute('href')
        }

    def save_also_vied(self):
        button = get_element_or_none('button.pv3.artdeco-card__action.artdeco-button.artdeco-button--muted',
                                     self.driver)

        self.__do_click(button)

        viewers = self.driver.find_elements(By.CSS_SELECTOR, '.ember-view.pv-browsemap-section__member')
        also_vied = map(lambda el: self.__parse_also_vied(el), viewers)

        AlsoViewed.insert_many(also_vied).on_conflict_ignore().execute()

    def get_fullname(self) -> Optional[str]:
        return get_text_or_none("h1.text-heading-xlarge.inline.t-24.v-align-middle.break-words", self.driver)

    def get_position(self) -> Optional[str]:
        return get_text_or_none("div.text-body-medium.break-words", self.driver)

    def get_about(self) -> Optional[str]:
        return get_text_or_none("section.pv-about-section div", self.driver)

    def get_or_create_current_company(self) -> Optional[Company]:
        company = get_element_or_none('a.pv-text-details__right-panel-item-link', self.driver)

        if not company:
            return None
        url = company.get_attribute('href')

        return Company.get_or_create(name=get_text_or_none('h2 div', company), url=url)[0]

    def get_avatar(self) -> Optional[str]:
        return get_elem_attribute_or_none('img.pv-top-card-profile-picture__image', "src", self.driver)

    def get_city(self) -> Optional[City]:
        city_name = get_text_or_none('span.text-body-small.inline.t-black--light.break-words', self.driver)

        if not city_name:
            return None

        city_name = city_name.lower().split(', ')[0]

        return City.get_or_create(name=city_name)[0]

    def get_following_count(self) -> Optional[str]:
        following_count = get_text_or_none('ul.pv-top-card--list li span', self.driver)

        return following_count.strip() if following_count else None

    @staticmethod
    def __parse_duration(elems):
        duration = []

        if len(elems) > 1:
            for elem in elems[1].text.split('–'):
                text = elem.strip()
                duration.append(text)

        return duration

    def save_experience(self, user: LinkedInUser):
        data = self.driver.find_elements(By.CSS_SELECTOR, 'section.pv-profile-section__card-item-v2')

        for item in data:
            if get_text_or_none('.pv-entity__company-details', item):
                company = Company.get_or_create(
                    name=get_text_or_none('.pv-entity__company-summary-info h3 span:last-child', item),
                    url=get_elem_attribute_or_none('a.full-width.ember-view', 'href', item)
                )[0]

                positions = item.find_elements(By.CSS_SELECTOR, '.pv-entity__position-group-role-item')
                if not positions:
                    positions = item.find_elements(By.CSS_SELECTOR,
                                                   '.pv-entity__position-group-role-item-fading-timeline')

                for position in positions:
                    elem = position.find_elements(By.CSS_SELECTOR, '.pv-entity__date-range span')

                    duration = self.__parse_duration(elem)

                    while len(duration) < 2:
                        duration.append('')

                    ex = WorkExperience.create(
                        company=company.id,
                        user=user.id,
                        position=get_text_or_none('div.pv-entity__summary-info--background-section '
                                                  'h3 span:last-child', position),
                        description=get_text_or_none('.pv-entity__description', position),
                        duration=' '.join(duration),
                        start_date=duration[0],
                        end_date='Present' if duration[1] == 'Present' else duration[1],
                        until_now=True if duration[1] == 'Present' else False
                    )

                    if ex.until_now:
                        user.current_company = company.id
                        user.save()
            else:
                elems = item.find_elements(By.CSS_SELECTOR, 'h4.pv-entity__date-range span')

                duration = self.__parse_duration(elems)

                company = Company.get_or_create(
                    name=get_text_or_none('p.pv-entity__secondary-title', item),
                    url=get_elem_attribute_or_none('a.full-width.ember-view', 'href', item)
                )[0]

                while len(duration) < 2:
                    duration.append('')

                ex = WorkExperience.create(
                    company=company.id,
                    user=user.id,
                    position=get_text_or_none('div.pv-entity__summary-info h3', item),
                    description=get_text_or_none('.pv-entity__description', item),
                    duration=' '.join(duration),
                    start_date=duration[0],
                    end_date='Present' if duration[1] == 'Present' else duration[1],
                    until_now=True if duration[1] == 'Present' else False
                )

                if ex.until_now:
                    user.current_company = company.id
                    user.save()

    def save_education(self, user: LinkedInUser):
        data = self.driver.find_elements(By.CSS_SELECTOR, 'li.pv-education-entity')

        for elem in data:
            institution = Company.get_or_create(
                name=get_text_or_none('h3.pv-entity__school-name', elem),
                url=get_elem_attribute_or_none('a', 'src', elem)
            )[0]

            degrees = elem.find_elements(By.CSS_SELECTOR, 'span.pv-entity__comma-item')
            duration = elem.find_elements(By.CSS_SELECTOR, 'p.pv-entity__dates span time')

            Education.create(
                institution=institution.id,
                user=user.id,
                degree=degrees[0].text if degrees else None,
                direction=degrees[1].text if len(degrees) > 1 else None,
                start_year=duration[0].text if duration else None,
                end_year=duration[1].text if len(duration) > 1 else None
            )

    def save_activity(self, user: LinkedInUser):
        elements = self.driver.find_elements(By.CSS_SELECTOR, 'li.pv-recent-activity-item-v2--expanded')

        for elem in elements:
            Activity.create(
                user=user.id,
                title=get_text_or_none('.pv-recent-activity-item-v2__title div', elem),
                attribution=get_text_or_none('.pv-recent-activity-item-v2__message div', elem),
                image=get_elem_attribute_or_none('img.ivm-view-attr__img--centered', 'src', elem),
                link=get_elem_attribute_or_none('a.pv-recent-activity-item-v2__detail', 'href', elem)
            )

    def save_user_contacts(self, user: LinkedInUser):
        open_button = get_element_or_none('a.ember-view.link-without-visited-state.cursor-pointer', self.driver)

        if not self.__do_click(open_button):
            return

        elements = self.driver.find_elements(By.CSS_SELECTOR, 'section.pv-contact-info__contact-type')

        for elem in elements:
            name = get_text_or_none('pv-contact-info__header', elem)

            link_elements = elem.find_elements(By.CSS_SELECTOR, 'a.pv-contact-info__contact-link')

            for link_elem in link_elements:
                UserContactInfo.create(
                    name=name,
                    user=user.id,
                    url=get_elem_attribute_or_none('a.pv-contact-info__contact-link', 'href', elem),
                    meta=get_text_or_none('span.t-14.t-black--light.t-normal', link_elem)
                )

        close_button = get_element_or_none('button.artdeco-modal__dismiss', self.driver)
        self.__do_click(close_button)

    def close_msg_tab(self):
        if get_element_or_none('.msg-overlay-list-bubble__content', self.driver):
            btn = get_element_or_none('.msg-overlay-bubble-header__control--new-convo-btn:last-child', self.driver)
            if btn:
                btn.click()


class PeopleSearchHelper(BaseHelper):
    driver: webdriver.Chrome
    city_ids = ["100265023", "90010153", "102301812", "103472036", "102084685", "106272742", "90010152",
                "100945174", "100674497", "105245374", "102450862", "90010149", "106769929", "102122368",
                "106843614", "105593862", "90010148", "104523009", "104043205", "100367933", "90010185",
                "107992632", "101777369", "90010146", "104359155", "90010184", "106686604", "90010145",
                "104994045", "101631519"]

    def __init__(self, driver):
        super(PeopleSearchHelper, self).__init__(driver)

    def __clean_city_ids(self):
        result = str(self.city_ids).replace('[', '%5B').replace(']', '%5D')
        return result.replace(' ', '').replace(',', '%2C').replace("'", '%22')

    @staticmethod
    def __clean_user_name(name):
        return urllib.parse.quote_plus(name)

    def find_people_in_big_city(self, name):
        url = 'https://www.linkedin.com/search/results/people/?geoUrn=%s&keywords=%s&origin=FACETED_SEARCH&sid=%s' % (
                    self.__clean_city_ids(), self.__clean_user_name(name), get_random_string(3))

        self.driver.get(url)

    @staticmethod
    def __clean_user_url(url) -> str:
        if url is not None:
            url_parse = urlparse(url)

            url = url_parse.scheme + '://' + url_parse.netloc + url_parse.path + '/'

        return url

    def __get_user_from_li(self, item) -> PeopleSearchResult:
        city_name = get_text_or_none('div.entity-result__secondary-subtitle', item)
        city_name = city_name.lower() if city_name else city_name

        url = get_elem_attribute_or_none('span.entity-result__title-text a', 'href', item)
        url = self.__clean_user_url(url)

        return PeopleSearchResult(
            fullname=get_text_or_none('.entity-result__title-text a span span', item),
            position=get_text_or_none('div.entity-result__primary-subtitle', item),
            avatar=get_elem_attribute_or_none('img.ivm-view-attr__img--centered', 'src', item),
            city=City.get_or_create(name=city_name)[0],
            url=url
        )

    def __get_people_from_search_page(self):
        logger = logging.getLogger('linkedin.helpers.PeopleSearchHelper.__get_people_from_search_page')
        people_blocks = self.driver.find_elements(By.CSS_SELECTOR, 'li.reusable-search__result-container')
        result = []

        for item in people_blocks:
            try:
                result.append(self.__get_user_from_li(item))
            except Exception as ex:
                logger.error(ex, exc_info=True)

        return result

    def get_people_from_search(self):
        def get_button():
            time.sleep(2)
            self.driver.execute_script("window.scrollBy(0, 2000);")
            time.sleep(2)
            return get_element_or_none('button.artdeco-button--icon-right.artdeco-button--1', self.driver)

        logger = logging.getLogger('linkedin.helpers.PeopleSearchHelper.get_people_from_search')

        result = self.__get_people_from_search_page()

        if not result:
            return result

        time.sleep(2)
        button = get_button()

        while button and button.is_enabled():
            logger.info('Search linkedin members, next page')
            button.click()
            time.sleep(4)

            self.driver.execute_script("window.scrollBy(0, document.body.scrollHeight);")
            result += self.__get_people_from_search_page()
            button = get_button()

            if not button:
                button = get_button()

        return result
