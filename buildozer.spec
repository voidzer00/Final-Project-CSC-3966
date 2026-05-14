[app]

# App identity
title = NoFlow
package.name = noflow

# Source
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json
source.exclude_dirs = venv,.buildozer,bin
source.exclude_patterns = send_sms.py,sms_bridge.py

# Version
version = 0.1

# Requirements
requirements = python3,kivy,pyjnius

# Orientation
orientation = portrait

# Permissions
android.permissions = INTERNET, RECEIVE_SMS, READ_SMS, WRITE_EXTERNAL_STORAGE, READ_EXTERNAL_STORAGE

# Android build settings
android.api = 33
android.minapi = 26
android.ndk_api = 26
android.ndk = 25b
android.archs = arm64-v8a


android.accept_sdk_license = True

# Fullscreen
fullscreen = 0

# Logging
log_level = 2
