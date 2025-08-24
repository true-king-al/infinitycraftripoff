[app]
title = Infinite Craft Game
package.name = infinitycraft
package.domain = org.al
source.dir = .
main = infinitecraft.py
version = 0.1
requirements = python3,kivy==2.3.0,openssl,libffi,openai==1.51.0,httpx,certifi,urllib3,idna,charset-normalizer
android.permissions = INTERNET
android.arch = arm64-v8a
android.minapi = 24
android.api = 34
android.ndk = 25b

[buildozer]
log_level = 2
