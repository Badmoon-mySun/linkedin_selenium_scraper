import imaplib
import re


class MailRuImap:
    def __init__(self, login, password):
        self.mail = imaplib.IMAP4_SSL('imap.mail.ru')
        self.mail.login(login, password)

    def get_last_message(self) -> str:
        self.mail.select("inbox")
        _, data = self.mail.search(None, "ALL")

        email_ids = data[0].split()
        last_email_id = email_ids[-1]

        _, data = self.mail.fetch(last_email_id, "(RFC822)")

        message = str(data[0][1])
        return message

    def get_last_email_verification_code(self) -> str:
        message = self.get_last_message()

        pattern = re.compile(r'complete your sign in: \d{6}')
        res = pattern.findall(message)

        if res:
            text = res[0]
            code = text.split()[-1]

            return code

        return ''

    def close(self):
        try:
            self.mail.close()
            self.mail.logout()
        except:
            pass
