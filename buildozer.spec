[app]
title = Infinite Alchemy
package.name = infinitealchemy
package.domain = com.yourcompany
source.dir = .
main = main.py
version = 1.0.0
version.regex = __version__ = ['"]([^'"]*)['"]
version.filename = %(source.dir)s/main.py

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

# App signing (for release builds)
android.debug = 0

# Optimize APK
android.add_aars =     

# App store metadata
android.gradle_dependencies =     

# Launch screen background color
android.presplash_color = #0A0A0B

# App bundle settings (for Play Store)
android.release_artifact = aab

# Proguard (code obfuscation)
android.add_gradle_buildscript =     
android.gradle_build_dir =     

[buildozer]
log_level = 2
warn_on_root = 1
