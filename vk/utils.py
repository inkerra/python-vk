import os
import shutil
import locale

MB = 1024.0 ** 2

def mkdir(path):
    if path != '' and not os.path.exists(path): os.makedirs(path)

def clean_dir(path):
    if os.path.exists(path): shutil.rmtree(path)
    os.makedirs(path)

get_unicode = lambda f: f if type(f) == unicode else f.decode(locale.getpreferredencoding())
