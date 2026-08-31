# pages/base_page.py
import time
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import ElementClickInterceptedException, WebDriverException
class BasePage:
    '''初始化'''
    def __init__(self, driver):
        self.driver = driver
        self.wait = WebDriverWait(driver, 10)

    '''查找单个元素'''
    def find(self,by, value):
        return self.driver.find_element(by, value)

    '''查找多个元素'''
    def finds(self,by,value):
        return self.driver.find_elements(by, value)

    '''点击'''
    def click(self,by,value):
        e = self.wait.until(EC.element_to_be_clickable((by, value)))
        try:
            e.click()
        except (ElementClickInterceptedException, WebDriverException):
            # 元素被弹窗/遮罩挡住时，改用 JS 点击兜底（如 Element UI 弹窗内的按钮）
            self.driver.execute_script("arguments[0].click();", e)
        return e

    '''输入'''
    def input(self,by,value,text):
        e1=self.wait.until(EC.visibility_of_element_located((by, value)))
        # 直接 send_keys 会自动聚焦，不用 click（弹窗内的 label 会挡住点击）
        # 再用全选删除清旧内容（比 clear() 更可靠，能触发前端框架事件）
        e1.send_keys(Keys.CONTROL, "a")
        e1.send_keys(Keys.DELETE)
        e1.send_keys(text)

    '''获取文本'''
    def get_text(self,by,value):
        return self.wait.until(EC.presence_of_element_located((by, value))).text

    '''等待可见'''
    def wait_visible(self, by, value):
        return self.wait.until(EC.visibility_of_element_located((by, value)))

    '''获取标题'''
    def get_title(self):
        return self.driver.title

    '''截图'''
    def screenshot(self, filename):
        self.driver.save_screenshot(filename)

    def is_visible(self, by, value, timeout=5):
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.visibility_of_element_located((by, value))
            )
            return True
        except:
            return False

    def title_contains(self, text):
        return self.wait.until(EC.title_contains(text))

    """获取全局消息提示（新增成功/已存在等），超时返回空串"""
    def get_message(self, timeout=5):
        try:
            el = WebDriverWait(self.driver, timeout).until(
                EC.visibility_of_element_located((By.CLASS_NAME, "el-message__content"))
            )
            return el.text
        except Exception:
            return ""

    """获取表单内联校验错误文本（如 请输入正确的手机号码）"""
    def get_form_error(self):
        els = self.driver.find_elements(By.CLASS_NAME, "el-form-item__error")
        for el in els:
            if el.text.strip():
                return el.text
        return ""

    """行内图标按钮无文字（Element Plus 纯 SVG 图标），靠悬停 tooltip 识别：
    逐个悬停行内按钮，当出现目标文字的 tooltip 时点击该按钮"""
    def click_row_icon_button(self, row, tooltip_text):
        buttons = row.find_elements(By.TAG_NAME, "button")
        for btn in buttons:
            try:
                ActionChains(self.driver).move_to_element(btn).perform()
                time.sleep(0.35)  # 等 tooltip 出现、上一个 tooltip 隐藏
                tips = [t for t in self.driver.find_elements(By.CSS_SELECTOR, "[role='tooltip'], .el-popper")
                        if t.is_displayed() and t.text.strip()]
                if any(tooltip_text == t.text.strip() for t in tips):
                    btn.click()
                    return True
            except Exception:
                continue
        return False
