from lastpage import config
from lastpage.local import oauth

from twisted.python import usage
from twisted.plugin import IPlugin
from twisted.application import service, internet
from twisted.web import server
from twisted.internet import protocol

from zope.interface import implements


class Options(usage.Options):
    """
    Command line options for the loveme.do service.
    """
    optParameters = [['conf', None, None, 'The configuration file to read.']]

    def postOptions(self):
        """
        Make sure we got a configuration file.
        """
        if not self['conf']:
            raise RuntimeError('You must use --conf config-file')


class ServiceMaker(object):
    """
    The loveme.do service.
    """
    implements(service.IServiceMaker, IPlugin)
    tapname = 'local-oauth'
    description = 'Fluidinfo lastpage.me local OAuth service.'
    options = Options

    def makeService(self, options):
        """
        Create a local Twisted OAuth service for lastpage.me

        @param options: A C{twisted.python.usage.Options} instance
            containing command line options, as above.

        @return: a Twisted C{service.MultiService} instance.
        """
        conf = config.Config(options['conf'])
        if not conf.noisy_logging:
            protocol.Factory.noisy = False
        oauthService = service.MultiService()
        root = oauth.LocalOAuth(conf)
        factory = server.Site(root)
        _server = internet.TCPServer(conf.local_oauth_port, factory,
                                     interface='localhost')
        _server.setServiceParent(oauthService)
        return oauthService

serviceMaker = ServiceMaker()
