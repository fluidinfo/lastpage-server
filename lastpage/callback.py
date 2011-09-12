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

import json
import uuid

from oauth.oauth import (
    OAuthToken, OAuthRequest, OAuthConsumer, OAuthSignatureMethod_HMAC_SHA1)

from twisted.python import log
from twisted.web import resource, client, server


class Callback(resource.Resource):
    """
    Handles a callback requests from Twitter's OAuth endpoint.

    @param cookieDict: A C{dict} mapping cookie values to Twitter usernames.
    @param oauthTokenDict: A C{dict} mapping OAuth keys to tokens.
    @param conf: A L{config.Config} instance holding configuration
        settings.
    """
    isLeaf = True

    def __init__(self, cookieDict, oauthTokenDict, conf):
        self._conf = conf
        self._cookieDict = cookieDict
        self._oauthTokenDict = oauthTokenDict

    def render_GET(self, request):
        """
        Handles a callback GET request.
        """
        log.err('Callback received: %s' % request)

        oauthToken = request.args['oauth_token']
        if oauthToken:
            oauthToken = oauthToken[0]
        else:
            log.err('Received callback with no oauth_token: %s' % request)
            raise Exception('Received callback with no oauth_token.')

        oauthVerifier = request.args['oauth_verifier']
        if oauthVerifier:
            oauthVerifier = oauthVerifier[0]
        else:
            log.err('Received callback with no oauth_verifier: %s' % request)
            raise Exception('Received callback with no oauth_verifier.')

        try:
            token = self._oauthTokenDict.pop(oauthToken)
        except KeyError:
            log.err('Received callback with unknown oauth_token: %s' %
                    oauthToken)
            raise Exception('Received callback with unknown oauth_token.')

        conf = self._conf
        consumer = OAuthConsumer(conf.consumer_key, conf.consumer_secret)
        oaRequest = OAuthRequest.from_consumer_and_token(
            consumer, token=token, verifier=oauthVerifier,
            http_url=conf.access_token_url)
        oaRequest.sign_request(
            OAuthSignatureMethod_HMAC_SHA1(), consumer, token)
        log.msg('Requesting access token.')
        d = client.getPage(oaRequest.to_url(), headers=oaRequest.to_header())
        d.addCallback(self._storeAccessToken, request)
        d.addErrback(log.err)
        return server.NOT_DONE_YET

    def _storeAccessToken(self, result, request):
        accessToken = OAuthToken.from_string(result)
        log.msg('Got access token: %s' % accessToken)
        conf = self._conf
        consumer = OAuthConsumer(conf.consumer_key, conf.consumer_secret)
        oaRequest = OAuthRequest.from_consumer_and_token(
            consumer, token=accessToken,
            http_url=conf.verify_credentials_url)
        oaRequest.sign_request(
            OAuthSignatureMethod_HMAC_SHA1(), consumer, accessToken)
        log.msg('Verifying credentials.')
        d = client.getPage(oaRequest.to_url())
        d.addCallback(self._storeUser, accessToken, request)
        d.addErrback(log.err)
        return d

    def _storeUser(self, result, accessToken, request):
        user = json.loads(result)
        key = str(uuid.uuid4())
        conf = self._conf
        self._cookieDict[key] = (user, accessToken)
        log.msg('Setting cookie %s' % key)
        request.addCookie(conf.cookie_name, key, path='/',
                          domain=conf.cookie_domain)
        request.redirect(conf.logged_in_redirect_url)
        log.msg('Redirecting to %s' % conf.logged_in_redirect_url)
        request.finish()
