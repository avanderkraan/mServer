import re
from mami.data.databaseConnection import DatabaseConnection


class Debug():
    def __init__(self):
        pass
        self.db_connection = DatabaseConnection()
        self.connection = self.db_connection.get_connection()

    def _get_result(self, db_query):
        '''
        remark: the with-statements does not seem to work
                there are issues with the context of it
                and is noted as a bug (somewhere)
        try:
            if not self.credentials or self.credentials == {}:
                self.credentials = self._get_credentials()
            with connect(
                host = self.credentials.get('host'),
                user = self.credentials.get('user'),
                password = self.credentials.get('password')
            ) as connection:
                with connection.cursor() as cursor:
                    cursor.execute(db_query)
                    result = cursor.fetchall()
                    return result
        except Error as e:
            print(e)
        '''
        try:
            cursor = self.connection.cursor()
            cursor.execute(db_query)
            result = cursor.fetchall()
            self.connection.close()  # remove this if it is a singleton
            return result
        except Exception as inst:
            print(inst, 'Check the credentials')
            return None

    def _update_db(self, db_query):
        try:
            cursor = self.connection.cursor()
            cursor.execute(db_query)
            result = cursor.fetchone()
            self.connection.commit()
            self.connection.close()
            return result
        except Exception as inst:
            print(inst, 'Check the credentials')
            return None

    def write_sender_debug_data(self, id=None, change_date='', info=None):
        '''
        Get last record, write only when info data has changed
        '''
        print('a a a', info)
        if id != None and info != None:
            my_query = "SELECT `info` \
                        FROM `mami_debug`.`sender` \
                        WHERE `id_sender` = '%s' \
                        ORDER BY `id` ASC LIMIT 1;" \
                        % id

            result = self._get_result(my_query)

            set_new_value_query = ''
            if len(result) == 0:
                # means a new record,
                set_new_value_query = "INSERT \
                    INTO `mami_debug`.`sender` \
                    (`id_sender`, `info`) \
                    VALUES ('%s', '%s');" \
                    % (id, info)
            else:
                latest_info = result[0][0]

                if (info != latest_info):
                    set_new_value_query = "UPDATE `mami_debug`.`sender` \
                        SET `info` = '%s' \
                        WHERE `id_sender` = '%s';" \
                        % (info, id)
            if set_new_value_query != '':
                # have to make a new connection because self._get_result closed it
                self.db_connection = DatabaseConnection()
                self.connection = self.db_connection.get_connection()

                # write to database when new values have arrived
                result = self._update_db(set_new_value_query)
