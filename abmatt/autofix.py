"""Debugging and fixing"""
import sys
import traceback
from collections.abc import Callable
from threading import Thread
from time import sleep
from typing import Any, Optional

if sys.platform == 'win32':
    from colorama import init

    init()


class bcolors:
    HEADER = '\033[35m'
    OKBLUE = '\033[34m'
    OKGREEN = '\033[32m'
    WARNING = '\033[33m'
    FAIL = '\033[31m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


class Bug:
    # bug levels
    # None 0
    # Errors 1
    # Warnings 2
    # Checks 3
    # Suggest 4
    # Prompt 5
    # notify levels, 0 silent, 1 quiet, 2 mid, 3 loud, 4 max, 5 debug
    def __init__(self, bug_level: int, notify_level: int, description: str, fix_des: str | None = None) -> None:
        self.bug_level = bug_level
        self.notify_level = notify_level  # lower numbers mean notify when quiet
        self.description = description
        self.fix_des = fix_des
        self.is_resolved = False
        AutoFix.notify(self)

    def resolve(self) -> None:
        self.is_resolved = True
        AutoFix.info(f'(FIXED): {self.fix_des}', self.notify_level)


class AutoFixAbort(BaseException):
    """Raised by prompt"""

    def __init__(self) -> None:
        super(AutoFixAbort, self).__init__('Operation aborted')


class MessageReceiver:
    """Interface to receive messages"""

    def info(self, message: str) -> None:
        raise NotImplementedError()

    def warn(self, message: str) -> None:
        raise NotImplementedError()

    def error(self, message: str) -> None:
        raise NotImplementedError()


class Message:
    def __init__(self, message: str) -> None:
        self.message = message

    def send(self, pipe: MessageReceiver | None) -> None:
        raise NotImplementedError()


class _AutoFix:
    # The module ends by rebinding the name AutoFix to the one instance of this class.
    # Fix Level
    # None 0
    # Errors 1
    # Warnings 2
    # Checks 3
    # Suggest 4
    # Prompt 5
    FIX_PROMPT = 5
    __AUTO_FIXER: Optional['_AutoFix'] = None

    # Loudness levels, 0 silent, 1 quiet, 2 mid, 3 loud, 4 max, 5 debug
    LOUD_LEVELS = ('SILENT', 'QUIET', 'MID', 'LOUD', 'MAX', 'DEBUG')
    FIX_LEVELS = ('NONE', 'ERRORS', 'WARNINGS', 'CHECKS', 'SUGGEST', 'PROMPT')
    ERROR_LEVELS = (bcolors.ENDC, bcolors.FAIL, bcolors.FAIL, bcolors.OKBLUE, bcolors.OKBLUE, bcolors.BOLD)
    RESULTS = ('NONE', 'ERROR', 'WARN', 'CHECK', 'SUCCESS')

    class Info(Message):
        def send(self, pipe: MessageReceiver | None) -> None:
            message = self.message
            print(message)
            if pipe:
                pipe.info(message)

    class Warn(Message):
        def send(self, pipe: MessageReceiver | None) -> None:
            message = self.message
            print(f'{bcolors.FAIL}WARN: {message}{bcolors.ENDC}')
            if pipe:
                pipe.warn(message)

    class Error(Message):
        def send(self, pipe: MessageReceiver | None) -> None:
            message = self.message
            print(f'{bcolors.FAIL}ERROR: {message}{bcolors.ENDC}')
            if pipe:
                pipe.error(message)

    thread: Thread

    def __init__(self, fix_level: int = 3, loudness: int = 3) -> None:
        if self.__AUTO_FIXER: raise RuntimeError('Autofixer already initialized')
        self.loudness = loudness
        self.fix_level = fix_level
        self.zero_level_func: Callable[[], Any] | None = None
        self.queue: list[Message] = []
        self.is_running = False
        self.pipe: MessageReceiver | None = None  # if set, output is sent to the pipe, must implement info warn and error.
        _AutoFix.__AUTO_FIXER = self  # the name AutoFix is not bound to the instance yet

    @staticmethod
    def quit() -> None:
        a = AutoFix.__AUTO_FIXER
        if a is not None:
            if a.is_running:
                a.is_running = False
                a.thread.join()
                _AutoFix.__AUTO_FIXER = None

    def run(self) -> None:
        self.is_running = True
        while len(self.queue):
            if len(self.queue):
                self.queue.pop(0).send(self.pipe)
            sleep(0.01)
        self.is_running = False

    def enqueue(self, message: Message) -> None:
        self.queue.append(message)
        if not self.is_running:
            self.thread = Thread(target=self.run)
            self.thread.start()

    @staticmethod
    def get(fixe_level: int = 3, loudness: int = 3) -> '_AutoFix':
        if _AutoFix.__AUTO_FIXER is None:
            _AutoFix.__AUTO_FIXER = _AutoFix(fixe_level, loudness)
        return _AutoFix.__AUTO_FIXER

    def set_pipe(self, obj: MessageReceiver | None) -> None:
        self.pipe = obj

    def set_fix_level(self, fix_level: int | str | None, zero_level_func: Callable[[], Any] | None = None) -> None:
        if zero_level_func:
            self.zero_level_func = zero_level_func
        if type(fix_level) is int:
            self.fix_level = fix_level
        elif fix_level is not None:
            try:
                self.fix_level = int(fix_level)
            except ValueError:
                fix_level = str(fix_level).upper()
                if fix_level == 'ALL':
                    self.fix_level = 4
                elif fix_level in self.FIX_LEVELS:
                    self.fix_level = self.FIX_LEVELS.index(fix_level)
        if self.fix_level == 0 and self.zero_level_func:
            self.zero_level_func()

    def can_prompt(self) -> bool:
        return self.fix_level == self.FIX_PROMPT

    def log(self, message: object) -> None:
        if self.loudness >= 5:
            self.enqueue(self.Info(str(message)))

    def info(self, message: object, loudness: int = 3) -> None:
        if self.loudness >= loudness:
            self.enqueue(self.Info(str(message)))

    def warn(self, message: object, loudness: int = 2) -> None:
        if self.loudness >= loudness:
            self.enqueue(self.Warn(str(message)))

    def error(self, message: object, loudness: int = 1) -> None:
        if self.loudness >= loudness:
            self.enqueue(self.Error(str(message)))

    def exception(self, exception: object = None, shutdown: bool = False) -> None:
        exc_type, exc_value, exc_tb = sys.exc_info()
        if self.loudness >= 5:  # Debug level
            s = traceback.format_exception(exc_type, exc_value, exc_tb)
        elif self.loudness >= 1:
            s = traceback.format_exception(exc_type, exc_value, exc_tb, 10)
        else:
            s = traceback.format_exception(exc_type, exc_value, exc_tb, 3)
        self.enqueue(self.Error(''.join(s)))
        if shutdown:
            self.thread.join(5)
            sys.exit(-1)

    # def should_fix(self, bug):
    #     """Determines if a bug should be fixed"""
    #     fix_level = self.fix_level
    #     if fix_level >= bug.bug_level:
    #         should_fix = True
    #         if fix_level == self.FIX_PROMPT:
    #             should_fix = self.prompt(bug.description, bug.fix_des)
    #         if should_fix:
    #             if self.loudness >= bug.notify_level:
    #                 print('FIX: {}'.format(bug.description))
    #             return True
    #     self.notify(bug)
    #     return False

    @staticmethod
    def prompt(description: str, proposed_fix: str | None = None) -> int:
        while True:
            fix = ',' + proposed_fix if proposed_fix else ''
            result = input('Fix: ' + description + fix + '? (y/n)').lower()[:1]
            if result == 'y':
                return 1
            elif result == 'n':
                return 0
            elif result == 'a':  # abort option
                raise AutoFixAbort()
            else:
                print('Invalid response, expects yes, no, or abort.')

    def display_result(self, bug: Bug, result_level: int = 4, result_message: str | None = None) -> None:
        if self.loudness >= bug.notify_level:
            if result_message:
                result_message = '(' + self.RESULTS[result_level] + ') ' + result_message
            else:
                result_message = '(' + self.RESULTS[result_level] + ') ' + (bug.fix_des or bug.description)
            self.info(result_message, 0)

    def notify(self, bug: Bug) -> None:
        """Notifies of a bug check"""
        if self.loudness >= bug.notify_level:
            self.info(bug.description, 0)

    def get_level(self, level_str: str) -> int:
        """Expects level to be a string, as a number or one of the Error levels"""
        try:
            level = int(level_str)
            if not 0 <= level < 6:
                raise ValueError('Loudness level out of range (0-6)')
            return int(level)
        except ValueError:
            level_str = level_str.upper()
            if level_str == 'ALL':
                return 4
            return self.LOUD_LEVELS.index(level_str)

    def set_loudness(self, level_str: str) -> None:
        self.loudness = self.get_level(level_str)


AutoFix = _AutoFix()
