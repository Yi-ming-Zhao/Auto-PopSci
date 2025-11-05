#!/bin/bash

# Frontiers for Young Minds 爬虫 - Selenium 安装脚本
echo "=== Frontiers for Young Minds 爬虫 Selenium 安装脚本 ==="

# 检查操作系统
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "检测到 macOS 系统"
    PLATFORM="mac"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo "检测到 Linux 系统"
    PLATFORM="linux"
else
    echo "检测到未知系统，请手动安装依赖"
    exit 1
fi

# 安装Python依赖
echo "正在安装Python依赖包..."
pip install requests beautifulsoup4 lxml aiohttp selenium

# 检查Chrome浏览器
echo "检查Chrome浏览器..."
if command -v google-chrome &> /dev/null; then
    echo "✓ 找到 Google Chrome"
    CHROME_CMD="google-chrome"
elif command -v chrome &> /dev/null; then
    echo "✓ 找到 Chrome"
    CHROME_CMD="chrome"
elif [[ "$PLATFORM" == "mac" ]] && [ -d "/Applications/Google Chrome.app" ]; then
    echo "✓ 找到 Chrome (macOS)"
    CHROME_CMD="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
else
    echo "❌ 未找到Chrome浏览器"
    echo "请访问 https://www.google.com/chrome/ 下载安装Chrome"
fi

# 获取Chrome版本
if command -v "$CHROME_CMD" &> /dev/null; then
    CHROME_VERSION=$("$CHROME_CMD" --version 2>/dev/null | grep -oP '\d+\.\d+\.\d+' | head -1)
    echo "Chrome版本: $CHROME_VERSION"
fi

# 下载ChromeDriver
echo "正在下载ChromeDriver..."
if [[ "$PLATFORM" == "mac" ]]; then
    # macOS
    CHROMEDRIVER_VERSION="120.0.6099.109"
    DOWNLOAD_URL="https://chromedriver.storage.googleapis.com/LATEST_RELEASE/chromedriver_mac64.zip"
elif [[ "$PLATFORM" == "linux" ]]; then
    # Linux
    CHROMEDRIVER_VERSION="120.0.6099.109"
    DOWNLOAD_URL="https://chromedriver.storage.googleapis.com/LATEST_RELEASE/chromedriver_linux64.zip"
fi

# 创建临时目录
TEMP_DIR=$(mktemp -d)
cd "$TEMP_DIR"

# 下载ChromeDriver
echo "从 $DOWNLOAD_URL 下载ChromeDriver..."
curl -O "$DOWNLOAD_URL"

# 解压ChromeDriver
echo "解压ChromeDriver..."
unzip chromedriver_*.zip

# 安装ChromeDriver到系统路径
echo "安装ChromeDriver到系统路径..."
if [[ "$PLATFORM" == "mac" ]]; then
    # macOS
    if [ -d "/usr/local/bin" ]; then
        cp chromedriver /usr/local/bin/
        echo "✓ ChromeDriver 已安装到 /usr/local/bin/"
    elif [ -d "$HOME/.local/bin" ]; then
        mkdir -p "$HOME/.local/bin"
        cp chromedriver "$HOME/.local/bin/"
        echo "✓ ChromeDriver 已安装到 $HOME/.local/bin/"
        echo "请将 $HOME/.local/bin 添加到 PATH 环境变量中"
    else
        echo "❌ 无法找到合适的安装目录，请手动处理"
        echo "当前目录: $(pwd)"
        echo "ChromeDriver 位置: $(ls -la chromedriver)"
    fi
elif [[ "$PLATFORM" == "linux" ]]; then
    # Linux
    if [ -d "/usr/local/bin" ]; then
        sudo cp chromedriver /usr/local/bin/
        echo "✓ ChromeDriver 已安装到 /usr/local/bin/"
    else
        echo "❌ 无法安装到系统目录，请手动处理"
        echo "当前目录: $(pwd)"
        echo "ChromeDriver 位置: $(ls -la chromedriver)"
    fi
fi

# 设置权限
chmod +x chromedriver

# 清理临时文件
cd /
rm -rf "$TEMP_DIR"

echo ""
echo "=== 安装完成 ==="
echo "ChromeDriver 版本信息:"
chromedriver --version

echo ""
echo "验证安装："
python3 -c "import selenium; print('✓ Selenium 安装成功')"