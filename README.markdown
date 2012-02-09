# Push-to-talk for Skype (on Linux)

This application allows one to assign a key, that while pushed, will unmute one's microphone in a skype conversation.

By default, this application listens for the F12 key, but can be configured to listen
to any X11 keycode by entering that keycode into a file at ``~/.push_to_talk_key``.

At the moment, this application provides no facility for providing you with the X11 keycode, but that is planned for future development.

## Dependencies

 - pygtk
 - xlib

## Installation

 - Run ``sudo ./install.sh``.
 - Restart gnome-panel by either logging-out/logging-in, or running ``sudo killall gnome-panel``.
 - Right-click on your gnome panel.
 - Select 'Add to panel'.
 - Add 'Skype Push-to-talk'.

## Keycode configuration

By default, this binds to the F12 key, but you may want to change the default key
by entering its decimal 'keysym' value into a file at ``~/.push_to_talk_key``.

At a later time, I might add a facility for gathering this keycode inside the app
itself, but for the moment this is a manual process.

To gather a new keycode:

 - Run ``xev``.  A window will appear.
 - Click on the window.
 - Press the key you'd like to use for push-to-talk.
 - Close the window.
 - Examine the terminal for a 'KeyPress' followed by a 'KeyRelease' event.  
 - Gather the value for 'keysym' on the 'KeyPress' or 'KeyRelease' event (they should be identical).  In the case of F12, the output looks like:

    KeyPress event, serial 36, synthetic NO, window 0x8200001,
        root 0x115, subw 0x0, time 1105893976, (85,-13), root:(466,577),
        state 0x10, keycode 96 (keysym *0xffc9*, F12), same_screen YES,
        XLookupString gives 0 bytes: 
        XmbLookupString gives 0 bytes: 
        XFilterEvent returns: False

 - Run ``python``.
 - Paste the value of keysym to the console.
 - Python will return the decimal value of the keysym you entered.
 - Open the file ``~/.push_to_talk_key``, and enter this integer as the sole contents of this file.
 - Save this file.
 - Log out/log in or run ``sudo killall gnome-panel``.

