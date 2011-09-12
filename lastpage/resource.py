# Copyright 2011 Fluidinfo Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you
# may not use this file except in compliance with the License.  You
# may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.  See the License for the specific language governing
# permissions and limitations under the License.

from jinja2.exceptions import TemplateNotFound

from random import randrange

from twisted.python import log
from twisted.web import resource, http, server
from twisted.web.resource import ErrorPage
from twisted.web.static import File

from txfluiddb.client import Endpoint, Namespace, Values
from txfluiddb.http import HTTPError

from lastpage.callback import Callback
from lastpage.login import Login
from lastpage.logout import Logout

# Content we serve statically, if static files are not being served by some
# other means (e.g., nginx).
_staticFiles = {
    '/static/favicon.ico': 'static/favicon.ico',
    '/robots.txt': 'static/robots.txt',
    '/static/bullet.png': 'static/bullet.png',
    '/static/icon.png': 'static/icon.png',
    '/static/login.png': 'static/login.png',
    '/static/logo.png': 'static/logo.png',
    '/static/style.css': 'static/style.css',
}


def _requestId():
    """
    Make a (fairly) unique request id for matching up error pages with
    errors in our logs.

    @return: a random C{str} identifier.
    """
    return ''.join([chr(ord('a') + randrange(0, 26)) for i in range(16)])


class LastPage(resource.Resource):
    """
    Top-level resource for the lastpage.me service.

    @param conf: A L{config.Config} instance holding configuration
        settings.
    @param env: The Jinja2 C{Environment} to use for rendering.
    @param cookieDict: a C{dict} that maps cookies to OAuth token keys.
    @param oauthTokenDict: a C{dict} that maps OAuth token keys to tokens.
    """
    allowedMethods = ('GET',)

    def __init__(self, conf, env, cookieDict, oauthTokenDict):
        resource.Resource.__init__(self)
        self._conf = conf
        self._env = env
        self._cookieDict = cookieDict
        self._oauthTokenDict = oauthTokenDict

    def getChild(self, what, request):
        """
        Find and return a child resource.

        @param what: The thing (either a user name or an html page) wanted.
        @param request: The HTTP request.
        """
        # Serve static files.
        if self._conf.serve_static_files:
            path = request.path
            if path in _staticFiles:
                filename = _staticFiles[path]
                log.msg('Serving static path %s -> %s.' % (path, filename))
                request.setResponseCode(http.OK)
                fileResource = File(filename)
                fileResource.isLeaf = True
                return fileResource

        # Serve .html requests.
        if what == '' or what.endswith('.html'):
            try:
                template = self._env.get_template(what or 'index.html')
            except TemplateNotFound:
                # There could in theory be a user whose name ends in .html,
                # so we'll just let this go through.
                pass
            else:
                self._template = template
                return self

        if what == '_login_':
            return Login(self._cookieDict, self._oauthTokenDict, self._conf)
        if what == '_logout_':
            return Logout(self._cookieDict, self._conf)
        if what == '_callback_':
            return Callback(self._cookieDict, self._oauthTokenDict, self._conf)

        log.msg('Request for path %s assumed to be a user URL lookup.' %
                request.path)

        # Serve normal user redirects.
        try:
            # Decode the path components into unicode.
            who = what.decode('utf-8')
            rest = u'-'.join([x.decode('utf-8') for x in request.postpath])
        except UnicodeDecodeError:
            return ErrorPage(http.BAD_REQUEST, 'Bad URI UTF-8', 'Bad UTF-8')

        if rest:
            tag = u'%s/lastpage-%s' % (who, rest)
        else:
            tag = u'%s/lastpage' % who
        return LastPageOf(self._conf, self._env, who, tag)

    def render_GET(self, request):
        """
        Handle a GET request. This is a request for a top-level HTML page
        like http://lastpage.me/tools.html

        @param request: The HTTP request.
        """
        cookie = request.getCookie(self._conf.cookie_name)
        print 'got cookie %r' % (cookie,)
        try:
            data = self._cookieDict[cookie]
        except:
            print 'missed on looking up cookie'
            username = None
        else:
            print 'found cookie'
            username = data[0]['screen_name']
            # token = data[1]
        return str(self._template.render(user=username))


class LastPageOf(resource.Resource):
    """
    A resource for a specific user of lastpage.me. This resource is used to
    handle requests for http://lastpage.me/username.

    @param conf: A L{config.Config} instance holding configuration
        settings.
    @param env: The Jinja2 C{Environment} to use for rendering.
    @param who: A C{unicode} username to redirect to, if possible.
    @param tag: The C{unicode} path name of the tag to query for.
    """
    allowedMethods = ('GET',)
    isLeaf = True

    def __init__(self, conf, env, who, tag):
        resource.Resource.__init__(self)
        self._endpoint = Endpoint(baseURL=conf.fluidinfo_endpoint)
        self._env = env
        self._who = who
        self._tag = tag

    def render_GET(self, request):
        """
        Handle a GET request.

        @param request: The HTTP request.
        @return: the twisted.web constant C{server.NOT_DONE_YET} to indicate
            that the request processing is still underway.
        """
        query = u'has %s' % self._tag
        d = Values().get(self._endpoint, query, tags=[u'fluiddb/about'])
        d.addCallback(self._finishHas, request)
        d.addErrback(self._hasErr, request)
        d.addErrback(log.err)
        return server.NOT_DONE_YET

    def _hasErr(self, fail, request):
        """
        Handle an error in the GET on the user's tag.

        @param fail: the Twisted failure.
        @param request: the original HTTP request.
        """
        fail.trap(HTTPError)
        errorClass = fail.value.response_headers.get('x-fluiddb-error-class')
        if errorClass:
            if errorClass[0] == 'TNonexistentTag':
                # A non-existent tag could be due to the user not existing
                # or the tag not existing. Find out which so we can be as
                # helpful as possible in the error message.
                d = Namespace(self._who).exists(self._endpoint)
                d.addCallback(self._testUserExists, request)
                d.addErrback(self._oops, request)
                d.addErrback(log.err)
                return d
            error = 'Fluidinfo error class %s.' % errorClass[0]
        else:
            error = ('No x-fluiddb-error-class in response headers! %r' %
                     fail.value.response_headers)

        _id = _requestId()
        log.msg('Error: request %s: %s' % (_id, error))
        log.err(fail)
        template = self._env.get_template('500.html')
        request.write(str(template.render(id=_id)))
        request.finish()

    def _finishHas(self, result, request):
        """
        Handle the result of the 'has username/lastpage' /values query. We
        just figure out how many objects are tagged and route the results
        (if any) and the request to a more specific method.

        @param result: the result of the query.
        @param request: the original HTTP request.
        """
        results = result['results']['id']
        nResults = len(results)
        if nResults == 0:
            self._noObjectsTagged(request)
        elif nResults == 1:
            self._oneObjectTagged(results, request)
        else:
            self._multipleObjectsTagged(results, request)

    def _noObjectsTagged(self, request):
        """
        The user's tag is not on any object, so we cannot redirect them.
        Instead, show an informative page to let them know what's up.

        @param request: the original HTTP request.
        """
        template = self._env.get_template('no-pages-tagged.html')
        request.write(str(template.render(user=self._who, tag=self._tag)))
        request.setResponseCode(http.OK)
        request.finish()

    def _oneObjectTagged(self, results, request):
        """
        The user's tag is only on one object, so we can redirect them,
        assuming the tag value looks like a URL.

        @param results: The C{dict} result from the /values call to
            get the fluiddb/about value of the user's tagged object.
        @param request: the original HTTP request.
        """
        url = results.values()[0]['fluiddb/about']['value']
        try:
            url = str(url)
        except UnicodeEncodeError:
            log.msg('Could not convert url %r to str.' % (url,))
            # Display the offending URL in an ASCII representation of
            # the unicode value.
            url = '%r' % (url,)
            request.setResponseCode(http.OK)
            template = self._env.get_template('tag-not-a-url.html')
            request.write(str(template.render(
                user=self._who, tag=self._tag, about=url)))
        else:
            if url.startswith('http'):
                log.msg('Redirect: %s -> %s' % (
                    self._tag.encode('utf-8'), url))
                request.setResponseCode(http.TEMPORARY_REDIRECT)
                request.redirect(url)
            else:
                request.setResponseCode(http.OK)
                template = self._env.get_template('tag-not-a-url.html')
                request.write(str(template.render(
                    user=self._who, tag=self._tag, about=url)))
        request.finish()

    def _multipleObjectsTagged(self, results, request):
        """
        The user's tag is on multiple objects, so we cannot redirect them,
        to just one URL. Instead we display the fluiddb/about values of the
        objects that are tagged.

        @param results: The C{dict} result from the /values call to
            get the fluiddb/about value of the user's tagged object.
        @param request: the original HTTP request.
        """
        pages = []
        for obj in results.values():
            url = obj['fluiddb/about']['value']
            try:
                url = str(url)
            except UnicodeEncodeError:
                log.msg('Tag URL %r could not be converted to str' % url)
                # Convert it to a string of some form, even though it's
                # not going to be a valid URL.  We could UTF-8 and
                # %-encode here but I'm not sure it's worth the
                # trouble. So for now let's just display the Unicode.
                url = '%r' % (url,)
            else:
                if url.startswith('http'):
                    url = '<a href="%s">%s</a>' % (url, url)
            pages.append(url)
        request.setResponseCode(http.OK)
        template = self._env.get_template('multiple-pages-tagged.html')
        request.write(str(template.render(
            user=self._who, tag=self._tag, pages=pages)))
        request.setResponseCode(http.OK)
        request.finish()

    def _testUserExists(self, exists, request):
        """
        Produce an informative page to indicate that we can't help because
        either the user doesn't exist or the tag isn't present.

        @param exists: C{True} if the user exists, else C{False}.
        @param request: the original HTTP request.
        """
        if exists:
            template = self._env.get_template('no-pages-tagged.html')
        else:
            template = self._env.get_template('no-user.html')
        request.write(str(template.render(user=self._who, tag=self._tag)))
        request.setResponseCode(http.OK)
        request.finish()

    def _oops(self, fail, request):
        """
        Produce an internal server error page to indicate that we had a
        severed problem.

        @param fail: the Twisted failure.
        @param request: the original HTTP request.
        """
        _id = _requestId()
        log.msg('Error: returning a 500 error. Request id = %s' % _id)
        log.err(fail)
        request.setResponseCode(http.INTERNAL_SERVER_ERROR)
        template = self._env.get_template('500.html')
        request.write(str(template.render(id=_id)))
        request.finish()
