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
    DEFAULT_INTERVAL = 5000
    MINIMUM_PING_INTERVAL = 1*1000
    MAXIMUM_PING_INTERVAL = 5*60*1000

    UNKNOWN, DISCONNECTED, CONNECTED = range(3)
    icon_filename = {
        UNKNOWN: 'unknown.png',
        DISCONNECTED: 'disconnected.png',
        CONNECTED: 'connected.png',
    }

    def __init__(self, good_ssids=()):
        self.good_ssids = good_ssids
        self.location = os.path.dirname(os.path.realpath(__file__))
        self.state = self.UNKNOWN
        self.matching_network = matching_wifi_network(self.good_ssids)
        self.update_icon()
        self.icon.connect('activate', self.icon_click)
        self.icon.set_tooltip("Waiting for data...")
        self.icon.set_visible(True)
        self.tick_interval = self.DEFAULT_INTERVAL #number of ms between each poll
        self.ssid_interval = self.DEFAULT_INTERVAL
        self.ping_interval = self.DEFAULT_INTERVAL
        self.down_timestamp = time.time()
        self.last_down_duration = 0 #secs

        self.last_ping = 0
        self.last_ssid = 0

    @property
    def unknown(self):
        return self.state == self.UNKNOWN
    @property
    def connected(self):
        return self.state == self.CONNECTED
    @property
    def disconnected(self):
        return self.state == self.DISCONNECTED

    @staticmethod
    def backoff(t, direction, factor=2, mn=5*1000, mx=5*60*1000):
        """
        Adjust update time expotentially between 5 seconds and 5 minutes
        >>> p = Ping()
        >>> p.backoff(10*1000, 1)
        20000
        >>> p.backoff(10*1000, -1)
        5000
        >>> p.backoff(7*1000, -1)
        5000
        >>> p.backoff(3*60*1000, 1)
        300000
        """
        def within(x, mn, mx):
            return max(min(x, mx), mn)
        assert direction in (-1, 1), "Please suply a direction either -1 or 1, you supplied %s" % direction
        new_t = t * factor ** direction
        return int(within(new_t, mn, mx))

    def icon_click(self, gtk_object):
        """
        Handle a click
        """
        print 'quit'
        gtk.main_quit()

    def test_connection(self):
        """ Issue a single ping to Google's fast DNS server
            Return either a string with the time if found or False
        """
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
        """ Initially set self.icon and then update with the
            icon for the current state
        """
        fn = self.icon_filename[self.state]
        path = os.path.join(self.location, fn)
        assert os.path.exists(path), 'File not found: %s' % path
        if hasattr(self, 'icon'):
            self.icon.set_from_file(path)
        else:
            self.icon = gtk.status_icon_new_from_file(path)

    def update(self):
        """
        This method is called everytime a tick interval occurs
        """
        print
        now = time.time()
        def st(t):
            return time.asctime(time.gmtime(t))

        print '\tnow', st(now)
        print '\tping', st(self.last_ping), 'interval:', self.ping_interval/1000.0
        print now, self.last_ping + self.ping_interval/1000.0, -now + self.last_ping + self.ping_interval/1000.0
        print '\tssid', st(self.last_ssid), 'interval:', self.ssid_interval/1000.0
        print now , self.last_ssid + self.ssid_interval/1000.0, -now + self.last_ssid + self.ssid_interval/1000.0
        #import pdb
        #pdb.set_trace()
        if self.unknown or self.last_ping + self.ping_interval/1000.0 < now :
            print 'update ping'
            self.update_ping()
            self.update_icon()
            self.last_ping = time.time()
        if not self.last_ssid or self.last_ssid + self.ssid_interval/1000.0 < now:
            print 'update ssid'
            self.matching_network = matching_wifi_network(self.good_ssids)
            self.last_ssid = time.time()
        self.adjust_intervals()
        gobject.timeout_add(self.tick_interval, self.update)
        print 'gobject.timeout_add(%s, %s)' % (self.tick_interval, self.update)

    def update_ping(self):
        res = self.test_connection()
        tooltip = []
        if res:
            # if moving from DIS to CONNECTED, store how long connection was down
            if self.disconnected:
                self.last_down_duration = time.time()-self.down_timestamp

            self.state = self.CONNECTED
            tooltip.append(res)

            # don't show downtime length if it was more than 5 mins ago
            if time.time()-self.down_timestamp > 5*60:
                self.down_timestamp = 0

            if self.last_down_duration:
                tooltip.append('(last downtime lasted=%.0f secs)' % self.last_down_duration)
        else:
            # if moving from CONN to DISCONNECTED, store timestamp of loss 
            if self.connected:
                self.down_timestamp = time.time()

            self.state = self.DISCONNECTED

            print 'Net Not Found'
            self.icon.set_tooltip('Lost %.0f secs ago' % (time.time()-self.down_timestamp))

        if self.tick_interval != self.DEFAULT_INTERVAL:
            tooltip.append('Interval: %s' % self.pretty_interval)

        tooltip = ' '.join(tooltip)
        print 'tooltip', tooltip
        self.icon.set_tooltip(tooltip)

    @property
    def pretty_interval(self):
        t = self.tick_interval / 1000.0
        unit = 'secs'
        if t >= 60:
            t /= 60.0
            unit = 'mins'
        return '%3.0f %s' % (float(t), unit)


    def adjust_intervals(self):
        """
        Check whether we're on a matching network and the current state
        and possibly apply exponential backoff to the interval time
        """
        if self.matching_network:
            print 'matching network'
            if self.connected or self.unknown:
                # look for tunnels
                self.ping_interval = self.DEFAULT_INTERVAL
                self.ssid_interval = self.DEFAULT_INTERVAL
            else:
                # look for the end of tunnels
                # disconnected pings use no external bandwidth
                self.ping_interval = self.MINIMUM_PING_INTERVAL
                self.ssid_interval = self.DEFAULT_INTERVAL
        else:
            print 'not matching network because self.matching_network=', self.matching_network, 'from matching_wifi_network(self.good_ssids)=', matching_wifi_network(self.good_ssids)
            if self.connected or self.unknown:
                # stop pinging, await switch to matching network 
                self.ping_interval = self.MAXIMUM_PING_INTERVAL
                self.ssid_interval = self.DEFAULT_INTERVAL
            else:
                # stop pinging, await matching network to connect
                self.ping_interval = self.MINIMUM_PING_INTERVAL
                self.ssid_interval = self.DEFAULT_INTERVAL

        print 'update interval', self.tick_interval/1000.0,
        #tick = self.backoff(self.tick_interval, direction)
        tick = min(self.ping_interval, self.ssid_interval)
        self.tick_interval = tick
        print '-->', tick/1000.0

    def main(self):
        """
        All PyGTK applications must have a gtk.main(). Control ends here
        and waits for an event to occur (like a key press or mouse event).
        """
        gobject.timeout_add(self.tick_interval, self.update)
        gtk.main()


if __name__ == "__main__":
    if sys.argv[1:2] == ['test']:
        import doctest
        doctest.testmod()
        sys.exit()
    # TODO decouple the interval for checking ping time and network name
    # TODO implement exponential backoff for states: conn, disconn, bad ssid.
    good_ssids = sys.argv[1:]

    app = Ping(good_ssids)
    app.main()
