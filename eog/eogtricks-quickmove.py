# Quick Move plugin for Eye of GNOME
# -*- encoding: utf-8 -*-
# Copyright (C) 2018 Florian Echtler <floe@butterbrot.org>
# Copyright (C) 2017 Andrew Chadwick <a.t.chadwick@gmail.com>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software Foundation,
# Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

from __future__ import print_function

import re
import os
import shutil
import logging

from gi.repository import Eog
from gi.repository import GObject
from gi.repository import Gio
from gi.repository import Gtk
from gi.repository import Pango
from gi.repository import GLib


logger = logging.getLogger(__name__)
if os.environ.get("EOGTRICKS_DEBUG"):
    logging.basicConfig(level=logging.DEBUG)

class QuickMove(GObject.GObject, Eog.WindowActivatable):

    ACTION_NEW_NAME = "new-quick-move-folder"
    ACTION_MOVE_NAME = "do-quick-move"

    window = GObject.property(type=Eog.Window)
    folder = None # os.path.expanduser('~')

    def __init__(self):
        super().__init__()
        self.action_new = Gio.SimpleAction(name=self.ACTION_NEW_NAME)
        self.action_move = Gio.SimpleAction(name=self.ACTION_MOVE_NAME)
        self.action_new.connect("activate", self._new_activated_cb)
        self.action_move.connect("activate", self._move_activated_cb)

    def do_activate(self):
        logger.debug("Activated. Adding action win.%s", self.ACTION_NEW_NAME)
        logger.debug("Activated. Adding action win.%s", self.ACTION_MOVE_NAME)
        self.window.add_action(self.action_new)
        self.window.add_action(self.action_move)
        app = self.window.get_application()
        app.set_accels_for_action( "win." + self.ACTION_NEW_NAME, ['N'], )
        app.set_accels_for_action( "win." + self.ACTION_MOVE_NAME, ['M'], )
        self.window.get_titlebar().set_subtitle("Target: None")

    def do_deactivate(self):
        logger.debug("Deactivated. Removing action win.%s", self.ACTION_NEW_NAME)
        logger.debug("Deactivated. Removing action win.%s", self.ACTION_MOVE_NAME)
        self.window.remove_action(self.ACTION_NEW_NAME)
        self.window.remove_action(self.ACTION_MOVE_NAME)

    def _move_activated_cb(self, action, param):
        if not self.folder:
            return

        img = self.window.get_image()
        if not img:
            return
        if not img.is_file_writable():
            return

        src = img.get_file().get_path()
        srcdir = os.path.dirname(src)
        dest = self.folder

        if srcdir == dest:
            return

        # Create directory if it doesn't exist.
        try:
            os.makedirs(dest)
        except OSError:
            pass

        # If you rename the current image, the image is
        # re-inserted at its new aphabetical location, and the
        # UI's idea of the current image resets to position
        # zero. This is confusing and makes things feel really
        # inconsistent.

        store = self.window.get_store()
        old_pos = store.get_pos_by_image(img)
        view = self.window.get_thumb_view()

        logger.debug("Adjusting view position to %d", old_pos+1)
        img2 = store.get_image_by_pos(old_pos+1)
        view.set_current_image(img2, True)
        store.remove_image(img)

        logger.debug("Move %r → %r", src, dest)
        shutil.move(src, dest)

    def _new_activated_cb(self, action, param):
        dialog = Gtk.FileChooserDialog("Choose new target directory", self.window,
            Gtk.FileChooserAction.SELECT_FOLDER,
            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OPEN, Gtk.ResponseType.OK))

        startfolder = self.folder if self.folder else os.path.expanduser('~')

        dialog.set_local_only(True)
        dialog.set_current_folder(startfolder)
        dialog.set_position(Gtk.WindowPosition.MOUSE)
        dialog.set_default_response(Gtk.ResponseType.OK)
 
        response = dialog.run()

        try:
            if response != Gtk.ResponseType.OK:
                return

            self.folder = dialog.get_filename()
            tb = self.window.get_titlebar()
            tb.set_subtitle("Target: "+self.folder)
            logger.debug("New target folder: %s",self.folder)

        except:
            raise
        finally:
            dialog.destroy()

