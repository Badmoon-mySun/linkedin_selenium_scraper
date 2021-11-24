import time
from typing import Optional

from selenium.common.exceptions import NoSuchElementException, ElementClickInterceptedException
from selenium.webdriver.common.by import By
from selenium import webdriver

from db import *
from services import logger, bcolors


class BaseHelper(object):
    def __init__(self, driver):
        self.driver = driver

    def is_element_present(self, how, what):
        try:
            self.driver.find_element(by=how, value=what)
        except NoSuchElementException as e:
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

    def is_email_verification_page(self):
        if 'checkpoint/challenge/' in self.driver.current_url:
            return True

        return False

    def is_identity_verification_page(self):
        if 'checkpoint/lg/login-submit' in self.driver.current_url:
            return True

        return False

    def is_add_phone_page(self):
        if 'check/add-phone' in self.driver.current_url:
            return True

        return False

    def is_auth_page(self):
        if 'authwall' in self.driver.current_url:
            return True

        return False


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
    def __init__(self, driver):
        super().__init__(driver)

    def skip_add_phone_page(self):
        self.driver.find_element(By.XPATH, '//*[@id="ember455"]/button').click()

    def do_verification(self, code):
        driver = self.driver

        elements = driver.find_elements(By.ID, "input__email_verification_pin")

        if elements:
            input_pin = elements[0]

            input_pin.click()
            input_pin.clear()
            input_pin.send_keys(code)

            driver.find_element(By.XPATH, "//button[@type='submit']").click()
        else:
            print('verification')
            time.sleep(6000)
            pass


class UserProfileHelper(BaseHelper):
    driver: webdriver.Chrome

    def __init__(self, driver):
        super(UserProfileHelper, self).__init__(driver)

    def __get_element_or_none(self, path, item=None):
        item = item if item else self.driver

        try:
            return item.find_element(By.CSS_SELECTOR, path)
        except NoSuchElementException:
            return None

    def __get_text_or_none(self, path, item=None) -> Optional[str]:
        elem = self.__get_element_or_none(path, item)

        return elem.text if elem else None

    def __get_elem_attribute_or_none(self, path, attr_name, item=None) -> Optional[str]:
        elem = self.__get_element_or_none(path, item)

        return elem.get_attribute(attr_name) if elem else None

    def __move_to_element(self, element):
        desired_y = (element.size['height'] / 2) + element.location['y']
        current_y = (self.driver.execute_script('return window.innerHeight') / 2) + self.driver.execute_script(
            'return window.pageYOffset')
        scroll_y_by = desired_y - current_y
        self.driver.execute_script("window.scrollBy(0, arguments[0]);", scroll_y_by)

    def __do_click(self, element) -> bool:
        try:
            if element:
                self.__move_to_element(element)
                time.sleep(1)

                element.click()
                return True
        except ElementClickInterceptedException as ex:
            logger(ex, bcolors.FAIL)

        return False

    def save_also_vied(self):
        button = self.__get_element_or_none('button.pv3.artdeco-card__action.artdeco-button.artdeco-button--muted')

        self.__do_click(button)

        viewers = self.driver.find_elements(By.CSS_SELECTOR, '.ember-view.pv-browsemap-section__member')
        links_data = map(lambda el: {'url': el.get_attribute('href')}, viewers)

        Link.insert_many(links_data).on_conflict_ignore().execute()

    def get_fullname(self) -> Optional[str]:
        return self.__get_text_or_none("h1.text-heading-xlarge.inline.t-24.v-align-middle.break-words")

    def get_position(self) -> Optional[str]:
        return self.__get_text_or_none("div.text-body-medium.break-words")

    def get_about(self) -> Optional[str]:
        return self.__get_text_or_none("section.pv-about-section div")

    def get_or_create_current_company(self) -> Optional[Company]:
        company = self.__get_element_or_none('a.pv-text-details__right-panel-item-link')

        if not company:
            return None
        url = company.get_attribute('href')

        return Company.get_or_create(name=self.__get_text_or_none('h2 div', company), url=url)[0]

    def get_avatar(self) -> Optional[str]:
        return self.__get_elem_attribute_or_none('img.pv-top-card-profile-picture__image', "src")

    def get_city(self) -> Optional[City]:
        city_name = self.__get_text_or_none('span.text-body-small.inline.t-black--light.break-words')

        if not city_name:
            return None

        city_name = city_name.lower().split(', ')[0]

        return City.get_or_create(name=city_name)[0]

    def get_following_count(self) -> Optional[str]:
        following_count = self.__get_text_or_none('ul.pv-top-card--list li span')

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
            if self.__get_text_or_none('.pv-entity__company-details', item):
                company = Company.get_or_create(
                    name=self.__get_text_or_none('.pv-entity__company-summary-info h3 span:last-child', item),
                    url=self.__get_elem_attribute_or_none('a.full-width.ember-view', 'href', item)
                )[0]

                positions = item.find_elements(By.CSS_SELECTOR, '.pv-entity__position-group-role-item')

                for position in positions:
                    elem = position.find_elements(By.CSS_SELECTOR, '.pv-entity__date-range span')

                    duration = self.__parse_duration(elem)

                    while len(duration) < 2:
                        duration.append(None)

                    WorkExperience.create(
                        company=company.id,
                        user=user.id,
                        position=self.__get_text_or_none('div.pv-entity__summary-info--background-section '
                                                         'h3 span:last-child', position),
                        description=self.__get_text_or_none('.pv-entity__description', position),
                        duration=' '.join(duration),
                        start_date=duration[0],
                        end_date='Present' if duration[1] == 'Present' else duration[1],
                        until_now=True if duration[1] == 'Present' else False
                    )
            else:
                elems = item.find_elements(By.CSS_SELECTOR, 'h4.pv-entity__date-range span')

                duration = self.__parse_duration(elems)

                company = Company.get_or_create(
                    name=self.__get_text_or_none('p.pv-entity__secondary-title', item),
                    url=self.__get_elem_attribute_or_none('a.full-width.ember-view', 'href', item)
                )[0]

                while len(duration) < 2:
                    duration.append(None)

                WorkExperience.create(
                    company=company.id,
                    user=user.id,
                    position=self.__get_text_or_none('div.pv-entity__summary-info h3', item),
                    description=self.__get_text_or_none('.pv-entity__description', item),
                    duration=' - '.join(duration),
                    start_date=duration[0],
                    end_date='Present' if duration[1] == '- Present' else duration[1],
                    until_now=True if duration[1] == '- Present' else False
                )

    def save_education(self, user: LinkedInUser):
        data = self.driver.find_elements(By.CSS_SELECTOR, 'li.pv-education-entity')

        for elem in data:
            institution = Company.get_or_create(
                name=self.__get_text_or_none('h3.pv-entity__school-name', elem),
                url=self.__get_elem_attribute_or_none('a', 'src', elem)
            )[0]

            degrees = elem.find_elements(By.CSS_SELECTOR, 'span.pv-entity__comma-item')
            duration = elem.find_elements(By.CSS_SELECTOR, 'p.pv-entity__dates span time')

            Education(
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
                title=self.__get_text_or_none('.pv-recent-activity-item-v2__title div', elem),
                attribution=self.__get_text_or_none('.pv-recent-activity-item-v2__message div', elem),
                image=self.__get_elem_attribute_or_none('img.ivm-view-attr__img--centered', 'src', elem),
                link=self.__get_elem_attribute_or_none('a.pv-recent-activity-item-v2__detail', 'href', elem)
            )

    def save_user_contacts(self, user: LinkedInUser):
        open_button = self.__get_element_or_none('a.ember-view.link-without-visited-state.cursor-pointer')

        if not self.__do_click(open_button):
            return

        elements = self.driver.find_elements(By.CSS_SELECTOR, 'section.pv-contact-info__contact-type')

        for elem in elements:
            name = self.__get_text_or_none('pv-contact-info__header', elem)

            link_elements = elem.find_elements(By.CSS_SELECTOR, 'a.pv-contact-info__contact-link')

            for link_elem in link_elements:
                UserContactInfo.create(
                    name=name,
                    user=user.id,
                    url=self.__get_elem_attribute_or_none('a.pv-contact-info__contact-link', 'href', elem),
                    meta=self.__get_text_or_none('span.t-14.t-black--light.t-normal', link_elem)
                )

        close_button = self.__get_element_or_none('button.artdeco-modal__dismiss')
        self.__do_click(close_button)
