import logging
import queue

class QueueLogHandler(logging.Handler):
    """
    A custom logging handler that puts log records into a queue.
    This is used to pass log messages from the bot thread to the web server.
    """
    def __init__(self, log_queue: queue.Queue):
        super().__init__()
        self.log_queue = log_queue

    def emit(self, record):
        # Format the record and put it into the queue
        self.log_queue.put(self.format(record))

def setup_logging(log_queue: queue.Queue) -> None:
    """
    Configures the root logger to use the QueueLogHandler.
    This function should be called once when the application starts.
    """
    # Get the root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Remove any existing handlers (like the default console handler)
    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    # Add our queue handler
    queue_handler = QueueLogHandler(log_queue)

    # Add a formatter to the handler
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    queue_handler.setFormatter(formatter)

    root_logger.addHandler(queue_handler)

    # Also add a console handler so we can see logs in the terminal during development
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    logging.info("Logging configured to use both queue and console handlers.")
