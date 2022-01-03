import re
import json
from mami.data.databaseConnection import DatabaseConnection


class Database():
    '''
    singleton class
    '''
    '''
    _instance = None
    def __new__(class_, *args, **kwargs):
        if not isinstance(class_._instance, class_):
            class_._instance = object.__new__(class_, *args, **kwargs)
            class_.db_connection = DatabaseConnection()
            class_.connection = class_.db_connection.get_connection()
        return class_._instance
    '''

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

    def get_feature_from_mac_address(self, mac_address=None):
        my_query = "SELECT \
                    mami_role.sender.id_sender, \
                    mami_role.sender.name, \
                    mami_role.sender.city, \
                    mami_role.sender.longitude, \
                    mami_role.sender.latitude, \
                    mami_identification.authorisation.authorisation_key \
                    FROM mami_identification.authorisation, \
                        mami_role.sender \
                    WHERE mami_role.sender.active = 1 \
                    AND mami_identification.authorisation.id = mami_role.sender.authorisation_key \
                    AND mami_identification.authorisation.authorisation_key = '%s';" \
                    % mac_address

        result = self._get_result(my_query)
        feature = ''
        if result:
            item = result[0]
            feature = '{ \
                    "geometry": { \
                    "type": "Point", \
                    "coordinates": [ \
                        %f, \
                        %f  \
                    ] \
                }, \
                "type": "Feature", \
                "properties": { \
                    "name": "%s", \
                    "city": "%s", \
                    "mac_address": "%s" \
                }, \
                "id": "%s" \
            }' % (float(item[3]), float(item[4]), item[1], item[2], item[5], item[0])
        return json.loads(feature)

    def get_all_ids_properties(self):
        '''
        property.update({'longitude': '%f' % float(item[3])})
        property.update({'latitude': '%f' % float(item[4])})
        property.update({'name': '%s' % item[1]})
        property.update({'city': '%s' % item[2]})
        property.update({'mac_address': '%s' % item[5]})
        property.update({'id': '%s' % item[0]})
        '''

        my_query = "SELECT \
                    mami_role.sender.id_sender, \
                    mami_role.sender.name, \
                    mami_role.sender.city, \
                    mami_role.sender.longitude, \
                    mami_role.sender.latitude, \
                    mami_identification.authorisation.authorisation_key \
                    FROM mami_identification.authorisation, \
                        mami_role.sender \
                    WHERE mami_role.sender.active = 1 \
                    AND mami_identification.authorisation.id = mami_role.sender.authorisation_key;"
        
        result = self._get_result(my_query)
        features = {}
        try:
            for item in result:
                property = {}
                property.update({'longitude': '%f' % float(item[3])})
                property.update({'latitude': '%f' % float(item[4])})
                property.update({'name': '%s' % item[1]})
                property.update({'city': '%s' % item[2]})
                property.update({'mac_address': '%s' % item[5]})
                property.update({'id': '%s' % item[0]})
                features['%s' % item[0]] = property
        except:
            pass
        return features

    def get_features_as_json(self):
        '''
        {
        "type": "FeatureCollection",
        "features": [
            {
                "geometry": {
                    "type": "Point",
                    "coordinates": [
                        4.497779,
                        52.053169
                    ]
                },
                "type": "Feature",
                "properties": {
                    "name": "De Hoop",
                    "mac_address": "84:CC:A8:A0:FE:2D"
                },
                "id": "00937"
            }
        ]
        '''

        my_query = "SELECT \
                    mami_role.sender.id_sender, \
                    mami_role.sender.name, \
                    mami_role.sender.city, \
                    mami_role.sender.longitude, \
                    mami_role.sender.latitude, \
                    mami_identification.authorisation.authorisation_key \
                    FROM mami_identification.authorisation, \
                        mami_role.sender \
                    WHERE mami_role.sender.active = 1 \
                    AND mami_identification.authorisation.id = mami_role.sender.authorisation_key;"
        
        result = self._get_result(my_query)
        features = '{ \
        "type": "FeatureCollection", \
        "features":['
        feature_items = ''
        for item in result:
            feature = '{ \
                    "geometry": { \
                    "type": "Point", \
                    "coordinates": [ \
                        %f, \
                        %f  \
                    ] \
                }, \
                "type": "Feature", \
                "properties": { \
                    "name": "%s", \
                    "city": "%s", \
                    "mac_address": "%s" \
                }, \
                "id": "%s" \
            },'

            feature_items += feature % (float(item[3]), float(item[4]), item[1], item[2], item[5], item[0])
        features += feature_items[:-1]  # remove last character (comma)
        features += ']}'
        return features

    def get_senders_as_json(self):
        '''
        {
            "A0:20:A6:29:18:13": {
                "comment": "de Roos",
                "key": "88888888-4444-4444-4444-121212121212",
                "previous_key": "88888888-4444-4444-4444-121212121212",
                "record_change_date": "",
                "ttl": "",
                "end_date": "",
                "proposed_key": "88888888-4444-4444-4444-121212121212"
            }
        },
        '''
        my_query = "SELECT \
                    mami_identification.authorisation.authorisation_key \
                    FROM mami_identification.authorisation, \
                        mami_role.sender \
                    WHERE mami_role.sender.active = 1 \
                    AND mami_identification.authorisation.id = mami_role.sender.authorisation_key;"

        result = self._get_result(my_query)
        senders = '['
        for item in result:
            sender = '{"%s" \
                :{ \
                "key":"%s", \
                "previous_key": "%s", \
                "record_change_date": "%s", \
                "ttl": "%s", \
                "end_date": "%s", \
                "proposed_key": "%s" \
                } \
                },'
            senders += sender % (item[0],
                                '88888888-4444-4444-4444-121212121212',
                                '88888888-4444-4444-4444-121212121212',
                                '',
                                '',
                                '',
                                '88888888-4444-4444-4444-121212121212')
        senders = senders[:-1]  # remove last character (comma)
        senders += ']'          
        return senders

    def get_models_as_json(self):
        '''
        {
            "84:CC:A8:B2:29:92": {
                "comment": "test motor",
                "key": "88888888-4444-4444-4444-121212121212",
                "previous_key": "88888888-4444-4444-4444-121212121212",
                "record_change_date": "",
                "ttl": "",
                "end_date": "",
                "proposed_key": "e5bace70-bbee-4c3c-84eb-cfcdcd177db5"
            }
        },
        '''
        my_query = "SELECT \
                    mami_identification.authorisation.authorisation_key \
                    FROM mami_identification.authorisation, \
                        mami_role.model \
                    WHERE mami_role.model.active = 1 \
                    AND mami_identification.authorisation.id = mami_role.model.authorisation_key;"

        result = self._get_result(my_query)
        models = '['
        for item in result:
            model = '{"%s" \
                :{ \
                "key":"%s", \
                "previous_key": "%s", \
                "record_change_date": "%s", \
                "ttl": "%s", \
                "end_date": "%s", \
                "proposed_key": "%s" \
                } \
                },'
            models += model % (item[0],
                                '88888888-4444-4444-4444-121212121212',
                                '88888888-4444-4444-4444-121212121212',
                                '',
                                '',
                                '',
                                '88888888-4444-4444-4444-121212121212')
        models = models[:-1]  # remove last character (comma)
        models += ']'          
        return models

    def get_active_sender_data(self):
        my_query = "SELECT \
                    mami_role.sender.id_sender, \
                    mami_role.sender.name, \
                    mami_role.sender.city, \
                    mami_role.sender.longitude, \
                    mami_role.sender.latitude \
                    FROM mami_role.sender \
                    WHERE mami_role.sender.active = 1;"
        result = self._get_result(my_query)
        return result

    def get_sender_ratio(self, id=""):
        '''
        id contains the id_sender
        '''
        my_query = "SELECT \
                    mami_role.sender.ratio \
                    FROM mami_role.sender \
                    WHERE mami_role.sender.id_sender = '%s';" \
                    % id
        result = self._get_result(my_query)
        return result

    def validate_model(self, id, value=None):
        '''
        id contains the mac address
        value contains the uuid which is not used at this moment
        '''
        my_query = "SELECT \
                    mami_identification.authorisation.authorisation_key \
                    FROM mami_identification.authorisation, \
                        mami_role.model \
                    WHERE mami_role.model.active = 1 \
                    AND mami_identification.authorisation.authorisation_key = '%s' \
                    AND mami_identification.authorisation.id = mami_role.model.authorisation_key;" \
                    % id

        result = self._get_result(my_query)
        for item in result:
            if id in item:
                return True
        return False

    def validate_sender(self, id, value=None):
        '''
        id contains the mac address
        value contains the uuid which is not used at this moment
              for the Update process the value will be None
        '''
        my_query = "SELECT \
                    mami_identification.authorisation.authorisation_key \
                    FROM mami_identification.authorisation, \
                        mami_role.sender \
                    WHERE mami_role.sender.active = 1 \
                    AND mami_identification.authorisation.authorisation_key = '%s' \
                    AND mami_identification.authorisation.id = mami_role.sender.authorisation_key;" \
                    % id

        result = self._get_result(my_query)
        for item in result:
            if id in item:
                return True
        return False

    def validate_viewer(self, id, value=None):
        '''
        id contains the mac address
        value contains the uuid which is not used at this moment
              for the Update process the value will be None
        '''
        my_query = "SELECT \
                    mami_identification.authorisation.authorisation_key \
                    FROM mami_identification.authorisation, \
                        mami_role.viewer \
                    WHERE mami_role.viewer.active = 1 \
                    AND mami_identification.authorisation.authorisation_key = '%s' \
                    AND mami_identification.authorisation.id = mami_role.viewer.authorisation_key;" \
                    % id

        result = self._get_result(my_query)
        for item in result:
            if id in item:
                return True
        return False

    def get_motor_properties_as_json(self, mac_address=None):
        my_query = "SELECT \
                    mami_properties.model_motor.steps_per_revolution, \
                    mami_properties.model_motor.max_speed, \
                    mami_properties.model_motor.direction, \
                    mami_properties.model_motor.motor_interface_type \
                    FROM mami_identification.authorisation, \
                         mami_role.model, \
                         mami_properties.model_motor \
                    WHERE mami_identification.authorisation.authorisation_key = '%s' \
                    AND mami_identification.authorisation.id = mami_role.model.authorisation_key \
                    AND mami_role.model.id_motor = mami_properties.model_motor.id;" \
                        % mac_address
        result = self._get_result(my_query)
        if result == []:
            return '["%s":{}]' %mac_address
        motor_properties = '['
        for item in result:
            motor_property = '{"%s" \
                :{ \
                "steps_per_revolution":"%s", \
                "max_speed": "%s", \
                "direction": "%s", \
                "motor_interface_type": "%s" \
                } \
                },'
            motor_properties += motor_property % (mac_address,
                                item[0],
                                item[1],
                                item[2],
                                item[3])
        motor_properties = motor_properties[:-1]  # remove last character (comma)
        motor_properties += ']'          
        return motor_properties
