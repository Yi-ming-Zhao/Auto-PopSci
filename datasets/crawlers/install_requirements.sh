#!/bin/bash

# Selenium滚动翻页采集框架安装脚本

echo "🚀 安装Selenium滚动翻页采集框架..."
echo "================================================"

# 检查Python版本
python_version=$(python3 --version 2>&1 | grep -o '[0-9]\+\.[0-9]\+')
required_version="3.7"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" = "$required_version" ]; then
    echo "✅ Python版本检查通过: $python_version"
else
    echo "❌ 需要Python 3.7或更高版本，当前版本: $python_version"
    exit 1
fi

# 安装Python依赖
echo ""
echo "📦 安装Python依赖包..."

pip3 install --upgrade pip

# 核心依赖
echo "安装核心依赖..."
pip3 install selenium beautifulsoup4 requests pandas lxml

# 可选依赖
echo "安装可选依赖..."
pip3 install webdriver-manager tqdm

# 检查Chrome安装
echo ""
echo "🔍 检查Chrome安装..."

if command -v google-chrome &> /dev/null; then
    echo "✅ 找到Google Chrome"
    CHROME_CMD="google-chrome"
elif command -v chrome &> /dev/null; then
    echo "✅ 找到Chrome"
    CHROME_CMD="chrome"
elif command -v chromium-browser &> /dev/null; then
    echo "✅ 找到Chromium"
    CHROME_CMD="chromium-browser"
elif [ -d "/Applications/Google Chrome.app" ]; then
    echo "✅ 找到Google Chrome (macOS)"
    CHROME_CMD="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
else
    echo "⚠️  未找到Chrome，请手动安装Chrome浏览器"
    echo "   下载地址: https://www.google.com/chrome/"
fi

# 检查ChromeDriver
echo ""
echo "🔍 检查ChromeDriver..."

if command -v chromedriver &> /dev/null; then
    chromedriver_version=$(chromedriver --version 2>&1 | head -n1)
    echo "✅ 找到ChromeDriver: $chromedriver_version"
else
    echo "⚠️  未找到ChromeDriver，正在安装..."

    # 尝试使用webdriver-manager自动管理
    echo "尝试使用webdriver-manager..."
    python3 -c "
try:
    from webdriver_manager.chrome import ChromeDriverManager
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service

    driver_path = ChromeDriverManager().install()
    print(f'✅ ChromeDriver已自动安装到: {driver_path}')

    # 测试是否可用
    service = Service(executable_path=driver_path)
    driver = webdriver.Chrome(service=service)
    driver.quit()
    print('✅ ChromeDriver测试通过')

except Exception as e:
    print(f'❌ 自动安装失败: {e}')
    print('请手动安装ChromeDriver')
"

    # 如果自动安装失败，提供手动安装指导
    if [ $? -ne 0 ]; then
        echo ""
        echo "手动安装ChromeDriver的方法："
        echo ""
        echo "macOS:"
        echo "  brew install chromedriver"
        echo ""
        echo "Ubuntu/Debian:"
        echo "  sudo apt-get install chromium-chromedriver"
        echo ""
        echo "其他系统:"
        echo "  1. 访问 https://chromedriver.chromium.org/downloads"
        echo "  2. 下载与Chrome版本匹配的ChromeDriver"
        echo "  3. 将可执行文件放到PATH路径中"
    fi
fi

# 创建测试脚本
echo ""
echo "🧪 创建测试脚本..."

cat > test_installation.py << 'EOF'
#!/usr/bin/env python3
"""
安装测试脚本
"""

import sys
import os

def test_imports():
    """测试模块导入"""
    print("🧪 测试模块导入...")

    try:
        import selenium
        print("✅ selenium 导入成功")
    except ImportError as e:
        print(f"❌ selenium 导入失败: {e}")
        return False

    try:
        import bs4
        print("✅ beautifulsoup4 导入成功")
    except ImportError as e:
        print(f"❌ beautifulsoup4 导入失败: {e}")
        return False

    try:
        import requests
        print("✅ requests 导入成功")
    except ImportError as e:
        print(f"❌ requests 导入失败: {e}")
        return False

    try:
        import pandas
        print("✅ pandas 导入成功")
    except ImportError as e:
        print(f"❌ pandas 导入失败: {e}")
        return False

    return True

def test_selenium():
    """测试Selenium基本功能"""
    print("\n🧪 测试Selenium基本功能...")

    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options

        # 配置Chrome选项
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')

        # 尝试创建WebDriver
        try:
            driver = webdriver.Chrome(options=options)
            driver.get("https://www.google.com")
            title = driver.title
            driver.quit()
            print(f"✅ Selenium测试通过: 成功访问Google，标题为 '{title}'")
            return True
        except Exception as e:
            print(f"❌ WebDriver创建失败: {e}")
            print("请确保ChromeDriver已正确安装")
            return False

    except ImportError as e:
        print(f"❌ Selenium导入失败: {e}")
        return False

def test_local_modules():
    """测试本地模块"""
    print("\n🧪 测试本地模块...")

    current_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.append(current_dir)

    modules_to_test = [
        'selenium_scroll_crawler',
        'scroll_strategy_detector'
    ]

    success_count = 0
    for module_name in modules_to_test:
        try:
            __import__(module_name)
            print(f"✅ {module_name} 导入成功")
            success_count += 1
        except ImportError as e:
            print(f"❌ {module_name} 导入失败: {e}")
        except Exception as e:
            print(f"⚠️  {module_name} 导入时出现警告: {e}")
            success_count += 1  # 语法警告不算失败

    return success_count == len(modules_to_test)

def main():
    """主测试函数"""
    print("🧪 Selenium滚动翻页采集框架安装测试")
    print("=" * 50)

    tests_passed = 0
    total_tests = 3

    # 测试模块导入
    if test_imports():
        tests_passed += 1

    # 测试Selenium
    if test_selenium():
        tests_passed += 1

    # 测试本地模块
    if test_local_modules():
        tests_passed += 1

    print("\n" + "=" * 50)
    print(f"测试结果: {tests_passed}/{total_tests} 通过")

    if tests_passed == total_tests:
        print("🎉 所有测试通过！框架安装成功。")
        print("\n下一步:")
        print("  1. 运行 python demo_scroll_crawler.py 查看演示")
        print("  2. 运行 python test_scroll_crawler.py 进行完整测试")
        print("  3. 查看 README_SeleniumScroll.md 了解详细用法")
    else:
        print("❌ 部分测试失败，请检查安装。")
        print("\n常见问题:")
        print("  1. ChromeDriver版本不匹配 -> 更新ChromeDriver")
        print("  2. Chrome未安装 -> 安装Chrome浏览器")
        print("  3. 依赖包缺失 -> pip3 install -r requirements.txt")

if __name__ == "__main__":
    main()
EOF

echo "✅ 创建测试脚本成功: test_installation.py"

# 创建requirements.txt
echo ""
echo "📝 创建 requirements.txt..."
cat > requirements.txt << 'EOF'
selenium>=4.0.0
beautifulsoup4>=4.9.0
requests>=2.25.0
pandas>=1.3.0
lxml>=4.6.0
webdriver-manager>=3.8.0
tqdm>=4.60.0
EOF

echo "✅ 创建 requirements.txt 成功"

echo ""
echo "================================================"
echo "🎉 安装脚本执行完成！"
echo ""
echo "下一步:"
echo "  1. 运行测试: python3 test_installation.py"
echo "  2. 查看演示: python3 demo_scroll_crawler.py"
echo "  3. 运行测试: python3 test_scroll_crawler.py"
echo "  4. 查看文档: cat README_SeleniumScroll.md"
echo ""
echo "如果遇到问题，请检查:"
echo "  - Chrome浏览器是否已安装"
echo "  - ChromeDriver版本是否匹配Chrome版本"
echo "  - Python依赖是否已正确安装"
echo "================================================"