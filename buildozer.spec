[app]
title = Infinite Craft Game
package.name = infinitycraft
package.domain = org.al
source.dir = .
main = infinitecraft.py
version = 0.1

# Keep requirements lean; include ssl/ffi explicitly
requirements = python3,kivy==2.3.0,openssl,libffi,openai==1.51.0,httpx,certifi,urllib3,idna,charset-normalizer

android.permissions = INTERNET
orientation = portrait
fullscreen = 0

# Build only 64-bit to cut time and complexity
android.arch = arm64-v8a
android.minapi = 24
android.api = 34

# Make p4a use freshest recipes if your image is crusty
p4a.branch = develop

[buildozer]
log_level = 1
