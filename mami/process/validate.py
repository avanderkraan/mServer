from pathlib import Path
import json
from mami.data import database

def validate_role_model(realm='role_model', key=None, value=None):
    '''
    Basic authentication does not accept colo characters, so they are replaced
    by an underscore, but the database contains a colon as part of the
    mac_address (=key)
    the value contains the uuid of the corresponding device, identified
    by the mac_address
    '''
    if key:
        key = key.replace('_', ':')

    db = database.Database()
    return db.validate_sender(key, value)

def validate_model(realm='model', key=None, value=None):
    '''
    Basic authentication does not accept colo characters, so they are replaced
    by an underscore, but the database contains a colon as part of the
    mac_address (=key)
    the value contains the uuid of the corresponding device, identified
    by the mac_address
    '''
    if key:
        key = key.replace('_', ':')

    db = database.Database()
    return db.validate_model(key, value)


