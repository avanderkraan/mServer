from pathlib import Path
import json
from mami.sql import database

def validate_role_model(realm='role_model', key=None, value=None):
    '''
    Basic authentication does not accept colo characters, so they are replaced
    by an underscore, but the database contains a colon as part of the
    mac_address (=key)
    the value contains the uuid of the corresponding device, identified
    by the mac_address
    '''
    #print('validating sender')
    """
    filename = Path(Path.joinpath(Path(__file__).resolve().parent,
                                  '..',
                                  'db',
                                  'authentication',
                                  'sender.json'))
    """

    if key:
        key = key.replace('_', ':')

    db = database.Database()
    return db.validate_sender(key)
    """
    if filename.exists():
        with filename.open('r') as file_read:
            content = json.loads(file_read.read())
            file_read.close()

        for item in content:
            if key in list(item.keys()):
                return True
    return False
    """

def validate_model(realm='model', key=None, value=None):
    #print('validating model', key, value)
    """
    filename = Path(Path.joinpath(Path(__file__).resolve().parent,
                                  '..',
                                  'db',
                                  'authentication',
                                  'model.json'))
    """
    if key:
        key = key.replace('_', ':')

    db = database.Database()
    return db.validate_model(key)

    """
    if filename.exists():
        with filename.open('r') as file_read:
            content = json.loads(file_read.read())
            file_read.close()

        for item in content:
            if key in list(item.keys()):
                return True
    return False
    """

