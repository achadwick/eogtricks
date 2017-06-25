# Safer File Deletion plugin for Eye of GNOME.
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
from __future__ import division

import logging
import os

from gi.repository import Eog
from gi.repository import GObject


logger = logging.getLogger(__name__)
if os.environ.get("EOGTRICKS_DEBUG"):
    logging.basicConfig(level=logging.DEBUG)


class NoDelete (GObject.Object, Eog.ApplicationActivatable):
    """Remove the insta-delete accelerator, Shift+Delete now trashes"""

    app = GObject.property(type=Eog.Application)

    def __init__(self):
        super(NoDelete, self).__init__()
        self._improved_bindings = {
            "win.delete": [],                    # was Shift+Delete
            "win.move-trash": ["<Shift>Delete"],  # was Delete
        }
        self._old_bindings = {}

    def do_activate(self):
        app = self.app
        action_descs = app.list_action_descriptions()
        for (detailed_name, new_accels) in self._improved_bindings.items():
            assert detailed_name in action_descs, \
                "Missing {} command".format(detailed_name)
            old_accels = app.get_accels_for_action(detailed_name)
            self._old_bindings[detailed_name] = old_accels
            app.set_accels_for_action(detailed_name, new_accels)
        logger.debug("Activated. Now using %r.", self._improved_bindings)

    def do_deactivate(self):
        app = self.app
        for (detailed_name, old_accels) in self._old_bindings.items():
            app.set_accels_for_action(detailed_name, old_accels)
        logger.debug("Deactivated. Reverting to %r.", self._old_bindings)
        self._old_bindings = {}

    def _dump_accels(self):
        for n in sorted(self.app.list_action_descriptions()):
            a = self.app.get_accels_for_action(n)
            print("%s → %r" % (n, a))
