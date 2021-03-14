'''
Created on Jan 11, 2018

@author: andre
'''

import cherrypy
import os
import json
from datetime import datetime, timedelta
from copy import deepcopy
from mami.io.data import Data
from mami.process.update import Update
from mami.process.validate import validate_model, validate_role_model
#from mako import exceptions
from mami import current_dir
from mami import module_dir
from mami import cache_delay
from mami import sse_timeout

from mami.locale.properties import LocaleHandle

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
model_inventory = {}  # holds model mac address as key and rolemodel_id as value
mac_address_sender = {}  # holds data from sender wih mac_address as key, like previous_cpm
mac_address_model = {}   # holds data from model wih mac_address as key

#    print(section, locale_handle.text.options(section))
#print (locale_handle.text.get('nl.base', 'title'))

class MamiRoot():
    def __init__(self, media_dir=''):
        print ('entered MamiRoot')
        self.max_feed_down = 10    # max difference to prevent a sudden 0
        self.max_feed_counter = 12 * 60 # with every 3 sec request, check every 1 hour if an update is nessecary
        self.max_eat_counter = 12 * 60 # with every 5 sec request, check every 1 hour if an update is nessecary

    def _get_section(self, template, locale='en'):
        return '%s.%s' % (locale, template.module_id.split('_')[0])

    @cherrypy.expose
    def myip(self):
        try:
            return cherrypy.request.headers.get('Remote-Addr')
        except:
            return ''

    @cherrypy.expose
    def _cleancache(self):
        """
        Should be entered regularly to cleanup cache (=dynamic dictionary), using crontab
        using an external program like cron or by this program itself, say every 5 minutes
        """
        # start dynamic dictionary
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
        # end dynamic dictionary

        # start mac_address_sender dictionary
        if len(mac_address_sender) > 1500:
            mac_address_sender = {}  # just empty, it will fill up itself
        # end mac_address_sender dictionary
       
        # start mac_address_model dictionary
        if len(mac_address_model) > 1500:
            mac_address_model = {}  # just empty, it will fill up itself
        # end mac_address_model dictionary

        # TODO clean model_inventory?

####################################################################################### 
    @cherrypy.expose
    def default(self, *args, **kwargs):
        '''
        redirects all not-defined URLs to root.index
        '''
        pass
        newUrl = '%s%s' % (cherrypy.request.script_name, '/')
        raise cherrypy.HTTPRedirect(newUrl)

    @cherrypy.expose
    def index(self, *args, **kwargs):
        template = mylookup.get_template('index.html')

        # start locale stuff
        locale_handle = LocaleHandle()
        text = locale_handle.text
        locale_available = locale_handle.locale_available
        message = locale_handle.message
        # end locale stuff

        # start language stuff
        language = 'en'
        if 'Accept-language' in cherrypy.request.headers:
            language = cherrypy.request.headers['Accept-language'][0:2]
        if 'language' in cherrypy.session.keys():
            language = cherrypy.session['language']
        if 'lang' in kwargs:
            language = kwargs.get('lang')
        cherrypy.session['language'] = language
        # setting cherrypy default url in the config
        text.set('DEFAULT', 'url',cherrypy.url())
        sectionList = text.sections()

        if not language in sectionList:
            cherrypy.session['language'] = 'en'
            language = cherrypy.session['language']
  
        language_options = ''
        for locale_item in locale_available:
            selected = ''
            if language == locale_item[0]:
                selected = 'selected'
            language_options += '<option %s value="%s">%s</option>' % (selected, locale_item[0], locale_item[1])

        section = self._get_section(template, language)
        # end language stuff

        try:
            #print (model_inventory) 
            data = Data()
            homepage_message = message.get(language, 'homepage_message')

            cpright = text.get(section, 'copyright')
            title = text.get(section, 'title')
            donation = text.get(section, 'donation')
            disclaimer = text.get(section, 'disclaimer')
            active_mills = text.get(section, 'active_mills')
            waiting = text.get(section, 'waiting')
            no_mdns = text.get(section, 'no_mdns')
            refresh_model_list = text.get(section, 'refresh_model_list')
            ok = text.get(section, 'ok')
            cancel = text.get(section, 'cancel')
            about_tab = text.get(section, 'about_tab')
            mill_map_tab = text.get(section, 'mill_map_tab')
            link_model_tab = text.get(section, 'link_model_tab')
            link_steps = text.get(section, 'link_steps')
            link_model_explanation = text.get(section, "link_model_explanation")
            step_1_select_mill = text.get(section, 'step_1_select_mill')
            step_2_select_model = text.get(section, 'step_2_select_model')
            step_3_confirm = text.get(section, 'step_3_confirm')
            on = text.get(section, 'on')
            off = text.get(section, 'off')
            no_available_mills = text.get(section, 'no_available_mills')
            no_available_models = text.get(section, 'no_available_models')
            table_mill_name = text.get(section, 'table_mill_name')
            table_ends = text.get(section, 'table_ends')
            table_model_name = text.get(section, 'table_model_name')
            table_model_connect = text.get(section, 'table_model_connect')
            home_text = text.get(section, 'home_text')
            now_closed = text.get(section, 'now_closed')
            now_open = text.get(section, 'now_open')
            no_news = text.get(section, 'no_news')
            goto_link_models = text.get(section, 'goto_link_models')

            return template.render_unicode(language_options = language_options,
                                           homepage_message = homepage_message,
                                           model_inventory = model_inventory,
                                           all_mills = data.get_all_ids_properties(),
                                           cpright = cpright,
                                           donation = donation,
                                           title = title,
                                           disclaimer = disclaimer,
                                           active_mills = active_mills,
                                           waiting = waiting,
                                           no_mdns = no_mdns,
                                           refresh_model_list = refresh_model_list,
                                           ok = ok,
                                           cancel = cancel,
                                           about_tab = about_tab,
                                           mill_map_tab = mill_map_tab,
                                           link_model_tab = link_model_tab,
                                           link_steps = link_steps,
                                           link_model_explanation = link_model_explanation,
                                           step_1_select_mill = step_1_select_mill,
                                           step_2_select_model = step_2_select_model,
                                           step_3_confirm = step_3_confirm,
                                           on = on,
                                           off = off,
                                           no_available_mills = no_available_mills,
                                           no_available_models = no_available_models,
                                           table_mill_name = table_mill_name,
                                           table_ends = table_ends,
                                           table_model_name = table_model_name,
                                           table_model_connect = table_model_connect,
                                           home_text = home_text,
                                           now_closed = now_closed,
                                           now_open = now_open,
                                           no_news = no_news,
                                           goto_link_models = goto_link_models).encode('utf-8', 'replace')
        except Exception as inst:
            print(inst)
            cherrypy.log('exception', traceback=True)
            return 

####################################################################################### 
    def _get_data(self):
        """
        It returns the data from all dynamic features
        Every feature has a key with its own properties
        "features": [{
            "id": "nl_03503",
            "geometry": {
                "type": "Point",
                "coordinates": [
                    4.351280,
                    52.013996
                ]
            },
            "type": "Feature",
            "properties": {
                "name": "De Roos",
                "mac_address": "A0:20:A6:29:18:13"
                < more properties from the sender >
            }
        }, and so on ...
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
        @see _get_data(self)
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
        data = 'retry: %s\n' % sse_timeout
        data_dict = self._get_data()
        if data_dict != {}:
            data += 'data: [\n'
            for item, value in self._get_data().items():
                data += 'data: {"%s": %s},\n' % (item, json.dumps(value))
            data = data[:-2]
            data += ']\n'
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

        if feature_id and client_id in clients.keys():
            # TODO: authenticate the client by its uuid
            #data = 'retry: %s\ndata: %s\n\n' % (sse_timeout, str(self._get(feature_id=feature_id)))
            data = 'retry: %s\ndata: %s\n\n' % (sse_timeout, str(677))
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
            mac_address=None,
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
            feature = feature_data.get_feature_from_mac_address(mac_address=mac_address)
            #feature = feature_data.get_feature(feature_id)
            now = datetime.now()
            feature_id = feature['id']
            #if feature and 'id' in feature.keys() and feature['id'] == feature_id:
            name = feature['properties']['name']
            dynamic[feature_id] = {'mac_address':mac_address,
                                   'uuid':uuid,
                                   'now':now,
                                   'name':name,
                                   'rawCounter':rawCounter,
                                   'cpm':cpm,
                                   'revolutions':revolutions,
                                   'isOpen':isOpen,
                                   'showData':showData,
                                   'message':message}
        except Exception as inst:

            print('most likely, mac_address is None', inst)
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
            # TODO: result['uuid'] = uuid coming from a separate client file (=model.json)
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

####################################################################################### 
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
            macAddress = body.get('data').get('macAddress')   
            isOpen = body.get('data').get('isOpen')   
            showData = body.get('data').get('showData')   
            message = body.get('data').get('message')
            version = body.get('data').get('firmwareVersion')

            # TODO: use uuid as the authentication-uuid-key from the device->pSettings
            # TODO: the factory-setting of the device is the fallback if the authentication-chain is broken
            # TODO: authenticate here, and return the new generated authentication-uuid so the device can save the new value
            #print('sender', macAddress)
            # TODO: with "pushFirmware=esp8266_0.0.9.bin" to push this version
            # TODO:      "pushFirmware=latest to push the latest

            try:
                previous_cpm = mac_address_sender.get(macAddress).get("stored_cpm")
                if (int(enden) > self.max_feed_down) and (previous_cpm - int(enden) > self.max_feed_down):
                    enden = str(int(previous_cpm - self.max_feed_down))
            except:
                pass
            try: 
                mac_address_sender[macAddress].update({"stored_cpm":int(enden)} )
            except:
                mac_address_sender.update({macAddress:{"stored_cpm":int(enden)}} )

            feed_counter = 0
            try:
                feed_counter = mac_address_sender.get(macAddress).get("feed_counter") or 0
                feed_counter += 1
                if feed_counter > self.max_feed_counter:
                    # push Update
                    # only update when cpm == 0
                    # do this because an update call blocks the device (shortly)
                    if enden and enden == "0":
                        feed_counter = -1   # means check for update
                    else:
                        feed_counter = 0    # means no check on update
            except:
                pass
            try:
                mac_address_sender[macAddress].update({"feed_counter": feed_counter} )
            except:
                mac_address_sender.update({macAddress:{"feed_counter": feed_counter}} )
            #print('version', version, feed_counter, enden, uuid)
            #print(mac_address_sender)


            # put feeded data in the dynamic features
            self.set(mac_address=macAddress,
                     uuid=uuid,
                     rawCounter=rawCounter,
                     cpm=enden,
                     revolutions=revolutions,
                     isOpen=isOpen,
                     showData=showData,
                     message=message)

            result = {}
            result.update({"cpm":enden,
                           "message":message,
                           "proposedUUID": uuid,  # TODO: change this 
                           "pushFirmware" : feed_counter == -1 and "latest" or "",
                           "macAddress": macAddress})

            #print(result)

            result_string = json.dumps(result)
            cherrypy.response.headers["Content-Length"] = len(result_string)
            return result_string.encode('utf-8', 'replace')

        result_string = '{"Error": "Request method should be POST"}'
        cherrypy.response.headers["Content-Length"] = len(result_string)
        return result_string.encode('utf-8', 'replace')

    @cherrypy.expose
    def authenticate_sender(self, mac_address="", key="", previous_key=""):
        """
        Authenticates the sender devices using their MAC address
        "00:00:00:00:00:00": {
            "key": "88888888-4444-4444-4444-121212121212 (uuid)",
            "previous_key": "88888888-4444-4444-4444-121212121212 (uuid)",
            "record_change_date": "yyyymmdd_hhmmss (utc)",
            "ttl": "nr (days)",
            "end_date": "yyyymmdd_hhmmss (utc)"
        }
        The key is renewed after calling this method and sent back
        so the calling device can change this value in the devices' settings
        """
        sender = Sender(mac_address, key, previous_key)
        return sender.response()

####################################################################################### 
    @cherrypy.expose
    def eat(self):
        """
        Only POST eats will be handled
        :return: a response in json format to the eating device
        """
        if cherrypy.request.method == 'POST':
            cherrypy.response.headers["Content-Type"] = "application/json"

            cl = cherrypy.request.headers['Content-Length']
            rawbody = cherrypy.request.body.read(int(cl))
            unicodebody = rawbody.decode(encoding="utf-8")
            body = json.loads(unicodebody)
            uuid = body.get('data').get('deviceKey')
            version = body.get('data').get('firmwareVersion')
            macAddress = body.get('data').get('macAddress')
            roleModel = body.get('data').get('roleModel') 

            #model = Model()
            #if macAddress in model.mac_address_list():
            # TODO: use uuid as the authentication-uuid-key from the device->pSettings
            # TODO: the factory-setting of the device is the fallback if the authentication-chain is broken
            # TODO: authenticate here, and return the new generated authentication-uuid so the device can save the new value
            #print('receiver',macAddress)

            if roleModel:
                # put roleModel_id and macAddress of model in dictionary
                model_inventory[macAddress] = roleModel

                # put all known information about the rolemodel in the response
                result = deepcopy(self._get_data().get(roleModel) or {})
                #print('roleModel data:', result)

                eat_counter = 0
                try:
                    eat_counter = mac_address_model.get(macAddress).get("eat_counter") or 0
                    eat_counter += 1
                    if eat_counter > self.max_eat_counter:
                        # push Update
                        # only update when cpm == 0; cpm comes from roleModel
                        # do this because an update call blocks the device (shortly)
                        # if no role model is choosen, the value will be "None"
                        if result.get("cpm") and result.get("cpm") == "0" or roleModel == "None":
                            eat_counter = -1   # means check for update
                        else:
                            eat_counter = 0    # means no check on update
                except:
                    pass
                try:
                    mac_address_model[macAddress].update({"eat_counter": eat_counter} )
                except:
                    mac_address_model.update({macAddress:{"eat_counter": eat_counter}} )

                # overwrite the response uuid and macAddress with model values
                result.update({"proposedUUID": uuid,  # TODO: change this 
                               "pushFirmware" : eat_counter == -1 and "latest" or "",
                               "macAddress": macAddress})
                #print('model data:', result)
                result_string = json.dumps(result)
                cherrypy.response.headers["Content-Length"] = len(result_string)
                return result_string.encode('utf-8', 'replace')
            else:
                result_string = '{"Error": "Role model not found"}'
                cherrypy.response.headers["Content-Length"] = len(result_string)
                return result_string.encode('utf-8', 'replace')

        result_string = '{"Error": "Request method should be POST"}'
        cherrypy.response.headers["Content-Length"] = len(result_string)
        return result_string.encode('utf-8', 'replace')


    feed._cp_config = {"request.methods_with_bodies": ("POST")}
    getDataSse._cp_config = {'response.stream': True, 'tools.encode.encoding':'utf-8'}     
    getFeatureDataSse._cp_config = {'response.stream': True, 'tools.encode.encoding':'utf-8'}     

if __name__ == '__main__':
    try:
        pass
    except Exception as inst:
        print(inst)

