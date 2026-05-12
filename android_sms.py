"""
android_sms.py - Real SMS interception for Android.
I apologize for the heinous amount of debugging messages. Reading on android is very tricky
to get right, so i had to put debug messages in every other place.
"""
from __future__ import annotations
import re, time, hashlib

def _is_android():
    try:
        import jnius  # noqa
        return True
    except Exception:
        return False

_ON_ANDROID = _is_android()


def _normalise(text):
    return re.sub(r'\s+', ' ', text.strip())


def _fingerprint(text):
    return hashlib.md5(text.encode()).hexdigest()[:10]


class AndroidSMSReceiver:
    def __init__(self, dedup_window=5.0):
        self._dedup_window = dedup_window
        self._seen = {}
        self._on_sms = None
        self._receiver = None

    def start(self, on_sms):
        self._on_sms = on_sms
        print(f"[AndroidSMSReceiver] start() called. on_android={_ON_ANDROID}")
        if not _ON_ANDROID:
            print("Not on android. Reciever inactive...")
            return
        from android.permissions import request_permissions, Permission  # noqa
        print("[AndroidSMSReceiver] Requesting SMS permissions...")
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
        print(f"[AndroidSMSReceiver] Permission result: {list(zip(permissions, grants))}")
        if not all(grants):
            print("[AndroidSMSReceiver] SMS permissions denied — receiver not registered.")
            return
        from android.broadcast import BroadcastReceiver  # noqa
        self._receiver = BroadcastReceiver(
            self._on_broadcast,
            actions=["android.provider.Telephony.SMS_RECEIVED"]
        )
        self._receiver.start()
        print("[AndroidSMSReceiver] Receiver registered and listening.")

    def _on_broadcast(self, context, intent):
        print("[AndroidSMSReceiver] Broadcast received!")
        try:
            from jnius import autoclass  # noqa
            SmsMessage = autoclass("android.telephony.SmsMessage")
            bundle = intent.getExtras()
            if not bundle:
                print("[AndroidSMSReceiver] No extras bundle in intent.")
                return
            pdus_obj = bundle.get("pdus")
            if not pdus_obj:
                print("[AndroidSMSReceiver] No PDUs found in bundle.")
                return
            fmt = bundle.getString("format")
            print(f"[AndroidSMSReceiver] PDU count={len(pdus_obj)}, format={fmt}")
            parts = []
            for pdu in pdus_obj:
                sms = (SmsMessage.createFromPdu(pdu, fmt)
                    if fmt else SmsMessage.createFromPdu(pdu))
                body = sms.getMessageBody()
                print(f"[AndroidSMSReceiver] PDU body: '{body}'")
                if body:
                    parts.append(body)
            text = "".join(parts).strip()
            print(f"[AndroidSMSReceiver] RAW TEXT: '{text}'")
            print(f"[AndroidSMSReceiver] Full text: '{text[:80]}'")
            if text:
                self._deliver(text)
            else:
                print("[AndroidSMSReceiver] Empty text after joining PDUs.")
        except Exception as e:
            print(f"[AndroidSMSReceiver] Broadcast error: {e}")

    def _deliver(self, raw):
        clean = _normalise(raw)
        if not clean:
            print("[AndroidSMSReceiver] Empty after normalise — dropped.")
            return
        fp, now = _fingerprint(clean), time.monotonic()
        if fp in self._seen and (now - self._seen[fp]) < self._dedup_window:
            print(f"[AndroidSMSReceiver] Duplicate suppressed (fp={fp}).")
            return
        self._seen[fp] = now
        print(f"[AndroidSMSReceiver] Delivering: '{clean[:80]}'")
        if self._on_sms:
            try:
                # The broadcast fires on a background thread.
                # Kivy UI calls must happen on the main thread, so we
                # schedule the callback there via Clock.schedule_once.
                from kivy.clock import Clock
                Clock.schedule_once(lambda dt: self._on_sms(clean), 0)
            except Exception as e:
                print(f"[AndroidSMSReceiver] Callback error: {e}")
        else:
            print("[AndroidSMSReceiver] No callback set — message dropped!")


def create_receiver_for_app(home_screen):
    return AndroidSMSReceiver()
