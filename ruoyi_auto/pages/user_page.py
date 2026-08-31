from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from pages.base_page import BasePage
import time

"""用户管理页面"""
class UserPage(BasePage):

    # 菜单导航
    SYSTEM_MENU = (By.XPATH, "//span[text()='系统管理']")
    USER_MENU = (By.XPATH, "//span[text()='用户管理']")

    # 列表页：按钮与搜索框
    ADD_BTN = (By.XPATH, "//button[contains(.,'新增')]")
    SEARCH_BTN = (By.XPATH, "//button[contains(.,'搜索')]")
    # 列表页搜索框（弹窗关闭时页面上唯一的"用户名称"输入框）
    SEARCH_USERNAME = (By.XPATH, "(//input[@placeholder='请输入用户名称'])[1]")

    # 新增弹窗：全部用 .el-dialog 限定作用域，避免误选到列表页同名输入框
    DIALOG = "//div[contains(@class,'el-dialog')]"
    USERNAME_INPUT = (By.XPATH, DIALOG + "//input[@placeholder='请输入用户名称']")
    NICKNAME_INPUT = (By.XPATH, DIALOG + "//input[@placeholder='请输入用户昵称']")
    PASSWORD_INPUT = (By.XPATH, DIALOG + "//input[@placeholder='请输入用户密码']")
    PHONE_INPUT = (By.XPATH, DIALOG + "//input[@placeholder='请输入手机号码']")
    EMAIL_INPUT = (By.XPATH, DIALOG + "//input[@placeholder='请输入邮箱']")
    SAVE_BTN = (By.XPATH, DIALOG + "//button[contains(translate(.,' ',''),'确定')]")
    Cancel_BTN = (By.XPATH, DIALOG + "//button[contains(translate(.,' ',''),'取消')]")

    # 删除确认框（MessageBox）的确定按钮
    CONFIRM_BTN = (By.XPATH, "//div[contains(@class,'el-message-box')]//button[contains(translate(.,' ',''),'确定')]")
    TABLE_ROWS = (By.CSS_SELECTOR, ".el-table__body-wrapper tbody tr")

    def navigate(self):
        """导航到用户管理页面"""
        self.click(*self.SYSTEM_MENU)
        self.click(*self.USER_MENU)
        time.sleep(1)
        return self

    def click_add(self):
        self.click(*self.ADD_BTN)
        self.wait_visible(*self.USERNAME_INPUT)
        return self

    def fill_user_form(self, username, nickname, password, phone="", email=""):
        self.input(*self.USERNAME_INPUT, username)
        self.input(*self.NICKNAME_INPUT, nickname)
        self.input(*self.PASSWORD_INPUT, password)
        if phone:
            self.input(*self.PHONE_INPUT, phone)
        if email:
            self.input(*self.EMAIL_INPUT, email)
        return self

    def click_save(self):
        """只点保存，不关弹窗：成功时弹窗自动关闭，校验失败时弹窗保留，由用例决定后续动作"""
        self.click(*self.SAVE_BTN)
        time.sleep(1)
        return self

    def close_dialog(self):
        """弹窗仍打开时（如校验失败），点取消关闭"""
        for b in self.finds(*self.Cancel_BTN):
            if b.is_displayed():
                b.click()
                time.sleep(0.5)
                break
        return self

    def add_user(self, username, nickname, password, phone="", email=""):
        """完整新增用户流程"""
        self.navigate()
        self.click_add()
        self.fill_user_form(username, nickname, password, phone, email)
        self.click_save()
        return self

    def search_user(self, username):
        """列表页按用户名搜索（配合断言/删除使用，规避分页问题）"""
        self.navigate()
        self.input(*self.SEARCH_USERNAME, username)
        self.click(*self.SEARCH_BTN)
        time.sleep(1)
        return self

    def get_row_count(self):
        """获取当前页表格行数"""
        rows = self.finds(*self.TABLE_ROWS)
        return len(rows)

    def is_user_in_table(self, username):
        """检查用户名是否出现在当前表格中（按行文本判断，比 page_source 准确）"""
        rows = self.finds(*self.TABLE_ROWS)
        return any(username in r.text for r in rows)

    def is_text_in_table(self, text):
        """检查任意文本（如修改后的昵称）是否出现在当前表格中"""
        rows = self.finds(*self.TABLE_ROWS)
        return any(text in r.text for r in rows)

    def edit_user_nickname(self, username, new_nickname):
        """搜索用户并点行内“修改”（图标按钮靠悬停 tooltip 识别），只改昵称后保存"""
        self.search_user(username)
        row = self.wait.until(EC.presence_of_element_located(
            (By.XPATH, f"//tbody//tr[contains(.,'{username}')]")))
        clicked = self.click_row_icon_button(row, "修改")
        assert clicked, f"未找到用户 {username} 的修改按钮"
        self.wait_visible(*self.NICKNAME_INPUT)
        self.input(*self.NICKNAME_INPUT, new_nickname)
        self.click_save()
        return self

    def delete_user_by_name(self, username):
        """按用户名搜索并删除该行用户（用于清理测试数据）。
        行内操作按钮是纯图标无文字，靠悬停 tooltip='删除' 识别"""
        self.search_user(username)
        row = self.wait.until(EC.presence_of_element_located(
            (By.XPATH, f"//tbody//tr[contains(.,'{username}')]")))
        clicked = self.click_row_icon_button(row, "删除")
        assert clicked, f"未找到用户 {username} 的删除按钮"
        time.sleep(0.5)
        self.click(*self.CONFIRM_BTN)
        time.sleep(1)
        return self
