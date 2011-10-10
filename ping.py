#!/usr/bin/env python
import os
import sys
import re
import subprocess
import time

import pygtk
import gtk
import gobject
pygtk.require('2.0')
gtk.gdk.threads_init()


IWCONFIG_PATH = '/sbin/iwconfig'


def matching_wifi_network(good_ssids=()):
    try:
        p = subprocess.Popen(IWCONFIG_PATH, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except OSError, e:
        print "Problem calling iwconfig at %s: %r" % (IWCONFIG_PATH, e)
        return False
    comms = p.communicate()
    conn_data = comms[0]
    return any(('ESSID:"%s"' % ssid) in conn_data for ssid in good_ssids)


class Ping(object):
    UNKNOWN, DISCONNECTED, CONNECTED = range(3)
    icon_filename = {
        UNKNOWN: 'unknown.png',
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
            ptime = re.findall(r' (time=[\d.]+ ms)', stdout)
            if ptime:
                return ptime[0].replace('time', 'ping')
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


if __name__ == "__main__":
    # TODO cope with moving between wifi networks while already running
    # TODO implement exponential backoff for states: conn, disconn, bad ssid.
    # TODO add a click handler to allow quiting
    if sys.argv[1:]:
        good_ssids = sys.argv[1:]
        if not matching_wifi_network(good_ssids):
            print "Not on a chosen wifi network so exiting"
            sys.exit()

    app = Ping()
    app.main()
