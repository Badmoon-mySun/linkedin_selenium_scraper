import time
from typing import Optional

from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium import webdriver

from db import *


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


class ProfileHelper(BaseHelper):
    def __init__(self, driver):
        super(ProfileHelper, self).__init__(driver)

    @staticmethod
    def __get_first_or_none(elements):
        if elements:
            return elements[0]

        return None

    def get_location(self):
        elements = self.driver.find_elements(
            By.XPATH, '//span[@class="text-body-small inline t-black--light break-words"]'
        )

        return self.__get_first_or_none(elements)

    def get_more_also_viewed_button(self):
        elements = self.driver.find_elements(
            By.XPATH,
            '//button[@class="pv3 artdeco-card__action artdeco-button artdeco-button--muted '
            'artdeco-button--icon-right artdeco-button--2 artdeco-button--fluid artdeco-button--tertiary ember-view"]'
        )

        return self.__get_first_or_none(elements)

    def get_also_viewed_members(self):
        return self.driver.find_elements(
            By.XPATH,
            '//a[@class="ember-view pv-browsemap-section__member align-items-center"]'
        )


class UserProfileHelper(BaseHelper):
    driver: webdriver.Chrome

    def __init__(self, driver):
        super(UserProfileHelper, self).__init__(driver)

    def __get_element_or_none(self, path, item=None):
        item = item if item else self.driver
        elements = item.find_elements(By.CSS_SELECTOR, path)

        if elements:
            return elements[0]

        return None

    def __get_text_or_none(self, path, item=None) -> Optional[str]:
        elem = self.__get_element_or_none(path, item)

        return elem.text if elem else None

    def __get_elem_attribute_or_none(self, path, attr_name, item=None) -> Optional[str]:
        elem = self.__get_element_or_none(path, item)

        return elem.get_attribute(attr_name) if elem else None

    def get_fullname(self) -> Optional[str]:
        return self.__get_text_or_none("h1.text-heading-xlarge.inline.t-24.v-align-middle.break-words")

    def get_position(self) -> Optional[str]:
        return self.__get_text_or_none("div.text-body-medium.break-words")

    def get_about(self) -> Optional[str]:
        return self.__get_text_or_none("section.pv-about-section div")

    def get_or_create_current_company(self) -> Company:
        return Company.get_or_create(
            name=self.__get_text_or_none('[data-section="currentPositionsDetails"] .top-card-link'),
            url=self.__get_elem_attribute_or_none('[data-section="currentPositionsDetails"] .top-card-link', 'href')
        )[0]

    def get_avatar(self) -> Optional[str]:
        return self.__get_elem_attribute_or_none('img.pv-top-card-profile-picture__image', "src")

    def get_city(self) -> Optional[City]:
        city_name = self.__get_text_or_none('span.text-body-small.inline.t-black--light.break-words')

        return City.get_or_create(name=city_name)[0] if city_name else None

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
            if self.__get_text_or_none('.pv-entity__company-details'):
                company = Company.get_or_create(
                    name=self.__get_text_or_none('.pv-entity__company-summary-info h3 span:last-child', item),
                    url=self.__get_elem_attribute_or_none('a.full-width.ember-view', 'href', item)
                )[0]

                positions = item.find_elements(By.CSS_SELECTOR, '.pv-entity__position-group-role-item')

                for position in positions:
                    elem = position.find_elements('.pv-entity__date-range span')

                    duration = self.__parse_duration(elem)

                    w = WorkExperience.create(
                        company=company.id,
                        user=user.id,
                        position=self.__get_text_or_none('div.pv-entity__summary-info--background-section '
                                                         'h3 span:last-child', position),
                        description=self.__get_text_or_none('.pv-entity__description', position),
                        duration=' '.join(duration),
                        start_date=duration[0] if duration else None,
                        end_date='Present' if len(duration) > 1 and duration[1] == 'Present' else duration[1],
                        until_now=True if len(duration) > 1 and duration[1] == 'Present' else False
                    )

                    print(w.company, w.user, w.position, w.duration, w.description, w.start_date, w.end_date,
                          w.until_now)
            else:
                elems = item.find_elements(By.CSS_SELECTOR, 'h4.pv-entity__date-range span')

                duration = self.__parse_duration(elems)

                company = Company.get_or_create(
                    name=self.__get_text_or_none('p.pv-entity__secondary-title', item),
                    url=self.__get_elem_attribute_or_none('a.full-width.ember-view', 'href', item)
                )[0]

                w = WorkExperience.create(
                    company=company.id,
                    user=user.id,
                    position=self.__get_text_or_none('div.pv-entity__summary-info h3', item),
                    description=self.__get_text_or_none('.pv-entity__description', item),
                    duration=' - '.join(duration),
                    start_date=duration[0] if duration else None,
                    end_date='Present' if len(duration) > 1 and duration[1] == '- Present' else duration[1],
                    until_now=True if len(duration) > 1 and duration[1] == '- Present' else False
                )
                print(w.company, w.user, w.position, w.duration, w.description, w.start_date, w.end_date, w.until_now)

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
                end_year=duration[1].text if len(duration) else None
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
        if not open_button:
            return

        open_button.click()
        time.sleep(1)
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
        if close_button:
            close_button.click()

