'''
Created on Feb 6, 2016

@author: andre
'''
import cherrypy
import os

class Logfiles(object):
    
    def __init__(self, media_dir='', 
                 default_dir='/tmp/dump', 
                 default_log_dir='/tmp/dump/log'):
        # media_dir is usually a mounted drive and that is what this program wants
        # because it runs from a sd-card and that is not a good place to write over and over  
        use_user_defined_dir = True
        exception_message = []
        #default_dir =  '/tmp/tournament'
        #default_log_dir = '/tmp/tournament/log'
        self.media_dir = media_dir
        if not self.media_dir:
            self.media_dir = '/tmp'
        if self.media_dir == default_dir:
            use_user_defined_dir = False

        self.log_dir = default_log_dir.replace('/tmp', self.media_dir)
        
        try:    
            if not os.path.isdir(self.log_dir):
                try:
                    os.makedirs(self.log_dir, exist_ok=True)
                except Exception as inst:
                    exception_message.append('Error making %s %s' % (self.log_dir, inst))
                    use_user_defined_dir = False
                    self.log_dir = default_log_dir
                    os.makedirs(default_log_dir, exist_ok=True)
            try:
                # default is also needed for the server app instantiation in server.py
                os.makedirs(default_log_dir, exist_ok=True)
            except Exception as inst:
                exception_message.append('Error making %s %s' % (default_log_dir, inst))
                

        except Exception as inst:
            exception_message.append('Error in creating directories %s' % inst)
        if use_user_defined_dir:
            print('Temporary directory is %s' % media_dir)
        else:
            for exc_message in exception_message:
                cherrypy.log(exc_message)
            print('Temporary directory is %s' % default_dir)
        