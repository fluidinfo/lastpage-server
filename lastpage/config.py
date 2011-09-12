from ConfigParserimport import ConfigParser


class Config(object):
    """
    Read a lastpage.me config file and provide easy access to its contents.

    @param file: The config file to read.
    """

    _SECTION = 'lastpage'
    _NON_STRING_VARS = {
        'local_oauth_port': int,
        'noisy_logging': bool,
        'port': int,
        'promiscuous': bool,
        'serve_static_files': bool,
    }

    def __init__(self, file):
        config = ConfigParser()
        config.read([file])
        for var, value in config.items(self._SECTION):
            varType = self._NON_STRING_VARS.get(var, str)
            if varType is int:
                value = config.getint(self._SECTION, var)
            elif varType is bool:
                value = config.getboolean(self._SECTION, var)
            setattr(self, var, value)
