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

from lastpage.twitter import getTwitterOAuthURL

from twisted.python import log
from twisted.web import resource, server


class Login(resource.Resource):
    """
    Handles login requests that will redirect to an OAuth endpoint.

    @param oauthTokenDict: A C{dict} mapping OAuth keys to tokens.
    @param conf: A L{config.Config} instance holding configuration
        settings.
    """
    isLeaf = True

    def __init__(self, cookieDict, oauthTokenDict, conf):
        self.cookieDict = cookieDict
        self.oauthTokenDict = oauthTokenDict
        self.conf = conf

    def render_GET(self, request):
        """
        Handle a login GET request.

        @param request: A twisted.web HTTP C{Request}.
        """
        log.err('Login request received: %s' % request)
        d = getTwitterOAuthURL(self.conf, self.oauthTokenDict)
        d.addCallback(self._redirect, request)
        d.addErrback(log.err)
        return server.NOT_DONE_YET

    def _redirect(self, URL, request):
        """
        Redirect the user to the OAuth endpoint for authorization.

        @param URL: The C{str} URL to redirect this request to.
        @param request: A twisted.web HTTP C{Request}.
        """
        log.msg('Got OAuth URL: %r. Redirecting' % URL)
        request.redirect(URL)
        request.finish()
