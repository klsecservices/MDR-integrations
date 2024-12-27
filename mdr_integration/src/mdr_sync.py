import yaml
import json
import time
import re
import logging
from typing import Optional, Dict, Any, List, Union

from src.mdr_api import MDRConsole

class MDRSync():

    IPV4_RE = '\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}'
    IPV6_RE = '(?:[a-fA-F0-9]{1,4}:){7}(?:[a-fA-F0-9]{1,4})'

    def __init__(self, config: Dict[str, Any]) -> None:
        api_url = config.get('api_url')
        client_id = config.get('client_id')
        ssl_cert = config.get('ssl_cert', False)
        self.timeout = config['mdr_sync'].get('timeout', 60)
        self.incident_timeout = config['mdr_sync']['modules']['incident'].get('timeout', 60)
        self.asset_timeout = config['mdr_sync']['modules']['asset'].get('timeout', 10800)
        self.timeout = 10  # default value for infinite loop
        self.data_dir = config.get('data_dir', 'data')
        self.token_dir = config.get('token_dir', 'conf')
        self.access_token = self.update_access_token()
        self.incident_filter = config['mdr_sync']['modules']['incident'].get('filter')
        self.asset_filter = config['mdr_sync']['modules']['asset'].get('filter')
        self.download_attachments_size_limit = config['mdr_sync'].get('download_attachments_size_limit')
        self.exclude_author = config['mdr_sync'].get('exclude_author')
        self.mdr = MDRConsole(api_url = api_url, client_id = client_id, access_token = self.access_token, ssl_cert = ssl_cert)
        self.max_incidents_at_time = config['mdr_sync'].get('max_incidents_at_time')
        self.enable_incident = config['mdr_sync']['modules']['incident'].get('enable', False)
        self.enable_asset = config['mdr_sync']['modules']['asset'].get('enable', False)
        self.asset_output_format = config['mdr_sync']['modules']['asset'].get('output_format', 'json')
    

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
        kwargs = self.incident_filter
        kwargs['min_update_time'] = last_check + 1
        # get count of incidents by filter
        try:
            incidents_count = self.mdr.get_incidents_count(**kwargs)['count']
        except Exception as e:
            self.logger.exception('Error while getting incidents count')
            return
        if incidents_count > self.max_incidents_at_time:
            self.logger.error(f'Too many incidents are going to be received: {incidents_count} > {self.max_incidents_at_time}')
            return f'Too many incidents are going to be received: {incidents_count} > {self.max_incidents_at_time}'
        try:
            incident_list = self.mdr.get_incidents_list(**kwargs)
        except Exception as e:
            self.logger.exception('Error while getting incident list')
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
            self.logger.exception('Error while downloading attachment')
            return
        with open(f'{self.data_dir}/files/{attachment_id}_{filename}', 'wb') as f:
            f.write(content)
            self.logger.info(f'file {filename} has been written to {self.data_dir}/files/{attachment_id}_{filename}')

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
            self.logger.info(f'new incident found. incident_id = {incident_id}, creation_time = {creation_time}')
            self.push_updates('new_incident', creation_time, incident_data)
        # Check if there is any updates of incident
        if update_time > last_check:
            self.logger.info(f'incident update found. incident_id = {incident_id}, update_time = {update_time}')
            self.push_updates('update_incident', update_time, incident_data)
        # Check updates in attachments
        for attachment in attachments: 
            if attachment['creation_time'] > last_check:  # attachment['was_read'] == False
                self.logger.info(f'new attachment found. incident_id = {incident_id}, filename = {attachment["full_name"]}, creation_time = {attachment["creation_time"]}')
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
                self.logger.info(f'new comment found. incident_id = {incident_id}, from = {comment["author_name"]}, creation_time = {comment["creation_time"]}')
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
                self.logger.info(f'new response found. incident_id = {incident_id}, creation_time = {response["creation_time"]}')
                response_creation_time = response['creation_time']
                response_data = {
                    'incident_id': incident_id, 
                    'responses': [response]
                }
                self.push_updates('new_response', response_creation_time, response_data)


    def get_assets(self):
        
        # get count of assets by filter
        kwargs = {}
        try:
            assets_count = self.mdr.get_assets_count(**kwargs)['count']
            self.logger.debug(f'MDR assets count = {str(assets_count)}')
        except Exception as e:
            self.logger.exception('Error while getting assets count')
            return
        
        if not isinstance(assets_count, int):
            self.logger.exception(f'Error while getting assets count: {str(assets_count)}')
            return

        # get asset list
        page_size = 1000  # default value
        first_page = 1  # default value
        page_total = - ( -assets_count // page_size )  # round up
        kwargs = {
            'page_size': page_size,
            'page': first_page,
            **self.asset_filter
        }
        assets = []
        for page in range(first_page, page_total+1):
            try:
                kwargs['page'] = page
                asset_list = self.mdr.get_assets_list(**kwargs)
                assets.extend(asset_list)
                self.logger.debug(f'MDR assets list has been recieved, count = {str(len(asset_list))}')
            except Exception as e:
                self.logger.exception('Error while getting assets list')
                return
        self.parse_assets(assets)
        return


    def parse_assets(self, assets_list):
        assets = []
        for asset in assets_list:
            if self.asset_output_format == 'csv':
                def merge_network_interface_data(asset_network_interfaces, param_name):
                    if param_name in ['ipv4', 'ipv6']:
                        match = {
                            'ipv4': self.IPV4_RE,
                            'ipv6': self.IPV6_RE
                        }
                        ips = []
                        for interface in asset_network_interfaces:
                            ips.extend([ ip for ip in interface['ip'].split('|') if re.match(ip, match(param_name)) ])
                        return '|'.join(ips)
                    return '|'.join([ interface[param_name] for interface in asset_network_interfaces ])
                network_interfaces = {
                    'network_interfaces_dsc':   merge_network_interface_data(asset['network_interfaces'], 'dsc'),
                    'network_interfaces_dnsd':  merge_network_interface_data(asset['network_interfaces'], 'dnsd'),
                    'network_interfaces_defg':  merge_network_interface_data(asset['network_interfaces'], 'defg'),
                    'network_interfaces_mac':   merge_network_interface_data(asset['network_interfaces'], 'mac'),
                    'network_interfaces_ipcm':  merge_network_interface_data(asset['network_interfaces'], 'ipcm'),
                    'network_interfaces_ipv4':  merge_network_interface_data(asset['network_interfaces'], 'ipv4'),
                    'network_interfaces_ipv6':  merge_network_interface_data(asset['network_interfaces'], 'ipv6')
                }
            elif self.asset_output_format == 'json':
                network_interfaces = {
                    'network_interfaces': asset['network_interfaces']
                }
            else:
                raise KeyError(f'{self.asset_output_format} is not correct format: "json" or "csv" are only allowed')
            assets.append({
                'asset_id': asset['asset_id'],
                'host_name': asset['host_name'],
                'domain': asset['domain'],
                'first_seen': asset['first_seen'],
                'last_seen': asset['last_seen'],
                'os_version': asset['os_version'],
                'installed_product_info': asset['installed_product_info'],
                'ksc_host_id': asset['ksc_host_id'],
                'tenant_name': asset['tenant_name'],
                'isolation': asset['isolation'],
                'status': asset['status'],
                'status_reasons': '|'.join(asset['status_reasons']),
                **network_interfaces
            })

        asset_import_time = int(time.time()*1000)
        self.push_updates(update_type = 'asset_export', timestamp = asset_import_time, data = assets, file_extension = self.asset_output_format)


    def push_updates(self, update_type: str, timestamp: int, data: Dict[str, Any], file_extension: str) -> None:
        if not file_extension:
            file_extension = 'json'
        timestamp = str(timestamp)
        filename = f'{timestamp}_{update_type}.json'
        with open(f'{self.data_dir}/{filename}', 'w') as f:
            json.dump(data, f)
            self.logger.info(f'An update has been writen to {filename}')
    

    def run(self, logging_queue, logging_configurer):
        logging_configurer(logging_queue)
        self.logger = logging.getLogger(__name__)
        self.logger.info('started')
        incident_timeout_cur = 0
        asset_timeout_cur = 0
        while True:
            
            if self.enable_incident and incident_timeout_cur <= 0:
                self.logger.info('getting incident updates from MDR..')
                self.mdr.access_token = self.update_access_token()
                self.get_incidents()
                self.logger.info('getting incident updates has been finished')
                incident_timeout_cur = self.incident_timeout

            if self.enable_asset and asset_timeout_cur <= 0:
                self.logger.info('getting assets from MDR..')
                self.mdr.access_token = self.update_access_token()
                self.get_assets()
                self.logger.info('getting assets has been finished')
                asset_timeout_cur = self.asset_timeout
            
            incident_timeout_cur = incident_timeout_cur - self.timeout
            asset_timeout_cur = asset_timeout_cur - self.timeout
            time.sleep(self.timeout)