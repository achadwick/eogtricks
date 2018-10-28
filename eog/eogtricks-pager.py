# Pager plugin for Eye of GNOME.
# -*- encoding: utf-8 -*-
# Copyright (C) 2018 Andrew Chadwick <a.t.chadwick@gmail.com>
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
from enum import Enum

from gi.repository import Eog
from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import Gio
from gi.repository import GLib


logger = logging.getLogger(__name__)
if os.environ.get("EOGTRICKS_DEBUG"):
    logging.basicConfig(level=logging.DEBUG)


FIT_PAGE_MIN_ACTION_NAME = "zoom-fit-page-min"
PAGE_FORWARD_ACTION_NAME = "page-forward"
PAGE_BACKWARD_ACTION_NAME = "page-backward"

PAGE_SCROLL_FRACTION = 0.9  # of a page


class PageDimension (Enum):
    WIDTH = 1
    HEIGHT = 2


class PagerPlugin (GObject.Object, Eog.WindowActivatable):
    """Page backwards and forwards."""

    # GObject properties:

    window = GObject.property(type=Eog.Window)

    # Construction:

    def __init__(self):
        super(PagerPlugin, self).__init__()
        self._hscroll = None
        self._vscroll = None
        self._old_accels = {}
        self._accels = {
            "win." + FIT_PAGE_MIN_ACTION_NAME: ["w", "x", "h"],
            "win." + PAGE_BACKWARD_ACTION_NAME: ["Prior", "b", "BackSpace"],
            "win." + PAGE_FORWARD_ACTION_NAME: ["Next", "space", "Return"],
        }
        self._signal_handlers = []
        self._just_paged_direction = 0
        self._actions = []
        self._fit_page_min = False

    # Plugin activation:

    def _setup_scroll_bars(self):
        """Find the scrollbars in the image view."""
        view = self.window.get_view()
        logger.debug("View: %r", view)
        if self._hscroll and self._vscroll:
            return
        for w in self._walk(view):
            if not isinstance(w, Gtk.Scrollbar):
                continue
            w_ori = w.get_orientation()
            if w_ori == Gtk.Orientation.VERTICAL:
                self._vscroll = w
            elif w_ori == Gtk.Orientation.HORIZONTAL:
                self._hscroll = w
        assert self._vscroll is not None
        assert self._hscroll is not None

    def _setup_accels(self):
        """Establish the plugin's key bindings."""
        assert not self._old_accels
        app = self._app

        action_descs = app.list_action_descriptions()

        # Preseve existing keybindings
        # where the keys will be shadowed by the new actions.
        shadowed_keys = set()
        for (name, keys) in self._accels.items():
            for key in keys:
                shadowed_keys.add(key)
        for name in action_descs:
            old_keys = app.get_accels_for_action(name)
            new_keys = [k for k in old_keys if k not in shadowed_keys]
            if new_keys == old_keys:
                continue
            self._old_accels[name] = old_keys
            app.set_accels_for_action(name, new_keys)
        logger.debug("Preserved %r", self._old_accels)

        # Associate the new keybindings with their actions.
        for (name, keys) in self._accels.items():
            app.set_accels_for_action(name, keys)
        logger.debug("Added bindings: %r", self._accels)

    def _setup_action(self, name, cb):
        action = Gio.SimpleAction(name=name)
        action.connect("activate", cb)
        self._actions.append(action)
        self.window.add_action(action)
        return action

    def do_activate(self):
        logger.debug("Activating...")

        # Create and bind the actions.
        assert not self._actions
        fit_page_min_action = self._setup_action(
            FIT_PAGE_MIN_ACTION_NAME,
            self._fit_to_width_activate_cb,
        )
        self._setup_action(
            PAGE_BACKWARD_ACTION_NAME,
            self._page_command_activate_cb,
        )
        self._setup_action(
            PAGE_FORWARD_ACTION_NAME,
            self._page_command_activate_cb,
        )
        assert self._actions
        self._fit_page_min_action = fit_page_min_action

        if False:
            ref_action = self.window.lookup_action("toggle-zoom-fit")
            if ref_action:
                # flags = GObject.BindingFlags.INVERT_BOOLEAN
                flags = GObject.BindingFlags.SYNC_CREATE
                ref_action.bind_property(
                    "enabled",
                    fit_page_min_action, "enabled",
                    flags,
                )
            else:
                logger.warning("Cannot bind enabled state to toggle-zoom-fit.")

        # Keys
        self._setup_accels()

        # UI
        self._setup_scroll_bars()

        # Set up signal handlers.
        scroll_view = self.window.get_view()
        handler_info = [
            ("notify::image", self._notify_image_cb),
            ("notify::zoom-mode", self._notify_zoom_mode_cb),
        ]
        for sig, func in handler_info:
            handler_id = scroll_view.connect(sig, func)
            self._signal_handlers.append((scroll_view, handler_id))

    # Plugin deactivation:

    def _teardown_accels(self):
        """Revert the plugin's key bindings."""
        app = self._app

        # Remove the accels set up earlier
        for name in self._accels.keys():
            app.set_accels_for_action(name, [])
        logger.debug("Removed bindings: %r", self._accels)

        # Restore any previously shadowed bindings to their prior state.
        for (name, old_keys) in self._old_accels.items():
            app.set_accels_for_action(name, old_keys)
        logger.debug("Restored %r", self._old_accels)
        self._old_accels.clear()

    def do_deactivate(self):
        logger.debug("Deactivating...")

        # Tear down the signal handlers.
        for (obj, hid) in self._signal_handlers:
            obj.disconnect(hid)
        self._signal_handlers[:] = []
        self._teardown_accels()

        # Remove the actions from the window.
        for action in self._actions:
            self.window.remove_action(action.get_name())
        self._actions[:] = []

    # Action callbacks:

    def _fit_to_width_activate_cb(self, action, param):
        self._fit_to_width(v=0.0)
        self._fit_page_min = True
        logger.debug("fit-page-min → ON")

    def _page_command_activate_cb(self, action, param):
        """Handle the user commands to page either backward or forward.

        The page forward/backward code code works by inspecting
        scrollbars, modifying their inderlying adjustment values, and
        sometimes causing eog to move on to the next or previous image.

        """

        # Decide the direction, limits, and a secondary action to invoke
        # based on the action that was activated.
        action_name = action.get_name()
        if action_name == PAGE_FORWARD_ACTION_NAME:
            sign = 1
            limit = 0.99
            within_limit = limit.__gt__
            go_action_name = "go-next"
        elif action_name == PAGE_BACKWARD_ACTION_NAME:
            sign = -1
            limit = 0.01
            within_limit = limit.__lt__
            go_action_name = "go-previous"
        else:
            raise ValueError("Unexpected pager action %r" % action_name)

        # Decide which scrollbar. This code uses the scrollbar
        # visibility state as a proxy for "has the image been zoomed to
        # less that the size of the screen (in a particular dimension)?
        #
        # TODO: switch between vertical and horizontal scrollbars
        # depending on whether it's fit-width or fit-height.

        view = self.window.get_view()
        sb = self._vscroll
        sb_visible = view.scrollbars_visible() and sb.get_visible()
        sb_frac = self._get_scroll_frac(sb)

        # Move by a screenful, or progress to the next or previous
        # image. Sometimes that means going to a specific end of the
        # previous or next image.
        if view.get_zoom_mode() != Eog.ZoomMode.FREE:
            logger.debug("%s: %s (fitted)", action_name, go_action_name)
            self._just_paged_direction = 0
            self.window.activate_action(go_action_name, None)
        elif sb_visible and (sb_frac is not None) and within_limit(sb_frac):
            logger.debug("%s: scroll %s page within the current image",
                         action_name, sign)
            self._scroll_by_pages(sb, sign * PAGE_SCROLL_FRACTION)
        else:
            logger.debug("%s: %s and go to top/bottom",
                         action_name, go_action_name)
            self._just_paged_direction = sign
            self.window.activate_action(go_action_name, None)

    # Fitting and scrolling:

    def _fit_to_width(self, v=0.0):
        self._scroll_to(self._hscroll, 0.5)
        self._fit_dimension(PageDimension.WIDTH)
        GLib.idle_add(self._scroll_to, self._vscroll, v)

    def _fit_dimension(self, dim, compensate=True):
        """Fits the image to the EogScrollView's width or height.

        Note that this will turn on the other dimension's scroll bar if
        the image is bigger in that dimension. This chnges the available
        screen size and thus the calculation that this function does.
        Therefore, this method normally requeues itself as a one-shot
        idle function if needed to compensate.

        """
        view = self.window.get_view()
        image = view.get_image()
        pixbuf = image.get_pixbuf()

        if dim is PageDimension.WIDTH:
            view_size = view.get_allocated_width()
            scroll_size = self._vscroll.get_allocated_width()
            image_size = pixbuf.get_width()
            image_size_other = pixbuf.get_height()
        elif dim is PageDimension.HEIGHT:
            view_size = view.get_allocated_height()
            scroll_size = self._hscroll.get_allocated_height()
            image_size = pixbuf.get_height()
            image_size_other = pixbuf.get_width()
        else:
            raise ValueError("Unknown dimension: %r" % (dim,))
        new_zoom = (view_size - scroll_size) / image_size

        if view.get_zoom_mode != Eog.ZoomMode.FREE:
            view.set_zoom_mode(Eog.ZoomMode.FREE)
        view.set_zoom(new_zoom)

        if (image_size_other > image_size) and compensate:
            logger.debug("compensating for scroll bars...")
            GLib.idle_add(self._fit_dimension, dim, False)
        return False

    def _scroll_to(self, range, frac):
        """Scrolls a GtkRange to a given fraction of its whole.

        This can be called as a one-shot idle function.

        """
        frac = min(1.0, max(0.0, float(frac)))
        v_adj = range.get_adjustment()

        lower = v_adj.get_lower()
        upper = v_adj.get_upper()
        page_size = v_adj.get_page_size()

        bottom = lower
        top = upper - page_size
        new_value = bottom + (frac * (top - bottom))

        v_adj.set_value(new_value)

        return False

    def _get_scroll_frac(self, range):

        v_adj = range.get_adjustment()
        value = float(v_adj.get_value())

        lower = v_adj.get_lower()
        upper = v_adj.get_upper()
        page_size = v_adj.get_page_size()
        logger.debug(
            "V=%r (L=%r, U=%r, P=%r)",
            value,
            lower, upper,
            page_size,
        )

        if upper <= lower:
            logger.debug("frac=None (weird initial state)")
            return None  # initial scrollbar state...

        at_end = ((value + page_size) >= upper)
        at_start = (value <= lower)
        if at_end and at_start:
            logger.debug("frac=None (image <= screen)")
            return None  # image is screen-sized or smaller

        bottom = lower
        top = upper - page_size

        frac = (value - bottom) / (top - bottom)

        logger.debug("frac=%0.2f (calculated)", frac)
        frac = min(1.0, max(0.0, float(frac)))
        logger.debug("frac=%0.2f (clamped)", frac)
        return frac

    def _scroll_by_pages(self, range, n):
        v_adj = range.get_adjustment()
        value = float(v_adj.get_value())

        lower = v_adj.get_lower()
        upper = v_adj.get_upper()
        page_size = v_adj.get_page_size()

        bottom = lower
        top = upper - page_size

        value += n * page_size
        value = min(top, max(bottom, value))
        v_adj.set_value(value)

        frac = (value - bottom) / (top - bottom)

        frac = min(1.0, max(0.0, float(frac)))
        return frac

    # Signal handlers:

    def _notify_image_cb(self, view, param):
        """Fit width or scroll to ends when the image changes."""
        logger.debug("change of %r detected", param.name)

        if self._just_paged_direction != 0:
            if self._fit_page_min:
                logger.debug("fitting new image to width")
                self._fit_dimension(PageDimension.WIDTH)

        if self._just_paged_direction < 0:
            logger.debug("scrolling new image to end")
            self._scroll_to(self._vscroll, 1)
        elif self._just_paged_direction > 0:
            logger.debug("scrolling new image to start")
            self._scroll_to(self._vscroll, 0)

        self._just_paged_direction = 0

    def _notify_zoom_mode_cb(self, view, param):
        """Changing the zoom mode turns off the min-dimension fitting."""
        view = self.window.get_view()
        mode = view.get_zoom_mode()
        if self._just_paged_direction == 0:
            if self._fit_page_min and (mode != Eog.ZoomMode.FREE):
                logger.debug("fit-page-min → off")
                self._fit_page_min = False

    # Helpers:

    @property
    def _app(self):
        """Returns the main application object."""
        return self.window.get_application()

    def _dump_accels(self):
        app = self._app
        for n in sorted(app.list_action_descriptions()):
            a = app.get_accels_for_action(n)
            print("%s → %r" % (n, a))

    def _walk(self, widget):
        """Recursively walk the descendent widgets of a container."""
        widgets = [widget]
        while widgets:
            w = widgets.pop(0)
            yield w
            if hasattr(w, "get_children"):
                for c in reversed(w.get_children()):
                    widgets.insert(0, c)
