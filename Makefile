SHELL   := /bin/bash
# 必须使用 ARM64 原生 Python，x86_64 构建的 App 在无 Rosetta 的 Mac 上无法运行
PYTHON  := $(shell arch -arm64 /usr/bin/python3 -c 'import sys; print(sys.executable)' 2>/dev/null || which python3)
NAME    := 番茄时钟
VERSION := $(shell grep '__version__' pomodoro_timer.py | head -1 | sed "s/.*= \"//;s/\".*//")
.DEFAULT_GOAL := help

# 构建前检查架构
define check_arch
	@ARCH=$$($(PYTHON) -c 'import platform; print(platform.machine())'); \
	if [ "$$ARCH" != "arm64" ]; then \
		echo "❌ 错误: Python 架构为 $$ARCH，必须是 arm64"; \
		echo "   当前 Python: $(PYTHON)"; \
		echo "   请安装 ARM64 原生 Python 或启用 Rosetta 2"; \
		exit 1; \
	fi
endef

.PHONY: help app dmg clean release tag

help: ## 显示帮助信息
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## 安装依赖
	$(PYTHON) -m pip install rumps py2app

icon: ## 生成应用图标
	$(PYTHON) make_icon.py

app: clean icon ## 构建 .app
	$(check_arch)
	$(PYTHON) setup.py py2app
	@echo "✅ 构建完成: dist/$(NAME).app"

dmg: app ## 构建 DMG 安装包
	@echo "创建 DMG..."
	hdiutil create -size 200m -fs HFS+ -type UDIF -volname "$(NAME)" /tmp/pomodoro_template.dmg
	hdiutil attach -nobrowse -mountpoint /tmp/pomodoro_mount /tmp/pomodoro_template.dmg
	ditto "dist/$(NAME).app" "/tmp/pomodoro_mount/$(NAME).app"
	ln -sf /Applications "/tmp/pomodoro_mount/Applications"
	cp icon.icns "/tmp/pomodoro_mount/.VolumeIcon.icns"
	/usr/bin/SetFile -a C "/tmp/pomodoro_mount"
	hdiutil detach "/tmp/pomodoro_mount"
	rm -rf /tmp/pomodoro_mount
	hdiutil convert /tmp/pomodoro_template.dmg -format UDZO -ov -o "$(NAME).dmg"
	rm -f /tmp/pomodoro_template.dmg
	@echo "✅ DMG 已生成: $(NAME).dmg"

release: tag dmg ## 发布新版本（打标签 + 构建 DMG）
	@echo "✅ Release v$(VERSION) 就绪！"
	@echo "   DMG: $(NAME).dmg"
	@echo "   在 GitHub 上创建 Release："
	@echo "   1. git push --tags"
	@echo "   2. gh release create v$(VERSION) $(NAME).dmg --title 'v$(VERSION)' --notes-file CHANGELOG.md"

tag: ## 打 Git 版本标签
	@if git rev-parse v$(VERSION) >/dev/null 2>&1; then \
		echo "⚠️  标签 v$(VERSION) 已存在"; \
	else \
		git tag -a v$(VERSION) -m "Release v$(VERSION)"; \
		echo "✅ 标签 v$(VERSION) 已创建"; \
	fi

clean: ## 清理构建产物（保留 releases/ 中的历史版本）
	rm -rf build dist *.egg-info __pycache__/
	rm -rf tomato.iconset
	@echo '✅ 清理完成（releases/ 已保留）'
