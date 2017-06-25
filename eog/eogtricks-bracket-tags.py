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

TAG_RE = re.compile(r'\s*(\[[^\[\]]*\])\s*')
FORBIDDEN_ENTRY_CHARS = '[ ] ; ,'.split(' ')
FORBIDDEN_CHARS = re.compile(r'[\[\];,/]')
FORBIDDEN_CHAR_REPLACEMENT = '_'


def uniq(list, seen=None):
    if seen is None:
        seen = set()
    for item in list:
        if item in seen:
            continue
        seen.add(item)
        yield(item)


def check_entry_text(widget, string, len, pos):
    # print([widget, string, len, pos])
    for c in string:
        if c in FORBIDDEN_ENTRY_CHARS:
            widget.stop_emission_by_name('insert-text')


def split_tags(basename):
    basename, ext = os.path.splitext(basename)
    tokens = TAG_RE.split(basename)
    tokens = [t for t in tokens if t != ""]
    if not tokens:
        return ([], basename, [], ext)

    start_tags = []
    end_tags = []

    if TAG_RE.fullmatch(tokens[0]):
        block = tokens[0].strip("[]").strip()
        tokens = tokens[1:]
        start_tags.extend(block.split())
    non_tag_tokens = []
    for token in tokens:
        if TAG_RE.fullmatch(token):
            block = token.strip("[]").strip()
            end_tags.extend(block.split())
        else:
            non_tag_tokens.append(token)

    basename = "".join(non_tag_tokens)

    seen = set()
    start_tags = list(uniq(start_tags, seen))
    end_tags = list(uniq(end_tags, seen))

    return (start_tags, basename, end_tags, ext)


def tags2editstr(start_tags, end_tags):
    seen = set()
    start_tags = list(uniq(start_tags, seen))
    end_tags = list(uniq(end_tags, seen))
    if start_tags and end_tags:
        return ' / '.join((' '.join(start_tags), ' '.join(end_tags)))
    elif end_tags and not start_tags:
        return ' '.join(end_tags)
    elif start_tags and not end_tags:
        return ' '.join(start_tags) + ' /'
    else:
        return ''


def editstr2tags(editstr):
    blocks = editstr.split('/')
    while len(blocks) > 2:
        blocks[1] = blocks[1] + ' ' + blocks.pop()
    tags = []
    for b in blocks:
        b_tags = b.lower().strip().split()
        b_tags = [
            FORBIDDEN_CHARS.sub(FORBIDDEN_CHAR_REPLACEMENT, w)
            for w in b_tags
            if w != ''
        ]
        tags.append(b_tags)
    start_tags = []
    end_tags = []
    if len(tags) == 2:
        start_tags, end_tags = tags
    else:
        end_tags = tags[0]
    seen = set()
    start_tags = list(uniq(start_tags, seen))
    end_tags = list(uniq(end_tags, seen))
    return start_tags, end_tags


class TagEditor (GObject.GObject, Eog.WindowActivatable):

    ACTION_NAME = "edit-filename-tags"

    window = GObject.property(type=Eog.Window)

    def __init__(self):
        super().__init__()
        self.action = Gio.SimpleAction(name=self.ACTION_NAME)
        self.action.connect("activate", self._action_activated_cb)

    def do_activate(self):
        logger.debug("Activated. Adding action win.%s", self.ACTION_NAME)
        self.window.add_action(self.action)
        app = self.window.get_application()
        app.set_accels_for_action(
            "win." + self.ACTION_NAME,
            ["numbersign"],
        )

    def do_deactivate(self):
        logger.debug("Deactivated. Removing action win.%s", self.ACTION_NAME)
        self.window.remove_action(self.ACTION_NAME)

    def _action_activated_cb(self, action, param):
        img = self.window.get_image()
        if not img:
            return
        if not img.is_file_writable():
            return

        flags = Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT
        dialog = Gtk.Dialog(
            "Edit Tags",
            self.window,
            flags,
            buttons=[
                "Cancel", Gtk.ResponseType.REJECT,
                "OK", Gtk.ResponseType.ACCEPT,
            ],
        )
        dialog.set_position(Gtk.WindowPosition.MOUSE)
        dialog.set_default_response(Gtk.ResponseType.ACCEPT)

        file = img.get_file()
        flags = Gio.FileQueryInfoFlags.NOFOLLOW_SYMLINKS
        attrs = Gio.FILE_ATTRIBUTE_STANDARD_EDIT_NAME
        fileinfo = file.query_info(attrs, flags)
        orig_edit_name = fileinfo.get_edit_name()

        tags1, basename, tags2, ext = split_tags(orig_edit_name)
        edit_str = tags2editstr(tags1, tags2)

        entry = Gtk.Entry()
        entry.set_text(edit_str)
        entry.set_activates_default(True)
        entry.set_input_purpose(Gtk.InputPurpose.FREE_FORM)
        hints = Gtk.InputHints.SPELLCHECK | Gtk.InputHints.LOWERCASE
        entry.set_input_hints(hints)
        entry.connect('insert-text', check_entry_text)
        entry.grab_focus()
        # entry.set_position(-1)
        entry.set_size_request(400, -1)
        # GLib.idle_add(entry.select_region, 0, 0)
        # GLib.idle_add(entry.set_position, -1)

        label = Gtk.Label("Editing tags for “%s”" % orig_edit_name)
        label.set_ellipsize(Pango.EllipsizeMode.MIDDLE)

        dialog.vbox.pack_start(label, 1, 1, 0)
        dialog.vbox.pack_start(entry, 0, 0, 0)

        entry.show()
        label.show()

        response = dialog.run()
        try:
            if response != Gtk.ResponseType.ACCEPT:
                return

            tags1, tags2 = editstr2tags(entry.get_text())
            new_edit_name = ""
            if tags1:
                new_edit_name += "[{}] ".format(" ".join(tags1))
            new_edit_name += basename
            if tags2:
                new_edit_name += " [{}]".format(" ".join(tags2))
            new_edit_name += ext

            # Rename the image by setting its GFile's display name.

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

    def _print_accels(self):
        app = self.window.get_application()
        for detailed_name in app.list_action_descriptions():
            print(detailed_name, end=", ")
            print(app.get_accels_for_action(detailed_name))
