#!/usr/bin/python

# Copyright (c) 2012 Adam Coddington
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
import os.path
import logging

from Xlib import display, X
from Xlib.ext import record
from Xlib.protocol import rq

__all__ = ['KeyMonitor', ]

class KeyMonitor(object):
    RELEASE = 0
    PRESS = 1

    UNMUTED = 0
    MUTED = 1

    F1_KEYCODE = 65470
    F12_KEYCODE = 65481
    """
    Heavily borrowed from PyKeyLogger
    """
    def __init__(self, interface, pipe, return_pipe, test = False):
        self.logger = logging.getLogger('push_to_talk_app.key_monitor')
        self.local_dpy = display.Display()
        self.record_dpy = display.Display()
        self.interface = interface
        self.pipe = pipe
        self.return_pipe = return_pipe

        self.configured_keycode = None
        self.state = KeyMonitor.MUTED

        if test == True:
            self.handler = self.print_action
        else:
            self.handler = self.interface_handler

    @property
    def configuration_file(self):
        return os.path.expanduser("~/.push_to_talk_key")

    def get_configured_keycode(self):
        if not self.configured_keycode:
            try:
                with open(self.configuration_file, "r") as infile:
                    keycode = infile.read()
                    self.configured_keycode = int(keycode)
            except:
                self.configured_keycode = KeyMonitor.F12_KEYCODE
        return self.configured_keycode

    def set_configured_keycode(self, keycode):
        self.logger.info("Setting keycode to %s" % keycode)
        try:
            with open(self.configuration_file, "w") as outfile:
                outfile.write(str(keycode))
                self.configured_keycode = None
            return True
        except Exception as e:
            self.logger.exception(e)
            return False

    def set_state(self, state):
        if self.state != state:
            self.pipe.put(("MUTED", state, ))
            if state == KeyMonitor.UNMUTED:
                self.interface.unmute()
            elif state == KeyMonitor.MUTED:
                self.interface.mute()
        self.state = state

    def interface_handler(self, key, action):
        configured = self.get_configured_keycode()
        if action == KeyMonitor.PRESS and key == configured:
            self.set_state(KeyMonitor.UNMUTED)
        elif action == KeyMonitor.RELEASE and key == configured:
            self.set_state(KeyMonitor.MUTED)

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
        if not self.return_pipe.empty():
            self.logger.debug("Key info %s" % keysym)
            data_object = self.return_pipe.get_nowait()
            data_type = data_object[0]
            self.logger.debug("Got data %s" % str(data_object))
            if data_type == "SET":
                self.set_configured_keycode(keysym)
            self.handler(keysym, action)
        else:
            self.handler(keysym, action)
