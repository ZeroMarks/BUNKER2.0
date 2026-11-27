"""The public IP display (off by default) may reach the network only while it
is switched on. Turning it off must stop the background lookups for good:
the thread wakes from its wait and exits, a lookup already in flight is
thrown away, and switching the display off and on again never leaves more
than one thread looking things up.

No test here touches the real network: the two lookup functions are replaced
by counters.
"""
import contextlib
import io
import threading
import time
import unittest
from unittest import mock

import main.SHARED_RESOURCES as S

WAIT = 5  # seconds; generous upper bound for a thread to react


class NetworkTouched(AssertionError):
    pass


TOUCHED = []  # every blocked call, even one the app code catches


def _blocked(*_a, **_k):
    TOUCHED.append(_a)
    raise NetworkTouched("network was touched")


def lookup_threads():
    return [t for t in threading.enumerate()
            if t.name == S.IP_THREAD_NAME and t.is_alive()]


class FakeNetwork:
    """Stands in for check_internet_connection and get_public_ipv4."""

    def __init__(self, online=True, ip="203.0.113.7"):
        self.online = online
        self.ip = ip
        self.checks = 0
        self.lookups = 0
        self.looked_up = threading.Event()   # set after every finished round
        self.in_lookup = threading.Event()   # set when a lookup has begun
        self.release = threading.Event()     # a lookup waits for this
        self.release.set()
        self._lock = threading.Lock()

    def check(self):
        with self._lock:
            self.checks += 1
        if not self.online:
            self.looked_up.set()
        return self.online

    def lookup(self):
        with self._lock:
            self.lookups += 1
        self.in_lookup.set()
        self.release.wait(WAIT)
        self.looked_up.set()
        return self.ip

    @property
    def calls(self):
        with self._lock:
            return self.checks + self.lookups


class IpDisplayThread(unittest.TestCase):
    def setUp(self):
        S.stop_ip_fetch_thread()
        self.net = FakeNetwork()
        self._patch(S, "check_internet_connection", self.net.check)
        self._patch(S, "get_public_ipv4", self.net.lookup)
        self.started = []
        self.addCleanup(self._stop_all)

    def _patch(self, obj, name, value):
        patcher = mock.patch.object(obj, name, value)
        patcher.start()
        self.addCleanup(patcher.stop)

    def _stop_all(self):
        self.net.release.set()
        S.stop_ip_fetch_thread()
        for thread in self.started:
            thread.join(WAIT)

    def start(self):
        S.start_ip_fetch_thread()
        thread = S.ip_fetch_thread
        if thread not in self.started:
            self.started.append(thread)
        return thread

    def wait_for_cached(self, value):
        deadline = time.monotonic() + WAIT
        while time.monotonic() < deadline:
            with S.cache_lock:
                if S.cached_ip == value:
                    return
            time.sleep(0.005)
        self.fail(f"cached_ip never became {value!r}")

    # --- turning it off ----------------------------------------------------

    def test_stop_wakes_the_waiting_thread_and_ends_it(self):
        self._patch(S, "IP_REFRESH_SECONDS", 3600)
        thread = self.start()
        self.wait_for_cached("203.0.113.7")
        S.stop_ip_fetch_thread()
        thread.join(WAIT)
        self.assertFalse(thread.is_alive(),
                         "the lookup thread was still running after the display was turned off")
        self.assertEqual(lookup_threads(), [])

    def test_no_lookups_after_stop(self):
        self._patch(S, "IP_REFRESH_SECONDS", 0.01)
        thread = self.start()
        deadline = time.monotonic() + WAIT
        while self.net.lookups < 3 and time.monotonic() < deadline:
            time.sleep(0.005)
        self.assertGreaterEqual(self.net.lookups, 3, "control: lookups repeat while it is on")
        S.stop_ip_fetch_thread()
        thread.join(WAIT)
        self.assertFalse(thread.is_alive())
        after_stop = self.net.calls
        time.sleep(0.2)  # twenty refresh periods
        self.assertEqual(self.net.calls, after_stop,
                         "the network was used after the display was turned off")

    def test_stop_forgets_the_cached_ip(self):
        self._patch(S, "IP_REFRESH_SECONDS", 3600)
        self.start()
        self.wait_for_cached("203.0.113.7")
        S.stop_ip_fetch_thread()
        with S.cache_lock:
            self.assertIsNone(S.cached_ip)

    def test_lookup_in_flight_when_stopped_is_discarded(self):
        self._patch(S, "IP_REFRESH_SECONDS", 3600)
        self.net.release.clear()
        thread = self.start()
        self.assertTrue(self.net.in_lookup.wait(WAIT))
        S.stop_ip_fetch_thread()
        self.net.release.set()
        thread.join(WAIT)
        self.assertFalse(thread.is_alive())
        with S.cache_lock:
            self.assertIsNone(S.cached_ip, "a result that arrived after 'off' was kept")
        self.assertEqual(self.net.lookups, 1)

    def test_stopped_between_check_and_lookup_makes_no_lookup(self):
        stop = threading.Event()

        def check_then_stop():
            stop.set()
            return True

        self._patch(S, "check_internet_connection", check_then_stop)
        S.fetch_ip_thread_func(stop)
        self.assertEqual(self.net.lookups, 0)

    def test_already_stopped_thread_never_touches_the_network(self):
        stop = threading.Event()
        stop.set()
        S.fetch_ip_thread_func(stop)
        self.assertEqual(self.net.calls, 0)

    def test_stop_when_nothing_runs_is_harmless(self):
        S.stop_ip_fetch_thread()
        S.stop_ip_fetch_thread()
        self.assertIsNone(S.ip_fetch_thread)
        self.assertEqual(self.net.calls, 0)

    # --- turning it on, and off and on again -------------------------------

    def test_start_twice_keeps_one_thread(self):
        self._patch(S, "IP_REFRESH_SECONDS", 3600)
        first = self.start()
        second = self.start()
        self.assertIs(first, second)
        self.assertEqual(len(lookup_threads()), 1)

    def test_off_on_cycles_do_not_stack_threads_or_lookups(self):
        self._patch(S, "IP_REFRESH_SECONDS", 3600)
        cycles = 6
        for _ in range(cycles):
            self.net.looked_up.clear()
            self.start()
            self.assertTrue(self.net.looked_up.wait(WAIT))
            S.stop_ip_fetch_thread()
        self.net.looked_up.clear()
        last = self.start()
        self.assertTrue(self.net.looked_up.wait(WAIT))
        for thread in self.started[:-1]:
            thread.join(WAIT)
        self.assertEqual(lookup_threads(), [last],
                         "more than one lookup thread survived off/on cycles")
        # One lookup per start, and none while the last thread waits.
        self.assertEqual(self.net.lookups, cycles + 1)
        time.sleep(0.1)
        self.assertEqual(self.net.lookups, cycles + 1)

    def test_restart_while_the_old_thread_is_still_finishing(self):
        """Off then on at once: the old thread is mid-lookup. It must not be
        mistaken for a running one, and it must not write its late result."""
        self._patch(S, "IP_REFRESH_SECONDS", 3600)
        self.net.release.clear()
        old = self.start()
        self.assertTrue(self.net.in_lookup.wait(WAIT))
        S.stop_ip_fetch_thread()
        new = self.start()
        self.assertIsNot(old, new)
        self.net.ip = "198.51.100.9"
        self.net.release.set()
        old.join(WAIT)
        self.assertFalse(old.is_alive())
        self.wait_for_cached("198.51.100.9")
        self.assertEqual(lookup_threads(), [new])

    # --- what the banner shows ---------------------------------------------

    def test_banner_text_for_each_state(self):
        with S.cache_lock:
            S.cached_ip = None
        self.assertIn("disabled", S.print_IP(True))
        self.assertIn("checking", S.print_IP(False))
        self.assertNotIn("None", S.print_IP(False))
        with S.cache_lock:
            S.cached_ip = ""
        self.assertIn("OFFLINE", S.print_IP(False))
        with S.cache_lock:
            S.cached_ip = "203.0.113.7"
        self.assertIn("203.0.113.7", S.print_IP(False))
        self.assertNotIn("203.0.113.7", S.print_IP(True))

    def test_offline_is_shown_and_no_lookup_is_made(self):
        self._patch(S, "IP_REFRESH_SECONDS", 3600)
        self.net.online = False
        self.start()
        self.wait_for_cached("")
        self.assertEqual(self.net.lookups, 0)
        self.assertIn("OFFLINE", S.print_IP(False))

    def test_banner_does_not_wait_for_a_slow_lookup(self):
        self._patch(S, "IP_REFRESH_SECONDS", 3600)
        self.net.release.clear()
        self.start()
        self.assertTrue(self.net.in_lookup.wait(WAIT))
        got = S.cache_lock.acquire(timeout=1)
        self.assertTrue(got, "the cache lock is held during the network lookup")
        S.cache_lock.release()
        self.assertIn("checking", S.print_IP(False))

    # --- the two banners ---------------------------------------------------

    def test_banners_with_display_off_stop_the_thread(self):
        self._patch(S, "IP_REFRESH_SECONDS", 3600)
        for banner in (S.display_watermark, S.display_bunker):
            with self.subTest(banner=banner.__name__):
                thread = self.start()
                self.wait_for_cached("203.0.113.7")
                with contextlib.redirect_stdout(io.StringIO()) as out:
                    banner(True)
                thread.join(WAIT)
                self.assertFalse(thread.is_alive())
                self.assertIn("IP fetching disabled", out.getvalue())
                self.assertNotIn("203.0.113.7", out.getvalue())

    def test_banners_with_display_off_never_touch_the_network(self):
        TOUCHED.clear()
        starts = []
        real_start = S.start_ip_fetch_thread
        self._patch(S, "start_ip_fetch_thread", lambda: (starts.append(1), real_start()))
        self._patch(S, "check_internet_connection", _blocked)
        self._patch(S, "get_public_ipv4", _blocked)
        with mock.patch("socket.create_connection", side_effect=_blocked), \
             mock.patch.object(S.subprocess, "check_output", side_effect=_blocked), \
             mock.patch.object(S.requests, "get", side_effect=_blocked), \
             contextlib.redirect_stdout(io.StringIO()):
            S.display_watermark(True)
            S.display_bunker(True)
        self.assertEqual(lookup_threads(), [])
        self.assertEqual(starts, [])
        self.assertEqual(TOUCHED, [])

    def test_banner_with_display_on_starts_exactly_one_thread(self):
        self._patch(S, "IP_REFRESH_SECONDS", 3600)
        with contextlib.redirect_stdout(io.StringIO()):
            S.display_watermark(False)
            self.started.append(S.ip_fetch_thread)
            S.display_watermark(False)
        self.assertEqual(len(lookup_threads()), 1)


if __name__ == "__main__":
    unittest.main()
