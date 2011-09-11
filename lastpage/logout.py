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

from twisted.web import resource


class Logout(resource.Resource):
    """
    Log the user out.

    @param cookieDict: A C{dict} mapping cookie values to Twitter usernames.
    """
    allowedMethods = ('GET',)

    def __init__(self, cookieDict, conf):
        resource.Resource.__init__(self)
        self._cookieDict = cookieDict
        self._conf = conf

    def render_GET(self, request):
        """
        Forget about the user's cookie and redirect them to our home page.

        @param request: The HTTP request.
        """
        try:
            del self._cookieDict[request.getCookie(self._conf.cookie_name)]
        except KeyError:
            pass
        request.redirect('/')
        return ''
