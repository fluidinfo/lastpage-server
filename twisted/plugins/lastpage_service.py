from jinja2 import Environment, PackageLoader

from lastpage import config
from lastpage.options import FluidinfoEndpointOptions
from lastpage import resource

from twisted.plugin import IPlugin
from twisted.application import service, internet
from twisted.web import server
from twisted.internet import protocol

from zope.interface import implements


class Options(FluidinfoEndpointOptions):
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
    The lastpage.me service.
    """
    implements(service.IServiceMaker, IPlugin)
    tapname = 'lastpage'
    description = 'Fluidinfo lastpage.me service.'
    options = Options

    def makeService(self, options):
        """
        Create a Twisted service for lastpage.me

        @param options: A C{twisted.python.usage.Options} instance
            containing command line options, as above.

        @return: a Twisted C{service.MultiService} instance.
        """
        conf = config.Config(options['conf'])
        if not conf.noisy_logging:
            protocol.Factory.noisy = False
        env = Environment(loader=PackageLoader('lastpage', 'templates'))
        lastpageService = service.MultiService()
        cookieDict = {}  # This should be persisted.
        oauthTokenDict = {}
        root = resource.LastPage(conf, env, cookieDict, oauthTokenDict)
        factory = server.Site(root)
        _server = internet.TCPServer(conf.port, factory, interface='localhost')
        _server.setServiceParent(lastpageService)
        return lastpageService

serviceMaker = ServiceMaker()
