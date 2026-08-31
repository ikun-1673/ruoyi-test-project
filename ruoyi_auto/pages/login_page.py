# pages/login_page.py
import time

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from pages.base_page import BasePage

class LoginPage(BasePage):
    #//input[ @ placeholder = "密码"]
    USERNAME = (By.CSS_SELECTOR, "input[placeholder = '账号']")
    PASSWORD = (By.CSS_SELECTOR, "input[placeholder = '密码']")
    LOGIN_BTN = (By.CSS_SELECTOR, "button[type='button']")
    ERROR_MSG = (By.CLASS_NAME, "el-message__content")
    #ERROR_MSG = (By.XPATH,"//p[@class='el-message__content']")

    CAPTCHA_IMG = (By.CSS_SELECTOR, "img.login-code-img")

    def open(self, url="http://localhost:8888"):
        self.driver.get(url)
        self.wait.until(EC.presence_of_element_located(self.USERNAME))
        return self

    def login(self, username, password):
        """执行登录操作"""
        self.input(*self.USERNAME, username)
        self.input(*self.PASSWORD, password)
        time.sleep(1)
        self.click(*self.LOGIN_BTN)
        return self

    def get_error_message(self):
        """获取登录失败的错误提示"""
        return self.get_text(*self.ERROR_MSG)

    def is_login_page(self):
        """判断是否还在登录页面"""
        return self.is_visible(*self.LOGIN_BTN)