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
        self.down_timestamp = time.time()
        self.last_down_duration = 0 #secs

    def test_connection(self):
        p = subprocess.Popen(
            ('ping', '-c 1', '-n', '8.8.8.8'),
            stdout=subprocess.PIPE)
        stdout = p.communicate()[0]
        if not p.returncode:
            ptime = re.findall(r' (ping=[\d.]+ ms)', stdout)
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
            # if moving from DIS to CONNECTED, store how long connection was down
            if self.state == self.DISCONNECTED:
                self.last_down_duration = time.time()-self.down_timestamp

            self.state = self.CONNECTED

            # don't show downtime length if it was more than 5 mins ago
            if time.time()-self.down_timestamp > 5*60:
                self.down_timestamp = 0

            if self.last_down_duration:
                res += ' (last downtime lasted=%.0f secs)' % self.last_down_duration
            self.icon.set_tooltip(res)
            print res
        else:
            # if moving from CONN to DISCONNECTED, store timestamp of loss 
            if self.state == self.CONNECTED:
                self.down_timestamp = time.time()

            self.state = self.DISCONNECTED

            print 'Net Not Found'
            self.icon.set_tooltip('Lost %.0f secs ago' % (time.time()-self.down_timestamp))

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
