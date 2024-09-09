import yaml
import json
import time
import re
import logging
from typing import Optional, Dict, Any, List, Union

from src.mdr_api import MDRConsole
#from src.logger import MDRLogger

logger = logging.getLogger(__name__)

class MDRSync():

    def __init__(self, config: Dict[str, Any]) -> None:
        api_url = config.get('api_url')
        client_id = config.get('client_id')
        ssl_cert = config.get('ssl_cert', False)
        self.period = config['mdr_sync'].get('period', 60)
        self.data_dir = config.get('data_dir', 'data')
        self.token_dir = config.get('token_dir', 'conf')
        self.access_token = self.update_access_token()
        self.filter = config['mdr_sync'].get('filter')
        self.download_attachments_size_limit = config['mdr_sync'].get('download_attachments_size_limit')
        self.exclude_author = config['mdr_sync'].get('exclude_author')
        self.mdr = MDRConsole(api_url = api_url, client_id = client_id, access_token = self.access_token, ssl_cert = ssl_cert)
        self.max_incidents_at_time = config['mdr_sync'].get('max_incidents_at_time')
    

    def update_access_token(self) -> str:
        with open(f'{self.token_dir}/.access_token', 'r') as f:
            access_token = f.read()
        return access_token


    def set_last_check(self, last_check: int) -> None:
        with open(f'{self.token_dir}/.last_check', 'w') as f:
            f.write(str(last_check))

    
    def get_last_check(self) -> int:
        try:
            with open(f'{self.token_dir}/.last_check', 'r') as f:
                last_check = f.read()
        except:
            last_check = 0
            self.set_last_check(last_check)
        return int(last_check)


    def get_incidents(self) -> Optional[str]:
        last_check = self.get_last_check()
        kwargs = self.filter.get('incidents')
        kwargs['min_update_time'] = last_check + 1
        # get count of incidents by filter
        try:
            incidents_count = self.mdr.get_incidents_count(**kwargs)['count']
        except Exception as e:
            logger.exception('Error while getting incidents count')
            return
        if incidents_count > self.max_incidents_at_time:
            logger.error(f'Too many incidents are going to be received: {incidents_count} > {self.max_incidents_at_time}')
            return f'Too many incidents are going to be received: {incidents_count} > {self.max_incidents_at_time}'
        try:
            incident_list = self.mdr.get_incidents_list(**kwargs)
        except Exception as e:
            logger.exception('Error while getting incident list')
            return
        for incident in incident_list:
            # identify updates and push them to data directory
            self.parse_incident_updates(incident, last_check)
            # update last_check parameter based on the latest appeared incident
            if incident['update_time'] > last_check:
                last_check = incident['update_time']
        self.set_last_check(last_check)
    

    def get_comments(self, incident_id: str) -> Optional[str]:
        fields = ["author_name", "comment_id", "creation_time", "origin", "text", "was_read"]
        comments_list = self.mdr.get_comments_list()


    def download_attachment(self, attachment: Dict[str, Any]) -> None:
        if attachment['file_size'] > self.download_attachments_size_limit:
            return
        attachment_id = attachment['attachment_id']
        filename = attachment['full_name']
        try:
            content = self.mdr.attachments_download(attachment_id = attachment_id)
        except Exception as e:
            logger.exception('Error while downloading attachment')
            return
        with open(f'{self.data_dir}/files/{attachment_id}_{filename}', 'wb') as f:
            f.write(content)
            logger.info(f'file {filename} has been written to {self.data_dir}/files/{attachment_id}_{filename}')

    def parse_incident_updates(self, incident_data: Dict[str, Any], last_check: int) -> Dict[str, Any]:
        incident_id = incident_data['incident_id']
        creation_time = incident_data['creation_time']
        update_time = incident_data['update_time']
        attachments = incident_data.get('attachments')
        incident_data.pop('attachments')
        comments = incident_data.get('comments')
        incident_data.pop('comments')
        responses = incident_data.get('responses')
        incident_data.pop('responses')
        # Check if it's the new incident
        if creation_time == update_time or creation_time > last_check:
            logger.info(f'new incident found. incident_id = {incident_id}, creation_time = {creation_time}')
            self.push_updates('new_incident', creation_time, incident_data)
        # Check if there is any updates of incident
        if update_time > last_check:
            logger.info(f'incident update found. incident_id = {incident_id}, update_time = {update_time}')
            self.push_updates('update_incident', update_time, incident_data)
        # Check updates in attachments
        for attachment in attachments: 
            if attachment['creation_time'] > last_check:  # attachment['was_read'] == False
                logger.info(f'new attachment found. incident_id = {incident_id}, filename = {attachment["full_name"]}, creation_time = {attachment["creation_time"]}')
                attachment_creation_time = attachment['creation_time']
                attachment_data = {
                    'incident_id': incident_id, 
                    'attachments': [attachment]
                }
                if re.match(self.exclude_author, attachment['author_name']):
                    continue
                self.push_updates('new_attachment', attachment_creation_time, attachment_data)
                self.download_attachment(attachment)
        # Check updates in comments
        for comment in comments: 
            if comment['creation_time'] > last_check:  # comment['was_read'] == False
                logger.info(f'new comment found. incident_id = {incident_id}, from = {comment["author_name"]}, creation_time = {comment["creation_time"]}')
                comment_creation_time = comment['creation_time']
                comment_data = {
                    'incident_id': incident_id, 
                    'comments': [comment]
                }
                if re.match(self.exclude_author, comment['author_name']):
                    continue
                self.push_updates('new_comment', comment_creation_time, comment_data)
        # Check updates in responses
        for response in responses:
            if response['creation_time'] > last_check:  # response['was_read'] == False 
                logger.info(f'new response found. incident_id = {incident_id}, creation_time = {response["creation_time"]}')
                response_creation_time = response['creation_time']
                response_data = {
                    'incident_id': incident_id, 
                    'responses': [response]
                }
                self.push_updates('new_response', response_creation_time, response_data)


    def push_updates(self, update_type: str, timestamp: int, data: Dict[str, Any]) -> None:
        timestamp = str(timestamp)
        filename = f'{timestamp}_{update_type}.json'
        with open(f'{self.data_dir}/{filename}', 'w') as f:
            json.dump(data, f)
            logger.info(f'An update has been writen to {filename}')
    

    def run(self, logging_queue, logging_configurer):
        logging_configurer(logging_queue)
        self.logger = logging.getLogger(__name__)
        logger.info('started')
        while True:
            logger.info('getting updates from MDR..')
            self.mdr.access_token = self.update_access_token()
            self.get_incidents()
            logger.info('getting updates finished')
            time.sleep(self.period)