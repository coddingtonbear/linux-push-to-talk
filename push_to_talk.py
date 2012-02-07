#!/usr/bin/python
import dbus
import gtk
import gnome.applet
from multiprocessing import Process
import os
import pygtk
from Xlib import display, X
from Xlib.ext import record
from Xlib.protocol import rq

OAFIID = "OAFIID:SkypePushToTalk"

class KeyMonitor(object):
    RELEASE = 0
    PRESS = 1

    F1_KEYCODE = 65470
    """
    Heavily borrowed from PyKeyLogger
    """
    def __init__(self, interface, test = False):
        self.local_dpy = display.Display()
        self.record_dpy = display.Display()
        self.interface = interface

        if test == True:
            self.handler = self.print_action
        else:
            self.handler = self.interface_handler

    def get_configured_keycode(self):
        return int(os.environ.get('PUSH_TO_TALK_KEYCODE', KeyMonitor.F1_KEYCODE))

    def interface_handler(self, key, action):
        configured = self.get_configured_keycode()
        if action == KeyMonitor.PRESS and key == configured:
            self.interface.unmute()
        elif action == KeyMonitor.RELEASE and key == configured:
            self.interface.mute()

    def print_action(self, key, action):
        if action == KeyMonitor.RELEASE:
            print "\n%s RELEASE" % key
        elif action == KeyMonitor.PRESS:
            print "\n%s PRESS" % key

    def start(self):
        self.ctx = self.record_dpy.record_create_context(
            0,
            [record.AllClients],
            [{
                    'core_requests': (0, 0),
                    'core_replies': (0, 0),
                    'ext_requests': (0, 0, 0, 0),
                    'ext_replies': (0, 0, 0, 0),
                    'delivered_events': (0, 0),
                    'device_events': (X.KeyPress, X.KeyRelease, ),
                    'errors': (0, 0),
                    'client_started': False,
                    'client_died': False,
            }])

        self.record_dpy.record_enable_context(self.ctx, self.processevents)
        self.record_dpy.record_free_context(self.ctx)

    def processevents(self, reply):
        if reply.category != record.FromServer:
            return
        if reply.client_swapped:
            return
        if not len(reply.data) or ord(reply.data[0]) < 2:
            # not an event
            return
        data = reply.data
        while len(data):
            event, data = rq.EventField(None).parse_binary_value(data, self.record_dpy.display, None, None)
            if event.type == X.KeyPress:
                self.keypressevent(event, KeyMonitor.PRESS)
            elif event.type == X.KeyRelease:
                self.keypressevent(event, KeyMonitor.RELEASE)

    def keypressevent(self, event, action):
        keysym = self.local_dpy.keycode_to_keysym(event.detail, 0)
        self.handler(keysym, action)

class SkypeInterface(object):
    def __init__(self, bus):
        self.bus = bus
        self.outgoing = self.bus.get_object('com.Skype.API', '/com/Skype')
        self.outgoing_channel = self.outgoing.get_dbus_method('Invoke')

    def mute(self):
        self._invoke("MUTE ON")

    def unmute(self):
        self._invoke("MUTE OFF")

    def _invoke(self, message):
        self.outgoing_channel(message)

    def start(self):
        self._invoke('NAME PushToTalk')
        self._invoke('PROTOCOL 5')

def monitor(options):
    system_bus = dbus.SessionBus()
    interface = SkypeInterface(system_bus)
    interface.start()

    monitor = KeyMonitor(interface, **options)
    monitor.start()

def main(applet, iid):
    # Start the process
    proc = Process(target=monitor)
    proc.start()

    # Make a little label
    label = gtk.Label("Labeled")
    applet.add(label)
    applet.show_all()
    return gtk.TRUE

pygtk.require('2.0')

gnome.applet.bonobo_factory(
        OAFIID, 
        gnome.applet.Applet.__gtype__,
        "Allows one to use push-to-talk with Skype",
        "0",
        main
    )
