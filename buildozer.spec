[app]

title = Task Planner
package.name = taskplanner
package.domain = org.taskplanner

source.dir = .
source.include_exts = py,png,jpg,kv,atlas,db

version = 1.0

requirements = python3,kivy==2.3.0,kivymd==1.2.0,pillow,sqlite3,certifi

orientation = portrait
fullscreen = 0

android.permissions = 
android.api = 33
android.minapi = 21
android.ndk = 25b
android.accept_sdk_license = True

[buildozer]

log_level = 2
warn_on_root = 1
