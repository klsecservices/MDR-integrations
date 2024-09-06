#!/usr/bin/env python3
# encoding: utf-8

import time
import yaml
import json
import re
from typing import Dict

from cortexutils.responder import Responder

from mdr_api import MDRConsole

class MDRResponder(Responder):
    
    def __init__(self):
        Responder.__init__(self)
        self.service = self.get_param('config.service', None, 'Service parameter is missing')
        self.api_url = self.get_param('config.api_url', None)
        self.client_id = self.get_param('config.client_id', None)
        self.token_dir = self.get_param('config.token_dir', None)
        self.ssl_cert = self.get_param('config.ssl_cert', False)
        config_path = self.get_param('config.config_path', None)
        if config_path:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
                self.api_url = config.get('api_url')
                self.client_id = config.get('client_id')
                self.ssl_cert = config.get('ssl_cert')
                self.token_dir = config.get('token_dir')
    
    def initMDRConnection(self):
        access_token = self.get_access_token(self.token_dir)
        self.mdr = MDRConsole(api_url = self.api_url, client_id = self.client_id, access_token = access_token, ssl_cert = self.ssl_cert)

    def get_access_token(self, token_dir: str) -> str:
        with open(f'{token_dir}/.access_token', 'r') as f:
            access_token = f.read()
        return access_token

    def send_task_log(self):
        self.initMDRConnection()  # since that we can use self.mdr for MDR API
        try:
            data = self.get_param('data')
            author = data['createdBy']
            message = data['message']
            attachment = data.get('attachment')
            if attachment:
                attachment_name = attachment['name']
                attachment_id = attachment['id']
            incident_id = data['case_task']['case']['customFields']['mdr-incident-id']['string']
            message = f'{author} wrote:\n>{message}'
            response = self.mdr.comments_create(incident_id = incident_id, text = message, markdown_to_html = True)
            
            report = {
                "success": True,
                "full": { "message": response },
                "operations":[]
            }
            return report
        except Exception as e:
            self.error(str(e))

    def close_incident(self):
        self.initMDRConnection()  # since that we can use self.mdr for MDR API
        try:
            data = self.get_param('data')
            incident_id = data['customFields']['mdr-incident-id']['string']
            resolution_status = data['resolutionStatus']
            if resolution_status == 'TruePositive':
                resolution_status = 'TRUE_POSITIVE'
            elif resolution_status == 'FalsePositive':
                resolution_status = 'FALSE_POSITIVE'
            else:
                self.error(f'resolution-status value should be one of (TruePositive, FalsePositive) not {resolution_status}')
            resolution_summary = data['summary']
            #response = self.mdr.close_incident(incident_id = incident_id, resolution_status = resolution_status, summary = resolution_summary)
            response = incident_id + resolution_status + resolution_summary
            
            report = {
                "success": True,
                "full": { "message": response },
                "operations":[]
            }
            return report
        except Exception as e:
            self.error(str(e))
    
    def confirm_response(self):
        self.initMDRConnection()  # since that we can use self.mdr for MDR API
        try:
            data = self.get_param('data')
            author = data['createdBy']
            message = data['message']
            #incident_id = data['case_task']['case']['customFields']['mdr-incident-id']['string']
            response_id = re.findall('ID\S*:\s+(\S+)\s.*', data['description'])[0]
            status = 'Confirmed'
            response = self.mdr.response_update(comment = message, response_id = response_id, status = status)
            
            report = {
                "success": True,
                "full": { "message": response },
                "operations":[]
            }
            return report
        except Exception as e:
            self.error(str(e))
    
    def decline_response(self):
        self.initMDRConnection()  # since that we can use self.mdr for MDR API
        try:
            data = self.get_param('data')
            group = data['group']
            if group != 'Response':
                self.error('The task should be in group Response')
            author = data['createdBy']
            message = data['message']
            #incident_id = data['case_task']['case']['customFields']['mdr-incident-id']['string']
            response_id = re.findall('ID\S*:\s+(\S+)\s.*', data['description'])
            if len(response_id) > 0:
                response_id = response_id[0]
            else:
                self.error('Cannot define the ID of the Response. ID shoud be specified in Description field.')
            status = 'Declined'
            response = self.mdr.response_update(comment = message, response_id = response_id, status = status)
            
            report = {
                "success": True,
                "full": { "message": response },
                "operations":[]
            }
            return report
        except Exception as e:
            self.error(str(e))

    def run(self):
        if self.service == 'send_task_log':
            report = self.send_task_log()
            self.report(report)
        elif self.service == 'close_incident':
            report = self.close_incident()
            self.report(report)
        elif self.service == 'confirm_response':
            report = self.confirm_response()
            self.report(report)
        elif self.service == 'decline_response':
            report = self.decline_response()
            self.report(report)
        else:
            self.error('Invalid service')

if __name__ == '__main__':
    MDRResponder().run()
