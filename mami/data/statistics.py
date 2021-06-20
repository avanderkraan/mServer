import re
from mami.data.databaseConnection import DatabaseConnection


class Statistics():
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

    def write_sender_statistics(self, id=None, change_date='', revolutions=0):
        '''
        Get last record, calculate the new values and write the result back
        '''
        if id != None and int(revolutions) > 0:
            my_query = "SELECT `latest_count`, `revolution_count` \
                        FROM `mami_statistic`.`sender` \
                        WHERE `id_sender` = '%s' \
                            AND date(`change_date`) >= '%s' AND date(`change_date`) <= '%s' \
                        ORDER BY `id` ASC LIMIT 1;" \
                        % (id, change_date, change_date)

            result = self._get_result(my_query)

            set_new_value_query = ''
            if len(result) == 0:
                # means a new day, 
                # latest_count gets value same value as int(revolutions)
                # revolution_count gets value 0
                set_new_value_query = "INSERT \
                    INTO `mami_statistic`.`sender` \
                    (`id_sender`, `latest_count`, `revolution_count`) \
                    VALUES ('%s', '%d', '%d');" \
                    % (id, int(revolutions), 0)
                latest_count = int(revolutions)
                revolution_count = 0
            else:
                latest_count = result[0][0]
                revolution_count = result[0][1]

                if (int(revolutions) != latest_count):
                    if int(revolutions) > latest_count:
                        # sender is internally accumulated
                        revolution_count += int(revolutions) - latest_count
                        latest_count = int(revolutions)
                    else:
                        # caused by a restart of the sender, internally counter = 0
                        revolution_count += int(revolutions)
                        latest_count = int(revolutions)
                    set_new_value_query = "UPDATE `mami_statistic`.`sender` \
                        SET `latest_count` = '%d', \
                            `revolution_count` = '%d' \
                        WHERE `id_sender` = '%s' \
                            AND date(`change_date`) = '%s';" \
                        % (latest_count, revolution_count, id, change_date)
            if set_new_value_query != '':
                # have to make a new connection because self._get_result closed it
                self.db_connection = DatabaseConnection()
                self.connection = self.db_connection.get_connection()

                # write to database when new values have arrived
                result = self._update_db(set_new_value_query)


    def get_sender_statistics(self, id=None, from_date=None, last_date=None):
        '''
        Gets statistics from the sender table, including the dates mentioned
        '''
        my_query = "SELECT `id`, `id_sender`, `change_date`, `revolution_count` \
                    FROM `mami_statistic`.`sender` \
                    WHERE `id_sender` = '%s' \
                        AND date(change_date) >= '%s' AND date(change_date) <= '%s' \
                    ORDER BY `change_date` ASC;" \
                    % (id, from_date, last_date)

        result = self._get_result(my_query)
        return result

