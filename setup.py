"""
setup.py - py2app 打包配置
用法: python3 setup.py py2app
"""

from setuptools import setup

APP = ["pomodoro_timer.py"]
DATA_FILES = []
OPTIONS = {
    "argv_emulation": False,
    "iconfile": "icon.icns",
    "plist": {
        "CFBundleName": "番茄时钟",
        "CFBundleDisplayName": "🍅 番茄时钟",
        "CFBundleIdentifier": "com.pomodoro.timer",
        "CFBundleVersion": "1.2.0",
        "CFBundleShortVersionString": "1.2.0",
        "CFBundleExecutable": "pomodoro_timer",
        "CFBundleDevelopmentRegion": "zh_CN",
        "NSHumanReadableCopyright": "Copyright © 2026. All rights reserved.",
        "LSUIElement": True,  # 无 Dock 图标，仅菜单栏
    },
    "packages": ["rumps"],
    # 添加 libffi 依赖（_ctypes 需要）
    "frameworks": ["/opt/miniconda3/lib/libffi.8.dylib"],
    "includes": ["ctypes"],
    "dylib_excludes": [],
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
