"""
android_sms.py - Real SMS interception for Android.
I apologize for the heinous amount of debugging messages. Reading on android is very tricky
to get right, so i had to put debug messages in every other place.
"""
from __future__ import annotations

import re
import time
import hashlib
import traceback


def _is_android():
    try:
        import jnius  # noqa
        return True
    except Exception:
        return False


_ON_ANDROID = _is_android()


def _normalise(text: str) -> str:
    return re.sub(r'\s+', ' ', text or "").strip()


def _fingerprint(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()[:12]


class AndroidSMSReceiver:
    def __init__(self, dedup_window=5.0):
        self._dedup_window = dedup_window
        self._seen = {}  # fp -> timestamp
        self._on_sms = None
        self._receiver = None

    def start(self, on_sms):
        self._on_sms = on_sms

        print(f"[SMS] start() on_android={_ON_ANDROID}")

        if not _ON_ANDROID:
            print("[SMS] Not Android environment → inactive")
            return

        try:
            from android.permissions import request_permissions, Permission  # noqa
        except Exception:
            print("[SMS] Permission module not available")
            return

        print("[SMS] Requesting permissions...")

        request_permissions(
            [Permission.RECEIVE_SMS, Permission.READ_SMS],
            self._on_permissions_result
        )

    def stop(self):
        if self._receiver:
            try:
                self._receiver.stop()
            except Exception:
                pass
        self._receiver = None


    def _on_permissions_result(self, permissions, grants):
        print(f"[SMS] Permission result: {list(zip(permissions, grants))}")

        if not all(grants):
            print("[SMS] Permissions denied")
            return

        try:
            from android.broadcast import BroadcastReceiver  # noqa
        except Exception as e:
            print(f"[SMS] BroadcastReceiver import failed: {e}")
            return

        self._receiver = BroadcastReceiver(
            self._on_broadcast,
            actions=["android.provider.Telephony.SMS_RECEIVED"]
        )

        self._receiver.start()
        print("[SMS] Receiver started")

    # -------------------------
    # Broadcast handler
    # -------------------------
    def _on_broadcast(self, context, intent):

        try:
            from jnius import autoclass  # noqa
            SmsMessage = autoclass("android.telephony.SmsMessage")

            bundle = intent.getExtras()
            if not bundle:
                print("[SMS] No bundle")
                return

            pdus_obj = bundle.get("pdus")
            if not pdus_obj:
                print("[SMS] No PDUs")
                return

            fmt = bundle.getString("format")
            print(f"[SMS] PDUs={len(pdus_obj)} format={fmt}")

            parts = []

            for i, pdu in enumerate(pdus_obj):
                try:
                    if fmt:
                        sms = SmsMessage.createFromPdu(pdu, fmt)
                    else:
                        sms = SmsMessage.createFromPdu(pdu)

                    body = sms.getMessageBody()
                    print(f"[SMS] PDU {i} body={body}")

                    if body:
                        parts.append(body)

                except Exception:
                    print(f"[SMS] PDU {i} parse FAILED")
                    traceback.print_exc()

            text = "".join(parts).strip()

            print(f"[SMS] RAW: {text}")

            if not text:
                print("[SMS] Empty message after parsing")
                return

            self._deliver(text)

        except Exception:
            print("[SMS] Broadcast crash")
            traceback.print_exc()

    #delivery, cleaning, dedup 
    def _deliver(self, raw: str):
        clean = _normalise(raw)

        if not clean:
            print("[SMS] Dropped empty after normalize")
            return

        fp = _fingerprint(clean)
        now = time.monotonic()

        last = self._seen.get(fp)
        if last and (now - last) < self._dedup_window:
            print(f"[SMS] Duplicate blocked fp={fp}")
            return

        self._seen[fp] = now

        print(f"[SMS] DELIVER → {clean[:80]}")

        if not self._on_sms:
            print("[SMS] No callback registered")
            return

        #i dont know what was causing this to crash, but doing the entire thing again seems to have fixed it.
        try:
            from kivy.clock import Clock
            Clock.schedule_once(lambda dt: self._safe_callback(clean), 0)
        except Exception:
            print("[SMS] Kivy Clock failed, calling directly")
            self._safe_callback(clean)

    def _safe_callback(self, text: str):
        try:
            self._on_sms(text)
        except Exception:
            print("[SMS] Callback crashed")
            traceback.print_exc()


def create_receiver_for_app(home_screen):
    return AndroidSMSReceiver()


