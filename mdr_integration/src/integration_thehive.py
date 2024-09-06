import glob
import os
import yaml
import json
import time
import uuid
from typing import Optional, Dict, Any, List, Union

from thehive4py.api import TheHiveApi
from thehive4py.query import And, Eq
from thehive4py.models import Alert, AlertArtifact, CustomFieldHelper
from thehive4py.models import Case, CaseObservable, CaseTask, CaseObservable, CaseTaskLog
from thehive4py.exceptions import AlertException, CaseException

from src.mdr_api import MDRConsole
from src.logger import MDRLogger

class TheHive():

    # Const
    priority_mapping = {
        'LOW': 1,
        'NORMAL': 2,
        'HIGH': 3,
        '': 4
    }

    resolution_mapping = {
        'False positive': 'FalsePositive',
        'True positive': 'TruePositive'
    }

    def __init__(self, config: Dict[str, Any]) -> None:
        logging_config = config.get('logging')
        self.logger = MDRLogger(config = logging_config, name = self.__class__.__name__).getLogger()
        api_url = config['thehive'].get('api_url')
        api_key = config['thehive'].get('api_key')
        ssl_cert = config['thehive'].get('ssl_cert')
        self.period = config['thehive'].get('period', 60)
        self.data_dir = config.get('data_dir', 'data')
        self.api = TheHiveApi(api_url, api_key)
        self.logger.info('initialized')


    def scan_folder(self):
        files = glob.glob(f'{self.data_dir}/*.json')
        self.logger.info(f'Found {len(files)} file(s) to process')
        return files

    
    def process_updates(self) -> None:
        files = self.scan_folder()
        for update_file in files:
            with open(update_file, 'r') as f:
                data = json.load(f)
            if 'new_incident' in update_file:
                if self.create_case(data):
                    self.set_update_as_processed(update_file)
            if 'update_incident' in update_file:
                if self.update_case(data):
                    self.set_update_as_processed(update_file)
            if 'new_attachment' in update_file:
                if self.add_attachment(data):
                    self.set_update_as_processed(update_file)
            if 'new_comment' in update_file:
                if self.add_comment(data):
                    self.set_update_as_processed(update_file)
            if 'new_response' in update_file:
                if self.create_response_task(data):
                    self.set_update_as_processed(update_file)        

    def create_response_task(self, data: Dict[str, Any]) -> bool:
        incident_id = data['incident_id']
        # Find the case
        query = And(
            Eq('customFields.mdr-incident-id.string', incident_id)
        )
        response = self.api.find_cases(query = query, sort = ['-createdAt'], range = 'all')
        if response.status_code != 200:
            self.logger.error(f'find_cases has been failed with status code {response.status_code} - {response.text}')
            return False 
        if len(response.json()) > 1:
            self.logger.error(f'found more than 1 cases by filter: {incident_id}: {response.text}')
            return False
        if len(response.json()) == 0:
            self.logger.error(f'Not found any cases by filter: {incident_id}: {response.text}')
            return False
        case = response.json()[0]
        
        # Build the task
        response_data = data['responses'][0]
        response_type = response_data['type']
        response_id = response_data['response_id']
        parameters = response_data['parameters']
        description = response_data['description']
        case_tasks = CaseTask(
            id = None,
            group = 'Response',
            title = response_type,
            description = f'**ID**: {response_id}  \n**Details**:  \n```\n{json.dumps(parameters, indent = 2)}\n```  \n**Comment**: {description}',
            status = 'InProgress',
            flag = False,
        )

        # Create Task
        try:
            response = self.api.create_case_task(case['id'], case_tasks)
            #print(response.status_code, json.dumps(response.json(), indent=2, sort_keys=True))
            if response.status_code != 201:
                self.logger.error(f'task creating has been failed with status code {response.status_code} - {response.text}')
                return False
            return True
        except CaseException as e:
            self.logger.exception('Task create error')

    def create_case(self, data: Dict[str, Any]) -> bool:
        # Add Task
        case_tasks = [
            CaseTask(
                id = None,
                title = 'MDR Response',
                description = 'The task to communicate with the MDR Team',
                status = 'InProgress',
                flag = False,
            )
        ]
        # Add Custom fields
        '''
        customFields = CustomFieldHelper()\
            .add_string('business-unit', 'HR')\
            .add_string('business-impact', 'HIGH')\
            .add_date('occur-date', int(time.time())*1000)\
            .add_number('cvss', 6)\
            .build()
        '''
        customFields = CustomFieldHelper().add_string('mdr-incident-id', data['incident_id']).build()
        # Build the alert
        case = Case(
            title = data['summary'],
            description = data['description'],
            tlp = 2,
            pap = 2,
            severity = self.priority_mapping.get(data['priority'], ''),
            flag = False,
            tags = ['MDR'],
            template = None,
            customFields = customFields,
            tasks = case_tasks
        )
        # Add observables
        case_observables = []
        for affected_host in data['affected_hosts_mappings']:
            case_observables.append( 
                CaseObservable(
                    id = None,
                    dataType = 'hostname', 
                    message = affected_host['host_id'],
                    tlp = 2,
                    pap = 2,
                    ioc = False,
                    tags = [],
                    data = affected_host['host_name']
                ) 
            )

        try:
            response = self.api.create_case(case)
            #print(response.status_code, json.dumps(response.json(), indent=4, sort_keys=True))
            if response.status_code != 201:
                self.logger.error(f'case creating has been failed with status code {response.status_code} - {response.text}')
                return False
            for case_observable in case_observables:
                response_obs = self.api.create_case_observable(response.json()['id'], case_observable)
                #print(response.status_code, json.dumps(response.json(), indent=4, sort_keys=True))
                if response_obs.status_code != 201:
                    self.logger.error(f'observable creating has been failed with status code {response_obs.status_code} - {response_obs.text}')
            return True
        except CaseException as e:
            self.logger.exception('Case create error')
        return False

    def update_case(self, data: Dict[str, Any]) -> bool:
        incident_id = data['incident_id']
        # Find the case
        query = And(
            Eq('customFields.mdr-incident-id.string', incident_id)
        )
        response = self.api.find_cases(query = query, sort = ['-createdAt'], range = 'all')
        if response.status_code != 200:
            self.logger.error(f'case finding has been failed with status code {response.status_code} - {response.text}')
            return False 
        if len(response.json()) > 1:
            self.logger.error(f'found more than 1 cases by filter: {incident_id}: {response.text}')
            return False
        if len(response.json()) == 0:
            self.logger.error(f'Not found any cases by filter: {incident_id}: {response.text}')
            return False
        case = response.json()[0]
        # Update Custom fields
        '''
        case['customFields']['mdr-incident-id']['string'] = 'qwe'
        '''
        # Update fields
        case = Case(json = case)
        case.title = data['summary']
        case.description = data['description']
        fields = ['title', 'description']

        if data['status'] == 'Closed':
            case.resolutionStatus = self.resolution_mapping[data['resolution']]
            case.status = 'Resolved'
            case.summary = data['status_description']
            fields.extend(['resolutionStatus', 'status', 'summary'])

        try:
            response = self.api.update_case(case, fields)
            #print(response.status_code, json.dumps(response.json(), indent=4, sort_keys=True))
            if response.status_code == 200:
                return True
        except CaseException as e:
            self.logger.exception('Case update error')
        self.logger.error(f'case updating has been failed with status code {response.status_code} - {response.text}')
        return False

    def add_attachment(self, data: Dict[str, Any]) -> None:
        incident_id = data['incident_id']
        # Find the case
        query = And(
            Eq('customFields.mdr-incident-id.string', incident_id)
        )
        response = self.api.find_cases(query = query, sort = ['-createdAt'], range = 'all')
        if response.status_code != 200:
            self.logger.error(f'find_cases has been failed with status code {response.status_code} - {response.text}')
            return False 
        if len(response.json()) > 1:
            self.logger.error(f'found more than 1 cases by filter: {incident_id}: {response.text}')
            return False
        if len(response.json()) == 0:
            self.logger.error(f'Not found any cases by filter: {incident_id}: {response.text}')
            return False
        case = response.json()[0]
        # Find the task
        response = self.api.get_case_tasks(case['id'])
        if response.status_code != 200:
            self.logger.error(f'get_case_tasks has been failed with status code {response.status_code} - {response.text}')
            return False 
        if len(response.json()) == 0:
            return False
        for task in response.json():
            if task['title'] == 'MDR Response':
                break
        #print(task)
        # Build case task log
        caption = data['attachments'][0]['caption']
        link = data['attachments'][0]['link']
        author_name = data['attachments'][0]['author_name']
        filename = data['attachments'][0]['full_name']
        attachment_id = data['attachments'][0]['attachment_id']
        filepath = f"{self.data_dir}/files/{attachment_id}_{filename}"
        if os.path.exists(filepath):
            case_task_log = CaseTaskLog(
                message = f'{author_name}\n> {caption}',
                file = filepath
            )
        else:
            case_task_log = CaseTaskLog(
                message = f'{author_name}\n> {caption}  \n  \n[{filename}]({link})'
            )

        # Create case task log
        #response = self.api.create_task_log(task['id'], case_task_log)
        try:
            response = self.api.create_task_log(task['id'], case_task_log)
            #print(response.status_code, json.dumps(response.json(), indent=4, sort_keys=True))
            if response.status_code == 201:
                return True
        except CaseException as e:
            self.logger.exception('Case task log creation error')
        self.logger.error(f'Case task log creation has been failed with status code {response.status_code} - {response.text}')
        return False

    def add_comment(self, data: Dict[str, Any]) -> None:
        incident_id = data['incident_id']
        # Find the case
        query = And(
            Eq('customFields.mdr-incident-id.string', incident_id)
        )
        response = self.api.find_cases(query = query, sort = ['-createdAt'], range = 'all')
        if response.status_code != 200:
            self.logger.error(f'find_cases has been failed with status code {response.status_code} - {response.text}')
            return False 
        if len(response.json()) > 1:
            self.logger.error(f'found more than 1 cases by filter: {incident_id}: {response.text}')
            return False
        if len(response.json()) == 0:
            self.logger.error(f'Not found any cases by filter: {incident_id}: {response.text}')
            return False
        case = response.json()[0]
        # Find the task
        response = self.api.get_case_tasks(case['id'])
        if response.status_code != 200:
            self.logger.error(f'get_case_tasks has been failed with status code {response.status_code} - {response.text}')
            return False 
        if len(response.json()) == 0:
            return False
        for task in response.json():
            if task['title'] == 'MDR Response':
                break
        #print(task)
        # Build case task log
        text = data['comments'][0]['text']
        author_name = data['comments'][0]['author_name']
        case_task_log = CaseTaskLog(
            message = f'{author_name}\n> {text}'
        )
        # Create case task log
        try:
            response = self.api.create_task_log(task['id'], case_task_log)
            #print(response.status_code, json.dumps(response.json(), indent=4, sort_keys=True))
            if response.status_code == 201:
                return True
        except CaseException as e:
            self.logger.exception('Case task log creation error')
        self.logger.error(f'Case task log creation has been failed with status code {response.status_code} - {response.text}')
        return False


    def set_update_as_processed(self, filename: str) -> None:
        os.rename(filename, f'{filename}.processed')


    def run(self) -> None:
        self.logger.info('started')
        while True:
            self.logger.info('starting to process new updates..')
            self.process_updates()
            self.logger.info('processing updates finished')
            time.sleep(self.period)