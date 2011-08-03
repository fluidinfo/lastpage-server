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

from twisted.internet import defer
from twisted.python import log
from twisted.web import resource, http, server
from twisted.web.resource import ErrorPage
from twisted.web.static import File

from txfluiddb.client import Object, Tag, Namespace
from txfluiddb.http import HTTPError

aboutTag = Tag(u'fluiddb', u'about')

# Content we serve statically, if static files are not being served by some
# other means (e.g., nginx).
_staticFiles = {
    '/favicon.ico': 'static/favicon.ico',
    '/robots.txt': 'static/robots.txt',
    '/static/style.css': 'static/style.css',
}


class LastPage(resource.Resource):
    """
    Top-level resource for the lastpage.me service.

    In production, requests for static files for lastpage.me should be
    served by some other process. This resource is best used to handle
    requests for the top-level site (/) and (via getChild) can produce
    resources for children (e.g., /username). If you do not set
    serveStaticFiles=True, it will 404 requests for things like
    /static/style.css or anything else (these requests may come from
    templates we return). It is suggested you use nginx or some other web
    server to deliver those resources (including requests for
    /favicon.ico).

    @param endpoint: the Fluidinfo API endpoint to use.
    @param env: The Jinja2 C{Environment} to use for rendering.
    @param serveStaticFiles: if C{True} handle requests for known
        static files.
    """
    allowedMethods = ('GET',)

    def __init__(self, endpoint, env, serveStaticFiles):
        resource.Resource.__init__(self)
        self._endpoint = endpoint
        self._env = env
        self._serveStaticFiles = serveStaticFiles

    def getChild(self, what, request):
        """
        Find and return a child resource.

        @param what: The thing (either a user name or an html page) wanted.
        @param request: The HTTP request.
        """
        # Serve static files.
        if self._serveStaticFiles:
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
        return LastPageOf(self._endpoint, self._env, who, tag)

    def render_GET(self, request):
        """
        Handle a GET request. This is a request for a top-level HTML page
        like http://lastpage.me/tools.html

        @param request: The HTTP request.
        """
        return str(self._template.render())


class LastPageOf(resource.Resource):
    """
    A resource for a specific user of lastpage.me. This resource is used to
    handle requests for http://lastpage.me/username.

    @param endpoint: the Fluidinfo API endpoint to use.
    @param env: The Jinja2 C{Environment} to use for rendering.
    @param who: A C{unicode} username to redirect to, if possible.
    @param tag: The C{unicode} path name of the tag to query for.
    """
    allowedMethods = ('GET',)
    isLeaf = True

    def __init__(self, endpoint, env, who, tag):
        resource.Resource.__init__(self)
        self._endpoint = endpoint
        self._env = env
        self._who = who
        self._tag = tag

    def render_GET(self, request):
        """
        Handle a GET request.

        @param request: The HTTP request.
        """
        query = u'has %s' % self._tag
        # log.msg('Sending %r query to %r.' % (query, self._endpoint.baseURL))
        d = Object.query(self._endpoint, query)
        d.addCallback(self._finishHas, request)
        d.addErrback(self._hasErr, request)
        d.addErrback(log.err)
        return server.NOT_DONE_YET

    def _hasErr(self, fail, request):
        """
        Handle an error in the get on the user's tag.

        @param fail: the Twisted failure.
        @param request: the original HTTP request.
        """
        fail.trap(HTTPError)
        errorClass = fail.value.response_headers.get('x-fluiddb-error-class')
        if errorClass:
            if errorClass[0] == 'TNonexistentTag':
                d = Namespace(self._who).exists(self._endpoint)
                d.addCallback(self._testUserExists, request)
                d.addErrback(self._oops, request)
                d.addErrback(log.err)
                return d
            else:
                log.msg('Fluidinfo error class %s.' % errorClass[0])
                log.err(fail)
                request.setResponseCode(http.NOT_FOUND)
                template = self._env.get_template('404.html')
                request.write(str(template.render()))
        else:
            request.write('Sorry! No Fluidinfo error class. %s' % fail)
        request.finish()

    def _finishHas(self, results, request):
        """
        Handle the result of the 'has username/lastpage' /objects query.

        @param results: the result of the query.
        @param request: the original HTTP request.
        """
        nResults = len(results)
        if nResults == 0:
            # This user doesn't have a lastpage tag on any page.
            template = self._env.get_template('no-pages-tagged.html')
            request.write(str(template.render(user=self._who,
                                              tag=self._tag)))
            request.setResponseCode(http.OK)
            request.finish()
        elif nResults == 1:
            # Normal case. There is a lastpage tag on one object, and we
            # can do the redirect. Because txFluidDB doesn't support
            # /values yet though, we need to send another request to
            # Fluidinfo (to get the fluiddb/about value of the object,
            # which will be the URL).
            obj = Object(results[0].uuid)
            d = obj.get(self._endpoint, aboutTag)
            d.addCallback(self._finishSingle, request)
            d.addErrback(self._hasErr, request)
            return d
        else:
            # There are lastpage tags on multiple objects. Get the
            # fluiddb/about for all of them.
            log.msg('got %d results' % nResults)
            deferreds = []
            for result in results:
                obj = Object(result.uuid)
                d = obj.get(self._endpoint, aboutTag)
                deferreds.append(d)
            d = defer.DeferredList(deferreds, consumeErrors=True)
            d.addCallback(self._finishMany, request)
            return d

    def _finishSingle(self, result, request):
        """
        Handle the result of a GET to fetch the user's tag from a single
        object.

        @param result: the result of the GET.
        @param request: the original HTTP request.
        """
        try:
            url = str(result)
        except:
            raise
        log.msg('Redirect: %s -> %s' % (self._who.encode('utf-8'), url))
        request.setResponseCode(http.TEMPORARY_REDIRECT)
        request.redirect(url)
        request.finish()

    def _finishMany(self, results, request):
        """
        Handle the result of a GET to fetch what are hopefully URLs
        (fluiddb/about values) of the many objects that have a
        username/lastpage on them.

        @param results: a list of (succeeded, result) 2-tuples from
            a C{DeferredList} firing. These are the results of the GET
            requests to fetch the fluiddb/about tags on the objects that
            have a username/lastpage tag on them.
        @param request: the original HTTP request.
        """
        templateURLs = []
        for (succeeded, result) in results:
            if succeeded:
                low = result.lower()
                if low.startswith('http://') or low.startswith('https://'):
                    result = '<a href="%s">%s</a>' % (result, result)
                templateURLs.append(result)
            else:
                log.msg('Failure getting %r/lastpage tag:' % self._who)
                log.err(result)
        if templateURLs:
            request.setResponseCode(http.OK)
            template = self._env.get_template('multiple-pages-tagged.html')
            request.write(str(template.render(user=self._who,
                                              tag=self._tag,
                                              pages=templateURLs)))
            request.setResponseCode(http.OK)
            request.finish()
        else:
            # We only got errors back...
            request.write('Oops, sorry, all we got were errs!')
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
        request.write(str(template.render(user=self._who)))
        request.setResponseCode(http.OK)
        request.finish()

    def _oops(self, fail, request):
        """
        Produce an internal server error page to indicate that we had a
        severed problem.

        @param fail: the Twisted failure.
        @param request: the original HTTP request.
        """
        log.err(fail)
        request.setResponseCode(http.INTERNAL_SERVER_ERROR)
        template = self._env.get_template('500.html')
        request.write(str(template.render()))
        request.finish()
