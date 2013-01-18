import urllib2
import urllib
import cookielib
from urlparse import urlparse
from HTMLParser import HTMLParser, HTMLParseError
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
        if not self.inside:
            return
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


def __auth(email, password, scope, opener):
    oauth_url = "http://oauth.vk.com/oauth/authorize?" + \
        "redirect_uri=http://oauth.vk.com/blank.html&response_type=token&" + \
        "client_id=%s&scope=%s&display=page" % (APP_ID, ",".join(scope))
    try:
        login_page = opener.open(oauth_url)
    except urllib2.URLError:
        raise AuthenticationError("No response from: %s" % oauth_url)

    parser = FormParser()
    parser.feed(login_page.read())
    parser.close()
    if not parser.is_parsed or parser.url is None \
            or "pass" not in parser.params or "email" not in parser.params:
        raise HTMLParseError("Login form is not parsed well.")
    parser.params["email"] = email
    parser.params["pass"] = password

    try:
        res = opener.open(parser.url, urllib.urlencode(parser.params))
    except urllib2.URLError:
        raise AuthenticationError("Can't log into: %s" % parser.url)
    return res.read(), res.geturl()


def __get_access(url, opener):
    doc = opener.open(url).read()
    parser = FormParser()
    parser.feed(doc)
    parser.close()
    return opener.open(parser.url).geturl()


def auth(email, password, scope):
    if not isinstance(scope, list):
        scope = [scope]
    opener = urllib2.build_opener(
        urllib2.HTTPCookieProcessor(cookielib.CookieJar()),
        urllib2.HTTPRedirectHandler())
    doc, url = __auth(email, password, scope, opener)
    if urlparse(url).path != "/blank.html":
        try:
            url = __get_access(url, opener)
        except urllib2.URLError:
            raise AuthenticationError("Unavailable url to get access.")
    if urlparse(url).path != "/blank.html":
        raise AuthenticationError("Can't get access w/ this login/pass.")

    res = dict(p.split('=') for p in urlparse(url).fragment.split("&"))
    if "access_token" not in res or "user_id" not in res:
        raise RuntimeError("Bad response.")
    return res["access_token"], res["user_id"]


def console_auth(scope, email=None, passwd=None):
    while not email:
        email = raw_input("Phone or email: ")

    if passwd:
        access_token, uid = auth(email, passwd, scope)
    else:
        for retry in range(PASS_RETRY_COUNT):
            passwd = getpass.getpass()
            try:
                access_token, uid = auth(email, passwd, scope)
            except AuthenticationError as e:
                print e.message
            else:
                break
        else:
            raise AuthenticationError("Exceeded maximal retry count.")

    return access_token, uid
