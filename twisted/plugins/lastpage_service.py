from jinja2 import Environment, PackageLoader

from lastpage import resource

from twisted.plugin import IPlugin
from twisted.application import service, internet
from twisted.web import server
from twisted.internet import protocol
from twisted.python import usage

from txfluiddb.client import Endpoint

from zope.interface import implements


class Options(usage.Options):
    """
    Command line options for the lastpage.me service.
    """
    optParameters = [
        ['endpoint', None, 'http://fluiddb.fluidinfo.com:80',
         'Fluidinfo endpoint.'],
        ['port', None, 8000, 'Port to listen on.'],
        ]
    optFlags = [
        ['noisy-logging', None, "If True, let factories log verbosely."],
        ['serve-static-files', None,
         """If True, also serve requests for static files. This is better
         handled by something like nginx in production."""],
        ]


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
        serveStaticFiles = options['serve-static-files']
        env = Environment(loader=PackageLoader('lastpage', 'templates'))
        if not options['noisy-logging']:
            protocol.Factory.noisy = False
        lastpageService = service.MultiService()
        root = resource.LastPage(
            Endpoint(baseURL=options['endpoint']), env, serveStaticFiles)
        factory = server.Site(root)
        _server = internet.TCPServer(int(options['port']),
                                     factory, interface='localhost')
        _server.setServiceParent(lastpageService)
        return lastpageService

serviceMaker = ServiceMaker()
