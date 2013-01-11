import os
import shutil
import locale
import urllib2

MB = 1024.0 ** 2

def mkdir(path):
    if path != '' and not os.path.exists(path): os.makedirs(path)

def clean_dir(path):
    if os.path.exists(path): shutil.rmtree(path)
    os.makedirs(path)

def get_unicode(s):
    if isinstance(s, unicode): return s
    return s.decode(locale.getpreferredencoding())

def remote_file_size(url):
    return int(urllib2.urlopen(url).info().getheader("Content-Length"))

def local_file_size(path):
    return os.path.getsize(path) if os.path.exists(path) else 0

def norm_path(path, name, fmt=None):
    return os.path.normpath(os.path.join(path, fmt % name if fmt else name))
