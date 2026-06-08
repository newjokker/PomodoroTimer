# 🏗 构建指南 — 番茄时钟

本项目使用 `py2app` 将 Python 脚本打包为 macOS 独立 App，再生成 DMG 安装包。

---

## 前置依赖

```bash
# 安装运行依赖
pip3 install rumps

# 安装打包工具
pip3 install py2app
```

> ⚠️ 建议使用 **系统 Python**（如 `/opt/miniconda3/bin/python3`）而非虚拟环境打包，以减少动态库兼容性问题。

---

## 分步构建

### 第 1 步：生成应用图标（可选）

```bash
python3 make_icon.py
```

生成后的 `icon.icns` 会被 `setup.py` 自动引用。

### 第 2 步：打包为 .app

```bash
# 清理旧构建
rm -rf build dist

# 构建
python3 setup.py py2app
```

产物：`dist/番茄时钟.app`（约 30MB）

### 第 3 步：创建 DMG 安装包

```bash
# 创建空白 DMG 模板
hdiutil create -size 200m -fs HFS+ -type UDIF -volname "番茄时钟" template.dmg

# 挂载
hdiutil attach -nobrowse -owners off template.dmg

# 拷贝 App 和 /Applications 快捷方式
ditto "dist/番茄时钟.app" "/Volumes/番茄时钟/番茄时钟.app"
ln -s /Applications "/Volumes/番茄时钟/Applications"

# 设置卷图标
cp icon.icns "/Volumes/番茄时钟/.VolumeIcon.icns"
/usr/bin/SetFile -a C "/Volumes/番茄时钟"

# （可选）定制 Finder 窗口布局
osascript -e '
tell application "Finder"
    tell disk "番茄时钟"
        open
        set current view of container window to icon view
        set toolbar visible of container window to false
        set statusbar visible of container window to false
        set the bounds of container window to {200, 200, 700, 450}
        set theViewOptions to the icon view options of container window
        set arrangement of theViewOptions to not arranged
        set icon size of theViewOptions to 128
        set position of item "番茄时钟.app" of container window to {120, 180}
        set position of item "Applications" of container window to {460, 180}
        close
    end tell
end tell
'

# 卸载
hdiutil detach "/Volumes/番茄时钟"

# 压缩为最终 DMG（UDZO 格式）
hdiutil convert template.dmg -format UDZO -ov -o "番茄时钟.dmg"

# 清理
rm template.dmg
```

产物：`番茄时钟.dmg`（约 30MB）

---

## 已修复的 Bug

### Bug：Launch Error / "See the py2app website for debugging launch issues"

**症状**：双击 .app 或从 DMG 安装后启动，弹出错误对话框"Launch error / See the py2app website for debugging launch issues"。

**根因**：`_ctypes` 模块依赖 `libffi.8.dylib`，但 py2app 没有自动将其打包到 `Contents/Frameworks/` 中。

**排查步骤**（来自 [py2app 调试文档](https://py2app.readthedocs.io/en/latest/debugging.html)）：

```bash
# 1. 从终端直接启动，观察真实错误信息
dist/番茄时钟.app/Contents/MacOS/pomodoro_timer

# 输出类似：
# ImportError: dlopen(…/_ctypes.so): Library not loaded: @rpath/libffi.8.dylib
```

**修复**：在 `setup.py` 的 `OPTIONS` 中显式添加 `frameworks` 配置：

```python
OPTIONS = {
    # ...
    "frameworks": ["/opt/miniconda3/lib/libffi.8.dylib"],
    "includes": ["ctypes"],
    "dylib_excludes": [],
}
```

然后重新执行 `python3 setup.py py2app`。

**验证**：打包后确认 `libffi.8.dylib` 已存在于 `Contents/Frameworks/` 中：

```bash
ls -la dist/番茄时钟.app/Contents/Frameworks/
# 应看到: libffi.8.dylib  libpython3.12.dylib
```

再从终端启动确认无报错。

---

## 一键构建

也可以使用 `Makefile` 快速执行：

```bash
make install    # 安装依赖
make app        # 构建 .app
make dmg        # 构建 DMG
make release    # 打标签 + 构建 DMG
make clean      # 清理构建产物
```

---

## GitHub Actions 自动发布

项目配置了 CI/CD 工作流（`.github/workflows/release.yml`），推送 Git 标签即可自动构建并发布 Release：

```bash
# 版本号从 pomodoro_timer.py 的 __version__ 自动读取
# 更新版本号后：

git add -A
git commit -m "Release v1.0.0"
git tag v1.0.0
git push origin v1.0.0    # ← 触发 Actions 自动构建
```

GitHub Actions 会自动：
1. 在 `macos-latest` runner 上构建 .app
2. 创建 DMG 安装包（文件名含版本号）
3. 创建 GitHub Release 并上传 DMG

---

## 如何发布一个新版本

```bash
# 1. 更新版本号
#    编辑 pomodoro_timer.py 的 __version__

# 2. 更新 CHANGELOG.md
#    在顶部新增 [x.y.z] 条目

# 3. 提交 + 打标签
git add -A
git commit -m "Release v{版本号}"
git tag v{版本号}

# 4. 推送（触发 Actions 自动构建）
git push origin v{版本号}

# 5. 等待 Actions 完成
#    访问: https://github.com/jokkerling/pomodoro-timer/actions
```

| 问题 | 方法 |
|------|------|
| Launch Error 弹窗 | 终端执行 `dist/xxx.app/Contents/MacOS/xxx` 查看真实报错 |
| 缺少模块 | 使用 `--includes` 或 `--packages` 添加到 setup.py |
| C 库找不到资源 | 使用 `--frameworks` 添加 .dylib 到 Frameworks |
| DMG 创建失败（挂载问题） | 先 `hdiutil detach "/Volumes/番茄时钟"` 清理残留 |
| 外部卷太慢 | 将项目复制到 `/tmp/` 下构建，完成后产物拷贝回来 |
