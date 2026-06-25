import logging
import os
from logging.handlers import RotatingFileHandler


def configure_logging(application):
    log_dir = os.path.normpath(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'logs')
    )
    os.makedirs(log_dir, exist_ok=True)

    fmt = logging.Formatter(
        '%(asctime)s %(levelname)-8s %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    file_handler = RotatingFileHandler(
        os.path.join(log_dir, 'helpdesk.log'),
        maxBytes=1_048_576,
        backupCount=5
    )
    file_handler.setFormatter(fmt)
    file_handler.setLevel(logging.INFO)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(fmt)
    console_handler.setLevel(logging.INFO)

    application.logger.setLevel(logging.INFO)
    application.logger.addHandler(file_handler)
    application.logger.addHandler(console_handler)
