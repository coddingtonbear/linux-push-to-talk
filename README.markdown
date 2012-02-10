# Push-to-talk for Skype (on Linux)

This gnome panel application allows one to assign a key (by default *F12*), that will unmute one's microphone in a skype conversation while pushed.

## Dependencies

 - pygtk
 - xlib

On Ubuntu, this is as easy as running ``sudo apt-get install python-gtk2 python-xlib``.

## Installation

 1. Run ``sudo ./install.sh``.
 2. Restart gnome panel by either logging-out/logging-in, or running ``sudo killall gnome-panel`` (it will automatically restart).
 3. Right-click on your gnome panel.
 4. Select 'Add to panel'.
 5. Add 'Skype Push-to-talk'.

## Changing the Push-to-talk Key

 1. Right-click on the 'TALK' icon in your gnome panel.
 2. Click 'Set Key'.
 3. Press the key you'd like to use.

