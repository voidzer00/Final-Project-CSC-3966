"""
send_sms.py — Inject a test SMS into the running RiskGuard app.
The app must already be running. Messages are delivered instantly
via a local socket and analysed.
"""

import socket
import sys

HOST = '127.0.0.1' #localhost//loopback address
PORT = 55755 #random source port (that i will always use!)

def send(message: str) -> None:
    try:
        #Try to open up a connection to the app
        with socket.create_connection((HOST, PORT), timeout=5) as sock:
            sock.sendall(message.encode('utf-8')) #sendall will convert the string into bytes and send it to our app in one go.
        print("Sent!")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python send_sms.py MESSAGE")
        sys.exit(1)
    send(' '.join(sys.argv[1:])) #Sends the message to send(), which then sends it to our app.
