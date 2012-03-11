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
import dbus
import logging

__all__ = ['SkypeInterface', ]

class SkypeInterface(object):
    verb = "Mute only Skype"

    def __init__(self):
        self.logger = logging.getLogger('push_to_talk_app.interfaces.skype')
        self.bus = dbus.SessionBus()
        self.configured = False

    def configure(self):
        try:
            self.logger.debug("Configuring...")
            self.outgoing = self.bus.get_object('com.Skype.API', '/com/Skype')
            self.outgoing_channel = self.outgoing.get_dbus_method('Invoke')
            self.configured = True

            self.start()
            self.logger.debug("Configured.")
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
