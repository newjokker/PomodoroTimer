# 构建指南

从源码构建 macOS `.app` 和 `.dmg` 安装包。

## 前置条件

| 条件 | 说明 |
|------|------|
| macOS | 仅支持 macOS |
| ARM64 Python 3.6+ | **必须用 ARM64 原生 Python**（Apple Silicon 上 x86_64 构建的 App 无法在无 Rosetta 2 的机器上运行） |
| Xcode CLT | Xcode Command Line Tools（`xcode-select --install`） |

## 验证架构

构建前必须确认 Python 是 ARM64：

```bash
python3 -c "import platform; print(platform.machine())"
# 必须输出: arm64
# 如果输出 x86_64，请安装 ARM64 原生 Python
```

## 一键构建

```bash
make dmg
```

这会自动检查架构、清理旧产物、生成图标、构建 `.app`，然后打包为 `.dmg`。生成的文件在 `releases/` 目录。

## 逐步构建

```bash
make install    # 安装依赖 (rumps, py2app)
make icon       # 生成应用图标
make app        # 构建 .app → dist/番茄时钟.app
make dmg        # 打包 .dmg
```

## Python 3.13 兼容性问题

### py2app 0.28.10 的 `zlib.__file__` Bug

Python 3.13 移除了 `zlib` 模块的 `__file__` 属性，py2app 0.28.10 在构建时会崩溃：

```
AttributeError: module 'zlib' has no attribute '__file__'
```

**修复方法：** 编辑 py2app 安装目录下的 `build_app.py`（第 2443 行附近）：

```bash
# 找到文件位置
python3 -c "import py2app.build_app; print(py2app.build_app.__file__)"
```

将这段代码：

```python
        self.copy_file(arcname, arcdir)
        if sys.version_info[0] != 2:
            import zlib

            self.copy_file(zlib.__file__, os.path.dirname(arcdir))
```

改为：

```python
        self.copy_file(arcname, arcdir)
        if sys.version_info[0] != 2:
            import zlib

            if hasattr(zlib, '__file__') and zlib.__file__ is not None:
                self.copy_file(zlib.__file__, os.path.dirname(arcdir))
```

> 注意：此修复已内置于 `py2app-python3.13-fix` skill 中，WorkBuddy 在构建时会自动处理。

## 故障排查

### "错误: Python 架构为 x86_64，必须是 arm64"

make 会阻塞使用 x86_64 Python 构建。解决：安装 ARM64 原生 Python（推荐通过 Xcode CLT 的 `/usr/bin/python3`）。

### 构建出的 App 打不开 / 闪退

1. 检查架构：`file dist/番茄时钟.app/Contents/MacOS/pomodoro_timer`（必须是 `arm64`）
2. 如果显示 `x86_64`，你的 Python 不是 ARM64，请切换
3. 检查 Info.plist 是否存在：`ls dist/番茄时钟.app/Contents/Info.plist`
4. 如果没有 Info.plist，构建中途崩溃了（通常是 py2app bug）

### 构建出的 App 被 Gatekeeper 阻止

这是正常的——App 未签名。解决方案：
- 右键点 App → "打开"（绕过 Gatekeeper）
- 或：`xattr -cr dist/番茄时钟.app && open dist/番茄时钟.app`

### hdiutil 卷名冲突

如果出现 `Resource busy` 或挂载失败：
```bash
# 清理所有残留
hdiutil detach /tmp/pomodoro_mount -force 2>/dev/null
rm -rf /tmp/pomodoro_mount
rm -f /tmp/pomodoro_template.dmg
```

## 版本发布

构建的 DMG 放入 `releases/` 文件夹：

```
releases/
├── PomodoroTimer-v1.0.0.dmg
├── PomodoroTimer-v1.1.0.dmg
└── ...
```

`releases/` 已在 `.gitignore` 中，不会被提交到 Git。
