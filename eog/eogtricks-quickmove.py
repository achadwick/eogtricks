# Edit Filename “Tags” plugin for Eye of GNOME
# -*- encoding: utf-8 -*-
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

    ACTION_NAME = "new-quick-move-folder"

    window = GObject.property(type=Eog.Window)

    def __init__(self):
        super().__init__()
        self.action_new = Gio.SimpleAction(name=self.ACTION_NAME)
        self.action_new.connect("activate", self._new_activated_cb)

    def do_activate(self):
        logger.debug("Activated. Adding action win.%s", self.ACTION_NAME)
        self.window.add_action(self.action_new)
        app = self.window.get_application()
        app.set_accels_for_action( "win." + self.ACTION_NAME, ['N'], )
        self.window.get_titlebar().set_subtitle("/home/floe/")

    def do_deactivate(self):
        logger.debug("Deactivated. Removing action win.%s", self.ACTION_NAME)
        self.window.remove_action(self.ACTION_NAME)

    def _move_activated_cb(self, action, param):
        img = self.window.get_image()
        if not img:
            return
        if not img.is_file_writable():
            return

        if new_edit_name != orig_edit_name:
            logger.debug("Rename %r → %r", orig_edit_name, new_edit_name)
            store = self.window.get_store()
            old_pos = store.get_pos_by_image(img)
            file.set_display_name(new_edit_name)

            # If you rename the current image, the image is
            # re-inserted at its new aphabetical location, and the
            # UI's idea of the current image resets to position
            # zero. This is confusing and makes things feel really
            # inconsistent.

            GLib.idle_add(self._set_current_idle_cb, old_pos)

    def _new_activated_cb(self, action, param):
        dialog = Gtk.FileChooserDialog("Choose new target directory", self.window,
            Gtk.FileChooserAction.SELECT_FOLDER,
            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OPEN, Gtk.ResponseType.OK))

        dialog.set_local_only(True)
        dialog.set_current_folder(self.window.get_titlebar().get_subtitle())
        dialog.set_position(Gtk.WindowPosition.MOUSE)
        dialog.set_default_response(Gtk.ResponseType.OK)
 
        response = dialog.run()

        try:
            if response != Gtk.ResponseType.OK:
                return

            newfolder = dialog.get_filename()
            tb = self.window.get_titlebar()
            tb.set_subtitle(newfolder)

        except:
            raise
        finally:
            dialog.destroy()

    def _set_current_idle_cb(self, old_pos):
        # Keeps the cursor position in the sequence at +1/0/-1 away
        # from its previous position.
        view = self.window.get_thumb_view()
        store = self.window.get_store()
        img = store.get_image_by_pos(old_pos)
        view.set_current_image(img, True)
        return False

#    def _print_accels(self):
#        app = self.window.get_application()
#        for detailed_name in app.list_action_descriptions():
#            print(detailed_name, end=", ")
#            print(app.get_accels_for_action(detailed_name))
