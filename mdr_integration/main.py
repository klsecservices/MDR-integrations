
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


SUPERVISOR_CHECK_INTERVAL = 60  # seconds between subprocess liveness checks


def process_logging_configurer(queue):
    h = logging.handlers.QueueHandler(queue)  # Just the one handler needed
    root = logging.getLogger()
    root.addHandler(h)
    root.setLevel(logging.DEBUG)


def build_process_specs(logging_queue):
    # Each spec is (name, factory) where factory() returns a fresh, unstarted
    # Process. Kept as factories (not Process instances) so a dead process can
    # be recreated on restart - a multiprocessing.Process can only run once.
    specs = []

    from src.token_updater import TokenUpdater
    def make_token_updater():
        token_updater = TokenUpdater(config)
        return multiprocessing.Process(target = token_updater.run, args=(logging_queue, process_logging_configurer))
    specs.append(('token_updater', make_token_updater))

    if config['mdr_sync']['modules']['incident']['enable'] or config['mdr_sync']['modules']['asset']['enable']:
        from src.mdr_sync import MDRSync
        def make_mdr_sync():
            mdr_sync = MDRSync(config)
            return multiprocessing.Process(target = mdr_sync.run, args=(logging_queue, process_logging_configurer))
        specs.append(('mdr_sync', make_mdr_sync))

    if config['kuma']['modules']['incident']['enable'] or config['kuma']['modules']['asset']['enable']:
        from src.integration_kuma import KUMA
        def make_kuma():
            kuma_intergation = KUMA(config)
            return multiprocessing.Process(target = kuma_intergation.run, args=(logging_queue, process_logging_configurer))
        specs.append(('kuma', make_kuma))

    if config['thehive']['modules']['incident']['enable']:
        from src.integration_thehive import TheHive
        def make_thehive():
            the_hive = TheHive(config)
            return multiprocessing.Process(target = the_hive.run, args=(logging_queue, process_logging_configurer))
        specs.append(('thehive', make_thehive))

    if config['event_sender']['modules']['incident']['enable'] or config['event_sender']['modules']['asset']['enable']:
        from src.integration_event_sender import EventSender
        def make_event_sender():
            event_sender = EventSender(config)
            return multiprocessing.Process(target = event_sender.run, args=(logging_queue, process_logging_configurer))
        specs.append(('event_sender', make_event_sender))

    return specs


def main():
    # Init Logger
    logging_config = config.get('logging')
    logging_queue = multiprocessing.Queue(-1)

    def make_logging_listener():
        mdr_logger = MDRLogger()
        return multiprocessing.Process(target=mdr_logger.run, args=(logging_queue, logging_config))

    logging_listener = make_logging_listener()
    logging_listener.start()

    process_logging_configurer(logging_queue)
    logger = logging.getLogger(__name__)
    logger.info('MDR Integration service is starting..')

    processes = {'logger': (logging_listener, make_logging_listener)}

    for name, factory in build_process_specs(logging_queue):
        proc = factory()
        proc.start()
        time.sleep(2)
        processes[name] = (proc, factory)

    logger.info('MDR Integration service started..')

    # Supervisor loop: restart any subprocess that has died, so a crash in
    # one integration doesn't silently disable it for the rest of the run.
    while True:
        time.sleep(SUPERVISOR_CHECK_INTERVAL)
        for name, (proc, factory) in list(processes.items()):
            if not proc.is_alive():
                logger.error(f'Process "{name}" has died (exitcode={proc.exitcode}), restarting..')
                new_proc = factory()
                new_proc.start()
                processes[name] = (new_proc, factory)


if __name__ == '__main__':
    main()