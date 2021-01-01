'''
Created on Mar 30, 2018

@author: andre
{
    "type": "FeatureCollection",
    "features": [
        {
            "geometry": {
                "type": "Point",
                "coordinates": [
                    4.34,
                    52.0
                ]
            },
            "type": "Feature",
            "properties": {
                "name": "This is a test Station."
            },
            "id": 51
        },
enz.

'''
import os
import sys
import json
import cherrypy
from mami import current_dir, data_file

class Data(object):
    def __init__(self):
        self.filename = data_file
        self.data = None
        with open(self.filename, 'r') as fh:
            self.data = json.load(fh)
        #print(self.filename)
        pass

    def get_all_ids_names(self):
        my_features = {}
        try:
            features = "features" in self.data.keys() and self.data["features"] or []
            for feature in features:
                if "id" in feature.keys():
                    my_features[feature.get("id")] = feature.get("properties").get("name")
        except:
            pass
        return my_features

    
    def get_ids(self):
        # returns a dictionary of feature-ids with properties
        ids = {}
        try:
            features = "features" in self.data.keys() and self.data["features"] or []
            for feature in features:
                for key in feature.keys():
                    if key == 'id':
                        ids.update({feature['id']: feature['properties']})
        except:
            pass
        return ids

    '''
    def get_feature_from_uuid(self, uuid=None):
        # search uuid and return the corresponding feature, using the feature_id
        try:
            ids = self.get_ids()
            #{'nl_12549': {'name': 'De Salamander'}, 'nl_03503': {'uuid': '88888888-4444-4444-4444-121212121212', 'name': 'De Roos'}}
            for id in ids.keys():
                if ids[id]['uuid'] == uuid:
                    return self.get_feature(_id=id) 
        except:
            return None
    '''

    def get_feature_from_mac_address(self, mac_address=None):
        # search mac_address and return the corresponding feature, using the feature_id
        try:
            ids = self.get_ids()
            #{'nl_12549': {'mac_address': 'A0:20:A6:14:85:06', 'name': 'De Salamander'}, 'nl_03503': {'mac_address': 'A0:20:A6:29:18:13', 'name': 'De Roos'}}
            for id in ids.keys():
                if ids[id]['mac_address'] == mac_address:
                    return self.get_feature(_id=id) 
        except:
            return None

    def get_feature(self, _id=None):
        my_feature = {}
        try:
            features = "features" in self.data.keys() and self.data["features"] or []
            for feature in features:
                if "id" in feature.keys() and feature["id"] == _id:
                    my_feature = feature
        except:
            pass
        return my_feature
    
if __name__ == '__main__':
    pass