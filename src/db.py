import json
import os.path

import peewee

from settings import ROOT_DIR


sqlite_db = peewee.SqliteDatabase(
    os.path.join(ROOT_DIR, '../sqlite.db'),
    pragmas={
        'journal_mode': 'wal',
        'cache_size': -1024 * 64}
)

# postgres_db = peewee.PostgresqlDatabase(
#     DB_NAME, user=DB_USERNAME, password=DB_PASSWORD,host=DB_HOST, port=DB_PORT
# )


class JSONField(peewee.TextField):
    def db_value(self, value):
        return json.dumps(value)

    def python_value(self, value):
        if value is not None:
            return json.loads(value)


class Link(peewee.Model):
    id = peewee.PrimaryKeyField()
    url = peewee.CharField(unique=True)
    is_checked = peewee.BooleanField(default=False)
    is_moscow_location = peewee.BooleanField(default=False)

    class Meta:
        database = sqlite_db
        table_name = 'link'


if not sqlite_db.table_exists('link'):
    sqlite_db.create_tables([Link])


class Proxy(peewee.Model):
    id = peewee.PrimaryKeyField()
    protocol = peewee.CharField(max_length=10)
    ip = peewee.CharField(max_length=20)
    port = peewee.CharField(max_length=5)
    need_auth = peewee.BooleanField()
    login = peewee.CharField(null=True, max_length=100)
    password = peewee.CharField(null=True, max_length=100)

    class Meta:
        database = sqlite_db
        table_name = 'proxy'


if not sqlite_db.table_exists('proxy'):
    sqlite_db.create_tables([Proxy])


class Account(peewee.Model):
    id = peewee.PrimaryKeyField()
    first_name = peewee.CharField(max_length=50)
    second_name = peewee.CharField(max_length=50)
    email = peewee.CharField(max_length=90, unique=True)
    linkedin_password = peewee.CharField(max_length=50)
    email_password = peewee.CharField(max_length=50)
    account_url = peewee.CharField(max_length=150)
    banned = peewee.BooleanField(default=False)
    proxy = peewee.ForeignKeyField(Proxy, null=True)

    class Meta:
        database = sqlite_db
        table_name = 'accounts'


if not sqlite_db.table_exists('accounts'):
    sqlite_db.create_tables([Account])



