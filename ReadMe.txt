# NoRush — README

# WHAT IT IS
# ----------
# Android app (Kivy) that scans incoming SMS messages for scam/phishing
# tactics and shows a behavioral intervention before the user acts on them.
# Risk analysis can run on-device or be offloaded to a Flask server on your PC!
#
# Files:
#   main.py          - Main kivy app (controller, updating, reading information and passing through to risk_analyzer)
#   risk_analyzer.py - SMS risk scoring, also used by the server.
#   android_sms.py   - Android SMS broadcast receiver
#   storage.py       - Saves decisions and user state to android storage by JSON.
#   server.py        - Flask server (run on your PC, optional)
#   buildozer.spec   - APK build config


# PREREQUISITES
# -------------
# Python 3.10 or 3.11  
# To install prerequisites:
# pip install kivy flask
# To set up ngrok, go to https://dashboard.ngrok.com/get-started/setup/linux (Or windows. Whichever setup method you prefer.
# The authtoken is 3DCG46m24Y6w0LUl7vwOoOWg6yw_4LDsiqbjUWmdj9W13tgcj


# RUNNING ON DESKTOP
# ---------------------------------------------
# The SMS receiver won't do anything outside Android, but the UI and
# risk analyzer work fine. Demo buttons on the home screen let you test.
# To run the main app:
#   python3 main.py
#


# REMOTE SERVER 
# ------------------------
# Run on your PC. The app will POST SMS text to it for analysis and fall
# back to on-device scoring if it can't reach the server.
#
#   python3 server.py
#
# After this, 
#
# To make it reachable from your phone, use ngrok:
#   ngrok http 5000


# BUILDING THE APK
# ----------------
# WARNING : BUILDING THIS APK CAN BE TIMECONSUMING. THERE ARE SEVERAL DEPENDANCIES TO BE MET. IF YOU WANT TO SEE THE APK:
# The APK is here : https://drive.google.com/file/d/1AkkhdlExktJZ_teA6wo-X-gOrgKPafK3/view?usp=sharing
#
# 1. Install dependencies 
#      sudo apt install git zip unzip openjdk-17-jdk python3-pip
#      pip install buildozer cython
#
# 2. From the project directory (Make sure that the .py files and buildozer.spec file are in the same directory.
#      buildozer android debug
#    if the build fails at the gradle section, execute:
#    ./gradlew assembleDebug -x validateSigningDebug  
#    in the same folder as your generated gradle file.
#
#    First run downloads the Android SDK/NDK (~5 GB) and takes 20-40 min.
#    Output APK: bin/riskguard-0.1-arm64-v8a-debug.apk
#
# 3. Install on phone:
#      You can either just install the app on your phone by copying it to your phone and installing it from there, or:
#      Setup ADB:
#        Linux/WSL2: export PATH=$PATH:~/.buildozer/android/platform/android-sdk/platform-tools
#        Windows:    download https://developer.android.com/tools/releases/platform-tools
#                    and add the extracted folder to your system PATH
#        Enable USB debugging on your phone (By going to Settings->About Phone->Tap build number 7 times.
#        Settings -> Developer Options -> enable USB Debugging
#
#        
#        adb devices //check to see if it works
#        adb install bin/riskguard-0.1-arm64-v8a-debug.apk
#
