# logging_setup.py

import logging
import logging.handlers
import os

def setup_logging(log_dir='logs', log_file='app.log', level=logging.INFO):
    """
    Sets up logging for the application.
    Logs are output to both the console and a rotating file handler.
    """
    # Ensure the log directory exists
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    log_path = os.path.join(log_dir, log_file)

    # Create the root logger
    logger = logging.getLogger()
    logger.setLevel(level)

    # Define a common log formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Console handler for output to the terminal
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Rotating file handler for saving logs to a file
    file_handler = logging.handlers.RotatingFileHandler(log_path, maxBytes=10*1024*1024, backupCount=5)
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger
