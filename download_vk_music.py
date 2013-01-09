#!/usr/bin/python
#-*- coding: utf-8 -*-

import os
import sys
import getpass
import getopt
import logging
from vk import auth, audio, utils
from vk.auth import AuthenticationError
from vk.utils import mkdir, clean_dir

def usage():
    print """Usage: %s [OPTIONS]
Options:
-v, --verbose    print all debug messages
-q, --quiet    no info messages (no progress bar)
-s, --silent    no messages at all
-j, --th_pool_sz=K    set K as max thread pool size (1 by default)
-u, --user_id=K    K is user's id, whose audios will be downloaded
-p, --path=D    D is a directory path to save audios
-l, --links_dir=D    D is a directory to save links to saved audios in directory with saved audios
-c, --clean_links    remove directory with old links before saving new links
-y, --yes    answer "yes" for all questions
-h, --help    display this help and exit""" % sys.argv[0]
    sys.exit(0)

PASS_RETRY_COUNT = 3

def main(argv):
    thread_pool_sz = 1
    path = ''
    alt_user_id = None
    links_dir = "links"
    clean_links = False
    yes = False

    options, remainder = getopt.gnu_getopt(argv, 'vqsj:u:p:l:cyh', \
        ['verbose', 'quiet', 'silent', 'th_pool_sz', 'user_id', 'path', 'links_dir', 'yes', 'help'])
    for opt, arg in options:
        if opt in ('-v', '--verbose'):
            logging.getLogger().setLevel(logging.DEBUG)
        elif opt in ('-q', '--quiet'):
            logging.getLogger().setLevel(logging.ERROR)
        elif opt in ('-s', '--silent'):
            logging.getLogger().setLevel(logging.CRITICAL)
        elif opt in ('-j', '--th_pool_sz'):
            thread_pool_sz = int(arg)
        elif opt in ('-u', '--user_id'):
            alt_user_id = arg
        elif opt in ('-p', '--path'):
            path = arg
        elif opt in ('-l', '--links_dir'):
            links_dir = arg
        elif opt in ('-c', '--clean_links'):
            clean_links = True
        elif opt in ('-y', '--yes'):
            yes = True
        elif opt in ('-h', '--help'):
            usage()

    path_to_links_dir = os.path.join(path, links_dir)

    mkdir(path)
    if clean_links:
        clean_dir(path_to_links_dir)
    else:
        mkdir(path_to_links_dir)

    email = raw_input("Email: ")
    for retry in range(PASS_RETRY_COUNT):
        password = getpass.getpass()
        try:
            access_token, user_id = auth.auth(email, password, "2260052", "audio")
        except AuthenticationError as e:
            print e.message
        else:
            break
    else:
        print("Exceeded maximal retry count.")
        sys.exit(1)

    if alt_user_id: user_id = alt_user_id

    audio_list = audio.get_audio_list(user_id, access_token)

    logging.debug("Audio list is downloaded.")

    assert len(audio_list) != 0, "got no audios."

    audio.download_audio_list(thread_pool_sz, audio_list[::-1], path, links_dir, yes)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='\n%(message)s')
    try:
        main(sys.argv[1:])
    except KeyboardInterrupt as e:
        logging.critical("\nInterrupted.")
