import requests
from typing import Optional, Dict, Any, List
import os
import json


class MDRConsole():

    ASSETS_COUNT_PATH = "assets/count"
    ASSETS_DETAILS_PATH = "assets/details"
    ASSETS_LIST_PATH = "assets/list"
    ATTACHMENTS_DOWNLOAD_PATH = "attachments/download"
    ATTACHMENTS_LIST_PATH = "attachments/list"
    ATTACHMENTS_UPLOAD_PATH = "attachments/upload"
    COMMENTS_CREATE_PATH = "comments/create"
    COMMENTS_DELETE_PATH = "comments/delete"
    COMMENTS_LIST_PATH = "comments/list"
    INCIDENTS_COUNT_PATH = "incidents/count"
    INCIDENTS_DETAILS_PATH = "incidents/details"
    INCIDENTS_LIST_PATH = "incidents/list"
    RESPONSE_UPDATE_PATH = "response/update"
    RESPONSES_LIST_PATH = "responses/list"
    RESPONSES_UPDATE_PATH = "responses/update"
    SESSION_CONFIRM_PATH = "session/confirm"
    INCIDENT_CLOSE_PATH = "incidents/close"

    def __init__(self, api_url: str, client_id: str, refresh_token: Optional[str] = None, access_token: Optional[str] = None, ssl_cert: Optional[str] = False) -> None:
        self.api_url = api_url
        self.client_id = client_id
        self.ssl_cert = ssl_cert
        if refresh_token:
            self.access_token, self.refresh_token = self.get_access_token(refresh_token)
        elif access_token:
            self.access_token = access_token
    

    def post(self, *, path: str, json_data: Dict[str, Any], headers: Optional[Dict[str, str]] = None, download: Optional[bool] = False) -> Dict:
        kwargs = {
            "url": f"{self.api_url}/{self.client_id}/{path}",
            "json": json_data,
            "verify": self.ssl_cert,
        }
        if headers is not None:
            kwargs["headers"] = headers
        #print(path)
        resp = requests.post(**kwargs)
        #print(kwargs)

        if resp.status_code == 200:
            if download:
                return resp.content
            return resp.json()
        else:
            raise Exception(f'Request to {path}, HTTP code {str(resp.status_code)} - {resp.text}')


    def get_access_token(self, refresh_token: str) -> str:
        result = self.post(path = self.SESSION_CONFIRM_PATH, json_data = {"refresh_token": refresh_token})
        access_token = result["access_token"]
        refresh_token = result["refresh_token"]
        return access_token, refresh_token


    def get_auth_header(self, access_token: str) -> Dict[str, str]:
        return {"Authorization": f"Bearer {access_token}"}


    def get_assets_count(self, **kwargs) -> Dict[str, Any]:
        """
        Example:
        kwargs = {
            "domain": "domain.ru",
            "host_names": ["HOST-NAME"],
            "is_isolated": True,
            "max_first_seen": get_now(),  # integer
            "max_last_seen": get_now(),  # integer
            "min_first_seen": 151964050900,  # integer
            "min_last_seen": 151964050900,  # integer
            "network_interface": "255.255.255.255",
            "os_version": "Mac OS X",
            "product": "KES",
            "related_incidents_ids": ["123456"],
            "search_phrase": "search_request_string",
            "statuses": ["BLOCKED"],  # "BLOCKED" "CRITICAL" "OK" "WARNING"
            "tenants_names": ["Tenant name"]
        }
        """
        headers = self.get_auth_header(self.access_token)
        result = post(path = self.ASSETS_COUNT_PATH, json_data = kwargs, headers=headers)
        return result


    def get_assets_details(self, asset_id: str, **kwargs) -> Dict[str, Any]:
        """
        Example:
        kwargs = {
            "asset_id": "0xEFBB3CE475B9AF2DDD4F73C48531234F",  # required
            "fields": ["asset_id", "domain", "first_seen", "host_name", "installed_product_info", "isolation", "isolation_task_id", "ksc_host_id", "last_seen", "network_interfaces", "os_version", "product_map", "status", "status_reasons", "tenant_name"]
        }
        """
        headers = self.get_auth_header(self.access_token)
        kwargs['asset_id'] = asset_id
        result = self.post(path = self.ASSETS_DETAILS_PATH, json_data = kwargs, headers=headers)
        return result


    def get_assets_list(self, **kwargs) -> Dict[str, Any]:
        """
        Example:
        kwargs = {
            "domain": "domain.ru",
            "fields": ["asset_id"],
            "host_names": ["HOST-NAME"],
            "is_isolated": True,
            "max_first_seen": get_now(),  # integer
            "max_last_seen": get_now(),  # integer
            "min_first_seen": 1519640509000,  # integer
            "min_last_seen": 1519640509000,  # integer
            "network_interface": "255.255.255.255",
            "os_version": "Mac OS X",
            "page": 1,
            "page_size": 100,
            "product": "KIS",
            "related_incidents_ids": ["123456"],
            "search_phrase": "search_request_string",
            "sort": "first_seen:asc",
            "statuses": ["BLOCKED"],  # "BLOCKED" "CRITICAL" "OK" "WARNING"
            "tenants_names": ["Tenant name"]
        }
        """
        headers = self.get_auth_header(self.access_token)
        result = self.post(path = self.ASSETS_LIST_PATH, json_data = kwargs, headers=headers)
        return result


    def attachments_download(self, attachment_id: str) -> Dict[str, Any]:
        """
        Example:
        kwargs = {
            "attachment_id": "2NJMGXkBNGNeZ5iut24S"  # required
        }
        """
        headers = self.get_auth_header(self.access_token)
        result = self.post(path = self.ATTACHMENTS_DOWNLOAD_PATH, json_data = {'attachment_id': attachment_id}, headers=headers, download = True)
        return result


    def get_attachments_list(self, incident_id: str, **kwargs) -> Dict[str, Any]:
        """
        Example:
        kwargs = {
            "fields": ["attachment_id", "author_name", "caption", "creation_time", "file_size", "full_name", "link", "origin", "was_read"],  
            "incident_id": "2NJMGXkBNGNeZ5iut24S",  # required
            "markdown_to_html": True
        }
        """
        headers = self.get_auth_header(self.access_token)
        kwargs['incident_id'] = incident_id
        result = self.post(path = self.ATTACHMENTS_LIST_PATH, json_data = kwargs, headers=headers)
        return result


    def attachments_upload(self, **kwargs) -> Dict[str, Any]:
        """
        Example:
        kwargs = {
            "file": "filepath", 
            "meta": {
                "caption": "comment_string",
                "incident_id": "2NJMGXkBNGNeZ5iut24S",  # required
            }
            
        }
        """
        path = self.ATTACHMENTS_UPLOAD_PATH
        headers = self.get_auth_header(self.access_token)
        resp = requests.post(
            url = f"{self.api_url}/{self.client_id}/{path}",
            headers = headers,
            files = {
                'file': (
                    os.path.basename(kwargs['file']),
                    open(kwargs['file'], 'rb'),
                    'application/octet-stream'
                )
            },
            data = {
                'meta': json.dumps(kwargs['meta'])
            }
        )
        if resp.status_code == 200:
            return resp.json()
        else:
            raise Exception(f'Request to {path}, HTTP code {str(resp.status_code)} - {resp.text}')


    def comments_create(self, incident_id: str, text: str, **kwargs) -> Dict[str, Any]:
        """
        Example:
        kwargs = {
            "incident_id": "2NJMGXkBNGNeZ5iut24S",  # required
            "markdown_to_html": True, 
            "text": "comment_text"
        }
        """
        headers = self.get_auth_header(self.access_token)
        kwargs['incident_id'] = incident_id
        kwargs['text'] = text
        result = self.post(path = self.COMMENTS_CREATE_PATH, json_data = kwargs, headers=headers)
        return result


    def comments_delete(self, comment_id: str, **kwargs) -> Dict[str, Any]:
        """
        Example:
        kwargs = {
            "comment_id": "2NJMGXkBNGNeZ5iut24S"  # required
        }
        """
        headers = self.get_auth_header(self.access_token)
        kwargs['comment_id'] = comment_id
        result = self.post(path = self.COMMENTS_DELETE_PATH, json_data = kwargs, headers=headers)
        return result


    def get_comments_list(self, incident_id: str, **kwargs) -> Dict[str, Any]:
        """
        Example:
        kwargs = {
            "fields": ["author_name", "comment_id", "creation_time", "origin", "text", "was_read"], 
            "incident_id": "2NJMGXkBNGNeZ5iut24S",  # required
            "markdown_to_html": True
        }
        """
        headers = self.get_auth_header(self.access_token)
        kwargs['incident_id'] = incident_id
        result = self.post(path = self.COMMENTS_LIST_PATH, json_data = kwargs, headers=headers)
        return result


    def get_incidents_count(self, **kwargs) -> Dict[str, Any]:
        """
        Example:
        kwargs = {
            "affected_hosts": ["HOST-NAME:0xEFBB3CE475B9AF2DDD4F73C48531234F"],
            "asset_ids": ["0xEFBB3CE475B9AF2DDD4F73C48531234F"],
            "detection_technologies": ["KATA"],
            "max_creation_time": get_now(),
            "max_update_time": get_now(),
            "min_creation_time": 1519640509000,
            "min_update_time": 1519640509000,
            "mitre_tactics": ["Collection", "Command and control", "Credential access", "Defense evasion", "Discovery", "Execution", "Exfiltration", "Impact", "Initial access", "Lateral movement", "Persistence", "Privilege escalation"],
            "mitre_techniques": ["T1134: Access Token Manipulation"],
            "priorities": ["HIGH"],
            "resolutions": ["False positive"],
            "response_statuses": ["Confirmed"],
            "response_types": ["File"],
            "search_phrase": "search_request_string",
            "statuses": ["Closed"],
            "tenants_names": ["Tenant name"],
        }
        """
        headers = self.get_auth_header(self.access_token)
        result = self.post(path = self.INCIDENTS_COUNT_PATH, json_data = kwargs, headers=headers)
        return result


    def get_incidents_details(self, incident_id: str, **kwargs) -> Dict[str, Any]:
        """
        Example:
        kwargs = {
            "fields": ["affected_hosts"], 
            "incident_id": "2NJMGXkBNGNeZ5iut24S",  # required
            "markdown_to_html": True
        }
        """
        headers = self.get_auth_header(self.access_token)
        kwargs['incident_id'] = incident_id
        result = self.post(path = self.INCIDENTS_DETAILS_PATH, json_data = kwargs, headers=headers)
        return result


    def get_incidents_list(self, **kwargs) -> Dict[str, Any]:
        """
        Example:
        kwargs = {
            "affected_hosts": ["HOST-NAME:0xEFBB3CE475B9AF2DDD4F73C48531234F"],
            "asset_ids": ["0xEFBB3CE475B9AF2DDD4F73C48531234F"],
            "detection_technologies": ["KATA"],
            "fields": ["affected_hosts"],
            "markdown_to_html": True,
            "max_creation_time": get_now(),  #integer
            "max_update_time": get_now(),  #integer
            "min_creation_time": 1519640509000,  #integer
            "min_update_time": 1519640509000,  #integer
            "mitre_tactics": ["Collection", "Command and control", "Credential access", "Defense evasion", "Discovery", "Execution", "Exfiltration", "Impact", "Initial access", "Lateral movement", "Persistence", "Privilege escalation"],
            "mitre_techniques": ["T1134: Access Token Manipulation"],
            "page": 1,
            "page_size": 100,
            "priorities": ["HIGH"],
            "resolutions": ["False positive"],
            "response_statuses": ["Confirmed"],
            "response_types": ["File"],
            "search_phrase": "search_request_string",
            "sort": "creation_time:asc",
            "statuses": ["Closed"],
            "tenants_names": ["Tenant name"],
        }
        """
        headers = self.get_auth_header(self.access_token)
        result = self.post(path = self.INCIDENTS_LIST_PATH, json_data = kwargs, headers=headers)
        return result


    def response_update(self, comment: str, response_id: str, status: str, **kwargs) -> Dict[str, Any]:
        """
        Example:
        kwargs = {
            "comment": "comment_text",  # required
            "response_id": "2NJMGXkBNGNeZ5iut24S",  # required 
            "status": "Confirmed"  # required
        }
        """
        headers = self.get_auth_header(self.access_token)
        kwargs['comment'] = comment
        kwargs['response_id'] = response_id
        kwargs['status'] = status
        result = self.post(path = self.RESPONSE_UPDATE_PATH, json_data = kwargs, headers=headers)
        return result


    def get_responses_list(self, incident_id: str, **kwargs) -> Dict[str, Any]:
        """
        Example:
        kwargs = {
            "fields": ["asset_id"], 
            "incident_id": "2NJMGXkBNGNeZ5iut24S",  # required
            "page": 1, 
            "page_size": 1
        }
        """
        headers = self.get_auth_header(self.access_token)
        kwargs['incident_id'] = incident_id
        result = self.post(path = self.RESPONSES_LIST_PATH, json_data = kwargs, headers=headers)
        return result


    def responses_update(self, comment: str, responses_ids: List[str], status: str, **kwargs) -> Dict[str, Any]:
        """
        Example:
        kwargs = {
            "comment": "comment_text", 
            "responses_ids": ["2NJMGXkBNGNeZ5iut24S"], 
            "status": "Confirmed"
        }
        """
        headers = self.get_auth_header(self.access_token)
        kwargs['comment'] = comment
        kwargs['responses_ids'] = responses_ids
        kwargs['status'] = status
        result = self.post(path = self.RESPONSES_UPDATE_PATH, json_data = kwargs, headers=headers)
        return result


    def close_incident(self, incident_id: str, resolution_status: str, summary: str) -> Dict[str, Any]:
        """
        Example:
        kwargs = {
            'incident_id': "ov2IOoIBVb6SRTN83Eis",
            'resolution_status': 'FALSE_POSITIVE',
            'summary': 'test'
        }
        """
        headers = self.get_auth_header(self.access_token)
        kwargs = {}
        kwargs['incident_id'] = incident_id
        kwargs['resolution_status'] = resolution_status
        kwargs['summary'] = summary
        result = self.post(path = self.INCIDENT_CLOSE_PATH, json_data = kwargs, headers=headers)
        return result


def main():
    mdr = MDRConsole(api_url = 'qwe', client_id = 'qwe', refresh_token = 'qwe')

if __name__ == '__main__':
    main()