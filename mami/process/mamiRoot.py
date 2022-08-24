'''
Created on Jan 11, 2018

@author: andre
'''

from re import I
import uuid
import cherrypy
import os
import json
from datetime import datetime, timedelta
from random import randrange
from copy import deepcopy
from mami.process.update import Update
from mami.process.validate import validate_model, validate_role_model
#from mako import exceptions
from mami import current_dir
from mami import module_dir
from mami import cache_delay
from mami import sse_timeout
from mami.data.database import Database
from mami.data.statistics import Statistics
from mami.data.debug import Debug


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
    def __init__(self):
        print ('entered MamiRoot')
        # to protect features from being exposed too easily
        self.get_features_code = str(uuid.uuid4())

        self.max_delta = 60             # max difference of rph to prevent a sudden 0
        self.max_feed_delta_update_hours = 1   # check after 1 hour or more if an update is nessecary
        self.max_feed_delta_info_hours = 1     # check every 24 hours or more if for new info
        self.max_eat_delta_update_hours = 1    # check after 1 hour or more if an update is nessecary
        self.max_eat_delta_info_hours = 1      # check every 24 hours or more if for new info

    def _get_section(self, template, locale='en'):
        return '%s.%s' % (locale, template.module_id.split('_')[0])

    @cherrypy.expose
    def get_features_from_data(self, f=None):
        cherrypy.request.headers['Pragma'] = 'no-cache'
        cherrypy.request.headers['Cache-Control'] = 'no-cache, must-revalidate'
        if f == self.get_features_code:
            database = Database()
            #features_as_json = json.loads(database.get_features_as_json())
            return database.get_features_as_json().encode('utf-8', 'replace')
        else:
            return '{"Availability": "None"}'.encode('utf-8', 'replace')

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
            data = Database()
            all_mills = data.get_all_ids_properties()
            #data = Data()
            homepage_message = message.get(language, 'homepage_message')

            cpright = text.get(section, 'copyright')
            title = text.get(section, 'title')
            donation = text.get(section, 'donation')
            disclaimer = text.get(section, 'disclaimer')
            unit_text = text.get(section, "unit_text")
            active_mills = text.get(section, 'active_mills')
            waiting = text.get(section, 'waiting')
            no_mdns = text.get(section, 'no_mdns')
            refresh_model_list = text.get(section, 'refresh_model_list')
            selected_rolemodel = text.get(section, 'selected_rolemodel')
            ok = text.get(section, 'ok')
            cancel = text.get(section, 'cancel')
            about_tab = text.get(section, 'about_tab')
            mill_map_tab = text.get(section, 'mill_map_tab')
            mill_table_map = text.get(section, 'mill_table_map')
            link_model_tab = text.get(section, 'link_model_tab')
            link_steps = text.get(section, 'link_steps')
            link_steps_explanation = text.get(section, 'link_steps_explanation')
            link_step_mdns_button = text.get(section, 'link_step_mdns_button')
            link_step_code_button = text.get(section, 'link_step_code_button')
            link_step_mdns = text.get(section, 'link_step_mdns')
            link_step_mdns_explanation = text.get(section, 'link_step_mdns_explanation')
            link_step_code = text.get(section, 'link_step_code')
            link_step_code_explanation = text.get(section, 'link_step_code_explanation')
            enter_code_guide = text.get(section, 'enter_code_guide')
            code_screenshot_1 = text.get(section, 'code_screenshot_1')
            code_screenshot_2 = text.get(section, 'code_screenshot_2')
            code_screenshot_3 = text.get(section, 'code_screenshot_3')
            code_screenshot_4 = text.get(section, 'code_screenshot_4')
            code_screenshot_5 = text.get(section, 'code_screenshot_5')
            menu = text.get(section, 'menu' )
            get_ip_number = text.get(section, 'get_ip_number')
            connect_wifi = text.get(section, 'connect_wifi')
            spin_settings_code = text.get(section, 'spin_settings_code')
            spin_settings_independent = text.get(section, 'spin_settings_independent')
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
            tenbruggecate_code = text.get(section, 'tenbruggecate_code')
            return template.render_unicode(language_options = language_options,
                                           millis = millis,
                                           get_features_code = self.get_features_code,
                                           homepage_message = homepage_message,
                                           model_inventory = model_inventory,
                                           all_mills = all_mills,
                                           cpright = cpright,
                                           donation = donation,
                                           title = title,
                                           disclaimer = disclaimer,
                                           unit_text = unit_text,
                                           active_mills = active_mills,
                                           waiting = waiting,
                                           no_mdns = no_mdns,
                                           refresh_model_list = refresh_model_list,
                                           selected_rolemodel = selected_rolemodel,
                                           ok = ok,
                                           cancel = cancel,
                                           about_tab = about_tab,
                                           mill_map_tab = mill_map_tab,
                                           mill_table_map = mill_table_map,
                                           link_model_tab = link_model_tab,
                                           link_steps = link_steps,
                                           link_steps_explanation = link_steps_explanation,
                                           link_step_mdns_button = link_step_mdns_button,
                                           link_step_code_button = link_step_code_button,
                                           link_step_mdns = link_step_mdns,
                                           link_step_mdns_explanation = link_step_mdns_explanation,
                                           link_step_code = link_step_code,
                                           link_step_code_explanation = link_step_code_explanation,
                                           enter_code_guide = enter_code_guide,
                                           code_screenshot_1 = code_screenshot_1,
                                           code_screenshot_2 = code_screenshot_2,
                                           code_screenshot_3 = code_screenshot_3,
                                           code_screenshot_4 = code_screenshot_4,
                                           code_screenshot_5 = code_screenshot_5,
                                           menu = menu,
                                           get_ip_number = get_ip_number,
                                           connect_wifi = connect_wifi,
                                           spin_settings_independent = spin_settings_independent,
                                           spin_settings_code = spin_settings_code,
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
                                           day_counter = day_counter,
                                           tenbruggecate_code = tenbruggecate_code
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
            "id": "03503",
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
            statistics = Statistics()
            stats = statistics.get_sender_statistics(id=feature_id,
                                                     from_date=now,
                                                     last_date=now)
            if len(stats) > 0:
                day_counter = 0
                try:
                    day_counter = stats[-1][3] #statistics[-1][3] - statistics[0][3]
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
            #uuid=None,
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
            # deprecated by using data. feature_data = Data()
            # deprecated by using data. feature = feature_data.get_feature_from_mac_address(mac_address=mac_address)
            database = Database()
            feature = database.get_feature_from_mac_address(mac_address=mac_address)
            #feature = feature_data.get_feature(feature_id)
            now = datetime.now()
            feature_id = feature['id']
            #if feature and 'id' in feature.keys() and feature['id'] == feature_id:
            name = feature['properties']['name']
            dynamic[feature_id] = {'mac_address':mac_address,
                                   #'uuid':uuid,
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
                    statistics = Statistics()
                    statistics.write_sender_statistics(id=feature_id,
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
            unicodebody = ""
            try:
                unicodebody = rawbody.decode(encoding="utf-8",errors="strict")
            except:
                # workaround of decode problem
                unicodebody = str(rawbody)[2:-1].replace("\\x","-")
            body = json.loads(unicodebody)
            revolutions = body.get('data').get('r')  # revolutions of the axis with blades
            #rawCounter = body.get('data').get('rawCounter')
            bpm = body.get('data').get('bpm')        # enden, bladesPerMinute, viewPulsesPerMinute
            macAddress = body.get('data').get('mac') # macAddress   
            #isOpen = body.get('data').get('isOpen')   
            #showData = body.get('data').get('showData')   
            #message = body.get('data').get('message')
            blades = body.get('data').get('b')       # number of blades

            # start backwards compatibility (< 0.1.7) for key and version
            '''
            uuid = body.get('data').get('key')       # deviceKey
            if uuid == None and body.get('info'):
                uuid = body.get('info').get('key')
            version = body.get('data').get('v')      # firmwareVersion
            if version == None and body.get('info'):
                version = body.get('info').get('v')
            # end backwards compatibility (< 0.1.7) for key and version
            '''

            #print(body.get('info'))
            # ratio_from_db gets the information from the miller/owner and/or
            # the data from the molendatabase.nl and compares it
            # every time when info is asked (e.g. every 24 hours)
            ratio_from_db = ""
            if body.get('info') != None:
                #uuid = body.get('info').get('key')
                version = body.get('info').get('v')
                # but first set some debug info in the database
                # start write debug info
                database = Database()
                feature = database.get_feature_from_mac_address(mac_address=macAddress)
                #feature = feature_data.get_feature(feature_id)
                now = datetime.now()
                feature_id = feature['id']
                #now = datetime.now().strftime('%Y-%m-%d')

                #print(datetime.now().strftime('%Y-%m-%d:%H:%M:%S'))

                '''
                keys, used by body.get('info'):
                
                v      : firmwareVersion
                key    : deviceKey
                ra     : ratio, given by user
                apssid : accespoint ssid, given by user
                stssid : station ssid, given by user
                cid    : ESP.getFlashChipId
                crs    : ESP.getFlashChipRealSize
                csi    : ESP.getFlashChipSize
                csp    : ESP.getFlashChipSpeed
                cm     : ESP.getFlashChipMode
                '''
                info = "version: %s, blades: %s, ratio: %s, WiFiSSID: %s" % \
                        (version, blades, body.get('info').get('ra'), body.get('info').get('stssid'))
                debug_data = Debug()
                debug_data.write_sender_debug_data(id=feature_id,
                                                   change_date=now,
                                                   info=info)
                # end write debug info
                # start get ratio_from_db to send it to the Sender
                database = Database()
                ratio_from_db_result = database.get_sender_ratio(id=feature_id)
                try:
                    ratio_from_db = ratio_from_db_result[0][0]
                except:
                    pass
                # end get ratio_from_db

            storage_mac_address_sender = mac_address_sender.get(macAddress)
            if storage_mac_address_sender == None:
                mac_address_sender.update({macAddress:{}})
                storage_mac_address_sender = mac_address_sender.get(macAddress)
            #print('a a a', storage_mac_address_sender)
            # rph is needed for the models, revolutions per hour, to get a big enough number
            rph = None
            try:
                rph = str(round(int(bpm) * 60 / int(blades))) # revolutions per hour of the axis with blades
            except:
                rph = "0"

            # TODO: use uuid as the authentication-uuid-key from the device->pSettings
            # TODO: the factory-setting of the device is the fallback if the authentication-chain is broken
            # TODO: authenticate here, and return the new generated authentication-uuid so the device can save the new value
            #print('sender', macAddress)
            # TODO: with "pushFirmware=esp8266_0.0.9.bin" to push this version
            # TODO:      "pushFirmware=latest to push the latest

            try:
                previous_rph = storage_mac_address_sender.get("stored_rph")
                # slowly lower rph value when it is suddenly 0
                if (int(rph) == 0) and (previous_rph > self.max_delta):
                    rph = str(int(previous_rph - self.max_delta))
            except:
                if rph != None:
                    storage_mac_address_sender.update({"stored_rph":int(rph)})

            feed_update_time = storage_mac_address_sender.get("feed_update_time")
            feed_info_time =  storage_mac_address_sender.get("feed_info_time")
            delta_update = None
            delta_info = None
            sender_update_flag = False
            sender_info_flag = False
            try:
                if feed_update_time != None:
                    delta_update = timedelta(hours = self.max_feed_delta_update_hours)
                else:
                    # First time after starting the server, so spread the load
                    delta_update = timedelta(seconds = randrange(1, 60))
                    feed_update_time = datetime.now() + delta_update
                    storage_mac_address_sender.update({"feed_update_time": feed_update_time})
                if feed_info_time != None:
                    delta_info = timedelta(hours = self.max_feed_delta_info_hours)
                else:
                    # First time after starting the server, so spread the load
                    delta_info = timedelta(seconds = randrange(1, 60))
                    feed_info_time = datetime.now() + delta_info
                    storage_mac_address_sender.update({"feed_info_time": feed_info_time})

                # push Update only when bpm (alias rph) == 0
                # do this because an update call blocks the device (shortly)
                
                if rph and rph == "0":
                    if datetime.now() > feed_update_time:
                        sender_update_flag = True
                        feed_update_time += delta_update
                        storage_mac_address_sender.update({"feed_update_time": feed_update_time})
                    if datetime.now() > feed_info_time:
                        sender_info_flag = True
                        feed_info_time += delta_info
                        storage_mac_address_sender.update({"feed_info_time": feed_info_time})
            except:
                pass

            # put feeded data in the dynamic features
            self.set(mac_address=macAddress,
                     #uuid=uuid,
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
            result.update({"pFv" : sender_update_flag and "latest" or "",
                           "pR"  : ratio_from_db,
                           "i"   : sender_info_flag and "info" or ""
                          })
            if body.get("info"):
                uuid = body.get("info").get("key")
                result.update({"pKey": uuid or "",  # proposedUUID ->TODO: change this value when needed as safety measurement (authentication of the sender)
                              })
            result_string = json.dumps(result)
            #print(result_string, feed_counter)
            cherrypy.response.headers["Content-Length"] = len(result_string)
            return result_string.encode('utf-8', 'replace')

        result_string = '{"Error": "Request method should be POST"}'
        cherrypy.response.headers["Content-Length"] = len(result_string)
        return result_string.encode('utf-8', 'replace')


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
            macAddress = body.get('data').get('mac')  # macAddress
            roleModel = body.get('data').get('rM')    # roleModel 

            # TODO: use uuid as the authentication-uuid-key from the device->pSettings
            # TODO: use from uuid import uuid4 to get a new uuid and the database to safe the proposed uuid
            # TODO: the factory-setting of the device is the fallback if the authentication-chain is broken
            # TODO: authenticate here, and return the new generated authentication-uuid so the device can save the new value
            #print('receiver',macAddress)
            if body.get('info') != None:
                #uuid = body.get('info').get('key')
                version = body.get('info').get('v')
                # but first set some debug info in the database
                # start write debug info
                now = datetime.now()
                '''
                keys, used by body.get('info'):
                
                v      : firmwareVersion
                key    : deviceKey
                spr    : steps per revolution, depends on motor properties
                ms     : maximum speed, depends om motor properties
                d      : direction, depends on motor properties
                mit    : motor interface type, depends on motor type, used by AccellStepper
                apssid : accespoint ssid, given by user
                stssid : station ssid, given by user
                cid    : ESP.getFlashChipId
                crs    : ESP.getFlashChipRealSize
                csi    : ESP.getFlashChipSize
                csp    : ESP.getFlashChipSpeed
                cm     : ESP.getFlashChipMode
                '''
                info = "version: %s, motor: %s|%s|%s|%s, WiFiSSID: %s" % \
                        (version,
                         body.get('info').get('spr'), 
                         body.get('info').get('ms'), 
                         body.get('info').get('d'), 
                         body.get('info').get('mit'), 
                         body.get('info').get('stssid'))
                debug_data = Debug()
                debug_data.write_model_debug_data(mac_address=macAddress,
                                                  change_date=now,
                                                  info=info)


            if roleModel:
                # put roleModel_id and macAddress of model in dictionary
                model_inventory[macAddress] = roleModel

                # put all known information about the rolemodel in the response
                result = deepcopy(self._get_data().get(roleModel) or {})
                # print('roleModel data:', result)
                # set a zero value if rolemodel doesn't give any data (about the speed)
                if result.get("rph") == None and roleModel != "independent":
                    result.update({"rph": "0"})

                storage_mac_address_model = mac_address_model.get(macAddress)
                if storage_mac_address_model == None:
                    mac_address_model.update({macAddress:{}})
                    storage_mac_address_model = mac_address_model.get(macAddress)

                eat_update_time = storage_mac_address_model.get("eat_update_time")
                eat_info_time =  storage_mac_address_model.get("eat_info_time")
                delta_update = None
                delta_info = None
                model_update_flag = False
                model_info_flag = False
                try:
                    if eat_update_time != None:
                        delta_update = timedelta(hours = self.max_eat_delta_update_hours)
                    else:
                        # First time after starting the server, so spread the load
                        delta_update = timedelta(seconds = randrange(1, 60))
                        eat_update_time = datetime.now() + delta_update
                        storage_mac_address_model.update({"eat_update_time": eat_update_time})
                    if eat_info_time != None:
                        delta_info = timedelta(hours = self.max_eat_delta_info_hours)
                    else:
                        # First time after starting the server, so spread the load
                        delta_info = timedelta(seconds = randrange(1, 60))
                        eat_info_time = datetime.now() + delta_info
                        storage_mac_address_model.update({"eat_info_time": eat_info_time})

                    if result.get("rph") and result.get("rph") == "0" or roleModel in ("None", "independent"):
                        # backwards compatibility for version < 0.1.5: roleModel "None"
                        # with version => 0.1.5 roleModel == "independent" is used
                        if datetime.now() > eat_update_time:
                            try:
                                database = Database()
                                motor_properties_as_json = database.get_motor_properties_as_json(mac_address=macAddress)
                                motor_properties = json.loads(motor_properties_as_json)
                                if motor_properties[0].get(macAddress) != {}:
                                    result.update({"spr": motor_properties[0].get(macAddress).get("steps_per_revolution") or "",
                                                   "ms": motor_properties[0].get(macAddress).get("max_speed") or  "",
                                                   "d": motor_properties[0].get(macAddress).get("direction") or "",
                                                   "mit": motor_properties[0].get(macAddress).get("motor_interface_type") or ""})
                            except Exception as inst:
                                pass
                            model_update_flag = True
                            eat_update_time += delta_update
                            storage_mac_address_model.update({"eat_update_time": eat_update_time})

                        if datetime.now() > eat_info_time:
                            model_info_flag = True
                            eat_info_time += delta_info
                            storage_mac_address_model.update({"eat_info_time": eat_info_time})

                except:
                    pass

                # overwrite the response uuid and macAddress with model values
                result.update({"pFv" : model_update_flag and "latest" or "",
                               "i"   : model_info_flag and "info" or ""
                               })
                if body.get("info"):
                    uuid = body.get("info").get("key")
                    result.update({"pKey": uuid or "",  # proposedUUID ->TODO: change this value when needed as safety measurement (authentication of the sender)
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

    @cherrypy.expose
    def codes(self, *args, **kwargs):
        """
        :return: a response of codes, millnames and places
        TODO: create a html template to show this data, with search capabilities?
        """
        template = mylookup.get_template('codes.html')

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
            database = Database()
            active_sender_codes = json.dumps(database.get_active_sender_data())

            homepage_message = message.get(language, 'homepage_message')

            code = text.get(section, 'code')
            name = text.get(section, 'name')
            city = text.get(section, 'city')
            cpright = text.get(section, 'copyright')
            title = text.get(section, 'title')
            donation = text.get(section, 'donation')

            return template.render_unicode(language_options = language_options,
                                           homepage_message = homepage_message,
                                           all_codes = active_sender_codes,
                                           code = code,
                                           name = name,
                                           city = city,
                                           cpright = cpright,
                                           donation = donation,
                                           title = title
                                           ).encode('utf-8', 'replace')
        except Exception as inst:
            print(inst)
            cherrypy.log('exception', traceback=True)
            return 

    feed._cp_config = {"request.methods_with_bodies": ("POST")}
    get_data_via_sse._cp_config = {'response.stream': True, 'tools.encode.encoding':'utf-8'}     
    
if __name__ == '__main__':
    try:
        pass
    except Exception as inst:
        print(inst)

