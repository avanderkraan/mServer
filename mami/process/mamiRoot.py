'''
Created on Jan 11, 2018

@author: andre
'''

import cherrypy
import os
import json
from datetime import datetime, timedelta
from mami.io.data import Data
from mami.process.update import Update
#from mako import exceptions
from mami import current_dir
from mami import module_dir
from mami import cache_delay
from mami import sse_timeout
from mami import firmware_dir
from mami import firmware_pattern

from mako.lookup import TemplateLookup
mylookup = TemplateLookup(directories=['%s%s' % (current_dir, '/static/templates'),
                                       '%s%s' % (current_dir, '/static/js'),
                                       '%s%s' % (current_dir, '/static/data'),
                                       '%s%s' % (current_dir, '/static'),
                                       #download_dir
                                       ],
                module_directory=module_dir, collection_size=500,
                output_encoding='utf-8', encoding_errors='replace')

dynamic = {}  # holds cpm(counts per minute) data per feature_id with a datetime when the value was set

class MamiRoot():
    def __init__(self, media_dir=''):
        print ('entered MamiRoot')
        
    @cherrypy.expose
    def _cleancache(self):
        """
        Should be entered regularly to cleanup cache (=dynamic dictionary), using crontab
        using an external program like cron or by this program itself, say every 5 minutes
        """
        now = datetime.now() 
        delta = timedelta(minutes=cache_delay)
        remove_objects = []
        for key in dynamic.keys():
            try:
                previous_now = dynamic.get(key).get('now')
                if previous_now + delta < now:
                    remove_objects.append(key)
            except Exception as inst:
                print(inst)
        for entry in remove_objects:
            dynamic.pop(entry)

    @cherrypy.expose
    def default(self):
        '''
        redirects all not-defined URLs to root.index
        '''
        pass
        newUrl = '%s%s' % (cherrypy.request.script_name, '/')
        raise cherrypy.HTTPRedirect(newUrl)

    @cherrypy.expose
    def index(self):
        template = mylookup.get_template('index.html')
        try:    
            return template.render_unicode().encode('utf-8', 'replace')
        except:
            cherrypy.log('exception', traceback=True)
            return 

    def _get_data(self):
        """
        It returns the data from all dynamic features
        Every feature has a key with its own properties
        """
        data = {}
        for key in dynamic.keys():
            data[key] = {}
            data[key]["name"] = dynamic.get(key).get('name')
            if dynamic.get(key).get('showData') == "1":
                data[key]["rawCounter"] = dynamic.get(key).get('rawCounter')
                data[key]["cpm"] = dynamic.get(key).get('cpm')
                data[key]["revolutions"] = dynamic.get(key).get('revolutions')
                data[key]["isOpen"] = dynamic.get(key).get('isOpen')
                data[key]["message"] = dynamic.get(key).get('message')
        return data

    @cherrypy.expose
    def getDataAsJSON(self, feature_id=None):
        """
        This method returns data in JSON format
        It returns the data from all dynamic features in sse-format
        Every feature has a key with its own properties
        """
        cherrypy.response.headers["Content-Type"] = "application/json"
        cherrypy.response.headers["Cache-Control"] = "no-cache"
        cherrypy.response.headers["Connection"] = "keep-alive"
        cherrypy.response.headers["Pragma"] = "no-cache"
        if feature_id:
            result = self._get_data().get(feature_id)
            if result:
                return json.dumps(result).encode('utf-8', 'replace')
        return json.dumps(self._get_data()).encode('utf-8', 'replace')

    @cherrypy.expose
    def getDataSse(self):
        """
        This method is an eventsource, called from index.html
        It returns the data from all dynamic features in sse-format
        Every feature has a key with its own properties
        """
        cherrypy.response.headers["Content-Type"] = "text/event-stream;charset=utf-8"
        cherrypy.response.headers["Cache-Control"] = "no-cache"
        cherrypy.response.headers["Connection"] = "keep-alive"
        cherrypy.response.headers["Pragma"] = "no-cache"
        data = '{\n'
        data = 'retry: %s\n' % sse_timeout
        data_dict = self._get_data()
        if data_dict != {}:
            for item, value in self._get_data().items():
                data += 'data: {"%s": %s},\n' % (item, json.dumps(value))
            data = data[:-2]
        else:
            data += 'data: {}'
        data += '\n\n'
        return data

    @cherrypy.expose
    def getFeatureDataSse(self, feature_id=None, client_id=None):
        """
        This method is an eventsource called from the index.html file
        This method written to do step 3 of the process
        1. Collect data through Counter (done with the method: feed)
        2. Show the data in de server (done with the method: getDataSSe)
        3. dispatch data of a single feature to a client (e.g. a mill-toy with motor)
        It gives a curated amount of data to the webserver
        TODO: authentication of the clients, should be done in a POST request from the client
              if that is possible with sse calls
        This method calls self._get(...)
        """
        cherrypy.response.headers["Access-Control-Allow-Origin"] = "*"
        cherrypy.response.headers["Access-Control-Allow-Methods"] = "POST"
        cherrypy.response.headers["Content-Type"] = "text/event-stream;charset=utf-8"
        cherrypy.response.headers["Cache-Control"] = "no-cache"
        cherrypy.response.headers["Connection"] = "keep-alive"
        cherrypy.response.headers["Pragma"] = "no-cache"

        # TODO: make client-table to allow clients
        clients = {}
        clients['uuid_from_client'] = 'time_left_before_payment and other data'
        # TODO: for now just made up a dummy dict

        if feature_id and client_id:
            if client_id in clients.keys():
                # TODO: authenticate the client by its uuid
                data = 'retry: %s\ndata: %s\n\n' % (sse_timeout, str(self._get(feature_id=feature_id)))
                return data
        else:
            # wrong parameter, just return 0
            def content():
                #data = 'retry: 200\ndata: ' + str( self.prog_output) + '\n\n'
                data = 'retry: %s\ndata: %s\n\n' % (sse_timeout, str(-1))
                return data
            return content()

    # @cherrypy.expose
    def set(self,
            uuid=None,
            rawCounter=-1,
            cpm=-1,
            revolutions=-1,
            isOpen=False,
            showData=False,
            message=''
            ):
        """
        This method is called to feed the dynamic features with data
        The uuid(=deviceKey) in the data is used to authenticate the feeding device
        """
        try:
            feature_data = Data()
            feature = feature_data.get_feature_from_uuid(uuid=uuid)
            #feature = feature_data.get_feature(feature_id)
            now = datetime.now()
            feature_id = feature['id']
            #if feature and 'id' in feature.keys() and feature['id'] == feature_id:
            name = feature['properties']['name']
            dynamic[feature_id] = {'now':now,
                                   'name':name,
                                   'rawCounter':rawCounter,
                                   'cpm':cpm,
                                   'revolutions':revolutions,
                                   'isOpen':isOpen,
                                   'showData':showData,
                                   'message':message}
        except Exception as inst:
            print('mamiRoot: uuid not found in features.json, in self.set(...)', inst)
            pass
        #print('feature', feature, now, cpm, message)
    
    def _get(self, feature_id=None):
        """
        Curates the data nessecary for the client
        TODO: add authentication and check authorisation. 
        TODO: Has the client payed to collect data
        :return: a curated amount of data for the client
        """
        result = {}
        try:
            result['cpm'] = dynamic.get(feature_id).get('cpm')
            # TODO: result['uuid'] = uuid coming from a separate client file
            # TODO: make client file (with uuid, end-date)
        except:
            pass
        return result

    @cherrypy.expose
    def get(self, feature_id=None):
        # get is used by the javascript in index.html to show the value with openstreetmap
        cherrypy.response.headers["Content-Type"] = "application/json"
        cpm = self._get(feature_id=feature_id)['cpm']
        message = self._get(feature_id=feature_id)['message']
        return json.dumps({"cpm":cpm,"message":message}).encode('utf-8', 'replace')

    @cherrypy.expose
    def feed(self):
        """
        Only POST feeds will be handled
        :return: a response in json format to the feeding device
        """
        if cherrypy.request.method == 'POST':
            cherrypy.response.headers["Content-Type"] = "application/json"
            cl = cherrypy.request.headers['Content-Length']
            rawbody = cherrypy.request.body.read(int(cl))
            unicodebody = rawbody.decode(encoding="utf-8")
            body = json.loads(unicodebody)
            revolutions = body.get('data').get('revolutions')
            rawCounter = body.get('data').get('rawCounter')
            enden = body.get('data').get('viewPulsesPerMinute')
            uuid = body.get('data').get('deviceKey')   
            isOpen = body.get('data').get('isOpen')   
            showData = body.get('data').get('showData')   
            message = body.get('data').get('message')

            # TODO: use uuid as the authentication-uuid-key from the device->pSettings
            # TODO: the factory-setting of the device is the fallback if the authentication-chain is broken
            # TODO: authenticate here, and return the new generated authentication-uuid so the device can save the new value


            # put feeded data in the dynamic features
            self.set(uuid=uuid,
                     rawCounter=rawCounter,
                     cpm=enden,
                     revolutions=revolutions,
                     isOpen=isOpen,
                     showData=showData,
                     message=message)
            
            return json.dumps({"cpm":enden,"message":message}).encode('utf-8', 'replace')

        return '{"Error": "Request method should be POST"}'.encode('utf-8', 'replace')

    @cherrypy.expose
    def updateFirmware(self):
        """
        Update the latest firmware
        or return a json formatted result
        """
        result = {}
        update = Update(firmware_path=firmware_dir, firmware_pattern=firmware_pattern)
        update_allowed, message_list = update.check_go()
        #print('a a a', update_allowed, message_list)
        if update_allowed:
            return update.send_file()
        else:
            cherrypy.response.headers["Content-Type"] = "application/json"
            cherrypy.response.headers["Access-Control-Allow-Origin"] = "*"
            cherrypy.response.headers["Access-Control-Allow-Methods"] = "POST"
            cherrypy.response.headers["Cache-Control"] = "no-cache"
            cherrypy.response.headers["Connection"] = "keep-alive"
            cherrypy.response.headers["Pragma"] = "no-cache"
            result["Message"] = message_list
            return json.dumps(result).encode('utf-8', 'replace')

    feed._cp_config = {"request.methods_with_bodies": ("POST")}
    getDataSse._cp_config = {'response.stream': True, 'tools.encode.encoding':'utf-8'}     
    getFeatureDataSse._cp_config = {'response.stream': True, 'tools.encode.encoding':'utf-8'}     

if __name__ == '__main__':
    try:
        pass
    except Exception as inst:
        print(inst)


      