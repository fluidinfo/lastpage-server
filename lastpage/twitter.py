from oauth.oauth import (
    OAuthToken, OAuthRequest, OAuthConsumer, OAuthSignatureMethod_HMAC_SHA1)

from twisted.python import log
from twisted.web import client

from txretry.retry import RetryingCall

# API URLs
TWITTER_API_URL = 'http://api.twitter.com/1'
VERIFY_CREDENTIALS_URL = TWITTER_API_URL + '/account/verify_credentials.json'


def getTwitterOAuthURL(conf, oauthTokenDict):
    """
    Obtain a URL from twitter.com that we can redirect a user to so they
    can authenticate themselves and authorize loveme.do to act on their
    behalf.

    @param conf: the lovemedo configuration.
    @param oauthTokenDict: A C{dict} mapping token keys to tokens.
    @return: A C{Deferred} that fires with the URL for OAuth verification.
    """
    log.msg('Got login URL request.')

    def _makeURL(result):
        token = OAuthToken.from_string(result)
        # Store the token by key so we can find it when (if) the callback
        # comes.
        oauthTokenDict[token.key] = token
        request = OAuthRequest.from_token_and_callback(
            token=token, http_url=conf.authorization_url)
        url = request.to_url()
        log.msg('Browser OAuth redirect URL = %r' % url)
        return url

    consumer = OAuthConsumer(conf.consumer_key, conf.consumer_secret)
    request = OAuthRequest.from_consumer_and_token(
        consumer, callback=conf.callback_url,
        http_url=conf.request_token_url)
    request.sign_request(OAuthSignatureMethod_HMAC_SHA1(), consumer, None)
    r = RetryingCall(
        client.getPage, conf.request_token_url, headers=request.to_header())
    d = r.start()
    d.addCallback(_makeURL)
    d.addErrback(log.err)
    return d
