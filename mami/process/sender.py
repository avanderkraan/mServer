"""
reads from db->authentication->sender.json and from static->data->featuress.json
creates a new uuid to be returned to the sender with the corresponding mac_address
"""
from pathlib import Path
from uuid import uuid4
import json

class Sender:
    def __init__(self, mac_address="", key="", previous_key=""):
        self.mac_address = mac_address
        self.key = key
        self.previous_key = previous_key
        self.content = None
        self.filename = Path(Path.joinpath(Path(__file__).resolve().parent,
                                           '..',
                                           'db',
                                           'authentication',
                                           'sender.json'))
        self.lock = Path('%s.%s' % (self.filename, 'lock'))
        self.proposed_key = None

    def _write_safe(self):
        """
        set a lock file
        looks for a mac address
        proposes a new key
        write the proposed_key in the sender.json
        """
        if not self.lock.exists():
            with self.lock.open('w') as lockfile:
                lockfile.write("lockfile for sender.json")
                lockfile.close()

            if self.filename.exists():
                with self.filename.open('r') as file_read:
                    self.content = json.loads(file_read.read())
                    file_read.close()

            found_flag = False
            for device in self.content:
                if not found_flag:
                    for mac_address, properties in device.items():
                        if mac_address == self.mac_address:
                            self.proposed_key = uuid4()
                            properties.update({"proposed_key": str(self.proposed_key)})
                            found_flag = True
                            break
            
            changed_content = json.dumps(self.content, indent=4)
            if len(changed_content) >= len(self.content):  # to prevent writing an empty file after some kind of error
                with self.filename.open('w') as file_write:
                    file_write.write(changed_content)
                    file_write.close()

            try:
                self.lock.unlink()  # remove file, exception if it does not exist
            except FileNotFoundError:
                # another process removed the lock file, so to be safe: return False
                return False
            return True  # everything went well
        return False

    def response(self):
        if self._write_safe():
            return self.proposed_key
        return None


if __name__ == "__main__":
    # A0:20:A6:29:18:13 hoort bij de roos
    # A0:20:A6:14:85:06 hoort bij salamander
    sender = Sender(mac_address="A0:20:A6:14:85:06", 
                    key="88888888-4444-4444-4444-121212121212",
                    previous_key="88888888-4444-4444-4444-121212121212")
    print(sender.response())