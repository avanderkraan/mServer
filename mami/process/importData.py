import requests
import json
from mami import import_credentials_file

class ImportData():
    '''
    imports data from external sources
    returns features and dynamic data in json format
    '''
    def __init__(self, source_id=None, source_key=None):
        self.credentials = self._get_credentials(source_id)
        if self.credentials.get('draaiendemolens_key') == source_key:
            self.url = '%s%s%s%s%s' % (self.credentials.get('protocol') or "",
                                       self.credentials.get('host') or "",
                                       self.credentials.get('port') and ":%s" % self.credentials.get('port') or "",
                                       self.credentials.get("path") or "",
                                       self.credentials.get("query"))
            self.process_import()
        else:
            return {}

        '''

        {'host': 'api.smartmolen.com', 'path': '/api/molenList', 'query': '', 'port': '', 'user': '', 'password': '', 'draaiendemolens_key': 'erew3'}


        self.url = args.get('url') or None
        self.method = args.get('method') or None

        self.source_id = args.get('source_id')
        self.source_key = args.get('draaiendemolens_key') or None
        credentials = self._get_credentials(name = self.source_id)
        print (credentials)
        self.result = {}
        if self.url and self.source_id:
            self.get_data()
        '''

    def _get_credentials(self, name=None):
        print(name)
        try:
            with open(import_credentials_file) as f:
                read_credentials = f.read()
                all_credentials = json.loads(read_credentials)
                for items in all_credentials:
                    credentials = items.get(name)
                    if credentials:
                        print (credentials)
                        return credentials
            return {}
        except Exception as inst:
            print(inst)
        return {}
        
    def get_data(self):
        if self.method.upper() == 'GET':
            self.result = requests.get(url=self.url)
        if self.method.upper() == 'POST':
            body_dict = self.body or {}
            headers = self.headers
            self.result = requests.post(url=self.url, data=json.dumps(body_dict), headers=headers)

    def process_import(self):
        '''
        returns a subset of features as json and a subset of corresponding dynamic data
        '''
        result = {}
        result["features"] = {}

        '''
    @cherrypy.expose
    def get_fea(self, f=None):
        cherrypy.request.headers['Pragma'] = 'no-cache'
        cherrypy.request.headers['Cache-Control'] = 'no-cache, must-revalidate'
        #if f == self.get_features_code:
        database = Database()
        features_as_json = json.loads(database.get_features_as_json().encode('utf-8', 'replace'))

        toevoeg =         {
            "geometry": {
                "type": "Point",
                "coordinates": [
                    4.5127,
                    51.0139
                ]
            },
            "type": "Feature",
            "properties": {
                "name": "AAAs",
                "city": "Delft",
                "mac_address": "anders"
            },
            "id": "anders"
        }
        print (toevoeg)

        features_as_json.get("features").append(toevoeg)
        print (json.dumps(features_as_json))
        return json.dumps(features_as_json)
        #lse:
        return '{"Availability": "None"}'.encode('utf-8', 'replace')


        '''
        '''
        {
    "type": "FeatureCollection",
    "features": [
        {
            "geometry": {
                "type": "Point",
                "coordinates": [
                    4.35127,
                    52.0139
                ]
            },
            "type": "Feature",
            "properties": {
                "name": "De Roos",
                "city": "Delft",
                "mac_address": "A0:20:A6:29:18:13"
            },
            "id": "03503"
        }
    ]
}
        '''