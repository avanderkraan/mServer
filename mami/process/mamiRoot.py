'''
Created on Jan 11, 2018

@author: andre
'''

from re import I
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
from mami import data_file
from mami.process.database import Database

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

dynamic = {}  # holds bpm(blades per minute) data per feature_id with a datetime when the value was set
model_inventory = {}  # holds model mac address as key and rolemodel_id as value
mac_address_sender = {}  # holds data from sender wih mac_address as key, like previous_bpm
mac_address_model = {}   # holds data from model wih mac_address as key

#    print(section, locale_handle.text.options(section))
#print (locale_handle.text.get('nl.base', 'title'))

class MamiRoot():
    def __init__(self, media_dir=''):
        print ('entered MamiRoot')
        self.max_delta = 60             # max difference of rph to prevent a sudden 0
        self.max_feed_counter = 12 * 60 # with every 5 sec request, check every 1 hour if an update is nessecary
        self.max_eat_counter = 12 * 60  # with every 5 sec request, check every 1 hour if an update is nessecary

    def _get_section(self, template, locale='en'):
        return '%s.%s' % (locale, template.module_id.split('_')[0])

    @cherrypy.expose
    def refresh_features(self):
        cherrypy.request.headers['Pragma'] = 'no-cache'
        cherrypy.request.headers['Cache-Control'] = 'no-cache, must-revalidate'
        database = Database()
        features_as_json = json.loads(database.get_features_as_json())
        with open(data_file, "w") as fp:
            json.dump(features_as_json, fp, indent=4)
        self._cleancache()
        newUrl = '%s%s' % (cherrypy.request.script_name, '/')
        raise cherrypy.HTTPRedirect(newUrl)

    @cherrypy.expose
    def myip(self):
        """
        Returns the IP address of the caller
        Purpose: The browser is part of a local network and
                 this gives a clue to find models in the same network
        """
        try:
            cherrypy.request.headers['Pragma'] = 'no-cache'
            cherrypy.request.headers['Cache-Control'] = 'no-cache, must-revalidate'
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
        cherrypy.request.headers['Pragma'] = 'no-cache'
        cherrypy.request.headers['Cache-Control'] = 'no-cache, must-revalidate'

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
            mac_address_sender.clear()  # just empty, it will fill up itself
        # end mac_address_sender dictionary
       
        # start mac_address_model dictionary
        if len(mac_address_model) > 1500:
            mac_address_model.clear()  # just empty, it will fill up itself
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

        millis = 'millis' in kwargs.keys() and kwargs.get('millis') or '-1'

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
            # TODO: use the database as data-source 
            data = Data()
            homepage_message = message.get(language, 'homepage_message')

            cpright = text.get(section, 'copyright')
            title = text.get(section, 'title')
            donation = text.get(section, 'donation')
            disclaimer = text.get(section, 'disclaimer')
            unit_text = text.get(section, "unit_text")
            active_mills = text.get(section, 'active_mills')
            waiting = text.get(section, 'waiting')
            waiting_for_ip = text.get(section, 'waiting_for_ip')
            router_close_button = text.get(section, 'router_close_button')
            router_clear_button = text.get(section, 'router_clear_button')
            router_ok_button = text.get(section, 'router_ok_button')
            no_mdns = text.get(section, 'no_mdns')
            router_placeholder = text.get(section, 'router_placeholder')
            refresh_model_list = text.get(section, 'refresh_model_list')
            selected_rolemodel = text.get(section, 'selected_rolemodel')
            ok = text.get(section, 'ok')
            cancel = text.get(section, 'cancel')
            about_tab = text.get(section, 'about_tab')
            mill_map_tab = text.get(section, 'mill_map_tab')
            mill_table_map = text.get(section, 'mill_table_map')
            link_model_tab = text.get(section, 'link_model_tab')
            link_steps = text.get(section, 'link_steps')
            link_model_explanation = text.get(section, "link_model_explanation")
            off = text.get(section, 'off')
            close_button = text.get(section, 'close_button')
            connect_button = text.get(section, 'connect_button')
            connect = text.get(section, 'connect')
            by_selecting = text.get(section, 'by_selecting')
            search = text.get(section, 'search')
            speed_buttons = text.get(section, 'speed_buttons')
            choice_button = text.get(section, 'choice_button')
            stand_alone_button = text.get(section, 'stand_alone_button')
            independent = text.get(section, 'independent')
            no_available_mills = text.get(section, 'no_available_mills')
            no_available_models = text.get(section, 'no_available_models')
            table_mill_name = text.get(section, 'table_mill_name')
            table_ends = text.get(section, 'table_ends')
            table_rpm = text.get(section, 'table_rpm')
            table_model_name = text.get(section, 'table_model_name')
            table_model_connect = text.get(section, 'table_model_connect')
            home_text = text.get(section, 'home_text')
            local_storage_text = text.get(section, 'local_storage_text')
            show_local_storage = text.get(section, 'show_local_storage')
            hide_local_storage = text.get(section, 'hide_local_storage')
            clear_local_storage = text.get(section, 'clear_local_storage')
            molendatabase = text.get(section, 'molendatabase')
            day_counter = text.get(section, 'day_counter')
            return template.render_unicode(language_options = language_options,
                                           millis = millis,
                                           homepage_message = homepage_message,
                                           model_inventory = model_inventory,
                                           all_mills = data.get_all_ids_properties(),
                                           cpright = cpright,
                                           donation = donation,
                                           title = title,
                                           disclaimer = disclaimer,
                                           unit_text = unit_text,
                                           active_mills = active_mills,
                                           waiting = waiting,
                                           waiting_for_ip = waiting_for_ip,
                                           router_close_button = router_close_button,
                                           router_clear_button = router_clear_button,
                                           router_ok_button = router_ok_button,
                                           no_mdns = no_mdns,
                                           router_placeholder = router_placeholder,
                                           refresh_model_list = refresh_model_list,
                                           selected_rolemodel = selected_rolemodel,
                                           ok = ok,
                                           cancel = cancel,
                                           about_tab = about_tab,
                                           mill_map_tab = mill_map_tab,
                                           mill_table_map = mill_table_map,
                                           link_model_tab = link_model_tab,
                                           link_steps = link_steps,
                                           link_model_explanation = link_model_explanation,
                                           off = off,
                                           close_button = close_button,
                                           connect_button = connect_button,
                                           connect = connect,
                                           by_selecting = by_selecting,
                                           search = search,
                                           speed_buttons = speed_buttons,
                                           choice_button = choice_button,
                                           stand_alone_button = stand_alone_button, 
                                           independent = independent,
                                           no_available_mills = no_available_mills,
                                           no_available_models = no_available_models,
                                           table_mill_name = table_mill_name,
                                           table_ends = table_ends,
                                           table_rpm = table_rpm,
                                           table_model_name = table_model_name,
                                           table_model_connect = table_model_connect,
                                           home_text = home_text,
                                           local_storage_text = local_storage_text,
                                           show_local_storage = show_local_storage,
                                           hide_local_storage = hide_local_storage,
                                           clear_local_storage = clear_local_storage,
                                           molendatabase = molendatabase,
                                           day_counter = day_counter
                                           ).encode('utf-8', 'replace')
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
            #data[key]["bpm"] = dynamic.get(key).get('bpm')
            data[key]["rph"] = dynamic.get(key).get('rph')
            data[key]["blades"] = dynamic.get(key).get('blades')
            data[key]["revolutions"] = dynamic.get(key).get('revolutions')
        return data

    @cherrypy.expose
    def get_data_as_json(self, feature_id=None):
        """
        This method returns data in JSON format, called from popup.html
        Every feature has a key with its own properties
        @see _get_data(self)
        """
        cherrypy.response.headers["Content-Type"] = "application/json"
        cherrypy.response.headers["Cache-Control"] = "no-cache"
        cherrypy.response.headers["Connection"] = "keep-alive"
        cherrypy.response.headers["Pragma"] = "no-cache"
        if feature_id:
            # TODO: do something eith the feature data in the popup?
            # for now: not using these values
            # result = self._get_data().get(feature_id)
            result = {}
            now = datetime.now().strftime('%Y-%m-%d')
            database = Database()
            statistics = database.get_sender_statistics(id=feature_id,
                                                        from_date=now,
                                                        last_date=now)
            if len(statistics) > 0:
                day_counter = 0
                try:
                    day_counter = statistics[-1][3] #statistics[-1][3] - statistics[0][3]
                    result.update({'day_counter': '%s' % day_counter})
                except:
                    pass
            return json.dumps(result).encode('utf-8', 'replace')
        return json.dumps(self._get_data()).encode('utf-8', 'replace')

    @cherrypy.expose
    def get_data_via_sse(self):
        """
        This method is an eventsource, called from index.html
        It returns the data from all dynamic features in sse-format
        Every feature has a key with its own properties
        @see _get_data(self)
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

    # @cherrypy.expose
    def set(self,
            mac_address=None,
            uuid=None,
            #rawCounter=-1,
            #bpm=-1,
            rph=-1,
            blades=-1,
            revolutions=-1,
            #isOpen=False,
            #showData=False,
            #message=''
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
                                   #'rawCounter':rawCounter,
                                   #'bpm':bpm,
                                   'rph':rph,
                                   'blades':blades,
                                   'revolutions':revolutions
                                   #'isOpen':isOpen,
                                   #'showData':showData,
                                   #'message':message
                                   }
            try:
                if (int(rph) > 0):  # write only when there is movement
                    now = datetime.now().strftime('%Y-%m-%d')
                    database = Database()
                    database.write_sender_statistics(id=feature_id,
                                                     change_date = now,
                                                     revolutions=revolutions)


            except:
                pass  # error while writing to the database

        except Exception as inst:

            print('most likely, mac_address is None', inst)
            pass
        #print('feature', feature, now, bpm, message)
    
    
    '''
    def _get(self, feature_id=None):
        """
        Curates the data nessecary for the client
        TODO: add authentication and check authorisation. 
        TODO: Has the client payed to collect data
        :return: a curated amount of data for the client
        """
        result = {}
        try:
            result['bpm'] = dynamic.get(feature_id).get('bpm')
            result['rph'] = dynamic.get(feature_id).get('rph')
            # TODO: result['uuid'] = uuid coming from a separate client file (=model.json)
            # TODO: make client file (with uuid, end-date)
        except:
            pass
        return result

    @cherrypy.expose
    def get(self, feature_id=None):
        # get is used by the javascript in index.html to show the value with openstreetmap
        cherrypy.response.headers["Content-Type"] = "application/json"
        bpm = self._get(feature_id=feature_id)['bpm']
        #message = self._get(feature_id=feature_id)['message']
        #return json.dumps({"bpm":bpm,"message":message}).encode('utf-8', 'replace')
        return json.dumps({"bpm":bpm,"rph":rph}).encode('utf-8', 'replace')
    '''
####################################################################################### 
    @cherrypy.expose
    def feed(self):
        """
        Only POST feeds will be handled
        incoming bpm, blades per minute is recalculated, 
           using parameter b (number of blades) to rph (revolutions per hour)
        :return: a response in json format to the feeding device

        """
        if cherrypy.request.method == 'POST':
            cherrypy.response.headers["Content-Type"] = "application/json"
            cl = cherrypy.request.headers['Content-Length']
            rawbody = cherrypy.request.body.read(int(cl))
            #print(rawbody)
            unicodebody = rawbody.decode(encoding="utf-8")
            body = json.loads(unicodebody)
            revolutions = body.get('data').get('r')  # revolutions of the axis with blades
            #rawCounter = body.get('data').get('rawCounter')
            bpm = body.get('data').get('bpm')        # enden, bladesPerMinute, viewPulsesPerMinute
            uuid = body.get('data').get('key')       # deviceKey
            macAddress = body.get('data').get('mac') # macAddress   
            #isOpen = body.get('data').get('isOpen')   
            #showData = body.get('data').get('showData')   
            #message = body.get('data').get('message')
            version = body.get('data').get('v')      # firmwareVersion
            blades = body.get('data').get('b')       # number of blades

            #backwards compatible for sender 0.1.2 and before
            #{"data": {"revolutions":"0","rawCounter":"6","viewPulsesPerMinute":"0","firmwareVersion":"0.1.2",
            # "deviceKey":"88888888-4444-4444-4444-121212121212","macAddress":"A0:20:A6:14:85:06","isOpen":"1","showData":"1","message":""}}'
            '''
            backwards_compatibility_on = False
            if revolutions == None:
                revolutions = body.get('data').get('revolutions')
            if bpm == None:
                bpm = body.get('data').get('viewPulsesPerMinute')
                blades = 4  # default
                backwards_compatibility_on = True
            if version == None:
                version = body.get('data').get('firmwareVersion')
            if uuid == None:
                uuid = body.get('data').get('deviceKey')
            if macAddress == None:
                macAddress = body.get('data').get('macAddress')
            '''
            # rph is needed for the models, revolutions per hour, to get a big enough number
            rph = None
            try:
                rph = str(round(int(bpm) * 60 / int(blades))) # revolutions per hour of the axis with blades
            except:
                pass

            # TODO: use uuid as the authentication-uuid-key from the device->pSettings
            # TODO: the factory-setting of the device is the fallback if the authentication-chain is broken
            # TODO: authenticate here, and return the new generated authentication-uuid so the device can save the new value
            #print('sender', macAddress)
            # TODO: with "pushFirmware=esp8266_0.0.9.bin" to push this version
            # TODO:      "pushFirmware=latest to push the latest

            try:
                previous_rph = mac_address_sender.get(macAddress).get("stored_rph")
                # slowly lower rph value when it is suddenly 0
                #if (int(rph) == 0) and (previous_rph > self.max_delta):
                #    rph = str(int(previous_rph - self.max_delta))
            except:
                pass
            try: 
                mac_address_sender[macAddress].update({"stored_rph":int(rph)} )
            except:
                if rph != None:
                    mac_address_sender.update({macAddress:{"stored_rph":int(rph)}} )

            feed_counter = 0
            try:
                feed_counter = mac_address_sender.get(macAddress).get("feed_counter") or 0
                feed_counter += 1
                if feed_counter > self.max_feed_counter:
                    # push Update
                    # only update when bpm == 0
                    # do this because an update call blocks the device (shortly)
                    if rph and rph == "0":
                        feed_counter = -1   # means check for update
                    else:
                        feed_counter = 0    # means no check on update
            except:
                pass
            try:
                mac_address_sender[macAddress].update({"feed_counter": feed_counter} )
            except:
                mac_address_sender.update({macAddress:{"feed_counter": feed_counter}} )
            #print('version', version, feed_counter, bpm, uuid)
            #print(mac_address_sender)


            # put feeded data in the dynamic features
            self.set(mac_address=macAddress,
                     uuid=uuid,
                     #rawCounter=rawCounter,
                     #bpm=bpm,
                     rph=rph,
                     blades=blades,
                     revolutions=revolutions,
                     #isOpen=isOpen,
                     #showData=showData,
                     #message=message
                     )

            result = {}

            '''
            if backwards_compatibility_on == True:
                #        "84:CC:A8:A3:09:11": { "comment": "(Tweemanspolder) Nr.3",
                #        "A0:20:A6:29:18:13": { "comment": "de Roos",
                #        "84:CC:A8:A0:FE:2D": { "comment": "de Hoop, Zoetermeer",
                
                backwards_compatible_list = ()
                
                if macAddress in backwards_compatible_list:
                    feed_counter = 0  # skip update to new version

                result.update({"bpm":bpm,
                            #"message":message,
                            "proposedUUID": uuid,  # TODO: change this 
                            "pushFirmware" : feed_counter == -1 and "latest" or "",
                            "macAddress": macAddress})
            '''
            #else:
            result.update({"pKey": uuid,  # proposedUUID ->TODO: change this value when needed as safety measurement (authentication of the sender)  
                        "pFv" : feed_counter == -1 and "latest" or ""
                        })

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
            #print(rawbody, cl)
            unicodebody = rawbody.decode(encoding="utf-8")
            body = json.loads(unicodebody)
            uuid = body.get('data').get('key')        # deviceKey
            version = body.get('data').get('v')       # firmwareVersion
            macAddress = body.get('data').get('mac')  # macAddress
            roleModel = body.get('data').get('rM')    # roleModel 

            # TODO: use uuid as the authentication-uuid-key from the device->pSettings
            # TODO: use from uuid import uuid4 to get a new uuid and the database to safe the proposed uuid
            # TODO: the factory-setting of the device is the fallback if the authentication-chain is broken
            # TODO: authenticate here, and return the new generated authentication-uuid so the device can save the new value
            #print('receiver',macAddress)

            if roleModel:
                # put roleModel_id and macAddress of model in dictionary
                model_inventory[macAddress] = roleModel

                # put all known information about the rolemodel in the response
                result = deepcopy(self._get_data().get(roleModel) or {})
                #print('roleModel data:', result)
                
                # set a zero value if rolemodel doesn't give any data (about the speed)
                if result.get("rph") == None and roleModel != "independent":
                    result.update({"rph": " 0"})

                eat_counter = 0
                try:
                    eat_counter = mac_address_model.get(macAddress).get("eat_counter") or 0
                    eat_counter += 1
                    if eat_counter > self.max_eat_counter:
                        # push Update
                        # only update when bpm == 0; bpm comes from roleModel
                        # do this because an update call blocks the device (shortly)
                        # if no role model is choosen, the value will be "None"
                        if result.get("rph") and result.get("rph") == "0" or roleModel == "None":
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
                result.update({"pKey": uuid,  # TODO: change this 
                               "pFv" : eat_counter == -1 and "latest" or ""
                               })
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
    get_data_via_sse._cp_config = {'response.stream': True, 'tools.encode.encoding':'utf-8'}     
    
if __name__ == '__main__':
    try:
        pass
    except Exception as inst:
        print(inst)

