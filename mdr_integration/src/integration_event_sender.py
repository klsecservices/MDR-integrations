import os
import time
import glob
import logging
import json
from typing import Optional, Dict, Any, List

from datetime import datetime
from urllib.parse import quote_plus
import socket
from contextlib import closing

class EventSender():
    
    # Const
    MAPPING_INCIDENT = {
        "incident_id":	        {"leef": "inc_id",	        "cef":"inc_id"},	  # "-MAfspsBq_r24TsN5-jl",
        "summary":	            {"leef": "summary",	        "cef":"summary"},	  # "Test",
        "priority":	            {"leef": "prio",	        "cef":"prio"},	  # "NORMAL",
        "status":	            {"leef": "status",	        "cef":"status"},	  # "On hold",
        "resolution":	        {"leef": "res",	            "cef":"res"},	  # "",
        "affected_hosts":	    {"leef": "aff_hs",	        "cef":"fiaff_hseld"},	  # [],
        #"affected_hosts_mappings":	{"leef": "aff_hs_m",	"cef":"aff_hs_m"},	  # [],
        "host_based_iocs":	    {"leef": "h_iocs",	        "cef":"h_iocs"},	  # [],
        "network_based_iocs":	{"leef": "net_iocs",	    "cef":"net_iocs"},	  # [],
        "detection_technology":	{"leef": "detect",	        "cef":"detect"},	  # "",
        "creation_time":	    {"leef": "cr_t",	        "cef":"cr_t"},	  # 1768219992478,
        "update_time":	        {"leef": "upd_t",	        "cef":"upd_t"},	  # 1768379938029,
        "attack_stage":	        {"leef": "stage",	        "cef":"stage"},	  # "",
        "mitre_tactics":	    {"leef": "tact",	        "cef":"tact"},	  # [],
        "mitre_techniques":	    {"leef": "tech",	        "cef":"tech"},	  # [],
        "description":	        {"leef": "desc",	        "cef":"desc"},	  # "test\n\n<!-- ваш комментарий -->",
        "incident_number":	    {"leef": "inc_n",	        "cef":"inc_n"},	  # 1336654,
        "client_description":	{"leef": "client_desc",	    "cef":"client_desc"},	  # "",
        "status_description":	{"leef": "stat_desc",	    "cef":"stat_desc"},	  # "",
        "origin":	            {"leef": "origin",	        "cef":"origin"},	  # "Service",
        "iocs":	                {"leef": "iocs",	        "cef":"iocs"},	  # [],
        "tenant_name":	        {"leef": "tenant",	        "cef":"tenant"},	  # "",
        "was_read":	            {"leef": "was_read",	    "cef":"was_read"},	  # true,
        "recommendations":	    {"leef": "rec",	            "cef":"rec"},	  # "",
        "client_comment":	    {"leef": "client_comm",	    "cef":"client_comm"},	  # ""
    }

    MAPPING_INCIDENT_DETAILS = {
        "incident_id":			    {"leef": "inc_id",		"cef":"inc_id"},	  # "-MAfspsBq_r24TsN5-jl",
        "summary":			        {"leef": "summary",		"cef":"summary"},	  # "Test",
        "priority":			        {"leef": "prio",		"cef":"prio"},	  # "NORMAL",
        "status":			        {"leef": "status",		"cef":"status"},	  # "On hold",
        "resolution":			    {"leef": "res",		    "cef":"res"},	  # "",
        "affected_hosts":			{"leef": "aff_hs",		"cef":"aff_hs"},	  # [],
        #"affected_hosts_mappings":			{"leef": "aff_hs_m", "cef":"aff_hs_m"},	  # [],
        "host_based_iocs":			{"leef": "h_iocs",		"cef":"h_iocs"},	  # [],
        "network_based_iocs":		{"leef": "net_iocs",	"cef":"net_iocs"},	  # [],
        "detection_technology":		{"leef": "detect",		"cef":"detect"},	  # "",
        "creation_time":			{"leef": "cr_t",		"cef":"cr_t"},	  # 1768219992478,
        "update_time":			    {"leef": "upd_t",		"cef":"upd_t"},	  # 1768379938029,
        "attack_stage":			    {"leef": "stage",		"cef":"stage"},	  # "",
        "mitre_tactics":			{"leef": "tact",		"cef":"tact"},	  # [],
        "mitre_techniques":			{"leef": "tech",		"cef":"tech"},	  # [],
        "description":			    {"leef": "desc",		"cef":"desc"},	  # "test\n\n<!-- ваш комментарий -->",
        "incident_number":			{"leef": "inc_n",		"cef":"inc_n"},	  # 1336654,
        "client_description":		{"leef": "client_desc",	"cef":"client_desc"},	  # "",
        "status_description":		{"leef": "stat_desc",	"cef":"stat_desc"},	  # "",
        "origin":			        {"leef": "origin",		"cef":"origin"},	  # "Service",
        "iocs":			            {"leef": "iocs",		"cef":"iocs"},	  # [],
        "tenant_name":			    {"leef": "tenant",		"cef":"tenant"},	  # "",
        "was_read":			        {"leef": "was_read",	"cef":"was_read"},	  # true,
        "recommendations":			{"leef": "rec",		    "cef":"rec"},	  # "",
        "client_comment":			{"leef": "client_comm",	"cef":"client_comm"},	  # ""
        "changed_at":			    {"leef": "devTime",		"cef":"devTime"},	  # 123
        "changed_by":			    {"leef": "usrName",		"cef":"usrName"},	  # qwe
        "operation":			    {"leef": "cat",		    "cef":"act"},	   # create
        "entity_type":              {"leef": "entity_type", "cef":"cat"},	   # create
    }

    MAPPING_INCIDENT_COMMENT = {
        "comment_id":	{"leef": "comm_id",		"cef":"comm_id"},	  # "1MBlsZsBq_r24TsNx9tW",
        "author_name":	{"leef": "author",		"cef":"author"},	  # "Security Team",
        "text":			{"leef": "text",		"cef":"text"},	  # "https://www.google.com/   - не ссылка",
        "creation_time":{"leef": "cr_t",		"cef":"cr_t"},	  # 1768207796052,
        "origin":		{"leef": "origin",		"cef":"origin"},	  # "Service",
        "was_read":		{"leef": "was_read",	"cef":"was_read"},	  # false
        "changed_at":	{"leef": "devTime",		"cef":"devTime"},	  # 123
        "changed_by":	{"leef": "usrName",		"cef":"usrName"},	  # qwe
        "operation":	{"leef": "cat",		    "cef":"act"},	   # create
        "entity_type":  {"leef": "entity_type", "cef":"cat"},	   # create
    }

    MAPPING_INCIDENT_RESPONSE = {
        "response_id":	{"leef": "resp_id",	"cef":"resp_id"},	  # "MDR_fc51163f-00a4-4d07-826e-bb92963bc856",
        "type":			{"leef": "type",	"cef":"type"},	  # "RUN_SCRIPT",
        "details":		{"leef": "details",	"cef":"details"},	  # { "file_path": "", "file_size_limit": 0 },
        "parameters":	{"leef": "params",	"cef":"params"},	  # { "interpreter": "powershell", "workingDirectory": "C:\\Windows", "interpreterParameters": null },
        "asset_id":		{"leef": "asset_id","cef":"asset_id"},	  # "0xe5afd1145ed019ed14e695a4ab8811dd",
        "status":		{"leef": "status",	"cef":"status"},	  # "Declined",
        "comment":		{"leef": "comm",	"cef":"comm"},	  # "Automatically rejected, because the task timeout has expired",
        "description":	{"leef": "desc",	"cef":"desc"},	  # "",
        "creation_time":{"leef": "cr_t",	"cef":"cr_t"},	  # 1769093340785,
        "update_time":	{"leef": "upd_t",	"cef":"upd_t"},	  # 1769093948832,
        "was_read":		{"leef": "was_read","cef":"was_read"},	  # false
        "changed_at":	{"leef": "devTime",	"cef":"devTime"},	  # 123
        "changed_by":	{"leef": "usrName",	"cef":"usrName"},	  # qwe
        "operation":	{"leef": "cat",		"cef":"act"},	   # create
        "entity_type":  {"leef": "entity_type", "cef":"cat"},	   # create
    }

    CONSUMER_NAME = 'event_sender'

    def __init__(self, config):
        dst_host = config['event_sender'].get('destination_host')
        dst_port = int(config['event_sender'].get('destination_port'))
        self.server_address = (dst_host, dst_port)
        self.protocol = config['event_sender'].get('protocol', 'tcp')
        self.format = config['event_sender'].get('format', 'raw').lower()
        self.syslog_header = config['event_sender'].get('syslog_header', False)
        self.hostname = socket.getfqdn() or 'unknown'
        self.incident_timeout = config['event_sender']['modules']['incident'].get('timeout', 60)
        self.timeout = 10  # default value for infinite loop
        self.data_dir = config.get('data_dir', 'data')
        self.token_dir = config.get('token_dir', 'conf')
        self.state_file = f'{self.token_dir}/.processed_{self.CONSUMER_NAME}'
        self.processed_files = self.load_processed_state()
        self.enable_incident = config['event_sender']['modules']['incident'].get('enable', False)
        self.enable_asset = config['event_sender']['modules']['asset'].get('enable', False)


    def load_processed_state(self):
        try:
            with open(self.state_file, 'r') as f:
                return set(json.load(f))
        except FileNotFoundError:
            return set()


    def save_processed_state(self):
        with open(self.state_file, 'w') as f:
            json.dump(sorted(self.processed_files), f)


    def read_file(self, filename):
        with open(filename, 'r') as f:
            data = json.load(f)
        return data


    def scan_folder(self):
        files = glob.glob(f'{self.data_dir}/*.json')
        files = [f for f in files if os.path.basename(f) not in self.processed_files]
        self.logger.info(f'Found {len(files)} file(s) to process')
        return files

    def send_to(self, sock, events):
        if self.protocol.lower() == 'tcp':
            self.send_TCP(sock, events)
        elif self.protocol.lower() == 'udp':
            self.send_UDP(sock, events)
        else:
            raise ValueError('"protocol" option should be in ["tcp", "udp"]')


    def send_TCP(self, sock, events):
        sock.connect(self.server_address)
        for event in events:
            sock.send(event.encode() + b'\n')

    def send_UDP(self, sock, events):
        for event in events:
            sock.sendto(event.encode() + b'\n', self.server_address)
    
    def process_updates(self):

        files = self.scan_folder()

        events = []
        matched_files = []

        for update_file in files:
            if 'new_incident' in update_file:
                event_type = 'new_incident'
            elif 'incident_updates' in update_file:
                event_type = 'incident_updates'
            else:
                continue

            event_data = self.read_file(update_file)
            if isinstance(event_data, list):
                for e in event_data:
                    event = self.build_event(e, event_type)
                    events.append(event)
            elif isinstance(event_data, dict):
                event = self.build_event(event_data, event_type)
                events.append(event)
            matched_files.append(update_file)

        if events:
            with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
                self.send_to(sock, events)

        for update_file in matched_files:
            self.set_update_as_processed(update_file)


    def process_assets(self):
        raise ValueError('Assets forwarding is under development, please disable this feature in config... sorry')

    def build_event(self, event_data, event_type):
        if self.format == 'raw':
            return self.build_format_raw(event_data)
        elif self.format == 'leef':
            return self.build_event_format(event_data, event_type, self.format)
        elif self.format == 'cef':
            return self.build_event_format(event_data, event_type, self.format)
    

    def build_format_raw(self, event):
        return json.dumps(event)
    
    def event_get_syslog_header(self):
        timestamp = datetime.now()
        hostname = self.hostname
        # RFC 5424: «Mmm dd HH:MM:SS hostname»
        ts = timestamp.strftime("%b %d %H:%M:%S") if timestamp else ""
        syslog_header = f"{ts} {hostname} "
        return syslog_header

    def event_get_cef_header(self, event_type):
        vendor = "Kaspersky"
        product = "MDR"
        product_version = "1.0"
        signature_id = ""
        name = event_type
        severity = "1"
        # build CEF header
        header = f"CEF:1.0|{vendor}|{product}|{product_version}|{signature_id}|{name}|{severity}|"
        return header

    def event_get_leef_header(self, event_type):
        vendor = "Kaspersky"
        product = "MDR"
        product_version = "1.0"
        # build LEEF header
        header = f"LEEF:1.0|{vendor}|{product}|{product_version}|{event_type}|"
        return header

    def event_cef_quoting(self, data):
        data = data.replace('\\', '\\\\').replace('=', '\\=')
        return data

    def event_leef_quoting(self, data):
        # URL encoding
        data = quote_plus(str(data))
        return data

    def build_event_format(self, event, event_type, event_format):
        if event_format == "leef":
            header = self.event_get_leef_header(event_type)
            quoting_func = self.event_leef_quoting
            format_sep = '\t'
        elif event_format == "cef":
            header = self.event_get_cef_header(event_type)
            quoting_func = self.event_cef_quoting
            format_sep = ' '
        else:
            raise ValueError('event format is invalid')
        
        # key value part
        kv_parts = []
        mapping = {}
        if event_type == 'new_incident':
            mapping = self.MAPPING_INCIDENT
        elif event_type == 'incident_updates':
            operation_type = {
                'incident_details': self.MAPPING_INCIDENT_DETAILS,
                'incident_comment': self.MAPPING_INCIDENT_COMMENT,
                'incident_response': self.MAPPING_INCIDENT_RESPONSE
            }
            for ot_type, ot_mapping in operation_type.items():
                if ot_type in event['entity']:
                    mapping = ot_mapping
                    event['entity'][ot_type]['entity_type'] = ot_type
                    event['entity'][ot_type]['changed_at'] = event['changed_at']
                    event['entity'][ot_type]['changed_by'] = event['changed_by']
                    event['entity'][ot_type]['operation'] = event['operation']
                    event = event['entity'][ot_type]
                    break
        for mdr_key, format_key in mapping.items():
            value = event[mdr_key]
            if isinstance(value, int) or isinstance(value, bool):
                value = str(value)
            elif isinstance(value, list) or isinstance(value, dict):
                value = json.dumps(value)
            else:
                value = str(value)
            value = quoting_func(value)
            kv_parts.append(f"{format_key[event_format]}={value}")

        payload = f"{format_sep}".join(kv_parts)

        message = f"{header}{payload}"

        if self.syslog_header:
            message = self.event_get_syslog_header() + message
            
        return message


    def set_update_as_processed(self, filename):
        self.processed_files.add(os.path.basename(filename))
        self.save_processed_state()


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
                self.process_assets()
                self.logger.info('MDR assets are processed')
                asset_timeout_cur = self.enable_asset
            
            incident_timeout_cur = incident_timeout_cur - self.timeout
            asset_timeout_cur = asset_timeout_cur - self.timeout
            time.sleep(self.timeout)
