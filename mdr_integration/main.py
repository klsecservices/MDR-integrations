
import os
import pathlib
import yaml
import time
import logging
import logging.config
import logging.handlers
import multiprocessing


#from src.mdr_api import MDRConsole
from src.token_updater import TokenUpdater
from src.mdr_sync import MDRSync
#from src.integration_thehive import TheHive
from src.logger import MDRLogger

WORK_DIR = os.path.dirname(os.path.abspath(__file__))
with open(f'{WORK_DIR}/conf/config.yml', 'r') as f:
    config = yaml.safe_load(f)
API_URL = config.get('api_url')
CLIENT_ID = config.get('client_id')
SSL_CERT = config.get('ssl_cert', True)
PERIOD = config['token_updater'].get('period')

config['token_dir'] = f"{WORK_DIR}/{config.get('token_dir', 'conf')}"
config['data_dir'] = f"{WORK_DIR}/{config.get('data_dir', 'conf')}"
config['logging']['log_dir'] = f"{WORK_DIR}/{config['logging'].get('log_dir', 'log')}"
if config.get('ssl_cert') not in [True, False]:
    config['ssl_cert'] = f"{WORK_DIR}/{config.get('ssl_cert', 'conf/mdr.pem')}"

temp_files = ['.access_token', '.refresh_token', '.last_check']
for temp_file in temp_files:
    if not pathlib.Path(f"{config['token_dir']}/{temp_file}").is_file():
        open(f"{config['data_dir']}/{temp_file}", 'w').close()


def process_logging_configurer(queue):
    h = logging.handlers.QueueHandler(queue)  # Just the one handler needed
    root = logging.getLogger()
    root.addHandler(h)
    # send all messages, for demo; no other level or filter logic applied.
    root.setLevel(logging.DEBUG)

def main():
    # Init Logger
    logging_config = config.get('logging')
    logging_queue = multiprocessing.Queue(-1)
    mdr_logger = MDRLogger()
    logging_listener = multiprocessing.Process(target=mdr_logger.run, args=(logging_queue, logging_config))
    logging_listener.start()

    process_logging_configurer(logging_queue)
    logger = logging.getLogger(__name__)
    logger.info('MDR Integration service is starting..')

    # Run automatic token updater
    token_updater = TokenUpdater(config)
    #token_updater.run()
    process_token_updater = multiprocessing.Process(target = token_updater.run, args=(logging_queue, process_logging_configurer))

    mdr_sync = MDRSync(config)
    #mdr_sync.run()
    process_mdr_sync = multiprocessing.Process(target = mdr_sync.run, args=(logging_queue, process_logging_configurer))

    #the_hive = TheHive(config)
    #the_hive.run()
    #process_the_hive = multiprocessing.Process(target = the_hive.run)

    process_token_updater.start()
    time.sleep(5)
    process_mdr_sync.start()
    time.sleep(5)
    #process_the_hive.start()

    logger.info('MDR Integration service started..')

if __name__ == '__main__':
    main()