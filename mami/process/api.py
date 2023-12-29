import json
from copy import deepcopy
from mami.data.database import Database
import datetime

class Api:
    '''
    Api processes api requests and returns a json-like string
    '''
    def __init__(self, body, dynamic_data, get_data_as_json):
        self.body = body                        # api request
        self.dynamic = dynamic_data             # dynamic mill data on this server

        self.dynamic = {'03503': {'mac_address': '84:CC:A8:A2:D1:84', 'now': datetime.datetime.now().astimezone(), 'name': 'Demo', 'rph': '555', 'blades': '4', 'revolutions': '6'}}

        self.get_data_as_json = get_data_as_json# method that gives coin-data as json
        self.requested_mills = None             # None or contains a list of mill-ids
        self.result_string = '{"Error": "Api request failed during processing"}'

        self.choices = {"version": ["1.0"], "action":["help", "all_data", "data_by_id"], "format":["indent"]}
        self.version = ""
        self.action = ""
        self.format = ""
        try:
            self._determinate_api_request()
            self._process_api_request(version=self.version)
        except:
            pass

    def result(self):
        '''
        returns a json-like string
        '''
        return self.result_string 
           
    def _help(self):
        #help = {"! help !": "valid json for an api request:","to get data from all defined mills": {"version": "1.0", "mills": []}, "to get data from specific mills": {"version": "1.0", "mills": ["<id>","<...>"]}, "to get a specific response format":{"<responseFormat>": "<smartmolen>"}}
        help = {"! help !": "valid json for an api request:","to get data from all defined mills": {"version": "1.0", "mills": []}, "to get data from specific mills": {"version": "1.0", "mills": ["<id>","<...>"]}, "to get an indented response":{"<indent>": "<1..4>"}}
        self.result_string = json.dumps(help, indent=4)
         
    def _confirm_choice(self, choice_key, choice_value):
        # validates and set choices in self.version, self.action
        if self.choices.get(choice_key) and choice_value in self.choices.get(choice_key):
            if choice_key == "version":
                self.version = choice_value
            if choice_key == "action":
                self.action = choice_value
            if choice_key == "format":
                self.format = choice_value
        else:
            self.result_string = '{"Error": "API failed due to incomplete self.choices, check method _determine_api_request"}'

    def _determinate_api_request(self):
        '''
        find out what is requested
        '''
        if self.body:
            # version
            self._confirm_choice("version", self.body.get("version") or "-")
            if self.version == "-":      # no version defined
                self._confirm_choice("action", "help")

            # only proceed if version-key is available
            else:
                # data
                _requested_mills = self.body.get('mills')
                if _requested_mills == None:
                    self._confirm_choice("action", "help")

                elif type(_requested_mills) == list:
                    if _requested_mills == []:     # all mills
                        self._confirm_choice("action", "all_data")
                    else:
                        self._confirm_choice("action", "data_by_id")
                        #format
                        indent = self.body.get("indent") or "-"     # no indent defined
                        try:
                            indent = int(indent)
                            if indent < 1 or indent > 4:
                                self._confirm_choice("action", "help")
                            else:
                                self.format = indent
                        except:
                            self._confirm_choice("action", "help")



    def _process_api_request(self, version="-"):
        '''
        process the requested version
        '''
        if self.version in ["-", ""] or self.action == "" or self.action == "help":  # wrong api request
            self._help()                        # sets result_string
        else:
            _method_name = "_get_api_version_%s" % self.version.replace(".", "_")
            method = getattr(self, _method_name)          # process corresponding version request
            self.result_string = json.dumps(method(version), indent=self.format)
 

    def _get_api_version_1_0(self, version):
        '''
        A response is built and returned for a version 1.0 request
        '''
        result = {}
        result.update({"version": version})
        mill_id_list = []
        # properties
        db = Database()
        mill_properties = deepcopy(db.get_all_ids_properties() or {})

        if self.action == "all_data":
            mill_id_list = mill_properties
        if self.action == "data_by_id":
            mill_id_list = self.body.get("mills") or []

        for id in mill_id_list:
            try:
                item = {}                           # contains all item data
                if  mill_properties.get(id).get("id"):
                    item.update({"id": mill_properties.get(id).get("id")})
                if mill_properties.get(id).get("name"):
                    item.update({"name": mill_properties.get(id).get("name")})
                if mill_properties.get(id).get("city"):
                    item.update({"city": mill_properties.get(id).get("city")})
                if mill_properties.get(id).get("longitude"):
                    item.update({"longitude": mill_properties.get(id).get("longitude")})
                if mill_properties.get(id).get("latitude"):
                    item.update({"latitude": mill_properties.get(id).get("latitude")})

                # dynamic
                item_dynamic_data = deepcopy(self.dynamic.get(id)) or {}
                
                if item_dynamic_data.get("now"):
                    item_dynamic_data["now"] = item_dynamic_data.get("now").isoformat()
                    item.update({"now": item_dynamic_data.get("now")})
                # make rpm of rph
                if item_dynamic_data.get("rph"):
                    item.update({"rpm": str(int(int(item_dynamic_data["rph"]) / 60))})

                # database_dynamic
                db_data = json.loads(self.get_data_as_json(feature_id=id))   # get database dynamic data
                if db_data.get("day_counter"):
                    item.update({"day_counter": db_data.get("day_counter")})
                if db_data.get("month_counter"):
                    item.update({"month_counter": db_data.get("month_counter")})
                if db_data.get("year_counter"):
                    item.update({"year_counter": db_data.get("year_counter")})

                result.update({id: item})

            except Exception as e:
                pass
        return result


    