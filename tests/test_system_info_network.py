"""The System info screen reaches the network only when the user explicitly
asks it to look up the public IP. Every other answer must leave the network
untouched: no socket connection, no DNS lookup, no HTTP request, no curl.
"""
import contextlib
import io
import socket
import unittest
from unittest import mock

import main.DESKTOP as D
import main.SHARED_RESOURCES as S


class NetworkTouched(AssertionError):
    pass


def _blocked(*_a, **_k):
    raise NetworkTouched("network was touched")


def responder(answers):
    def answer(prompt, *_a, **_k):
        for key, value in answers.items():
            if key in prompt:
                return value
        if "Press 'enter'" in prompt:
            return ""
        raise AssertionError(f"unexpected prompt: {prompt!r}")
    return answer


class SystemInfoNetwork(unittest.TestCase):
    def _run(self, answers, lookup=None):
        lookup = lookup or mock.Mock(side_effect=_blocked)
        out = io.StringIO()
        with contextlib.ExitStack() as stack:
            for target in ("socket.socket.connect", "socket.socket.connect_ex",
                           "socket.create_connection", "socket.getaddrinfo",
                           "socket.gethostbyname", "socket.gethostbyname_ex"):
                stack.enter_context(mock.patch(target, side_effect=_blocked))
            stack.enter_context(mock.patch.object(S.requests, "get", side_effect=_blocked))
            stack.enter_context(mock.patch.object(S.subprocess, "check_output", side_effect=_blocked))
            # psutil.cpu_percent(interval=1) only slows the test down.
            stack.enter_context(mock.patch.object(D.psutil, "cpu_percent", return_value=0.0))
            stack.enter_context(mock.patch.object(D, "get_external_ip", lookup))
            stack.enter_context(mock.patch("builtins.input", side_effect=responder(answers)))
            stack.enter_context(contextlib.redirect_stdout(out))
            D.system_info(None, None)
        return out.getvalue(), lookup

    def test_no_network_details(self):
        out, lookup = self._run({"network details": "n"})
        lookup.assert_not_called()
        self.assertNotIn("External IP", out)

    def test_details_but_no_ip_addresses(self):
        out, lookup = self._run({"network details": "y",
                                 "detailed network connections": "n",
                                 "IP addresses": "n"})
        lookup.assert_not_called()
        self.assertNotIn("Local IP", out)

    def test_local_ip_only_stays_offline(self):
        out, lookup = self._run({"network details": "y",
                                 "detailed network connections": "n",
                                 "IP addresses": "y",
                                 "public IP online": "n"})
        lookup.assert_not_called()
        self.assertIn("Local IP Address", out)
        self.assertNotIn("External IP", out)

    def test_public_ip_only_after_explicit_yes(self):
        # Control round: the harness does reach the lookup when asked to.
        lookup = mock.Mock(return_value="203.0.113.7")
        out, lookup = self._run({"network details": "y",
                                 "detailed network connections": "n",
                                 "IP addresses": "y",
                                 "public IP online": "y"}, lookup=lookup)
        lookup.assert_called_once()
        self.assertIn("External IP Address: 203.0.113.7", out)

    def test_local_ipv4_needs_no_network(self):
        with mock.patch("socket.socket.connect", side_effect=_blocked), \
             mock.patch("socket.gethostbyname", side_effect=_blocked), \
             mock.patch("socket.getaddrinfo", side_effect=_blocked):
            self.assertIsInstance(S.local_ipv4(), str)


if __name__ == "__main__":
    unittest.main()
