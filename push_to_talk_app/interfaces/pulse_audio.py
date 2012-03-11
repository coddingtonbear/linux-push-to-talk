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
import subprocess

__all__ = ['PulseAudioInterface', ]

class PulseAudioInterface(object):
    verb = "Mute for all applications"

    INPUTS = {}

    def __init__(self):
        self.logger = logging.getLogger('push_to_talk_app.interfaces.pulse_audio')
        super(PulseAudioInterface, self).__init__()
        self.update_input_list()

    def update_input_list(self):
        self.INPUTS = {}

        proc = subprocess.Popen(
                [
                    'pactl',
                    'list',
                    'short',
                    'sources',
                ], 
                stdout = subprocess.PIPE
            )
        out, err = proc.communicate()
        input_lines = out.split('\n')
        for input_line in input_lines:
            input_line = input_line.strip()
            if not input_line:
                break

            details = input_line.split('\t')

            index = details[0]
            parsed = {
                        'name': details[1],
                        'module': details[2],
                        'sound': details[3],
                        'status': details[4],
                    }
            self.logger.debug("Found device %s" % parsed['name'])
            self.INPUTS[index] = parsed

    def mute(self):
        for index in self.INPUTS.keys():
            subprocess.call([
                    'pactl',
                    'set-source-mute',
                    str(index),
                    '1',
                ])

    def unmute(self):
        for index in self.INPUTS.keys():
            retval = subprocess.call([
                    'pactl',
                    'set-source-mute',
                    str(index),
                    '0',
                ])
