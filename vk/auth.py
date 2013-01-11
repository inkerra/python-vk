import urllib2
import urllib
import cookielib
from urlparse import urlparse
from HTMLParser import HTMLParser
from HTMLParser import HTMLParseError
import getpass

PASS_RETRY_COUNT = 3
APP_ID = 2260052

class AuthenticationError(Exception):
    pass

class FormParser(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self.url = None
        self.params = dict()
        self.inside = False
        self.is_parsed = False

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag == "form":
            if self.is_parsed:
                raise HTMLParseError("Not a single <%s>." % tag)
            if self.inside:
                raise HTMLParseError("Nested <%s>." % tag)
            self.inside = True
        if not self.inside: return
        attrs = dict((name.lower(), value) for name, value in attrs)
        if tag == "form":
            self.url = attrs["action"]
        elif tag == "input" and "name" in attrs:
            self.params[attrs["name"]] = attrs.get("value", "")

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag == "form":
            if not self.inside:
                raise HTMLParseError("Unexpected </%s>" % tag)
            self.inside = False
            self.is_parsed = True

def __auth(email, password, client_id, scope, opener):
    resp = opener.open(
        "http://oauth.vk.com/oauth/authorize?" + \
        "redirect_uri=http://oauth.vk.com/blank.html&response_type=token&" + \
        "client_id=%s&scope=%s&display=wap" % (client_id, ",".join(scope))
        )
    parser = FormParser()
    parser.feed(resp.read())
    parser.close()
    if not parser.is_parsed or parser.url is None \
        or "pass" not in parser.params or "email" not in parser.params:
        raise HTMLParseError("Login form is not parsed well.")
    parser.params["email"] = email
    parser.params["pass"] = password

    res = opener.open(parser.url, urllib.urlencode(parser.params))
    return res.read(), res.geturl()

def __get_access(url, opener):
    doc = opener.open(url).read()
    parser = FormParser()
    parser.feed(doc)
    parser.close()
    return opener.open(parser.url).geturl()

def auth(email, password, client_id, scope):
    if not isinstance(scope, list): scope = [scope]
    opener = urllib2.build_opener(
        urllib2.HTTPCookieProcessor(cookielib.CookieJar()),
        urllib2.HTTPRedirectHandler())
    doc, url = __auth(email, password, client_id, scope, opener)
    if urlparse(url).path != "/blank.html":
        url = __get_access(url, opener)
    if urlparse(url).path != "/blank.html":
        raise AuthenticationError("Can't get access w/ this login/pass.")

    res = dict(p.split('=') for p in urlparse(url).fragment.split("&"))
    if "access_token" not in res or "user_id" not in res:
        raise RuntimeError("Bad response.")
    return res["access_token"], res["user_id"]

def console_auth(scope):
    email = raw_input("Email: ")
    for retry in range(PASS_RETRY_COUNT):
        pswd = getpass.getpass()
        try:
            access_token, uid = auth(email, pswd, APP_ID, scope)
        except AuthenticationError as e:
            print e.message
        else:
            break
    else:
        raise AuthenticationError("Exceeded maximal retry count.")
    return access_token, uid
