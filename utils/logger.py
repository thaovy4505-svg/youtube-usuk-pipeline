import logging
import os

def setup_logger():
    logger = logging.getLogger(__name__)
    
    if logger.handlers:
        return logger
    
    log_file = os.path.join(os.path.dirname(__file__), 'app.log')
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)