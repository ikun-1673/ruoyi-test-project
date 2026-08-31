# tests/test_login.py
import os
import pytest
import time
from selenium.webdriver.support.ui import WebDriverWait
from pages.login_page import LoginPage

# 测试账号从环境变量读取（若依公开默认值作兜底），避免仓库硬编码凭据
USERNAME = os.getenv("RUOYI_USERNAME", "admin")
PASSWORD = os.getenv("RUOYI_PASSWORD", "admin123")


def wait_for_home(driver, timeout=15):
    """显式等待首页渲染完成（首条用例可能赶上 Vite 冷启动，固定 sleep 不可靠）"""
    WebDriverWait(driver, timeout).until(lambda d: "首页" in d.page_source)

'''登录模块测试'''
class Test_login:

    def test_valid_login(self, driver, base_url):
        """TC-LOGIN-001：正确账号密码登录"""
        login_page = LoginPage(driver)
        login_page.open(base_url).login(USERNAME, PASSWORD)
        # 进入首页（显式等待渲染完成）
        wait_for_home(driver)
        assert "首页" in driver.page_source, "登录失败，未检测到主页文本"
        print('登陆成功')
        #// *[contains(text(), '若依后台管理框架')]

    def test_wrong_password(self, driver, base_url):
        """TC-LOGIN-004：错误密码，页面应停留登录页"""
        login_page = LoginPage(driver)
        login_page.open(base_url).login(USERNAME, "wrong_password")
        # 还在登录页面
        assert login_page.is_login_page()
        time.sleep(1)

    @pytest.mark.parametrize("username,password,expect_fail", [
        ("", "123456", True),  # 空用户名
        (USERNAME, "", True),  # 空密码
        (USERNAME, PASSWORD, False),  # 正确的（对比组）
    ])
    def test_login_boundary(self, driver, base_url, username, password, expect_fail):
        """边界值：空用户名/空密码，对比组验证正确凭据可登录"""
        login_page = LoginPage(driver)
        login_page.open(base_url).login(username, password)

        if expect_fail:
            time.sleep(0.5)
            assert login_page.is_login_page(), "应该还在登录页面"
        else:
            # 对比组必须有断言：正确凭据应成功进入首页，否则登录失败也会被误判为通过
            wait_for_home(driver)
            assert "首页" in driver.page_source, "对比组登录失败，未进入首页"