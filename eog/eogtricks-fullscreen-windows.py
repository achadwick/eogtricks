# Fullscreen by Default plugin for Eye of GNOME
# -*- encoding: utf-8 -*-
# Copyright (C) 2017 Andrew Chadwick <a.t.chadwick@gmail.com>
# Copyright (C) 2015 Felix Riemann <friemann@gnome.org>
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

from __future__ import print_function, division

import logging
import os

from gi.repository import Eog
from gi.repository import GObject
from gi.repository import GLib


logger = logging.getLogger(__name__)
if os.environ.get("EOGTRICKS_DEBUG"):
    logging.basicConfig(level=logging.DEBUG)


class FullscreenWindows (GObject.Object, Eog.WindowActivatable):
    """Plugin causing new EogWindows to open in fullscreen mode."""

    window = GObject.property(type=Eog.Window)

    def __init__(self):
        super(FullscreenWindows, self).__init__()

    def do_activate(self):
        """Maximize each window this plugin is activated for."""
        assert self.window.has_action("view-fullscreen"), \
            "Eog.Window doesn't have the view-fullscreen action any more"

        # Could use self.window.fullscreen(), but doing it this way
        # resizes the image nicely too. And without it, the edge
        # revealers won't work.

        logger.debug("Activated. Setting view-fullscreen to True.")
        self.window.change_action_state(
            "view-fullscreen",
            GLib.Variant("b", True),
        )

        return False

    def do_deactivate(self):
        """Does nothing on deactivation"""
        pass
