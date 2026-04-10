import os
import time
import glob
import logging
import json
from typing import Optional, Dict, Any, List

from src.kuma_api import KUMA_API

class KUMA():

    # Const
    priority_mapping = {
        'LOW': 1,
        'NORMAL': 2,
        'HIGH': 3,
        '': 4
    }

    def __init__(self, config):
        api_url = config['kuma'].get('api_url')
        api_token = config['kuma'].get('api_token')
        api_version = config['kuma'].get('api_version', 'v2.1')
        ssl_cert = config['kuma'].get('ssl_cert', False)
        self.tenant_id = config['kuma'].get('tenant_id')
        self.incident_timeout = config['kuma']['modules']['incident'].get('timeout', 60)
        self.asset_timeout = config['kuma']['modules']['asset'].get('timeout', 10800)
        self.timeout = 10  # default value for infinite loop
        self.data_dir = config.get('data_dir', 'data')
        self.api = KUMA_API(api_url, api_token, ssl_cert, api_version)
        self.enable_incident = config['kuma']['modules']['incident'].get('enable', False)
        self.enable_asset = config['kuma']['modules']['asset'].get('enable', False)


    def scan_folder(self):
        files = glob.glob(f'{self.data_dir}/*.json')
        self.logger.info(f'Found {len(files)} file(s) to process')
        return files

    
    def process_updates(self):
        files = self.scan_folder()
        for update_file in files:
            def read_file(filename):
                with open(filename, 'r') as f:
                    data = json.load(f)
                return data
            if 'new_incident' in update_file:
                if self.create_incident(read_file(update_file)):
                    self.set_update_as_processed(update_file)
            if 'incident_updates' in update_file:
                if self.update_incident(read_file(update_file)):
                    self.set_update_as_processed(update_file)
            if '-update_incident' in update_file:
                if self.update_incident(read_file(update_file)):
                    self.set_update_as_processed(update_file)
            if '-new_attachment' in update_file:
                if self.add_attachment(read_file(update_file)):
                    self.set_update_as_processed(update_file)
            if '-new_comment' in update_file:
                if self.add_comment(read_file(update_file)):
                    self.set_update_as_processed(update_file)


    def import_assets(self):
        pass


    def create_incident(self, data):
        
        incident_data = {
            "name": f'{data["incident_number"]} - {data["summary"]}',
            "tenantID": self.tenant_id,
            "description": f'https://mdr.kaspersky.com/incidents/{data["incident_id"]}\n\nDescription: {data["description"]}\n\nStatus description: {data["status_description"]}',
            "type": {},
            "priority": self.priority_mapping[data['priority']],
            "assigneeId": "",
            "alerts": [],
            "assets": [],
            "accounts": [],
            "availableTenants": []
        }
        
        try:
            response = self.api.create_incident(incident_data)
            if response.status_code != 200:
                self.logger.error(f"KUMA incident creation has been failed with status code {response.status_code}: {response.text}")
                return False
            self.logger.info(f"KUMA incident has been created successfully: {response.json()['id']}: {response.json()['name']}")
            return True
        except Exception as e:
            self.logger.exception(f'Incident create error: {str(e)}')
        return False


    def get_kuma_incidents(self, params):
        try:
            response = self.api.get_incidents(params)
            if response.status_code != 200:
                self.logger.error(f"KUMA get incident with params = {str(params)} has been failed with status code {response.status_code}: {response.text}")
                return False
            self.logger.debug(f"KUMA incident has been recived successfully: count = {response.json()['count']}")
            return response.json()
        except Exception as e:
            self.logger.exception(f'Get incident error: {str(e)}')
        return False


    def update_incident(self, data):
        changed_ats = sorted([ ent['changed_at'] for ent in data ])
        incident_number = False
        result = True
        for changed_at in changed_ats:
            update = [ u for u in data if u['changed_at'] == changed_at][0]
            for entity in update['entity']:
                if entity == 'incident_details':
                    incident_number = update['entity'][entity]['incident_number']
                    result = self.update_incident_details(update['entity'][entity]) and result
                if entity == 'incident_comment':
                    result = self.update_incident_comment(update['entity'][entity], incident_number) and result
                if entity == 'incident_attachment':
                    result = self.update_incident_attachment(update['entity'][entity], incident_number) and result
                if entity == 'incident_response':
                    result = self.update_incident_response(update['entity'][entity], incident_number) and result
        return result


    def update_incident_details(self, data):
        # there are no corresponding method in KUMA API
        return True


    def update_incident_comment(self, data, incident_number):

        params = {
            "name": fr"^{incident_number}\s\-\s"
        }
        response = self.get_kuma_incidents(params)
        if not response:
            self.logger.error(f"KUMA get incidents error")
            return False
        if response['count'] != 1:
            self.logger.error(f"KUMA get more than 1 incidents with name {incident_number}")
            return False
        
        incident = response['incidents'][0]
        comment_data = {
            "id": incident['id'],
            "comment": f"New MDR comment: Author: {data['author_name']}, Comment: {data['text']}"
        }
        
        try:
            response = self.api.create_incident_comment(comment_data)
            if response.status_code != 204:
                self.logger.error(f"KUMA incident comment creation has been failed with status code {response.status_code}: {response.text}")
                return False
            self.logger.debug(f"KUMA incident comment has been created successfully")
            return True
        except Exception as e:
            self.logger.exception(f'Incident comment creation error: {str(e)}')
        return False


    def update_incident_attachment(self, data, incident_number):
        
        params = {
            "name": fr"^{incident_number}\s\-\s"
        }
        response = self.get_kuma_incidents(params)
        if not response:
            self.logger.error(f"KUMA get incidents error")
            return False
        if response['count'] != 1:
            self.logger.error(f"KUMA get more than 1 incidents with name {incident_number}")
            return False
        
        incident = response['incidents'][0]
        comment_data = {
            "id": incident['id'],
            "comment": f"New MDR attachment: Author: {data['author_name']}, Attachment: {data['full_name']}, Size: {data['file_size']}, Link: {data['link']}"
        }
        
        try:
            response = self.api.create_incident_comment(comment_data)
            if response.status_code != 204:
                self.logger.error(f"KUMA incident comment creation has been failed with status code {response.status_code}: {response.text}")
                return False
            self.logger.debug(f"KUMA incident comment has been created successfully")
            return True
        except Exception as e:
            self.logger.exception(f'Incident comment creation error: {str(e)}')
        return False


    def update_incident_response(self, data, incident_number):
        
        params = {
            "name": fr"^{incident_number}\s\-\s"
        }
        response = self.get_kuma_incidents(params)
        if not response:
            self.logger.error(f"KUMA get incidents error")
            return False
        if response['count'] != 1:
            self.logger.error(f"KUMA get more than 1 incidents with name {incident_number}")
            return False
        
        incident = response['incidents'][0]
        comment_data = {
            "id": incident['id'],
            "comment": f"New MDR response"
        }
        
        try:
            response = self.api.create_incident_comment(comment_data)
            if response.status_code != 204:
                self.logger.error(f"KUMA incident comment creation has been failed with status code {response.status_code}: {response.text}")
                return False
            self.logger.debug(f"KUMA incident comment has been created successfully")
            return True
        except Exception as e:
            self.logger.exception(f'Incident comment creation error: {str(e)}')
        return False


    def set_update_as_processed(self, filename):
        os.rename(filename, f'{filename}.processed')


    def run(self, logging_queue, logging_configurer):
        if not self.enable_incident and not self.enable_asset:
            return
        logging_configurer(logging_queue)
        self.logger = logging.getLogger(__name__)
        self.logger.info('started')
        incident_timeout_cur = 0
        asset_timeout_cur = 0
        while True:

            if self.enable_incident and incident_timeout_cur <= 0:
                self.logger.info('starting to process new updates..')
                self.process_updates()
                self.logger.info('MDR updates are processed')
                incident_timeout_cur = self.incident_timeout
            
            if self.enable_asset and asset_timeout_cur <= 0:
                self.logger.info('starting to import assets..')
                self.import_assets()
                self.logger.info('MDR assets are processed')
                asset_timeout_cur = self.enable_asset
            
            incident_timeout_cur = incident_timeout_cur - self.timeout
            asset_timeout_cur = asset_timeout_cur - self.timeout
            time.sleep(self.timeout)
