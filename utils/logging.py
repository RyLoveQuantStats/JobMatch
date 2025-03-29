import logging
import logging.handlers
import os
import sys

def setup_logging(log_dir='logs', log_file='app.log', level=logging.INFO):
    logger = logging.getLogger()
    # If handlers already exist, return the logger to avoid duplicate messages.
    if logger.hasHandlers():
        return logger

    # Ensure the log directory exists.
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    log_path = os.path.join(log_dir, log_file)
    logger.setLevel(level)

    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Create a stream handler with UTF-8 encoding to avoid Unicode errors.
    stream_handler = logging.StreamHandler(sys.stdout)
    try:
        stream_handler.setStream(sys.stdout)
    except Exception:
        pass
    stream_handler.setLevel(level)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    # Create a rotating file handler.
    file_handler = logging.handlers.RotatingFileHandler(log_path, maxBytes=10*1024*1024, backupCount=5, encoding='utf-8')
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger
