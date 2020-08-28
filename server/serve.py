'''
Created on Jun 12, 2015

@author: andre
'''
import cherrypy
import sys
import os
sys.path.append('%s' % os.getcwd())
# before mounting anything
from cherrypy.process.plugins import Daemonizer
#Daemonizer(cherrypy.engine).subscribe()
#from server.logfiles import Logfiles
from server import current_dir
from mami.process.mamiRoot import MamiRoot

# 20200328: logfiles uitgezet
useLog = False
if useLog:
    from server.logfiles import Logfiles



class Server(object):
    def __init__(self):
        pass
    
    @staticmethod
    def setup_server(media_dir = ''):
        class Root(object):
            @cherrypy.expose
            def default(self,*args,**kwargs):
                '''
                redirects all not-defined URLs to root.index
                '''
                newUrl = '%s%s' % (cherrypy.request.script_name, '/')
                raise cherrypy.HTTPRedirect(newUrl)

        root = Root()
        root.mami =  MamiRoot()
        # configure server and engine
        cherrypy.config.update('%s/%s' % (current_dir, '../settings/server.conf'))

        root_app = cherrypy.tree.mount(root,
                            script_name='/', 
                            config='%s/%s' % (current_dir, '../settings/vhost.conf'))

        # take care of logfiles
        if useLog:
            logfiles = Logfiles(media_dir = directory)

            baseLogDict = {}
            baseLogDict['log.access_file'] = '%s/%s' % (logfiles.log_dir, '/access_base.log')
            baseLogDict['log.error_file'] = '%s/%s' % (logfiles.log_dir, '/error_base.log')
            #root_app.merge({'/':baseLogDict})

            mamiLogDict = {}
            mamiLogDict['log.access_file'] = '%s/%s' % (logfiles.log_dir, '/access_mami.log')
            mamiLogDict['log.error_file'] = '%s/%s' % (logfiles.log_dir, '/error_mami.log')
            
            #root_app.merge({'/mami':mamiLogDict})
        
            root_app.merge({'/':baseLogDict,
                            '/mami':mamiLogDict
                           })

if __name__ == '__main__':
    """
    starts the server
    """
    '''
    # TODO change this if you want to use logfiles elsewhere
    directory = None
    if len(sys.argv) != 2:
        pass
        print('One directory argument for temporary files is required\n')
        print('Do not use a limited writing device like SD-cards')
        print('Use something like </tmp> or an external mounted harddisk like </media/tournamentfiles>')
    else:
        directory = sys.argv[1]
        if not directory[0] == '/':
            directory = '/%s' % directory
 
        server = Server()
        server.setup_server(media_dir = directory)
        cherrypy.engine.stop()
        cherrypy.server.httpserver = None
        
        #server.ssl_module = 'builtin'
        #server.ssl_certificate = '/cherrypyServer/ssl/cert.pem'
        #server.ssl_private_key = '/cherrypyServer/ssl/privkey.pem'
    '''
    server = Server()
    server.setup_server(media_dir = '/tmp')
    cherrypy.engine.stop()
    cherrypy.server.httpserver = None

    cherrypy.engine.start()  
    cherrypy.engine.block()
