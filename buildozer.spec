[app]
title = Infinite Alchemy
package.name = infinitealchemy
package.domain = com.loganlarrabee
source.dir = .
main = main.py
version = 1.3.1
#version.regex = __version__ = ['"]([^'"]*)['"]
#version.filename = %(source.dir)s/main.py

# App description and metadata
description = Create unlimited combinations in this addictive alchemy crafting game! Start with basic elements and discover hundreds of new items.
author = logan larrabee
copyright = logan inc

# Icon and splash screen
icon.filename = %(source.dir)s/assets/icon.png
presplash.filename = %(source.dir)s/assets/splash.png

# App store optimization
android.meta_data = com.google.android.gms.ads.APPLICATION_ID:ca-app-pub-xxxxxxxxxxxxxxxx~xxxxxxxxxx

requirements = python3,kivy==2.3.0,openssl,libffi,openai==1.51.0,httpx,httpcore,h11,certifi,urllib3,idna,charset-normalizer

# Permissions
android.permissions = INTERNET,ACCESS_NETWORK_STATE,WAKE_LOCK

# Build configuration
android.build_tools = 35.0.0
android.api = 34
android.minapi = 24
android.ndk = 25b
android.arch = arm64-v8a,armeabi-v7a
orientation = portrait
fullscreen = 0

# Auto-accept license prompts
android.accept_sdk_license = True


# Launch screen background color
android.presplash_color = #0A0A0B

# App bundle settings (for Play Store)
android.release_artifact = aab

[buildozer]
log_level = 2
warn_on_root = 1
