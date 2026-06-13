[app]
title = YouTube Clipper
package.name = ytclipper
package.domain = org.ytclipper
source.dir = .
source.include_exts = py,png,jpg,kv,atlas
version = 1.0
requirements = python3,yt-dlp,google-api-python-client,google-auth-oauthlib,kivy,ffmpeg
orientation = portrait
fullscreen = 0
android.api = 33
android.minapi = 21
android.ndk = 25b
android.sdk = 33
android.permissions = INTERNET,ACCESS_NETWORK_STATE
android.archs = arm64-v8a
android.accept_sdk_license = True

[buildozer]
log_level = 2
warn_on_root = 1
