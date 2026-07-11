
import os
import pathlib
import yaml
import time
import logging
import logging.config
import logging.handlers
import multiprocessing

from src.logger import MDRLogger


WORK_DIR = os.path.dirname(os.path.abspath(__file__))
with open(f'{WORK_DIR}/conf/config.yml', 'r') as f:
    config = yaml.safe_load(f)

config['token_dir'] = f"{WORK_DIR}/{config.get('token_dir', 'conf')}"
config['data_dir'] = f"{WORK_DIR}/{config.get('data_dir', 'conf')}"
config['logging']['log_dir'] = f"{WORK_DIR}/{config['logging'].get('log_dir', 'log')}"

temp_files = ['.access_token', '.refresh_token', '.last_check']
for temp_file in temp_files:
    if not pathlib.Path(f"{config['token_dir']}/{temp_file}").is_file():
        open(f"{config['token_dir']}/{temp_file}", 'w').close()


def process_logging_configurer(queue):
    h = logging.handlers.QueueHandler(queue)  # Just the one handler needed
    root = logging.getLogger()
    root.addHandler(h)
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
    from src.token_updater import TokenUpdater
    token_updater = TokenUpdater(config)
    process_token_updater = multiprocessing.Process(target = token_updater.run, args=(logging_queue, process_logging_configurer))
    time.sleep(2)
    process_token_updater.start()

    
    if config['mdr_sync']['modules']['incident']['enable'] or config['mdr_sync']['modules']['asset']['enable']:
        from src.mdr_sync import MDRSync
        mdr_sync = MDRSync(config)
        process_mdr_sync = multiprocessing.Process(target = mdr_sync.run, args=(logging_queue, process_logging_configurer))
        time.sleep(2)
        process_mdr_sync.start()

    if config['kuma']['modules']['incident']['enable'] or config['kuma']['modules']['asset']['enable']:
        from src.integration_kuma import KUMA
        kuma_intergation = KUMA(config)
        process_kuma_intergation = multiprocessing.Process(target = kuma_intergation.run, args=(logging_queue, process_logging_configurer))
        time.sleep(2)
        process_kuma_intergation.start()
    
    if config['thehive']['modules']['incident']['enable']:
        from src.integration_thehive import TheHive
        the_hive = TheHive(config)
        process_the_hive = multiprocessing.Process(target = the_hive.run, args=(logging_queue, process_logging_configurer))
        time.sleep(2)
        process_the_hive.start()

    if config['event_sender']['modules']['incident']['enable'] or config['event_sender']['modules']['asset']['enable']:
        from src.integration_event_sender import EventSender
        event_sender = EventSender(config)
        process_event_sender = multiprocessing.Process(target = event_sender.run, args=(logging_queue, process_logging_configurer))
        time.sleep(2)
        process_event_sender.start()

    logger.info('MDR Integration service started..')


if __name__ == '__main__':
    main()