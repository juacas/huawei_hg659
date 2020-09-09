"""The huawei_router component."""
import logging
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from datetime import datetime
import base64
import logging
import re
import sys
import json
import hashlib
from requests import session
from bs4 import BeautifulSoup

DOMAIN = 'huawei_hg659'
CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Optional(CONF_USERNAME): cv.string,
        vol.Optional(CONF_PASSWORD): cv.string,
        vol.Optional(CONF_PASSWORD): cv.string,
    }, extra=vol.ALLOW_EXTRA),
}, extra=vol.ALLOW_EXTRA)

_LOGGER = logging.getLogger(__name__)

def setup(hass, config):
    """Set up is called when Home Assistant is loading our component."""
    conf = config.get(DOMAIN)
    url = conf[CONF_HOST]
    client = huawei_hg659_client(conf)
    hass.data[DOMAIN] = client

    def handle_reboot(call):
        """Handle the service call."""
        # name = call.data.get(ATTR_NAME, DEFAULT_NAME)
        result = client.reboot()
        hass.states.set(f"{DOMAIN}.last_reboot", datetime.now())
        return True

    hass.services.register(DOMAIN, "reboot", handle_reboot)
    _LOGGER.debug(f"Register {DOMAIN} service 'reboot'")
    # Return boolean to indicate that initialization was successfully.
    return True
class huawei_hg659_client:
    def __init__(self, config):
        """Initialize the scanner."""
        self.host = config[CONF_HOST]
        self.username = config[CONF_USERNAME]
        self.password = config[CONF_PASSWORD]
        # REBOOT THE ROUTER

    def reboot(self) -> bool:
        s = session()
        if self.login(s) == False:
            return False
        # REBOOT REQUEST
        _LOGGER.debug("Requesting reboot")
        try:
            data = {
                'csrf': {'csrf_param': data['csrf_param'], 'csrf_token': data['csrf_token']}}
            r = s.post('http://{0}/api/service/reboot.cgi'.format(IP_ADDR),
                       data=json.dumps(data, separators=(',', ':')))
            data = json.loads(re.search('({.*?})', r.text).group(1))
            assert data['errcode'] == 0, data
            _LOGGER.info("Rebooting HG659")
            return True
        except Exception as e:
            _LOGGER.error('Failed to reboot: {0}'.format(e))
            return False

    # LOGIN PROCEDURE
    def login(self, sess) -> bool:
        pass_hash = hashlib.sha256(self.password.encode()).hexdigest()
        pass_hash = base64.b64encode(pass_hash.encode()).decode()
        _LOGGER.debug('Username {0} PassHash {1}'.format(
            self.username, pass_hash))
        _LOGGER.debug("Logging in")
        ## INITIAL CSRF ##
        try:
            r = sess.get('http://{0}'.format(self.host))
            html = BeautifulSoup(r.text, 'html.parser')
            data = {
                'csrf_param': html.find('meta', {'name': 'csrf_param'}).get('content'),
                'csrf_token': html.find('meta', {'name': 'csrf_token'}).get('content'),
            }
            assert data['csrf_param'] and data['csrf_token'], 'Empty csrf_param or csrf_token'
            _LOGGER.debug("Acquired CSRF")
        except Exception as e:
            _LOGGER.error('Failed to get CSRF: {0}'.format(e))
            return False

        ## LOGIN ##
        try:
            pass_hash = self.username + pass_hash + \
                data['csrf_param'] + data['csrf_token']
            pass_hash = hashlib.sha256(pass_hash.encode()).hexdigest()
            data = {'csrf': {'csrf_param': data['csrf_param'], 'csrf_token': data['csrf_token']}, 'data': {
                'UserName': self.username, 'Password': pass_hash}}
            #_LOGGER.debug('Body: {0}'.format(json.dumps(data, separators=(',', ':'))))
            r = sess.post('http://{0}/api/system/user_login'.format(self.host),
                          data=json.dumps(data, separators=(',', ':')))
            data = json.loads(re.search('({.*?})', r.text).group(1))
            assert data.get('errorCategory', '').lower() == 'ok', data
            _LOGGER.debug("Logged in")
            return True
        except Exception as e:
            _LOGGER.error('Failed to login: {0}'.format(e))
            return False

    def get_devices_response(self):
        """Get the raw string with the devices from the router."""
        s = session()
        if self.login(s) == False:
            return False
        # GET DEVICES RESPONSE
        _LOGGER.debug("Requesting host info data")
        try:
            rdev = s.get('http://{0}/api/system/HostInfo'.format(self.host))
            devices_text = re.search('\/\*(.*?)\*\/', rdev.text).group(1)
            devices = json.loads(devices_text)
        except Exception as e:
            _LOGGER.error('Failed to get Devices: {0}'.format(e))
            return False
        return (devices)
