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
from __future__ import with_statement
import dbus
import gtk
import gobject
import logging
from multiprocessing import Process, Queue
from optparse import OptionParser
import os
import os.path
import pygtk
import subprocess
from Xlib import display, X
from Xlib.ext import record
from Xlib.protocol import rq

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
        logging.info("Setting keycode to %s" % keycode)
        try:
            with open(self.configuration_file, "w") as outfile:
                outfile.write(str(keycode))
                self.configured_keycode = None
            return True
        except Exception as e:
            logging.exception(e)
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
            logging.debug("Key info %s" % keysym)
            data_object = self.return_pipe.get_nowait()
            data_type = data_object[0]
            logging.debug("Got data %s" % str(data_object))
            if data_type == "SET":
                self.set_configured_keycode(keysym)
            self.handler(keysym, action)
        else:
            self.handler(keysym, action)

class PulseAudioInterface(object):
    verb = "Mute for all applications"

    def mute(self):
        index = 0
        while True:
            retval = subprocess.call([
                    'pactl',
                    'set-source-mute',
                    str(index),
                    '1',
                ])
            if retval != 0:
                return
            index = index + 1

    def unmute(self):
        index = 0
        while True:
            retval = subprocess.call([
                    'pactl',
                    'set-source-mute',
                    str(index),
                    '0',
                ])
            if retval != 0:
                return
            index = index + 1

class SkypeInterface(object):
    verb = "Mute only Skype"

    def __init__(self):
        self.bus = dbus.SessionBus()
        self.configured = False

    def configure(self):
        try:
            logging.debug("Configuring...")
            self.outgoing = self.bus.get_object('com.Skype.API', '/com/Skype')
            self.outgoing_channel = self.outgoing.get_dbus_method('Invoke')
            self.configured = True

            self.start()
            logging.debug("Configured.")
            return False
        except:
            # This happens if Skype is not available.
            return True

    def mute(self):
        self._invoke("MUTE ON")

    def unmute(self):
        self._invoke("MUTE OFF")

    def _invoke(self, message):
        if not self.configured:
            self.configure()
        try:
            self.outgoing_channel(message)
        except:
            self.configured = False

    def start(self):
        self._invoke('NAME PushToTalk')
        self._invoke('PROTOCOL 5')

class PushToTalk(gtk.StatusIcon):
    INTERVAL = 100
    INTERFACES = [
            PulseAudioInterface,
            SkypeInterface,
            ]

    def __init__(self):
        gtk.StatusIcon.__init__(self)

        saved_interface = self.get_saved_interface()
        self.audio_interface = saved_interface if saved_interface else self.INTERFACES[0]

        self.do_setup_menu()
        
        self.reset_ui()
        self.set_tooltip('Test')
        self.set_visible(True)
        self.start()

    def get_saved_interface(self):
        try:
            name = self.get_saved_interface_name()
            for interface in self.INTERFACES:
                if interface.__name__ == name:
                    return interface
        except:
            pass
        return None

    @property
    def preferences_file(self):
        return os.path.expanduser(
                    "~/.push_to_talk_saved",
                )

    def get_saved_interface_name(self):
        with open(self.preferences_file, "r") as infile:
            interface = infile.read()
        return interface

    def set_saved_interface_name(self, name):
        with open(self.preferences_file, "w") as outfile:
            outfile.write(name)
        return name

    def process(self, pipe, return_pipe):
        monitor = KeyMonitor(
                self.audio_interface(), 
                pipe,
                return_pipe,
                test=False
            )
        monitor.start()

    def read_incoming_pipe(self):
        while not self.pipe.empty():
            data_object = self.pipe.get_nowait()
            data_type = data_object[0]
            data = data_object[1]
            logging.debug("Incoming Data -- %s" % str(data_object))
            if data_type == "MUTED":
                if data == KeyMonitor.UNMUTED:
                    self.set_ui_talk()
                elif data == KeyMonitor.MUTED:
                    self.reset_ui()
        return True

    def reset_ui(self):
        self.set_from_file(os.path.join(
                os.path.dirname(__file__),
                'icons/mute.png'
            ))

    def set_ui_talk(self):
        self.set_from_file(os.path.join(
                os.path.dirname(__file__),
                'icons/talk.png'
            ))

    def set_ui_setkey(self):
        self.set_from_file(os.path.join(
                os.path.dirname(__file__),
                'icons/setkey.png'
            ))

    def reset_process(self):
        logging.debug("Killing process...")
        self.p.terminate()
        self.start()

    def start(self):
        self.pipe = Queue()
        self.return_pipe = Queue()

        self.p = Process(
                target=self.process,
                args=(self.pipe, self.return_pipe, )
            )
        self.p.start()

        logging.debug("Process spawned")
        gobject.timeout_add(PushToTalk.INTERVAL, self.read_incoming_pipe)

    def set_key(self, *arguments):
        logging.debug("Attempting to set key...")
        self.set_ui_setkey()
        self.return_pipe.put(("SET", 1, ))

    def change_interface(self, uicomponent, verb):
        logging.debug("Setting to verb '%s'" % verb)
        for interface in self.INTERFACES:
            if interface.verb == verb:
                logging.debug("Interface is set!")
                self.set_saved_interface_name(interface.__name__)
                self.audio_interface = interface
        self.do_setup_menu()
        self.reset_process()

    def get_audio_xml(self):
        xml_strings = {}
        for interface in self.INTERFACES:
            xml_strings[interface.verb] = "<menuitem action=\"%s\" />" % (
                                interface.verb,
                            )
        return xml_strings

    def do_setup_menu(self):
        verbs = [(
                'Menu',
                None,
                'Menu', 
                ),
                (
                'SetKey', 
                None, 
                'Set Key', 
                None, 
                'Set key to use for push-to-talk', 
                self.set_key, 
            ),]
        for interface in self.INTERFACES:
            if self.audio_interface.verb != interface.verb:
                verbs.append((
                                interface.verb, 
                                None, 
                                interface.verb, 
                                None, 
                                '', 
                                self.change_interface, 
                        ),)

        action_group = gtk.ActionGroup('Actions')
        action_group.add_actions(verbs)

        self.manager = gtk.UIManager()
        self.manager.insert_action_group(action_group, 0)
        self.manager.add_ui_from_string(self.menu_xml)
        self.menu = self.manager.get_widget('/Menubar/Menu/SetKey').props.parent

        self.connect('popup-menu', self.on_popup_menu)

    def on_popup_menu(self, status, button, time):
        self.menu.popup(None, None, None, button, time)

    @property
    def menu_xml(self):
        audio_xml = self.get_audio_xml()
        start_xml = """
            <ui>
                <menubar name="Menubar">
                    <menu action="Menu">
                        <menuitem action="SetKey"/>
                        <separator/>
            """
        for audio_source_verb, audio_item in audio_xml.items():
            if self.audio_interface.verb == audio_source_verb:
                del(audio_xml[audio_source_verb])
        end_xml = """
                    </menu>
                </menubar>
            </ui>"""
        final_xml = start_xml + "".join(audio_xml.values()) + end_xml
        logging.debug(final_xml)
        return final_xml

def configure_unity():
    pass

def run_from_cmdline():
    logging.info("Starting application...")
    
    parser = OptionParser()
    parser.add_option('-v', '--verbose', dest='verbose', action='store_true', default=False)
    parser.add_option('--configure-unity', dest='configure_unity', action='store_true', default=False)
    (opts, args, ) = parser.parse_args()

    if opts.configure_unity:
        configure_unity()
    else:
        logging.basicConfig(
                level=logging.DEBUG if opts.verbose else logging.INFO
            )

        PushToTalk()
        gtk.main()
