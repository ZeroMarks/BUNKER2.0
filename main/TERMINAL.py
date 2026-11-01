"""
TERMINAL - make BUNKER's output robust and accessible.

* Characters the terminal cannot encode (for example emoji on a legacy
  Windows code page, or output piped with an ASCII encoding) are replaced
  instead of raising UnicodeEncodeError and ending the session.
* BUNKER_NO_EMOJI=1 strips emoji and other pictographs from everything BUNKER
  prints. Screen readers otherwise read each one aloud by name ("locked
  padlock", "red exclamation mark"), which makes the menus hard to follow.
  Combine with NO_COLOR=1 for plain text.
"""

import os
import re
import sys

# Pictographs, dingbats, symbols and the joiners/selectors that build emoji,
# plus the one space that usually follows an emoji in BUNKER's labels.
_EMOJI = re.compile(
    "["
    "\U0001F000-\U0001FAFF"   # pictographs, emoji, symbols & pictographs ext.
    "\u2600-\u27BF"           # misc symbols, dingbats
    "\u2B00-\u2BFF"           # arrows & stars used as emoji
    "\u2300-\u23FF"           # misc technical (timers, keyboards)
    "\uFE0E\uFE0F\u200D"      # variation selectors, zero-width joiner
    "]+ ?"
)


def strip_emoji(text):
    """Remove emoji (and the space after each). All other spacing, such as
    the ASCII art and aligned menus, is left exactly as it was."""
    return _EMOJI.sub("", text)


class _EmojiFreeStream:
    """Thin wrapper over a text stream that strips emoji on write."""

    def __init__(self, stream):
        self._stream = stream

    def write(self, text):
        return self._stream.write(strip_emoji(text))

    def __getattr__(self, name):
        return getattr(self._stream, name)


def setup_output():
    """Call once at startup, before anything is printed."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="replace")
        except (AttributeError, ValueError):
            pass
    if os.environ.get("BUNKER_NO_EMOJI"):
        if not isinstance(sys.stdout, _EmojiFreeStream):
            sys.stdout = _EmojiFreeStream(sys.stdout)
