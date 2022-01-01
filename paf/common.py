'''
Created on Dec 28, 2021

@author: vladyslav_goncharuk
'''

import importlib

import os
import io

if os.name == 'nt':
    import msvcrt
    from ctypes import Structure, c_ushort, windll, POINTER, byref
    from ctypes.wintypes import HANDLE, _COORD, _SMALL_RECT
else:
    import fcntl
    import struct
    import termios
    import tty
   
def has_fileno(stream):
    """
    Cleanly determine whether ``stream`` has a useful ``.fileno()``.
    .. note::
        This function helps determine if a given file-like object can be used
        with various terminal-oriented modules and functions such as `select`,
        `termios`, and `tty`. For most of those, a fileno is all that is
        required; they'll function even if ``stream.isatty()`` is ``False``.
    :param stream: A file-like object.
    :returns:
        ``True`` if ``stream.fileno()`` returns an integer, ``False`` otherwise
        (this includes when ``stream`` lacks a ``fileno`` method).
    .. versionadded:: 1.0
    """
    try:
        return isinstance(stream.fileno(), int)
    except (AttributeError, io.UnsupportedOperation):
        return False

def isatty(stream):
    """
    Cleanly determine whether ``stream`` is a TTY.
    Specifically, first try calling ``stream.isatty()``, and if that fails
    (e.g. due to lacking the method entirely) fallback to `os.isatty`.
    .. note::
        Most of the time, we don't actually care about true TTY-ness, but
        merely whether the stream seems to have a fileno (per `has_fileno`).
        However, in some cases (notably the use of `pty.fork` to present a
        local pseudoterminal) we need to tell if a given stream has a valid
        fileno but *isn't* tied to an actual terminal. Thus, this function.
    :param stream: A file-like object.
    :returns:
        A boolean depending on the result of calling ``.isatty()`` and/or
        `os.isatty`.
    .. versionadded:: 1.0
    """
    # If there *is* an .isatty, ask it.
    if hasattr(stream, "isatty") and callable(stream.isatty):
        return stream.isatty()
    # If there wasn't, see if it has a fileno, and if so, ask os.isatty
    elif has_fileno(stream):
        return os.isatty(stream.fileno())
    # If we got here, none of the above worked, so it's reasonable to assume
    # the darn thing isn't a real TTY.
    return False
    
def bytes_to_read(input_):
    """
    Query stream ``input_`` to see how many bytes may be readable.
    .. note::
        If we are unable to tell (e.g. if ``input_`` isn't a true file
        descriptor or isn't a valid TTY) we fall back to suggesting reading 1
        byte only.
    :param input: Input stream object (file-like).
    :returns: `int` number of bytes to read.
    .. versionadded:: 1.0
    """
    # NOTE: we have to check both possibilities here; situations exist where
    # it's not a tty but has a fileno, or vice versa; neither is typically
    # going to work re: ioctl().
    if not os.name == 'nt' and isatty(input_) and has_fileno(input_):
        fionread = fcntl.ioctl(input_, termios.FIONREAD, "  ")
        return struct.unpack("h", fionread)[0]
    return 1

def create_class_instance(full_class_name):
    try:
        module_path, class_name = full_class_name.rsplit('.', 1)
        module = importlib.import_module(module_path)
        return getattr(module, class_name)
    except (ImportError, AttributeError) as e:
        raise ImportError(full_class_name)