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
from glob import glob
from contextlib import closing

MAX_ARTIST_LEN = 40
MAX_TITLE_LEN = 60

SHORT_ARTIST_LIM = 18
SHORT_TITLE_LIM = 31

MAX_ID_NAME_LIM = 13

FILENAME_FMT = "%s.mp3"

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
            progress = ("\r#%0" + self.w + "d/%d %-55s %-5.02fMB %3d%%") \
                % (
                    self.idx + 1,
                    self.total,
                    self.name,
                    written_len / MB,
                    100.0 * written_len / remote_sz
                )

        sys.stdout.write(progress)
        sys.stdout.flush()

def download_audio((i, audio), total, path, lnks_path, m_th=True):
    filepath = norm_path(path, audio.name)

    if os.path.exists(filepath):
        logging.debug("[%d/%d] \"%s\" has been downloaded.",
            i + 1, total, filepath)
    else:
        tmp_name = norm_path(path, audio.id_name)


        sz = local_file_size(tmp_name)
        try:
            remote_sz = remote_file_size(audio.url)
        except urllib2.URLError as e:
            logging.critical("Skipping file: %s.\n" \
                + "Can't get access to %s: %s", audio.name, audio.url, e)
            return

        logging.debug("[#%d] %s - %d (%.02fM)",
            i + 1, audio.url, remote_sz, remote_sz / MB)

        if sz != remote_sz:
            if logging.getLogger().isEnabledFor(logging.INFO):
                progress_bar = \
                    AudioDownloadProgressBar(i, total, m_th, audio.short_name)
            else:
                progress_bar = None

            logging.log(logging.WARNING if m_th or not progress_bar \
                else logging.DEBUG,
                "[#%d/%d] \"%s\" (%s, %s bytes)",
                i + 1, total, filepath, audio.id_name, remote_sz - sz)

            download_file(tmp_name, audio.url, progress_bar)

        try:
            os.rename(tmp_name, filepath)
        except OSError as e:
            print tmp_name, " AND ", filepath
            print type(tmp_name), " AND ", type(filepath)
            raise RuntimeError("Can't rename: %s -> %s" \
                % (tmp_name, filepath))

    relpath = os.path.relpath(os.path.abspath(path), os.path.abspath(lnks_path))
    new_path = norm_path(relpath, audio.name)

    lnk_fmt = "%%0%dd=%%s" % len(str(total))
    lnk = lnk_fmt % (i + 1, audio.name)

    if sys.platform.startswith('win'):
        lnk = ''.join(lnk.rpartition('.')[:-1] + ('lnk',))

    lnk_path = norm_path(lnks_path, lnk)

    try:
        symlink(new_path, lnk_path)
    except Exception as e:
        raise RuntimeError("Can't create link: %s -> %s" \
            % (lnk_path, new_path))
    logging.debug("[#%d] %s -> %s", i + 1, lnk_path, new_path)

def audio_elem(audio, elem):
    t = audio.find(elem).text
    return valid_filename(t) if t else u''

def get_id_name(audio):
    return basename(audio.find("url").text)

def artist_title(audio, a_lim=MAX_ARTIST_LEN, t_lim=MAX_TITLE_LEN, tail=''):
    artist = (audio_elem(audio, 'artist'), a_lim)
    title = (audio_elem(audio, 'title'), t_lim)

    def cut((name, lim), (o_name, o_lim), tail):
        lim += o_lim - len(o_name) if o_lim > len(o_name) else 0
        return name[:(lim - len(tail))] + tail if len(name) > lim else name

    return "%s__%s" % (cut(artist, title, tail), cut(title, artist, tail))

class Audio(object):
    def __init__(self, audio, vk_name, id_name, dbl=0):
        self.audio = audio
        self.vk_name = vk_name
        self.id_name = id_name
        self.dbl = dbl

    def __call__(self):
        self.url = self.audio.find("url").text
        sh_title_lim = SHORT_TITLE_LIM - (MAX_ID_NAME_LIM if self.dbl else 0)
        short = artist_title(self.audio, SHORT_ARTIST_LIM, sh_title_lim, '..')
        if self.dbl:
            self.name = '-'.join([self.vk_name, self.id_name])
            self.short_name = '-'.join([short, self.id_name])
        else:
            self.name = FILENAME_FMT % self.vk_name
            self.short_name = FILENAME_FMT % short

def download_audio_list(th_pool_sz, audio_list, path, lnks_path, ans=None):
    vk_names = {}
    unique = set()
    audios = []

    for audio, vk_name in zip(audio_list, map(artist_title, audio_list)):
        vk_names.setdefault(vk_name, 0)
        iname = get_id_name(audio)
        if not vk_names[vk_name] or iname not in unique:
            audios.append(Audio(audio, vk_name, iname, dbl=vk_names[vk_name]))
            vk_names[vk_name] += 1
        unique.add(iname)

    for audio in audios:
        if vk_names[audio.vk_name] > 1:
            audio.dbl += 1
        audio()

    e_audios = enumerate(audios)

    params = (len(audios), path, lnks_path)

    if th_pool_sz > 1:
        params_q = Queue.Queue()

        for i in range(th_pool_sz):
            th = DownloaderThread(i + 1, download_audio, params_q)
            th.setDaemon(True)
            th.start()

        for p in e_audios:
            params_q.put(((p, ) + params))

        params_q.join()
    else:
        for p in e_audios:
            download_audio(p, *params, m_th=False)

    logging.warning("All Done.")

    y_or_n = lambda ans: ans.strip()[:1].lower() if ans else ''

    if y_or_n(ans) == 'n':
        return

    files = glob(os.path.join(path, FILENAME_FMT % '*'))
    playlist = {audio.name for audio in audios}
    old = [f for f in files if basename(f) not in playlist]

    if old:
        logging.info('Outdated audios:\n' + '\n'.join(old))
        if not ans:
            prompt = "Delete outdated audios?[%d] (y or n) [n] " %  len(old)
            ans = raw_input(prompt)
        if y_or_n(ans) == 'y':
            for f in old:
                logging.debug("Deleting %s ...", f)
                os.remove(f)
            logging.warning("Deleted outdated files [%d].", len(old))

def get_audio_list(user_id, access_token):
    url = "https://api.vkontakte.ru/method/audio.get.xml?" \
            + "uid=%s&access_token=%s" % (user_id, access_token)
    with closing(urllib2.urlopen(url)) as handle:
        doc  = html.document_fromstring(handle.read())
        return doc.cssselect('audio')
