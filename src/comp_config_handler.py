# comp_config_handler.py

"""
Configuration parser for pricing competition
"""
import sys
import numpy as np
import configparser
from optparse import OptionParser


def get_config():
    """ Get config file from given option, -f.
    """
    def usage(msg=''):
        """ Usage
        """
        use_ = "usage: prog -f config_file\n\n"
        sys.stdout.write(msg + use_)
        sys.exit(0)

    use = "usage: %prog -f config_file"
    parser = OptionParser(usage=use)
    parser.add_option("-f", "--config",
                      action="store",
                      type="string",
                      dest="config",
                      help="config file")
    (options, args) = parser.parse_args()
    
    if parser.has_option("-f") and options.config:
        return options.config
    else : 
        usage()


#-----------------------------------------------------------------------------
# Classes
#-----------------------------------------------------------------------------

class Config(object):
    """Reading ESN parameters given in configuration file.
    """
    PG_PARAMS = 'PG_PARAMS'
    SERVER_PARAMS = 'SERVER_PARAMS'
    COMP_PARAMS = 'COMP_PARAMS'
    
    def __init__(self, cfgfile):
        self.config = configparser.ConfigParser()
        self.config.read( cfgfile )
    
    def pg_params(self):
    	pg_params = {}
    	pg_params['host'] = self.config.get(Config.PG_PARAMS, 'host')
        pg_params['port'] = self.config.get(Config.PG_PARAMS, 'port')
    	pg_params['database'] = self.config.get(Config.PG_PARAMS, 'database')
    	pg_params['user'] = self.config.get(Config.PG_PARAMS, 'user')
    	pg_params['password'] = self.config.get(Config.PG_PARAMS, 'password')
    	return pg_params
    
    def server_params(self):
    	server_params = {}
    	server_params['address'] = self.config.get(Config.SERVER_PARAMS, 'address')
    	server_params['port'] = self.config.getint(Config.SERVER_PARAMS, 'port')
    	return server_params

    def comp_params(self):
		comp_params = {}
		comp_params['lead_t'] = self.config.getint(Config.COMP_PARAMS, 'lead_t')
		comp_params['n_max_range'] = self.config.getint(Config.COMP_PARAMS, 'n_max_range')
		comp_params['n_min_num'] = self.config.getint(Config.COMP_PARAMS, 'n_min_num')
		comp_params['n_max_num'] = self.config.getint(Config.COMP_PARAMS, 'n_max_num')
		comp_params['one_rule'] = self.config.getboolean(Config.COMP_PARAMS, 'one_rule')
		comp_params['com_conf_div'] = self.config.getboolean(Config.COMP_PARAMS, 'com_conf_div')
		comp_params['hour_min'] = self.config.getint(Config.COMP_PARAMS, 'hour_min')
		comp_params['rule_conf'] = self.config.getfloat(Config.COMP_PARAMS, 'rule_conf')
		comp_params['com_conf'] = self.config.getfloat(Config.COMP_PARAMS, 'com_conf')
		return comp_params

if __name__ == "__main__":

    config = Config(get_config())
    pg_params = np.loadtxt(config.pg_params())
    server_params = np.loadtxt(config.server_params())
    comp_params = np.loadtxt(config.comp_params())