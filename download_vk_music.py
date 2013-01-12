#!/usr/bin/python
#-*- coding: utf-8 -*-

import os
import sys
import logging
from vk import auth, audio, utils
from vk.utils import mkdir, clean_dir

import argparse

def options():
    parser = argparse.ArgumentParser(description='Options:')
    parser.add_argument('-v', '--verbose', action='store_true',
        help='print all debug messages')
    parser.add_argument('-q', '--quiet', action='store_true',
        help='no info messages (no progress bar)')
    parser.add_argument('-s', '--silent', action='store_true',
        help='no messages')
    parser.add_argument('-l', '--login', metavar='LOGIN',
        help='login (phone or email)')
    parser.add_argument('-p', '--passwd', metavar='PASSWD',
        help='password')
    parser.add_argument('-r', '--reverse', action='store_true',
        help='download new audios first')
    parser.add_argument('-j', '--th_pool_sz', metavar='N', type=int,
        default=0, choices=range(2, 8), help='max thread pool size')
    parser.add_argument('-u', '--user_id', metavar='UID', type=int,
        help="user's id, whose audios will be downloaded")
    parser.add_argument('-d', '--dir', metavar='DIR', default='.',
        help='directory path to save audios')
    parser.add_argument('--links_dir', metavar='DIR', default='playlist',
        help="directory name to save playlist's links")
    parser.add_argument('-f', '--force', choices='yn',
        help='force answer to questions')

    return vars(parser.parse_args()).items()

def main():
    for opt, arg in options():
        if opt == 'verbose':
            if arg: logging.getLogger().setLevel(logging.DEBUG)
        elif opt == 'quiet':
            if arg: logging.getLogger().setLevel(logging.WARNING)
        elif opt == 'silent':
            if arg: logging.getLogger().setLevel(logging.CRITICAL)
        elif opt == 'login':
	     login = arg
        elif opt == 'passwd':
	     passwd = arg
        elif opt == 'th_pool_sz':
            th_pool_sz = arg
        elif opt == 'user_id':
            user_id = arg
        elif opt == 'dir':
            dir = arg
        elif opt == 'links_dir':
            links_dir = arg
        elif opt == 'reverse':
            reverse = arg
        elif opt == 'force':
            ans = arg

    access_token, uid = auth.console_auth("audio", login, passwd)

    if user_id: uid = user_id

    audio_list = audio.get_audio_list(uid, access_token)
    if not reverse:
        audio_list.reverse()

    if audio_list:
        logging.debug("Audio list is downloaded.")
    else:
        logging.warning("got no audios.")
        return

    mkdir(dir)
    clean_dir(os.path.join(dir, links_dir))

    audio.download_audio_list(th_pool_sz, audio_list, dir, links_dir, ans)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='\n%(message)s')
    try:
        main()
    except KeyboardInterrupt as e:
        logging.critical("Interrupted.")
    except auth.AuthenticationError as e:
        logging.critical(e)
        sys.exit(1)
