#!/usr/bin/env python
import os
import re
import subprocess
import time

import pygtk
import gtk
import gobject
pygtk.require('2.0')
gtk.gdk.threads_init()


class Ping(object):
    UNKNOWN, DISCONNECTED, CONNECTED = range(3)
    icon_filename = {
        UNKNOWN: 'disconnected.png',
        DISCONNECTED: 'disconnected.png',
        CONNECTED: 'connected.png',
    }

    def __init__(self):
        self.location = os.path.dirname(os.path.realpath(__file__))
        self.state = self.UNKNOWN
        self.update_icon()
        self.icon.set_tooltip("Waiting for data...")
        self.icon.set_visible(True)
        self.tick_interval = 5000 #number of ms between each poll

    def test_connection(self):
        p = subprocess.Popen(
            ('ping', '-c 1', '-n', '8.8.8.8'),
            stdout=subprocess.PIPE)
        stdout = p.communicate()[0]
        if not p.returncode:
            ptime = re.findall(r' (time=[\d.]+ ms)', stdout)
            if ptime:
                return ptime[0]
        return False

    def update_icon(self):
        fn = self.icon_filename[self.state]
        path = os.path.join(self.location, fn)
        assert os.path.exists(path), 'File not found: %s' % path
        if hasattr(self, 'icon'):
            self.icon.set_from_file(path)
        else:
            self.icon = gtk.status_icon_new_from_file(path)

    def update(self):
        """This method is called everytime a tick interval occurs"""
        res = self.test_connection()
        if res:
            self.state = self.CONNECTED
            self.icon.set_tooltip(res)
            print res
        else:
            self.state = self.DISCONNECTED
            print 'Net Not Found'
            self.icon.set_tooltip('Disconnected')

        self.update_icon()
        gobject.timeout_add(self.tick_interval, self.update)

    def main(self):
        # All PyGTK applications must have a gtk.main(). Control ends here
        # and waits for an event to occur (like a key press or mouse event).
        gobject.timeout_add(self.tick_interval, self.update)
        gtk.main()


# If the program is run directly or passed as an argument to the python
# interpreter then create a Ping instance and show it
if __name__ == "__main__":
    app = Ping()
    app.main()
