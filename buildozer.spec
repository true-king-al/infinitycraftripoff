[app]
title = Infinite Craft Game
package.name = infinitycraft
package.domain = org.al
source.dir = .
main = infinitecraft.py
version = 0.2

requirements = python3,kivy==2.3.0,openssl,libffi,openai==1.51.0,httpx, httpcore, certifi,urllib3,idna,charset-normalizer
android.permissions = INTERNET

# Pin stable, not RC junk
android.build_tools = 35.0.0
android.api = 34
android.minapi = 24
android.arch = arm64-v8a
orientation = portrait

# Auto-accept license prompts
android.accept_sdk_license = True
