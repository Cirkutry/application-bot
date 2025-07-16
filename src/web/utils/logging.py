import datetime
import logging


class SimpleAccessFormatter(logging.Formatter):
    """Custom formatter for access logs"""

    def format(self, record):
        # Format timestamp
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S,%f")[:-3]

        # Extract the message parts
        parts = record.getMessage().split('"')
        if len(parts) >= 3:
            # Format: timestamp - IP request status size
            ip = parts[0].split()[0]
            request = parts[1]
            status_size = parts[2].strip()
            return f"{timestamp} - {ip} {request} {status_size}"
        return f"{timestamp} - {record.getMessage()}"


def setup_logging():
    """Setup logging configuration for the web server"""
    # Configure basic logging
    logging.basicConfig(level=logging.INFO)
    aiohttp_logger = logging.getLogger("aiohttp.access")
    aiohttp_logger.setLevel(logging.INFO)

    # Create custom access logger
    access_logger = logging.getLogger("aiohttp.access")
    access_logger.setLevel(logging.INFO)
    access_logger.propagate = False

    # Add handler with custom format
    handler = logging.StreamHandler()
    handler.setFormatter(SimpleAccessFormatter())
    access_logger.addHandler(handler)

    return access_logger
