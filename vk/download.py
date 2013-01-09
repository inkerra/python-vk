import urllib2
import sys
import threading
from utils import MB

DEFAULT_BLOCK_SIZE = 1024

class DownloadProgressBar(object):
    def __init__(self, idx, multithreading=False, short_name=None, vk_filename=None):
        self.idx = idx
        self.multithreading = multithreading
        self.short_name = short_name
        self.vk_filename = vk_filename

    def show(self, written_len, remote_len):
        pass

def download_file(filename, url, local_len, remote_len, progress_bar=None):
    req = urllib2.Request(url)
    req.headers['Range'] = 'bytes=%d-' % local_len
    try:
        local_file = open(filename, "wb" if 0 == local_len else "ab")
        remote_file = urllib2.urlopen(req)

        remote_len = remote_len
        written_len = local_len

        block_size = DEFAULT_BLOCK_SIZE
        while written_len < remote_len:
            block_size = min(block_size, remote_len - written_len)
            written_len += block_size
            block = remote_file.read(block_size)
            local_file.write(block)
            if progress_bar: progress_bar.show(written_len, remote_len)
    except Exception as e:
        raise e
    finally:
        local_file.close()
        remote_file.close()

def get_file_size(url):
    res = urllib2.urlopen(url)
    assert res.getcode() == 200, "failed request to get %s" % url
    return int(res.info().getheader("Content-Length"))

class DownloaderThread(threading.Thread):
    """ Threaded downloader """
    def __init__(self, name, task, params_q, res_q=None):
        threading.Thread.__init__(self, name=name)
        self.task = task
        self.params_q = params_q
        self.res_q = res_q

    def run(self):
        while 1:
            params = self.params_q.get()
            if params is None: break
            res = self.task(*params)
            if self.res_q is not None:
                self.res_q.put(res)
            self.params_q.task_done()
