from db import Account, Proxy
from python_anticaptcha import AnticaptchaClient, FunCaptchaTask

from settings import ANTICAPTCHA_KEY


class Anticaptcha:
    def __init__(self, account: Account, user_agent: str):
        self.account = account
        self.user_agent = user_agent
        self.api_key = ANTICAPTCHA_KEY
        self.client = AnticaptchaClient(self.api_key)

    def solve_captcha(self, url, site_key):
        proxy: Proxy = self.account.proxy

        task = FunCaptchaTask(
            url,
            site_key,
            proxy_type=proxy.protocol,
            user_agent=self.user_agent,
            proxy_address=proxy.ip,
            proxy_port=proxy.port,
            proxy_login=proxy.login,
            proxy_password=proxy.password
        )

        job = self.client.createTask(task)
        job.join()

        return job.get_token_response()
