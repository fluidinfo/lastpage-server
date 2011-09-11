import json
import os

from twisted.python import log
from twisted.web import resource, http
from twisted.web.resource import ErrorPage

_fakeRequestToken = 'eJwBWACn_6fOaAg6Qzlj8tR3KQQxum4nl'
_fakeAccessToken = 'tyjEyHIl667oYbFBAoD8s5dyGPRHaTOxj'


class LocalOAuth(resource.Resource):
    """A local OAuth server.

    @param conf: A L{lastpage.config.Config} object with configuration details.
    """

    allowedMethods = ('GET',)

    def __init__(self, conf):
        resource.Resource.__init__(self)
        self.conf = conf

    def getChild(self, what, request):
        """
        Find and return a child resource.

        @param what: The name of the resource requested.
        @param request: The HTTP request.
        @return: A instance of C{twisted.web.resource.Resource}.
        """
        if what == 'request-token':
            return RequestToken()
        elif what == 'authorization':
            return Authorization(self.conf)
        elif what == 'authorization-fail':
            return AuthorizationFail()
        elif what == 'access-token':
            return AccessToken()
        elif what == 'verify-credentials':
            return VerifyCredentials()
        else:
            return ErrorPage(http.NOT_FOUND,
                             '%r is unknown.' % what,
                             '%r is unknown.' % what)


class RequestToken(resource.Resource):
    """Provide a temporary access token.

    A resource that knows how to supply a request token. The request token
    is what a consumer will exchange for an access token once the user has
    authorized the application with the service provider.
    """
    def render(self, request):
        """Supply the OAuth token and token secret.

        @param request: The HTTP request.
        @return: A C{str} in URI argument format with the OAuth token details.
        """
        request.setResponseCode(http.OK)
        request.setHeader('content-type', 'text/plain')
        return ('oauth_token=%s&oauth_token_secret=fake-secret' %
                _fakeRequestToken)


class Authorization(resource.Resource):
    """Ask a user to authorize a consumer.

    A resource that knows how to prompt for authorization and to send an
    accepting user to the callback URL on the consumer, with an oauth_token
    argument containing the request token that we gave the consumer on the
    earlier /request-token request.
    """

    def __init__(self, conf):
        resource.Resource.__init__(self)
        self.conf = conf

    def render(self, request):
        """Ask the user to authorize the consumer.

        @param request: The HTTP request.
        @return: A C{str} of HTML with the authorization request.
        """
        request.setResponseCode(http.OK)
        request.setHeader('content-type', 'text/html')
        return """
<html>
<head>
<title>lastpage.me</title>
<head>
<body>
<p>
authorize???
<a href=%s?oauth_token=%s&oauth_verifier=fake-verifier>yes</a>
</p>
</body>
</html>""" % (self.conf.callback_url, _fakeRequestToken)


class AuthorizationFail(resource.Resource):
    """OAuth authorization failure."""

    def render(self, request):
        """Reassure the user that authorization was not granted.

        @param request: The HTTP request.
        @return: A C{str} of HTML showing the authorization was denied.
        """
        request.setResponseCode(http.OK)
        request.setHeader('content-type', 'text/html')
        return """
<html>
<head>
<title>lastpage.me</title>
<head>
<body>
<p>
ok, I did not authorize lastpage.me to access your account.
</p>
</body>
</html>
        """


class AccessToken(resource.Resource):
    """Provide access tokens to consumers.

    A resource that knows how to supply an access token. The access token
    is what a consumer will use to make API calls to the service provider.
    """
    def render(self, request):
        """Provide an access token.

        @param request: The HTTP request.
        @return: A C{str} containing details of the OAuth access token.
        """
        request.setResponseCode(http.OK)
        request.setHeader('content-type', 'text/plain')
        return ('oauth_token=%s&oauth_token_secret=fake-token-secret' %
                _fakeAccessToken)


class VerifyCredentials(resource.Resource):
    """Verify user credentials at the service provider.

    A resource that knows how to verify credentials to provide details of
    the user on the service provider.
    """
    def render(self, request):
        """Deliver user details, just as Twitter would (though much reduced).

        Note that we'll probably need to add an 'id' key here at some point.

        @param request: The HTTP request.
        @return: A JSON encoded C{dict} with a (Twitter) screen_name key
            and a username value.
        """
        username = os.environ.get('USER', 'yourname')
        log.msg('Verify credentials called. Returning username %r.' % username)
        request.setResponseCode(http.OK)
        request.setHeader('content-type', 'text/plain')
        result = {'screen_name': username}
        return json.dumps(result)
