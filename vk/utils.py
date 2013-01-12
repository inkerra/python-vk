import os
import sys
import shutil
import locale
import urllib2
from HTMLParser import HTMLParser

MB = 1024.0 ** 2

if sys.platform.startswith('win'):
    import winshell
    import win32com.client
    import pythoncom
    import threading

    def symlink(src, dst):
    	lnk = os.path.abspath(dst)
	target = norm_path(os.path.dirname(lnk), src)
	
	th_name = threading.currentThread().name
	
	if th_name != "MainThread": pythoncom.CoInitialize()
	
	shell = win32com.client.Dispatch('WScript.Shell')
	
	shortcut = shell.CreateShortCut(lnk)
	shortcut.Targetpath = target
	shortcut.save()
	
	if th_name != "MainThread": pythoncom.CoUninitialize()

    INVALID_FILENAME_CHARS = u'?/\\:<>"*|'

elif sys.platform.startswith('lin'):
    symlink = os.symlink
    INVALID_FILENAME_CHARS = u'/'

def mkdir(path):
    if path != '' and not os.path.exists(path): os.makedirs(path)

def clean_dir(path):
    if os.path.exists(path): shutil.rmtree(path)
    os.makedirs(path)

def get_unicode(s):
    if isinstance(s, unicode): return s
    return s.decode(locale.getpreferredencoding())

def valid_filename(s):
    unescape = HTMLParser().unescape
    unsupported = dict((ord(ch), u'') for ch in INVALID_FILENAME_CHARS)
    return get_unicode(unescape(s)).translate(unsupported)

def remote_file_size(url):
    return int(urllib2.urlopen(url).info().getheader("Content-Length"))

def local_file_size(path):
    return os.path.getsize(path) if os.path.exists(path) else 0

def norm_path(path, name, fmt=None):
    return os.path.normpath(os.path.join(path, fmt % name if fmt else name))
