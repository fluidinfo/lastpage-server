import ConfigParser


class Config(object):
    """
    Read a lastpage.me config file and provide easy access to its contents.

    @param file: The config file to read.
    """

    _SECTION = 'lastpage'
    _KNOWN_VARS = {
        'access_token_url': str,
        'authorization_url': str,
        'authorization_url': str,
        'callback_child': str,
        'callback_url': str,
        'consumer_key': str,
        'consumer_secret': str,
        'filesystem_root_dir': str,
        'fluidinfo_endpoint': str,
        'local_oauth_port': int,
        'noisy_logging': bool,
        'port': int,
        'promiscuous': bool,
        'request_token_url': str,
        'serve_static_files': bool,
    }

    def __init__(self, file):
        config = ConfigParser.ConfigParser()
        config.read([file])
        for var, value in config.items(self._SECTION):
            varType = self._KNOWN_VARS.get(var, str)
            if varType is str:
                pass
            elif varType is int:
                value = config.getint(self._SECTION, var)
            elif varType is bool:
                value = config.getboolean(self._SECTION, var)
            else:
                raise RuntimeError('Unknown variable type %s.' % varType)
            setattr(self, var, value)
