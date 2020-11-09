import logging
import os
import time


def full_debug(logfile):
    # Log DEBUG to a file, INFO to stderr
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s [%(levelname)s] %(message)s',
        filename=logfile
    )

    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
    console.setFormatter(formatter)
    logging.getLogger('').addHandler(console)


def enable_logger(directory="logs", filename="logfile", extension=".log", level=logging.INFO):
    logging_directory = os.path.join(os.getcwd(), directory)
    if not os.path.exists(logging_directory):
        os.makedirs(logging_directory)
    timestamp = str(time.time()).split('.')[0]
    filename = filename + str(timestamp) + extension
    logfile = os.path.join(logging_directory, filename)
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(logfile),
            logging.StreamHandler()
        ]
    )
