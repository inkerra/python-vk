import sys
if sys.platform.startswith('win'):
    try:
        try:
            import py2exe.mf as modulefinder
        except ImportError:
            import modulefinder
        import win32com, sys
        for p in win32com.__path__[1:]:
            modulefinder.AddPackagePath("win32com", p)
        for extra in ["win32com.shell"]: #,"win32com.mapi"
            __import__(extra)
            m = sys.modules[extra]
            for p in m.__path__[1:]:
                modulefinder.AddPackagePath(extra, p)
    except ImportError:
        pass

from distutils.core import setup
import py2exe
import lxml

setup(
    name='vk_music_downloader',
    version="1.0",
    author="inKerra",
    author_email='inkerra@gmail.com',
    console=["download_vk_music.py"],
    options={
        'py2exe':
	{
	    'includes': ['lxml.etree', 'lxml._elementpath'],
	},
    },
)
