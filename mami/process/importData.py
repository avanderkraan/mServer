import requests
import json
from copy import deepcopy
from mami import import_credentials_file

class ImportData():
    '''
    imports data from external sources
    returns features and dynamic data in json format
    '''
    def __init__(self, source_id="", source_key=""):
        self.data = {}                 # contains requested data from self.url, converted and per source_id
        self.status = '{"Message": "Valid import from %s"}' % source_id
        self.credentials = self._get_credentials(source_id)
        if self.credentials.get('draaiendemolens_key') == source_key:
            self.url = '%s%s%s%s%s' % (self.credentials.get('protocol') or "",
                                    self.credentials.get('host') or "",
                                    self.credentials.get('port') and ":%s" % self.credentials.get('port') or "",
                                    self.credentials.get("path") or "",
                                    self.credentials.get("query"))
            self._get_data(source_id)
            self.status = self._process_import(source_id)
         
        else:
            self.status = '{"Error": "Invalid credentials for data import from source: %s"}' % source_id

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
        try:
            with open(import_credentials_file) as f:
                read_credentials = f.read()
                all_credentials = json.loads(read_credentials)
                for items in all_credentials:
                    credentials = items.get(name)
                    if credentials:
                        return credentials
        except Exception as inst:
            self.status = '{"Error": "Cannot find valid credentials"}'
        
    def _get_data(self, source_id):
        if self.credentials.get("method").upper() == 'GET':
            result = requests.get(url=self.url)
            self.data[source_id] = result.content
        if self.credentials.get("method").upper() == 'POST':
            body_str = self.credentials.get("body") or ""
            #import base64
            #b64Val = base64.b64encode("%s:%s") % (self.credentials.get("user") or "", self.credentials.get("password") or "")
            #headers={"Authorization": "Basic %s" % b64Val}

            headers = json.loads(self.credentials.get("headers")) or {}

            result = requests.post(self.url, data=body_str, headers=headers)
            self.data[source_id] = result.content

    def _process_import(self, source_id):
        '''
        returns a subset of external features as python-object, converted for this program
        '''
        result = []                    # list of dictionaries
        # conversion may be different per external source
        if source_id == "smartmolen_molenList":
            try:
                default_feature = {"geometry": {"type": "Point", "coordinates": []},
                                   "type": "Feature", 
                                   "properties": {"name": "", "city": "", "mac_address": "",
                                                  "source_id": "", 
                                                  "rpm": "",
                                                  "day_counter": "", 
                                                  "year_counter": "",
                                                  "cap_orientation": ""}, 
                                   "id": ""}

                external_mills = json.loads(self.data.get(source_id))

                for mill in external_mills:
                    converted_item = deepcopy(default_feature)
                    converted_item.get("geometry")["coordinates"] = [mill.get("location").get("longitude"), mill.get("location").get("latitude")] 
                    converted_item.get("properties")["name"] = mill.get("name")
                    converted_item.get("properties")["source_id"] = source_id
                    if mill.get("latestSailRotationReading"):
                        converted_item.get("properties")["rpm"] = mill.get("latestSailRotationReading").get("currentSpeedRPM") or 0
                        converted_item.get("properties")["day_counter"] = mill.get("latestSailRotationReading").get("revCountToday") or 0
                        converted_item.get("properties")["year_counter"] = mill.get("latestSailRotationReading").get("revCountThisYear") or 0
                    else:
                        converted_item.get("properties")["day_counter"] = -1   # no spin-sensor available
                        converted_item.get("properties")["year_counter"] = -1  # no spin-sensor available
                    if mill.get("latestOrientationSensorReading"):
                        converted_item.get("properties")["cap_orientation"] = mill.get("latestOrientationSensorReading").get("compassPoint") or ""
                    converted_item["id"] = mill.get("shortName")
                    result.append(converted_item)
                self.data[source_id] = result
            except Exception as e:
                print (e)

        return '{"Message": "Valid import of data from source: %s"}' % source_id


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