# 本机构建指南 (BUILD_LOCAL.md)

> 适用于当前 macOS 机器（Apple Silicon / ARM64）。
> 下次构建前先读此文件，按步骤执行即可。

## 环境概述

| 项目 | 值 |
|------|-----|
| 构建用 Python | Managed Python 3.13.12（arm64） |
| Python 路径 | `/Users/jokkerling/.workbuddy/binaries/python/versions/3.13.12/bin/python3` |
| 虚拟环境（site-packages） | `/Users/jokkerling/.workbuddy/binaries/python/envs/default/` |
| pip 路径 | `/Users/jokkerling/.workbuddy/binaries/python/envs/default/bin/pip` |
| 依赖 | rumps, py2app |
| 构建产物 | `dist/番茄时钟.app`（arm64 原生） |
| DMG 产物 | `releases/PomodoroTimer-v{VERSION}.dmg` |

**不能用的 Python：**
- `/usr/bin/python3`（系统 Python 3.9，ARM64 但无编译器，无法安装 pyobjc-core）
- `/opt/miniconda3/bin/python3`（x86_64，构建产物架构错误）

## 一次性环境准备（首次构建或重装系统后）

### 1. 安装依赖

```bash
/Users/jokkerling/.workbuddy/binaries/python/envs/default/bin/pip install rumps py2app
```

### 2. 修复 pyobjc 签名问题

Managed Python 3.13 的二进制带有 `runtime` hardened signature，pip 安装的 pyobjc .so 是 `adhoc` 签名，
Team ID 不匹配导致 `dlopen` 失败。解决：将 Python 二进制重签为 ad-hoc。

```bash
# 重签 Python 解释器
codesign -f -s - /Users/jokkerling/.workbuddy/binaries/python/versions/3.13.12/bin/python3

# 重签所有 .so（含 pyobjc 等）
find /Users/jokkerling/.workbuddy/binaries/python/envs/default/lib/python3.13/site-packages -name "*.so" | xargs codesign -f -s -

# 验证
/Users/jokkerling/.workbuddy/binaries/python/envs/default/bin/python -c "import rumps; print('rumps OK')"
# 必须输出: rumps OK
```

### 3. 修复 py2app 的 zlib.__file__ bug（Python 3.13+）

Python 3.13 移除了 `zlib.__file__` 属性，py2app 0.28.10 构建时崩溃。
需要打补丁到 `py2app/build_app.py`。

```bash
# 补丁文件位置
PY2APP_BUILD=/Users/jokkerling/.workbuddy/binaries/python/envs/default/lib/python3.13/site-packages/py2app/build_app.py
```

找到约 2440 行，将：

```python
        self.copy_file(arcname, arcdir)
        if sys.version_info[0] != 2:
            import zlib

            self.copy_file(zlib.__file__, os.path.dirname(arcdir))
```

替换为：

```python
        self.copy_file(arcname, arcdir)
        if sys.version_info[0] != 2:
            import zlib

            if hasattr(zlib, '__file__') and zlib.__file__ is not None:
                self.copy_file(zlib.__file__, os.path.dirname(arcdir))
```

> 提示：可以用 WorkBuddy 的 `py2app-python3.13-fix` skill 自动完成此步骤。
> 如果 `py2app` 升级后此补丁仍需手动验证，检查补丁是否还在。

## 每次构建步骤

### 前置检查（30 秒）

```bash
# 1. 确认 Python 是 arm64
/Users/jokkerling/.workbuddy/binaries/python/envs/default/bin/python -c "import platform; print(platform.machine())"
# 必须输出: arm64

# 2. 确认 rumps 能正常导入
/Users/jokkerling/.workbuddy/binaries/python/envs/default/bin/python -c "import rumps; print('rumps OK')"
# 必须输出: rumps OK

# 3. 确认 py2app zlib 补丁已打
grep -c "hasattr(zlib" /Users/jokkerling/.workbuddy/binaries/python/envs/default/lib/python3.13/site-packages/py2app/build_app.py
# 必须输出: 1（如果输出 0 说明补丁丢失，需要重新打）
```

### 构建 .app

```bash
cd /Volumes/Jokker/Code/番茄时钟
rm -rf build dist
/Users/jokkerling/.workbuddy/binaries/python/envs/default/bin/python make_icon.py
/Users/jokkerling/.workbuddy/binaries/python/envs/default/bin/python setup.py py2app
```

> **重要：** 以上命令必须在 WorkBuddy 沙箱外执行（`dangerouslyDisableSandbox: true`）。
> 沙箱内 managed Python 的 `dlopen` 受限，会导致 pyobjc 加载失败。

### 验证构建产物

```bash
file dist/番茄时钟.app/Contents/MacOS/pomodoro_timer
# 必须输出: Mach-O 64-bit executable arm64
```

### 打包 DMG

```bash
rm -f /tmp/pomodoro_template.dmg
hdiutil create -size 200m -fs HFS+ -type UDIF -volname "番茄时钟" /tmp/pomodoro_template.dmg
hdiutil attach -nobrowse -mountpoint /tmp/pomodoro_mount /tmp/pomodoro_template.dmg
ditto "dist/番茄时钟.app" "/tmp/pomodoro_mount/番茄时钟.app"
ln -sf /Applications "/tmp/pomodoro_mount/Applications"
cp icon.icns "/tmp/pomodoro_mount/.VolumeIcon.icns"
/usr/bin/SetFile -a C "/tmp/pomodoro_mount"
hdiutil detach "/tmp/pomodoro_mount"
rm -rf /tmp/pomodoro_mount
VERSION=$(grep '__version__' pomodoro_timer.py | head -1 | sed "s/.*= \"//;s/\".*//")
hdiutil convert /tmp/pomodoro_template.dmg -format UDZO -ov -o "releases/PomodoroTimer-v${VERSION}.dmg"
rm -f /tmp/pomodoro_template.dmg
```

## 完整一键构建（确认环境已就绪后）

```bash
cd /Volumes/Jokker/Code/番茄时钟
rm -rf build dist

/Users/jokkerling/.workbuddy/binaries/python/envs/default/bin/python make_icon.py
/Users/jokkerling/.workbuddy/binaries/python/envs/default/bin/python setup.py py2app

# 验证
file dist/番茄时钟.app/Contents/MacOS/pomodoro_timer

# 打包 DMG
rm -f /tmp/pomodoro_template.dmg
hdiutil create -size 200m -fs HFS+ -type UDIF -volname "番茄时钟" /tmp/pomodoro_template.dmg
hdiutil attach -nobrowse -mountpoint /tmp/pomodoro_mount /tmp/pomodoro_template.dmg
ditto "dist/番茄时钟.app" "/tmp/pomodoro_mount/番茄时钟.app"
ln -sf /Applications "/tmp/pomodoro_mount/Applications"
cp icon.icns "/tmp/pomodoro_mount/.VolumeIcon.icns"
/usr/bin/SetFile -a C "/tmp/pomodoro_mount"
hdiutil detach "/tmp/pomodoro_mount"
rm -rf /tmp/pomodoro_mount
VERSION=$(grep '__version__' pomodoro_timer.py | head -1 | sed "s/.*= \"//;s/\".*//")
hdiutil convert /tmp/pomodoro_template.dmg -format UDZO -ov -o "releases/PomodoroTimer-v${VERSION}.dmg"
rm -f /tmp/pomodoro_template.dmg
```

## 排障速查

| 现象 | 原因 | 解决 |
|------|------|------|
| `No module named 'rumps'` | 依赖未安装 | `pip install rumps py2app` |
| `code signature ... different Team IDs` | pyobjc 签名不匹配 | `codesign -f -s -` 重签 Python 和所有 .so |
| `AttributeError: module 'zlib' has no attribute '__file__'` | py2app zlib 补丁丢失 | 重新打补丁（见上方步骤 3） |
| `Python 架构为 x86_64` | 用错了 Python | 确认使用 managed Python 3.13 路径 |
| `Cannot locate a working compiler` | 系统无 Xcode CLT 或用了错误 Python | 使用 managed Python 3.13 |
| 构建 App 被 Gatekeeper 阻止 | 未签名 App | `xattr -cr dist/番茄时钟.app` |
