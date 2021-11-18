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


if __name__ == '__main__':
    mail = MailRuImap('maria_nash_1964@inbox.ru', 'MEcetLhHqq7qKZRF6D62')
    code = mail.get_last_email_verification_code()
    print(code)
