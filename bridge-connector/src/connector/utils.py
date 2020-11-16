import logging
import os


def log_to_file(logfile, level=logging.DEBUG):
    # Log given level to a file, INFO to stderr
    if os.path.dirname(logfile):
        os.makedirs(os.path.dirname(logfile), exist_ok=True)

    logging.basicConfig(
        level=level,
        format='%(asctime)s [%(levelname)s] %(message)s',
        filename=logfile
    )

    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
    console.setFormatter(formatter)
    logging.getLogger('').addHandler(console)
