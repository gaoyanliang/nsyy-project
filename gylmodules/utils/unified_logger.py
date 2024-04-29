import logging

from gylmodules import global_config


class UnifiedLogger:
    _instance = None

    def __new__(cls, file_name: str):
        cls.file_name = file_name
        if cls._instance is None:
            cls._instance = super(UnifiedLogger, cls).__new__(cls)
            cls._instance._logger = logging.getLogger(file_name)

            cls._instance._logger.setLevel(logging.DEBUG)

            # Create a formatter
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

            # Create a console handler
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.ERROR)
            console_handler.setFormatter(formatter)

            # Add the handlers to the logger
            cls._instance._logger.addHandler(console_handler)

            if not global_config.run_in_local:
                # Create a file handler
                file_handler = logging.FileHandler(file_name)
                file_handler.setLevel(logging.INFO)
                file_handler.setFormatter(formatter)
                cls._instance._logger.addHandler(file_handler)

        return cls._instance

    def log(self, level, message):
        if level == 'debug':
            self._logger.debug(message)
        elif level == 'info':
            self._logger.info(message)
        elif level == 'warning':
            self._logger.warning(message)
        elif level == 'error':
            self._logger.error(message)
        elif level == 'critical':
            self._logger.critical(message)

    def debug(self, message):
        self._logger.debug(message)

    def info(self, message):
        self._logger.info(message)

    def warning(self, message):
        self._logger.warning(message)

    def error(self, message):
        self._logger.error(message)

    def critical(self, message):
        self._logger.critical(message)


if __name__ == "__main__":
    logger = UnifiedLogger("unified_logger_test.log")
    logger.log('debug', 'This is a debug message.')
    logger.log('info', 'This is an info message.')
    logger.log('warning', 'This is a warning message.')
    logger.log('error', 'This is an error message.')
    logger.log('critical', 'This is a critical message.')

    logger.debug('This is a debug message.')
    logger.info('This is an info message.')
    logger.warning('This is a warning message.')
    logger.error('This is an error message.')
    logger.critical('This is a critical message.')


