[app]
title = YouTube Clipper
package.name = youtubeclipper
package.domain = org.youtubclipper
source.dir = .
source.include_exts = py,png,jpg,kv,atlas
version = 1.0
requirements = python3,yt-dlp,google-api-python-client,google-auth-oauthlib,kivy
orientation = portrait
osx.python_version = 3
osx.kivy_version = 2.2.1
fullscreen = 0

[buildozer]
log_level = 2
warn_on_root = 1

[app]
android.api = 33
android.minapi = 21
android.ndk = 25b
android.sdk = 33
android.gradle_dependencies = 
android.add_src = 
android.permissions = INTERNET,ACCESS_NETWORK_STATE,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE
android.extra_jars = 
android.add_libs_arm64 = 
android.add_libs_armv7a = 
android.add_libs_x86 = 
android.add_libs_x86_64 = 
android.ffmpeg = True

[buildozer]
# Copy ffmpeg binary for Android
android.archs = arm64-v8a

[app]
# Include ffmpeg Android binary
android.add_libs_arm64 = 

# p4a hooks
p4a.hooks = hooks.py
