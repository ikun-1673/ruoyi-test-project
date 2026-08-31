# tests/test_role_create.py
import os
import pytest
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from pages.login_page import LoginPage
from pages.base_page import BasePage

class RolePage(BasePage):
    SYSTEM_MENU = (By.XPATH, "//span[text()='系统管理']")
    ROLE_MENU = (By.XPATH, "//span[text()='角色管理']")

    # 列表页
    ADD_BTN = (By.XPATH, "//button[contains(.,'新增')]")
    SEARCH_BTN = (By.XPATH, "//button[contains(.,'搜索')]")
    SEARCH_ROLE = (By.XPATH, "(//input[@placeholder='请输入角色名称'])[1]")

    # 新增弹窗：用 .el-dialog 限定作用域，避免误选列表页同名输入框
    DIALOG = "//div[contains(@class,'el-dialog')]"
    ROLE_NAME_INPUT = (By.XPATH, DIALOG + "//input[@placeholder='请输入角色名称']")
    ROLE_KEY_INPUT = (By.XPATH, DIALOG + "//input[@placeholder='请输入权限字符']")
    # 显示排序在若依里标签叫"角色顺序"，是 el-input-number 没有 placeholder，用 label 定位；
    # 注意用 contains(.,...) 而非 contains(text(),...)：Vue 注释节点会把文本拆成多个节点，text() 匹配不到
    ROLE_SORT_INPUT = (By.XPATH, DIALOG + "//label[contains(.,'角色顺序')]/following::input[1]")
    SAVE_BTN = (By.XPATH, DIALOG + "//button[contains(translate(.,' ',''),'确定')]")
    Cancel_BTN = (By.XPATH, DIALOG + "//button[contains(translate(.,' ',''),'取消')]")

    # 删除确认框
    CONFIRM_BTN = (By.XPATH, "//div[contains(@class,'el-message-box')]//button[contains(translate(.,' ',''),'确定')]")
    TABLE_ROWS = (By.CSS_SELECTOR, ".el-table__body-wrapper tbody tr")

    def navigate(self):
        self.click(*self.SYSTEM_MENU)
        self.click(*self.ROLE_MENU)
        time.sleep(1)
        return self

    def click_add(self):
        self.click(*self.ADD_BTN)
        self.wait_visible(*self.ROLE_NAME_INPUT)
        return self

    def add_role(self, role_name, role_key):
        """完整新增角色流程：角色名称 + 权限字符为必填，缺一会被校验拦截弹窗不关闭"""
        self.navigate()
        self.click_add()
        self.input(*self.ROLE_NAME_INPUT, role_name)
        self.input(*self.ROLE_KEY_INPUT, role_key)
        self.input(*self.ROLE_SORT_INPUT, "9")
        self.click(*self.SAVE_BTN)
        time.sleep(1)
        return self

    def close_dialog(self):
        for b in self.finds(*self.Cancel_BTN):
            if b.is_displayed():
                b.click()
                time.sleep(0.5)
                break
        return self

    def search_role(self, role_name):
        self.navigate()
        self.input(*self.SEARCH_ROLE, role_name)
        self.click(*self.SEARCH_BTN)
        time.sleep(1)
        return self

    def is_role_in_table(self, role_name):
        rows = self.finds(*self.TABLE_ROWS)
        return any(role_name in r.text for r in rows)

    def delete_role_by_name(self, role_name):
        """按名称搜索并删除角色（清理测试数据），行内按钮靠悬停 tooltip 识别"""
        self.search_role(role_name)
        row = self.wait.until(EC.presence_of_element_located(
            (By.XPATH, f"//tbody//tr[contains(.,'{role_name}')]")))
        clicked = self.click_row_icon_button(row, "删除")
        assert clicked, f"未找到角色 {role_name} 的删除按钮"
        time.sleep(0.5)
        self.click(*self.CONFIRM_BTN)
        time.sleep(1)
        return self

class TestRoleCreate:
    @pytest.fixture(autouse=True)
    def setup(self, driver, base_url):
        LoginPage(driver).open(base_url).login(
            os.getenv("RUOYI_USERNAME", "admin"), os.getenv("RUOYI_PASSWORD", "admin123"))
        time.sleep(1)

    def test_create_role(self, driver):
        """TC-ROLE-002：新增角色成功，搜索后应出现在列表中"""
        ts = int(time.time())
        role_name = f"测试角色_{ts}"
        role_key = f"auto_{ts}"

        page = RolePage(driver)
        page.add_role(role_name, role_key)
        msg = page.get_message()
        assert "成功" in msg, f"新增角色应提示成功，实际提示：{msg}"

        # 搜索定位新角色（规避分页问题）
        page.search_role(role_name)
        assert page.is_role_in_table(role_name), "新增角色应出现在搜索结果列表中"

        # 清理测试数据
        page.delete_role_by_name(role_name)
