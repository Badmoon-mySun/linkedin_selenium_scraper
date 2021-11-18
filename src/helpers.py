import time

from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By


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
