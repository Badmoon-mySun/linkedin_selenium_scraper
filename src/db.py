import os.path

import peewee

from settings import ROOT_DIR, DB_NAME, DB_USERNAME, DB_PASSWORD, DB_HOST, DB_PORT, DEBUG

sqlite_db = peewee.SqliteDatabase(
    os.path.join(ROOT_DIR, '../sqlite.db'),
    pragmas={
        'journal_mode': 'wal',
        'cache_size': -1024 * 64}
)

postgres_db = peewee.PostgresqlDatabase(
    DB_NAME, user=DB_USERNAME, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT
)

current_db = sqlite_db if DEBUG else postgres_db


class Link(peewee.Model):
    id = peewee.PrimaryKeyField()
    url = peewee.CharField(max_length=510, unique=True)
    is_checked = peewee.BooleanField(default=False)
    is_moscow_location = peewee.BooleanField(default=False)

    class Meta:
        database = current_db
        table_name = 'link'


class Proxy(peewee.Model):
    id = peewee.PrimaryKeyField()
    protocol = peewee.CharField(max_length=10)
    ip = peewee.CharField(max_length=20, unique=True)
    port = peewee.CharField(max_length=5)
    need_auth = peewee.BooleanField()
    login = peewee.CharField(null=True, max_length=100)
    password = peewee.CharField(null=True, max_length=100)

    class Meta:
        database = current_db
        table_name = 'proxy'


class Account(peewee.Model):
    id = peewee.PrimaryKeyField()
    first_name = peewee.CharField(max_length=50)
    second_name = peewee.CharField(max_length=50)
    email = peewee.CharField(max_length=90, unique=True)
    linkedin_password = peewee.CharField(max_length=50)
    email_password = peewee.CharField(max_length=50)
    account_url = peewee.CharField(max_length=510)
    banned = peewee.BooleanField(default=False)
    proxy = peewee.ForeignKeyField(Proxy, null=True)

    class Meta:
        database = current_db
        table_name = 'account'


class Company(peewee.Model):
    id = peewee.PrimaryKeyField()
    name = peewee.CharField(max_length=255, null=True)
    url = peewee.CharField(max_length=510, null=True)

    class Meta:
        database = current_db
        table_name = 'linkedin_company'


class City(peewee.Model):
    id = peewee.PrimaryKeyField()
    name = peewee.CharField(max_length=100, unique=True, verbose_name='City name')

    def __str__(self):
        return self.name

    class Meta:
        database = current_db
        table_name = 'city'


class Language(peewee.Model):
    id = peewee.PrimaryKeyField()
    name = peewee.CharField(max_length=50, unique=True)

    class Meta:
        database = current_db
        table_name = 'language'


class LinkedInUser(peewee.Model):
    id = peewee.PrimaryKeyField()
    fullname = peewee.CharField(max_length=150, null=True)
    position = peewee.CharField(max_length=250, null=True)
    following = peewee.CharField(max_length=50, null=True)
    about = peewee.TextField(null=True)
    avatar = peewee.CharField(null=True)
    current_company = peewee.ForeignKeyField(Company, null=True, related_name='employees')
    city = peewee.ForeignKeyField(City, null=True)
    languages = peewee.ManyToManyField(Language)
    url = peewee.CharField(max_length=510, null=True)

    class Meta:
        database = current_db
        table_name = 'linkedin_user'


class Education(peewee.Model):
    id = peewee.PrimaryKeyField()
    user = peewee.ForeignKeyField(LinkedInUser, null=True)
    degree = peewee.CharField(max_length=200, null=True)
    institution = peewee.ForeignKeyField(Company, null=True)
    start_year = peewee.IntegerField(null=True)
    direction = peewee.CharField(max_length=150, null=True)
    end_year = peewee.IntegerField(null=True)

    class Meta:
        database = current_db
        table_name = 'linkedin_education'


class Activity(peewee.Model):
    id = peewee.PrimaryKeyField()
    user = peewee.ForeignKeyField(LinkedInUser, null=True)
    title = peewee.TextField(null=True)
    attribution = peewee.TextField(null=True)
    image = peewee.CharField(null=True)
    link = peewee.CharField(null=True)

    class Meta:
        database = current_db
        table_name = 'linkedin_user_activity'


class WorkExperience(peewee.Model):
    id = peewee.PrimaryKeyField()
    company = peewee.ForeignKeyField(Company, null=True)
    user = peewee.ForeignKeyField(LinkedInUser, null=True)
    position = peewee.CharField(max_length=150, null=True)
    description = peewee.TextField(null=True)
    duration = peewee.CharField(max_length=50, null=True)
    start_date = peewee.CharField(max_length=10, null=True)
    end_date = peewee.CharField(max_length=10, null=True)
    until_now = peewee.BooleanField(default=False)

    class Meta:
        database = current_db
        table_name = 'linkedin_work_experience'


class UserContactInfo(peewee.Model):
    id = peewee.PrimaryKeyField()
    user = peewee.ForeignKeyField(LinkedInUser, null=True)
    name = peewee.CharField(max_length=100, null=True)
    url = peewee.CharField(max_length=510, null=True)
    meta = peewee.CharField(max_length=100, null=True)

    class Meta:
        database = current_db
        table_name = 'user_contact_info'


class SiteLink(peewee.Model):
    id = peewee.PrimaryKeyField()
    url = peewee.CharField(max_length=510, unique=True)

    class Meta:
        database = current_db
        table_name = 'site_link'


tables = {
    'proxy': Proxy,
    'link': Link,
    'account': Account,
    'linkedin_company': Company,
    'city': City,
    'language': Language,
    'linkedin_user': LinkedInUser,
    'linkedin_user_activity': Activity,
    'linkedin_education': Education,
    'linkedin_work_experience': WorkExperience,
    'user_contact_info': UserContactInfo,
    'site_link': SiteLink
}

for table_name, model in tables.items():
    if not current_db.table_exists(table_name):
        current_db.create_tables([model])
