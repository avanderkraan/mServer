import json
from mysql.connector import connect, Error
from mami import db_credentials_file


class DatabaseConnection():
    def __init__(self):
        self.credentials = None

    def get_connection(self):
        try:
            if not self.credentials or self.credentials == {}:
                self.credentials = self._get_credentials()
            return connect(
                host = self.credentials.get('host'),
                user = self.credentials.get('user'),
                password = self.credentials.get('password')
            )
        except Error as e:
            print(e)
        return None

    def _get_credentials(self, name="website"):
        try:
            with open(db_credentials_file) as f:
                read_credentials = f.read()
                all_credentials = json.loads(read_credentials)
                for items in all_credentials:
                    credentials = items.get(name)
                    if credentials:
                        return credentials
            return {}
        except Exception as inst:
            print(inst)
        return {}
