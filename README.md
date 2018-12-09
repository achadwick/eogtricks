# EOGtricks: customizations for EOG

These are some custom plugins of mine for the Eye of GNOME Image viewer.

## Plugin descriptions

* **Fullscreen by Default** (eogtricks-fullscreen-windows):  
  Ensures that new windows are fullscreened by default,
  because pressing <kbd>F11</kbd> is tedious for photo review.

* **Safer File Deletion** (eogtricks-safer-delete):  
  The default trash (<kbd>Delete</kbd>)
  and perma-delete (<kbd>Shift+Delete</kbd>) keys are silent,
  and therefore dangerous.
  This plugin turns off <kbd>Delete</kbd> entirely,
  and moves the trash action to <kbd>Shift+Delete</kbd>.

* **Edit Filename “Tags”** (eogtricks-bracket-tags):  
  Makes <kbd>#</kbd> append or prepend <samp>[tags like this]</samp>
  to the filename using a dialog.
  Front and back keywords are separated with a “<samp>/</samp>”
  character.

* **Quick Move to Folder** (eogtricks-quickmove):
  Makes <kbd>M</kbd> move the current image to the folder chosen
  by pressing the <kbd>N</kbd> earlier.
  Contributed by Florian Echtler (@floe).

## Installation & management

To install:

    pip3 install .

Then enable the plugin from EOG’s preferences dialog.
Other management commands:

    pip3 install --upgrade .
    pip3 uninstall eogtricks

If you need to install for a particular python version:

    python3.7 -m pip install --verbose .

## Testing

    EOGTRICKS_DEBUG=1 eog
