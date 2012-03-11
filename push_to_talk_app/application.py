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
import logging
from multiprocessing import Process, Queue
from optparse import OptionParser
import os
import os.path

from gi.repository import GObject, Gio, GLib
import gtk

from interfaces import SkypeInterface, PulseAudioInterface
from key_monitor import KeyMonitor

class PushToTalk(gtk.StatusIcon):
    INTERVAL = 100
    INTERFACES = [
            PulseAudioInterface,
            SkypeInterface,
            ]

    def __init__(self):
        self.logger = logging.getLogger('push_to_talk_app')

        gtk.StatusIcon.__init__(self)

        self.configure_unity()

        saved_interface = self.get_saved_interface()
        self.audio_interface = saved_interface if saved_interface else self.INTERFACES[0]

        self.do_setup_menu()
        
        self.reset_ui()
        self.set_tooltip('Test')
        self.set_visible(True)
        self.start()

    def configure_unity(self):
        application_name = 'ptt'
        schema = 'com.canonical.Unity.Panel'
        key = 'systray-whitelist'
        settings = Gio.Settings(schema)
        value = settings.get_value(key)
        if value:
            if 'all' not in value and application_name not in value:
                unpacked = value.unpack()
                unpacked.append(application_name)
                updated = GLib.Variant('as', unpacked)
                settings.set_value(key, updated)
                raise Exception("You must log-out and log-in again for your system tray icon to appear.")

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
            self.logger.debug("Incoming Data -- %s" % str(data_object))
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
        self.logger.debug("Killing process...")
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

        self.logger.debug("Process spawned")
        GObject.timeout_add(PushToTalk.INTERVAL, self.read_incoming_pipe)

    def set_key(self, *arguments):
        self.logger.debug("Attempting to set key...")
        self.set_ui_setkey()
        self.return_pipe.put(("SET", 1, ))

    def change_interface(self, action):
        verb = action.get_name()
        self.logger.debug("Setting to verb '%s'" % verb)
        for interface in self.INTERFACES:
            if interface.verb == verb:
                self.logger.debug("Interface is set!")
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
        self.logger.debug(final_xml)
        return final_xml

def run_from_cmdline():
    parser = OptionParser()
    parser.add_option('-v', '--verbose', dest='verbose', action='store_true', default=False)
    (opts, args, ) = parser.parse_args()

    logging.basicConfig(
            level=logging.DEBUG if opts.verbose else logging.WARNING
        )

    PushToTalk()
    gtk.main()
