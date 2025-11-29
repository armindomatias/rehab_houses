"""
Centralized logging configuration for the code_housing project.
"""

import logging


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with standardized configuration.
    
    Args:
        name: Logger name (typically __name__ of the calling module)
    
    Returns:
        Configured logger instance
    """
    # Configure logging if not already configured
    if not logging.root.handlers:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[logging.StreamHandler()]
        )
    
    return logging.getLogger(name)

