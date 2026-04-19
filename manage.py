#!/usr/bin/env python3
"""
Django's command-line utility for administrative tasks.

This script is a wrapper around Django's manage.py command, providing
administrative functionality for the Django project.
"""
import logging
import os
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main() -> None:
    """Run administrative tasks for the Django project."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "portfolio.settings")
    
    try:
        from django.core.management import execute_from_command_line
    except ImportError as e:
        logger.error(
            "Failed to import Django. Ensure Django is installed and "
            "the PYTHONPATH environment variable is set correctly."
        )
        
        try:
            import django  # noqa: F401
        except ImportError:
            raise ImportError(
                "Couldn't import Django. Are you sure it's installed and "
                "available on your PYTHONPATH environment variable? Did you "
                "forget to activate a virtual environment?"
            ) from e
        
        logger.error("An unexpected error occurred while importing Django.", exc_info=True)
        raise
    
    try:
        execute_from_command_line(sys.argv)
    except KeyboardInterrupt:
        logger.info("Command interrupted by user.")
        sys.exit(1)
    except Exception as e:
        logger.error("An error occurred while executing the command.", exc_info=True)
        raise


if __name__ == "__main__":
    main()

