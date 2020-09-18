"""The huawei_router component."""
import logging
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers import discovery
import voluptuous as vol
from datetime import datetime
import base64
import re
import sys
import json
import hashlib
from requests import session
from bs4 import BeautifulSoup
from .const import DOMAIN


CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Optional(CONF_USERNAME): cv.string,
        vol.Optional(CONF_PASSWORD): cv.string,
        vol.Optional(CONF_PASSWORD): cv.string,
    }, extra=vol.ALLOW_EXTRA),
}, extra=vol.ALLOW_EXTRA)

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor"]

def setup(hass, config):
    """Set up is called when Home Assistant is loading our component."""
    plattform_conf = config.get(DOMAIN)
    client = huawei_hg659_client(plattform_conf)
    # Create DATA dict
    hass.data[DOMAIN] = {}
    hass.data[DOMAIN]['client'] = client
    hass.data[DOMAIN]['last_reboot'] = None
    hass.data[DOMAIN]['scanning'] = False
    hass.data[DOMAIN]['statusmsg'] = 'OK'

    def handle_reboot(call):
        """Handle the service call."""
        # name = call.data.get(ATTR_NAME, DEFAULT_NAME)
        result = client.reboot()
        hass.data[DOMAIN]["last_reboot"] = datetime.now()
        hass.states.set(f"{DOMAIN}.last_reboot", datetime.now())
        return True

    hass.services.register(DOMAIN, "reboot", handle_reboot)

    # Load platforms
    for platform in PLATFORMS:
        hass.async_create_task(
            discovery.async_load_platform(
                hass, platform, DOMAIN, plattform_conf, config
            )
        )

    _LOGGER.debug(f"Register {DOMAIN} service '{DOMAIN}.reboot'")
    # Return boolean to indicate that initialization was successfully.
    return True

class huawei_hg659_client:
    def __init__(self, config):
        """Initialize the client."""
        self.host = config[CONF_HOST]
        self.username = config[CONF_USERNAME]
        self.password = config[CONF_PASSWORD]
        self.session = None
        self.logindata = None

    # REBOOT THE ROUTER
    def reboot(self) -> bool:
        if self.login() == False:
            return False
        # REBOOT REQUEST
        _LOGGER.info("Requesting reboot")
        try:
            data = {
                'csrf': {'csrf_param': self.logindata['csrf_param'], 'csrf_token': self.logindata['csrf_token']}}
            r = s.post('http://{0}/api/service/reboot.cgi'.format(self.host),
                       data=json.dumps(data, separators=(',', ':')))
            data = json.loads(re.search('({.*?})', r.text).group(1))
            assert data['errcode'] == 0, data
            _LOGGER.info("Rebooting HG659")
            return True
        except Exception as e:
            _LOGGER.error('Failed to reboot: {0} with data {1}'.format(e, data))
            return False
        finally:
            self.logout()

    # LOGIN PROCEDURE
    def login(self) -> bool:
        pass_hash = hashlib.sha256(self.password.encode()).hexdigest()
        pass_hash = base64.b64encode(pass_hash.encode()).decode()
        ## INITIAL CSRF ##

        try:
            self.session = session()
            r = self.session.get('http://{0}'.format(self.host))
            html = BeautifulSoup(r.text, 'html.parser')
            data = {
                'csrf_param': html.find('meta', {'name': 'csrf_param'}).get('content'),
                'csrf_token': html.find('meta', {'name': 'csrf_token'}).get('content'),
            }
            assert data['csrf_param'] and data['csrf_token'], 'Empty csrf_param or csrf_token'
        except Exception as e:
            _LOGGER.error('Failed to get CSRF. error "{0}" with data {1}'.format(e, data))
            self.statusmsg = e.errorCategory
            return False

        ## LOGIN ##
        try:
            pass_hash = self.username + pass_hash + \
                data['csrf_param'] + data['csrf_token']
            pass_hash = hashlib.sha256(pass_hash.encode()).hexdigest()
            data = {'csrf': {'csrf_param': data['csrf_param'], 'csrf_token': data['csrf_token']}, 'data': {
                'UserName': self.username, 'Password': pass_hash}}
            r = self.session.post('http://{0}/api/system/user_login'.format(self.host),
                          data=json.dumps(data, separators=(',', ':')))
            data = json.loads(re.search('({.*?})', r.text).group(1))
            assert data.get('errorCategory', '').lower() == 'ok', data.get('errorCategory', 'unknown Login error')
            # _LOGGER.debug("Logged in")
            self.logindata = data
            self.statusmsg = None
            return True
        except Exception as e:
            _LOGGER.error('Failed to login: {0}'.format(e))
            self.statusmsg = 'Failed login: {0}'.format(e)
            self.logindata = None
            self.session.close()
            return False
    ## LOGOUT ##
    def logout(self):
        try:
            data = {'csrf': {
                            'csrf_param': self.logindata['csrf_param'],
                            'csrf_token': self.logindata['csrf_token']
                            }
                    }
            r = self.session.post('http://{0}/api/system/user_logout'.format(
                self.host), data=json.dumps(data, separators=(',', ':')))
            data = json.loads(re.search('({.*?})', r.text).group(1))
            assert data['csrf_param'] == 'NULL_token', data
            _LOGGER.debug("Logged out")
        except Exception as e:
            _LOGGER.error('Failed to logout: {0}'.format(e))
        finally:
            self.session.close()

    def get_devices_response(self):
        """Get the raw string with the devices from the router."""

        if self.login() == False:
            return False
        # GET DEVICES RESPONSE
        try:
            query = 'http://{0}/api/system/HostInfo'.format(self.host)
            rdev = self.session.get(query)
            devices_text = re.search('\/\*(.*?)\*\/', rdev.text).group(1)
            devices = json.loads(devices_text)
            self.statusmsg = 'OK'
        except Exception as e:
            _LOGGER.error('Failed to get Devices: {0} with query {1} rdev {2}'.format(e, query, rdev))
            self.statusmsg = e.errorCategory
            return False
        finally:
            self.logout()
        return (devices)
