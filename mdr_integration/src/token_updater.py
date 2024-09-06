import yaml
import time
import logging
import jwt
import datetime
from typing import Optional, Dict, Any, List

from src.mdr_api import MDRConsole

class TokenUpdater():

    def __init__(self, config: Dict[str, Any]) -> None:
        api_url = config.get('api_url')
        client_id = config.get('client_id')
        ssl_cert = config.get('ssl_cert')
        self.period = config['token_updater'].get('period', 600)
        self.token_dir = config.get('token_dir', 'conf')
        self.mdr = MDRConsole(api_url = api_url, client_id = client_id, ssl_cert = ssl_cert)

    def run(self, logging_queue, logging_configurer) -> None:
        logging_configurer(logging_queue)
        self.logger = logging.getLogger(__name__)
        self.logger.info('started')
        while True:
            
            # check if refresh token is actual or it's needed to be updated
            refresh_token = self.read_refresh_token()
            if refresh_token:
                refresh_token_exp = jwt.decode(refresh_token, options={"verify_signature": False}).get("exp")
                self.logger.info(f'refresh_token expiration time: {datetime.datetime.fromtimestamp(refresh_token_exp)}')
                if refresh_token_exp > time.time():
                    self.logger.info(f'refresh_token is actual')
                else:
                    self.logger.error(f'You should update {self.token_dir}/.refresh_token. Please take it from MDR Console (https://support.kaspersky.com/MDR/en-US/204468.htm).')
            else:
                self.logger.error(f'You should fill {self.token_dir}/.refresh_token. Please take it from MDR Console (https://support.kaspersky.com/MDR/en-US/204468.htm).')

            # check if access token is actual or it's needed to be updated
            access_token = self.read_access_token()
            need_update_access_token = False
            if access_token:
                access_token_exp = jwt.decode(access_token, options={"verify_signature": False}).get("exp")
                self.logger.info(f'access_token expiration time: {datetime.datetime.fromtimestamp(access_token_exp)}')
                if access_token_exp > time.time():
                    self.logger.info(f'access_token is actual')
                else:
                    need_update_access_token = True
            else:
                need_update_access_token = True

            if need_update_access_token:
                refresh_token = self.read_refresh_token()
                access_token, refresh_token = self.update_token(refresh_token)
                self.write_access_token(access_token)
                self.write_refresh_token(refresh_token)

            self.logger.info('tokens updating finished')
            time.sleep(self.period)

    def read_refresh_token(self):
        with open(f'{self.token_dir}/.refresh_token', 'r') as f:
            refresh_token = f.read()
        return refresh_token
    
    def read_access_token(self):
        with open(f'{self.token_dir}/.access_token', 'r') as f:
            access_token = f.read()
        return access_token
    
    def write_refresh_token(self, refresh_token):
        with open(f'{self.token_dir}/.refresh_token', 'w') as f:
            f.write(refresh_token)
    
    def write_access_token(self, access_token):
        with open(f'{self.token_dir}/.access_token', 'w') as f:
            f.write(access_token)

    def update_token(self, refresh_token) -> None:
        refresh_token = self.read_refresh_token()
        access_token = ''
        try:
            access_token, refresh_token = self.mdr.get_access_token(refresh_token)
        except Exception as e:
            self.logger.error('Error while refreshing the access token')
            return access_token, refresh_token
        return access_token, refresh_token