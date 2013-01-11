import urllib2
from lxml import html
import os
import sys
import threading
import Queue
import logging
from download import download_file, DownloadProgressBar, DownloaderThread
from utils import *
import re
import math
from HTMLParser import HTMLParser

MAX_ARTIST_LEN = 40
MAX_TITLE_LEN = 60
SHORT_ARTIST_LIM = 30
SHORT_TITLE_LIM= 30
NAME_FMT = "%s__%s.mp3"

class AudioDownloadProgressBar(DownloadProgressBar):
    def show(self, written_len, remote_sz):
        if self.multithreading:
            cur_thread = int(threading.current_thread().getName()) - 1
            progress = '\r' + '\t' * (cur_thread * 3) \
                + "#%-5d(%-5.02fMB %3d%%)" \
                % (
                    self.idx + 1,
                    written_len / MB,
                    100.0 * written_len / remote_sz
                )
        else:
            progress = "\r#%-5d %-66s[%-10s](%-5.02fMB %3d%%)" \
                % (
                    self.idx + 1,
                    self.short,
                    self.vk_name,
                    written_len / MB,
                    100.0 * written_len / remote_sz
                )

        sys.stdout.write(progress)
        sys.stdout.flush()

def get_name(audio, a_lim=MAX_ARTIST_LEN, t_lim=MAX_TITLE_LEN, tail=''):
    def get(audio, elem):
        t = audio.find(elem).text
        if t:
            return get_unicode(HTMLParser().unescape(t).replace(os.sep, ''))
        return u''

    artist = (get(audio, 'artist'), a_lim)
    title = (get(audio, 'title'), t_lim)

    def cut((name, lim), (o_name, o_lim), tail):
        lim += o_lim - len(o_name) if o_lim > len(o_name) else 0
        return name[:(lim - len(tail))] + tail if len(name) > lim else name

    return NAME_FMT % (cut(artist, title, tail), cut(title, artist, tail))

def download_audio((i, audio), amount, path, lnks_path, lnk_fmt, m_th=True):
    basename = get_name(audio)

    filename = norm_path(path, basename)

    if os.path.exists(filename):
        logging.debug("[%d/%d] \"%s\" has been downloaded.",
            i + 1, amount, filename)
    else:
        url = audio.find('url').text
        name = re.search(r"[0-9a-zA-Z]+\.mp3$", url).group()
        vk_name = norm_path(path, name)

        sz = local_file_size(vk_name)
        remote_sz = remote_file_size(url)

        logging.debug("[#%d] %s - %d (%.02fM)",
            i + 1, url, remote_sz, remote_sz / MB)

        short = get_name(audio, SHORT_ARTIST_LIM, SHORT_TITLE_LIM, '...')
        if sz != remote_sz:
            logging.warning("[#%d/%d] \"%s\" (%s, %s bytes)",
                i + 1, amount, filename, name, remote_sz - sz)

            if logging.getLogger().isEnabledFor(logging.INFO):
                progress_bar = \
                    AudioDownloadProgressBar(i, m_th, short, name)
            else:
                progress_bar = None

            download_file(vk_name, url, progress_bar)

        try:
            os.rename(vk_name, filename)
        except OSError as e:
            raise RuntimeError("Can't rename: %s -> %s" \
                % (vk_name, filename))

    relpath = os.path.relpath(os.path.abspath(path),
                                os.path.abspath(lnks_path))
    new_path = norm_path(relpath, basename)

    lnk = lnk_fmt % (i + 1, basename)
    lnk_path = norm_path(path, lnk)

    try:
        os.symlink(new_path, lnk_path)
    except OSError as e:
        raise RuntimeError("Can't create symlink: %s -> %s" \
            % (lnk_path, new_path))
    logging.debug("[#%d] %s -> %s", i + 1, lnk, new_path)
    return basename

def download_audio_list(th_pool_sz, audio_list, path, lnk_dir, ans=None):
    amount = len(audio_list)

    lnk_fmt = norm_path(lnk_dir, int(1 + math.log10(amount)), "%%0%dd=%%s")
    lnks_path = norm_path(path, lnk_dir)

    vk_files = []

    params = (amount, path, lnks_path, lnk_fmt)
    audios = enumerate(audio_list)

    if th_pool_sz > 1:
        params_q = Queue.Queue()
        res_q = Queue.Queue()

        for i in range(th_pool_sz):
            th = DownloaderThread(i + 1, download_audio, params_q, res_q)
            th.setDaemon(True)
            th.start()

        for p in audios:
            params_q.put(((p, ) + params))

        params_q.join()

        while res_q.qsize():
            vk_files.append(res_q.get())
    else:
        vk_files = [download_audio(p, *params, m_th=False) for p in audios]

    logging.warning("All Done.")

    root, dirs, files = os.walk(path).next()
    files = [get_unicode(re.match('.*[.]mp3', f).group()) for f in files]

    old_files = [f for f in files if f not in vk_files]

    logging.info('Outdated audios:\n' + '\n'.join(old_files))

    if len(old_files):
        if ans is None:
            ans = raw_input("Delete outdated audios?[%d] (y or n) [n] "\
                %  len(old_files))
        if ans.strip().lower().startswith('y'):
            for f in old_files:
                logging.debug("Deleting %s ...", f)
                os.remove(norm_path(path, f))
            logging.warning("Deleted outdated files [%d].", len(old_files))

def get_audio_list(user_id, access_token):
    url = "https://api.vkontakte.ru/method/audio.get.xml?uid=%s&access_token=%s" % (user_id, access_token)
    doc  = html.document_fromstring(urllib2.urlopen(url).read())
    return doc.cssselect('audio')
