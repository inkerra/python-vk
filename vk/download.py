import urllib2
import threading
import utils
from contextlib import closing

BLOCK_SIZE = 1024


class DownloadProgressBar(object):
    def __init__(self, idx, total, multithreading=False, name=None):
        self.idx = idx
        self.total = total
        self.w = str(len(str(self.total)))
        self.multithreading = multithreading
        self.name = name

    def show(self, written_len, remote_len):
        pass


def download_file(path, url, progress_bar=None):
    remote_sz = utils.remote_file_size(url)
    sz = utils.local_file_size(path)

    req = urllib2.Request(url)
    req.headers['Range'] = 'bytes=%d-' % sz

    with open(path, "ab" if sz else "wb") as fd:
        with closing(urllib2.urlopen(req)) as remote_fd:
            remote_fd = urllib2.urlopen(req)
            written = sz

            while written < remote_sz:
                block = remote_fd.read(BLOCK_SIZE)
                fd.write(block)
                written += len(block)
                if progress_bar:
                    progress_bar.show(written, remote_sz)


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
            if params is None:
                break
            res = self.task(*params)
            if self.res_q is not None:
                self.res_q.put(res)
            self.params_q.task_done()
