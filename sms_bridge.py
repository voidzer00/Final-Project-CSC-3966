"""
sms_bridge.py
Listens on a local TCP socket for incoming SMS text injected via send_sms.py, and then
forwards it to risk_analyzer for analysing (specifically to Homescreen.recieve_sms())
"""

from __future__ import annotations

import re
import time
import socket
import hashlib
from threading import Thread
from typing import Optional

def normalise(text: str):
    #strip trailing and leading whtiespaces, and convert runs of whitespace into
    #a single whitespace.
    return re.sub(r'\s+', ' ', text.strip())


def _msg_fingerprint(text: str):
    #for efficiency. I create a md5 hash of the text and compare it in order to
    #detect duplicate messages.
    return hashlib.md5(text.encode()).hexdigest()[:10]

class SocketSMSSource:
    """
    Opens a local TCP socket and waits for connections from send_sms.py.
    Each connection delivers exactly one SMS, and then closes. The portnumbers must match
    for a valid session to be established.
    """

    def __init__(self, host: str = '127.0.0.1', port: int = 55755):
        self._host = host
        self._port = port
        self._running = False
        self._thread: Optional[Thread] = None
        self._server = None
        self._on_sms = None

    def set_callback(self, cb):
        #register as the reciever (only called once)
        self._on_sms = cb

    def start(self):
        #start the background listener! (but only if it isnt running)
        if self._running:
            return
        self._running = True
        self._thread = Thread(target=self._loop, daemon=True) #this is important.
        #without threading loop would spinlock forever, so i create a new thread to run that.
        self._thread.start()

    def stop(self) -> None:
        #closes the socket.
        self._running = False
        # Closing the socket unblocks accept() immediately so the thread exits cleanly!
        if self._server:
            try:
                self._server.close()
            except Exception:
                pass

    def _loop(self):
        # AF_INET = IPv4, SOCK_STREAM = TCP
        self._server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # the problem here is that when the app shuts down, the port is stuck in the TIME_WAIT state for 60s.
        # this might cause problems, so REUSE_ADDR allows for the port number to be reused immediately after
        # the app closes.
        self._server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server.bind((self._host, self._port))
        self._server.listen(5)
        # 1 second timeout so the while loop can check _running regularly
        # rather than blocking on accept() forever!
        self._server.settimeout(1.0)

        while self._running:
            try:
                conn, _ = self._server.accept()  # spinlock until connected
                with conn:
                    data = b''
                    while True:
                        chunk = conn.recv(4096)
                        if not chunk:
                            # Empty chunk = send_sms.py closed the connection,
                            # which signals the full message has been sent
                            break
                        data += chunk
                    text = data.decode('utf-8').strip()
                    if text and self._on_sms:
                        self._on_sms(text)  # Decodes the text and sends it up to handle_raw!
            except OSError:
                # settimeout(1.0) raises OSError every second if nothing connects —
                # that's fine, check running_again (maybe there's a better way to do this?
                pass


class SMSBridge:
    """
    Receives raw text from SocketSMSSource, normalises it, suppresses
    duplicates, then forwards it to HomeScreen.receive_sms().
    """

    def __init__(self, source, on_sms, dedup_window: float = 5.0):
        self._source       = source
        self._on_sms       = on_sms
        self._dedup_window = dedup_window
        # Maps message fingerprint → timestamp of last delivery
        self._seen: dict[str, float] = {}
        # Register ourselves as the receiver so the source knows where to send messages!
        self._source.set_callback(self.handle_raw)

    def start(self):
        self._source.start()

    def stop(self):
        self._source.stop()

    def handle_raw(self, raw: str):
        clean = normalise(raw)
        if not clean:
            return

        fp  = _msg_fingerprint(clean)
        now = time.monotonic()

        # Ignore if we've already delivered this exact message within dedup_window seconds.
        # This is neat, because it prevents flooding of spam messages.
        if fp in self._seen and (now - self._seen[fp]) < self._dedup_window:
            return

        self._seen[fp] = now
        self.deliver(clean)

    def deliver(self, text: str):
        try:
            self._on_sms(text)
        except Exception as exc:
            print("error delivering the mesage.")

def create_bridge_for_app(home_screen) -> SMSBridge:
    """Creates and returns a bridge wired to HomeScreen.receive_sms(). Not yet started."""
    source = SocketSMSSource()
    return SMSBridge(source=source, on_sms=home_screen.receive_sms)
