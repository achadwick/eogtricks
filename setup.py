from distutils.core import setup
import glob

setup(
    name="eogtricks",
    version="0.0.2",
    description="Personal plugins for EOG (Eye of GNOME Image Viewer)",
    author="Andrew Chadwick",
    author_email="a.t.chadwick@gmail.com",
    data_files=[
        ('share/eog/plugins', (
            list(glob.glob("eog/*.py")) +
            list(glob.glob("eog/*.plugin"))
        )),
    ],
)
