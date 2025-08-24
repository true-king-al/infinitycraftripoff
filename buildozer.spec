[app]
title = Infinite Craft Game
package.name = infinitycraft
package.domain = org.al

# where your source lives (current folder)
source.dir = .
# your entrypoint file
main = infinitecraft.py

# bump this when you want new installs to overwrite old
version = 0.1

# keep these minimal but complete for networking
requirements = python3,kivy==2.3.0,openai==1.51.0,httpx,certifi,urllib3,idna,charset-normalizer
android.permissions = INTERNET

# UI bits
orientation = portrait
fullscreen = 0

# target SDKs (safe defaults)
android.minapi = 24
android.api = 34

[buildozer]
log_level = 2
