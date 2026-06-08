SHELL   := /bin/bash
PYTHON  := python3
NAME    := 番茄时钟
VERSION := $(shell grep '__version__' pomodoro_timer.py | head -1 | sed "s/.*= \"//;s/\".*//")
.DEFAULT_GOAL := help

.PHONY: help app dmg clean release tag

help: ## 显示帮助信息
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## 安装依赖
	pip3 install rumps py2app

icon: ## 生成应用图标
	python3 make_icon.py

app: clean icon ## 构建 .app
	python3 setup.py py2app
	@echo "✅ 构建完成: dist/$(NAME).app"

dmg: app ## 构建 DMG 安装包
	@echo "创建 DMG..."
	hdiutil create -size 200m -fs HFS+ -type UDIF -volname "$(NAME)" /tmp/pomodoro_template.dmg
	hdiutil attach -nobrowse -owners off /tmp/pomodoro_template.dmg
	ditto "dist/$(NAME).app" "/Volumes/$(NAME)/$(NAME).app"
	ln -s /Applications "/Volumes/$(NAME)/Applications"
	cp icon.icns "/Volumes/$(NAME)/.VolumeIcon.icns"
	/usr/bin/SetFile -a C "/Volumes/$(NAME)"
	hdiutil detach "/Volumes/$(NAME)"
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

clean: ## 清理构建产物
	rm -rf build dist *.dmg *.egg-info __pycache__/
	rm -rf tomato.iconset
