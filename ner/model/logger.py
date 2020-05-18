import logging
import sys


class NERLogger:
    def __init__(self, debug: bool):
        self._debug = debug
        self._log_formatter = logging.Formatter(
            "%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s"
        )
        self._logger = logging.getLogger()
        self._reset_logger()

        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(self._log_formatter)
        self._logger.addHandler(console_handler)

        if self._debug:
            self._logger.setLevel(logging.DEBUG)
        else:
            self._logger.setLevel(logging.INFO)

    def info(self, message: str):
        self._logger.info(message)

    def addHandler(self, handler):
        self._logger.addHandler(handler)

    def setLevel(self, debug: bool):
        if debug:
            self._logger.setLevel(logging.DEBUG)
        else:
            self._logger.setLevel(logging.INFO)

    def _reset_logger(self):
        for handler in self._logger.handlers[:]:
            self._logger.removeHandler(handler)

        for f in self._logger.filters[:]:
            self._logger.removeFilters(f)

    @property
    def log_formatter(self):
        return self._log_formatter
