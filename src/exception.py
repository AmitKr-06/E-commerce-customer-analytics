"""Exception that adds the file and line where the original error was raised."""
import sys


def error_message_detail(error, exc_info = None):
    _, _, tb = exc_info or sys.exc_info()
    if tb is None:            # raised outside and except block
        return str(error)
    while tb.tb_next:
        tb = tb.tb_next
    return (f"Error in script [{tb.tb_frame.f_code.co_filename}]" 
            f"line [{tb.tb_lineno}]: {error}")


class CustomException(Exception):
    """Use inside an except block: raise CustomException(e) from e"""

    def __init__(self, error, error_detail = None):
        info = error_detail.exc_info() if error_detail is not None else None   # accepts 'sys' too
        self.error_message = error_message_detail(error, info)
        super().__init__(self.error_message)

    def __str__(self):
        return self.error_message