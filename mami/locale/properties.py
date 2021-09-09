'''
Created on Feb 16, 2021

@author: andre
'''
import configparser
import os

from mami import current_dir
properties_dir = os.path.join(current_dir, 'locale', 'content')
from configparser import ConfigParser

class LocaleHandle:
    '''
    Reads language properties, using ConfigParser
    First reads language_properties file to get available languages
    Then reads text and messages
    '''
    def __init__(self):

        self.locale_properties_file = os.path.join(properties_dir, 'locale.properties')
        self.text_properties_file = os.path.join(properties_dir, 'text.properties')
        self.message_properties_file = os.path.join(properties_dir, 'message.properties')
        self.locale_available = {}  # contains the available locales
        self.read_locale()    # get available locales

        self.text = self.read_property(self.text_properties_file)        # contains all text {locale:property} 
        self.message = self.read_property(self.message_properties_file)  # contains all messages {locale:property}

    def read_locale(self):
        properties = ConfigParser()
        try:
            with open(self.locale_properties_file, 'r', encoding='utf-8') as properties_file:
            #with self.language_properties, encoding='iso-8859-1')
                properties.read_file(properties_file)
            for item in properties.items('DEFAULT'):
                self.locale_available.update({item[0].split('_')[1]: item[1]})
            self.locale_available = sorted(self.locale_available.items(), key=lambda kv: kv[1])
        except Exception as inst:
            print(inst)

    def read_property(self, property_file):
        properties = ConfigParser()
        try:
            with open(property_file, 'r', encoding='utf-8') as properties_file:
            #with self.language_properties, encoding='iso-8859-1')
                properties.read_file(properties_file)
        except Exception as inst:
            print(inst)
        return properties


if __name__ == '__main__':
    locale_handle = LocaleHandle()
    print (locale_handle.text.items('DEFAULT'))

    #for locale in locale_handle.locale_available.keys():
    #print (locale_handle.text.sections())
    for section in locale_handle.text.sections():
        print(section, locale_handle.text.options(section))

    #print('%s %s' % ('resultaat:', properties.items('DEFAULT')))
    #print(locale_handle.locale_available)

    #print(locale_handle.text)
    #print(locale_handle.read_text().items('%s.%s' % (locale_handle.localelist[0], 'base')))

    #print(locale_handle.message)

    #print(locale_handle.read_message().items(locale_handle.localelist[0]))      