from twisted.python.usage import Options


class FluidinfoEndpointOptions(Options):
    """
    Options handling to allow the specification of a Fluidinfo endpoint.
    """
    FLUIDINFO_ENDPOINT = 'http://fluiddb.fluidinfo.com/'
    SANDBOX_ENDPOINT = 'http://sandbox.fluidinfo.com/'
    LOCAL_ENDPOINT = 'http://localhost:8080/'

    optParameters = [
        ['endpoint', None, None, 'The Fluidinfo endpoint URL.'],
        ]
    optFlags = [
        ['local', 'L', 'If True use the a local Fluidinfo'],
        ['sandbox', 'S', 'If True use the sandbox Fluidinfo'],
        ]

    def postOptions(self):
        """
        Allow for the convenience flags -L and -S to set the endpoint to be
        either a local Fluidinfo or the sandbox.
        """
        endpointURL = self['endpoint']
        local = self['local']
        sandbox = self['sandbox']

        if endpointURL:
            assert not (local or sandbox)
        else:
            if local or sandbox:
                assert not (local and sandbox)
                if local:
                    endpointURL = self.LOCAL_ENDPOINT
                else:
                    endpointURL = self.SANDBOX_ENDPOINT
            else:
                endpointURL = self.FLUIDINFO_ENDPOINT
        if not endpointURL.endswith('/'):
            endpointURL += '/'
        self['endpoint'] = endpointURL
