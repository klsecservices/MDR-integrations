import logging
from logging.handlers import TimedRotatingFileHandler
from typing import Optional, Dict, Any, List

class MDRLogger():

    level = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL
    }

    def __init__(self) -> Any:
        pass
    
    def init(self, config, name):
        log_level = self.level[config['log_level'].upper()]
        log_dir = config['log_dir']
        self.logger = logging.getLogger(name)
        self.logger.setLevel(log_level)
        file_handler = TimedRotatingFileHandler(
            filename = f'{log_dir}/app.log',
            when = 'D',
            interval = 1,
            backupCount = 7
        )
        
        file_handler.setLevel(log_level)
        log_format = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s')
        file_handler.setFormatter(log_format)
        self.logger.addHandler(file_handler)

    def run(self, queue, config):
        self.init(config, __name__)
        self.logger.info('MDR logger started')
        while True:
            try:
                record = queue.get()
                if record is None:
                    break
                self.logger.handle(record)
            except Exception:
                import sys, traceback
                print('Whoops! Problem:', file=sys.stderr)
                traceback.print_exc(file=sys.stderr)

