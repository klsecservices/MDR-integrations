import requests
import json
import urllib.parse
import urllib3
import logging

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class KUMA_API:

    INCIDENT_CREATE_PATH = "/incidents/create"
    
    def __init__(self, url, api_token, ssl_cert):
        self.url = url + '/api/v2.1'
        headers = {
            'Authorization': f'Bearer {api_token}'
        }

        self.session = requests.Session()
        self.session.headers.update(headers)
        self.session.verify = ssl_cert
    
    def create_incident(self, incident_data):
        """
        Example:
        incident_data = {
            "name": "alert_name",
            "tenantID": "00000000-0000-0000-0000-000000000000",
            "description": "description of alert",
            "type": {},
            "priority": 1,
            "assigneeId": "00000000-0000-0000-0000-000000000000",
            "alerts": [
                {
                "id": "00000000-0000-0000-0000-000000000000"
                },
                {
                "id": "11111111-1111-1111-1111-111111111111"
                }
            ],
            "assets": [
                {
                "id": "00000000-0000-0000-0000-000000000000"
                },
                {
                "id": "11111111-1111-1111-1111-111111111111"
                }
            ],
            "accounts": [
                {
                "id": "00000000-0000-0000-0000-000000000000"
                },
                {
                "id": "11111111-1111-1111-1111-111111111111"
                }
            ],
            "availableTenants": [
                "00000000-0000-0000-0000-000000000000",
                "11111111-1111-1111-1111-111111111111"
            ]
        }
        """
        url = self.url + self.INCIDENT_CREATE_PATH
        result = self.session.post(url = url, json = incident_data)
        return result