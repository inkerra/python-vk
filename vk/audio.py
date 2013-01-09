import urllib2
from lxml import html
import os
import sys
import threading
import Queue
import logging
from download import download_file, DownloadProgressBar, get_file_size, DownloaderThread
from utils import MB, get_unicode
import re
import math
from HTMLParser import HTMLParser

MAX_ARTIST_LEN = 40
MAX_TITLE_LEN = 60
SHORT_ARTIST_LIM = 30
SHORT_TITLE_LIM= 30

class AudioDownloadProgressBar(DownloadProgressBar):
    def show(self, written_len, remote_len):
        if self.multithreading:
            try:
                cur_thread = int(threading.current_thread().getName()) - 1
            except Exception as e:
                print "[%s] #%d:%s [thread=%s]" % (e, (self.idx + 1), self.short_name, cur_thread)
                sys.exit(1)

            sys.stdout.write('\r' + '\t' * (cur_thread * 3)  + "#%-5d(%-5.02fMB %3d%%)" \
                % (self.idx + 1, written_len / MB, 100.0 * written_len / remote_len))
        else:
            sys.stdout.write("\r#%-5d %-66s[%-10s](%-5.02fMB %3d%%)" \
                % (self.idx + 1, self.short_name, self.vk_filename, written_len / MB, 100.0 * written_len / remote_len))
        sys.stdout.flush()

def get_name(audio, a_lim=MAX_ARTIST_LEN, t_lim=MAX_TITLE_LEN, tail=''):
    escape = lambda t: '' if t is None or len(t) == 0 else HTMLParser().unescape(t).replace(os.sep, '')
    get = lambda audio, elem: get_unicode(escape(audio.find(elem).text))

    artist = get(audio, 'artist')
    title = get(audio, 'title')

    cut = lambda name, lim, tail: \
        name[:(lim - len(tail))] + tail if len(name) > lim else name
    fund = lambda name, lim: lim - len(name) if lim > len(name) else 0

    return "__".join([ \
        cut(artist, a_lim + fund(title, t_lim), tail), \
        cut(title, t_lim + fund(artist, a_lim), tail) \
        ]) + ".mp3"

def download_audio(audio, idx, amount, path, path_to_links_dir, linkname_fmt, multithreading=True):
    basename = get_name(audio)

    get_filepath = lambda path, name, fmt=None: os.path.join(path, fmt % name if fmt else name)

    final_filename = get_filepath(path, basename)

    if os.path.exists(final_filename):
        logging.debug("[%d/%d] \"%s\" has been downloaded." % (idx + 1, amount, final_filename))
    else:
        url = audio.find('url').text
        name = re.search(r"[0-9a-zA-Z]+\.mp3$", url).group()
        vk_filename = os.path.join(path, name)

        local_len = os.path.getsize(vk_filename) if os.path.exists(vk_filename) else 0

        remote_len = get_file_size(url)

        logging.debug("[#%d] %s - %d (%.02fM)" % (idx + 1, url, remote_len, remote_len / MB))

        short_name = get_name(audio, SHORT_ARTIST_LIM, SHORT_TITLE_LIM, '...')
        if local_len != remote_len:
            logging.error("[#%d/%d] \"%s\" (%s, %s bytes)" \
                % (idx + 1, amount, final_filename, name, remote_len - local_len))

            progress_bar = AudioDownloadProgressBar(idx, multithreading, short_name, name) \
                if logging.getLogger().getEffectiveLevel() < logging.ERROR else None
            download_file(vk_filename, url, local_len, remote_len, progress_bar)

        try:
            os.rename(vk_filename, final_filename)
        except OSError as e:
            raise RuntimeError("Can't rename: %s -> %s" % (vk_filename, final_filename))

    relpath = os.path.relpath(os.path.abspath(path), os.path.abspath(path_to_links_dir))
    path_to_new_file = get_filepath(relpath, basename)

    linkname = linkname_fmt % (idx + 1, basename)
    path_to_link = get_filepath(path, (idx + 1, basename), linkname_fmt)

    if not os.path.exists(path_to_link):
        try:
            os.symlink(path_to_new_file, path_to_link)
        except OSError as e:
            raise RuntimeError("Can't create symlink: %s -> %s" % (path_to_link, path_to_new_file))
        logging.error("[#%d] %s -> %s" % (idx + 1, linkname, path_to_new_file))
    return basename

def download_audio_list(thread_pool_sz, audio_list, path, links_dir, yes=False):
    amount = len(audio_list)

    linkname_fmt = os.path.join(links_dir, "%%0%dd=%%s" % int(1 + math.log10(amount)))
    path_to_links_dir = os.path.join(path, links_dir)

    vk_files = []

    if thread_pool_sz > 1:
        params_q = Queue.Queue()
        res_q = Queue.Queue()

        for i in range(thread_pool_sz):
            th = DownloaderThread(i + 1, download_audio, params_q, res_q)
            th.setDaemon(True)
            th.start()

        for i, audio in enumerate(audio_list):
            params_q.put((audio, i, amount, path, path_to_links_dir, linkname_fmt))

        params_q.join()

        while res_q.qsize():
            vk_files.append(res_q.get())
    else:
        for i, audio in enumerate(audio_list):
            res = download_audio(audio, i, amount, path, path_to_links_dir, linkname_fmt, multithreading=False)
            vk_files.append(res)

    logging.error("All Done.")

    for root, dirs, files in os.walk(path): break
    files = filter(lambda f: re.match('.*[.]mp3', f) is not None, files)
    files = map(get_unicode, files)

    old_files = filter(lambda f: f not in vk_files, files)

    logging.debug('Outdated audios:\n' + '\n'.join(old_files[:50]))
    if len(old_files) > 50:
        logging.debug('.' * 50 + ' and others.')

    if len(old_files):
        answer = 'y' if yes else raw_input("Would you like to delete outdated audios? [%d] (y or n) [n] " %  len(old_files))
        if re.match('[yY].*', answer):
            for f in old_files:
                logging.debug("Deleting %s ..." %  f)
                os.remove(os.path.join(path, f))
            logging.error("Deleted outdated files [%d]." % len(old_files))

    for root, dirs, links in os.walk(path_to_links_dir): break
    links = map(lambda lnk: os.path.join(root, lnk), links)
    broken_links = filter(lambda lnk: not os.path.exists(lnk) and os.path.lexists(lnk), links)

    if len(broken_links):
        logging.debug('Deleting broken links:\n' + '\n'.join(broken_links))
        for lnk in broken_links:
            os.unlink(lnk)
        logging.error("Deleted broken links.")

def get_audio_list(user_id, access_token):
    url = "https://api.vkontakte.ru/method/audio.get.xml?uid=" + str(user_id) + "&access_token=" + access_token
    doc  = html.document_fromstring(urllib2.urlopen(url).read())
    return doc.cssselect('audio')
