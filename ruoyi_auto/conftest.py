import os
import pytest
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By

@pytest.fixture(scope="session")
def driver():
    options = Options()
    # 禁用浏览器的密码保存/自动填充，避免干扰输入框清空逻辑
    prefs = {
        "credentials_enable_service": False,
        "profile.password_manager_enabled": False,
    }
    options.add_experimental_option("prefs", prefs)
    driver = webdriver.Chrome(options=options)
    driver.maximize_window()
    driver.implicitly_wait(10)
    yield driver
    driver.quit()

@pytest.fixture(scope="session", autouse=True)
def cleanup_leftover_users():
    """会话开始前清理数据库中残留的测试用户（autotest_*/mtest_*/phone_*），
    避免残留数据导致重名拦截、用例失败。
    数据库凭据从环境变量读取（见 .env.example），未配置时静默跳过清理，不影响用例执行。"""
    db_pwd = os.getenv("RUOYI_DB_PASSWORD")
    if not db_pwd:
        yield
        return
    try:
        import pymysql
        conn = pymysql.connect(host=os.getenv("RUOYI_DB_HOST", "localhost"),
                               port=int(os.getenv("RUOYI_DB_PORT", "3306")),
                               user=os.getenv("RUOYI_DB_USER", "root"), password=db_pwd,
                               database=os.getenv("RUOYI_DB_NAME", "ry-vue"), charset='utf8mb4')
        cur = conn.cursor()
        cur.execute("SELECT user_id FROM sys_user "
                    "WHERE user_name LIKE 'autotest\\_%' OR user_name LIKE 'mtest\\_%' "
                    "OR user_name LIKE 'phone\\_%'")
        ids = [r[0] for r in cur.fetchall()]
        if ids:
            fmt = ','.join(['%s'] * len(ids))
            cur.execute(f"DELETE FROM sys_user_role WHERE user_id IN ({fmt})", ids)
            cur.execute(f"DELETE FROM sys_user_post WHERE user_id IN ({fmt})", ids)
            cur.execute(f"DELETE FROM sys_user WHERE user_id IN ({fmt})", ids)
            conn.commit()
        conn.close()
    except Exception:
        pass
    yield

@pytest.fixture(autouse=True)
def reset(driver, base_url):
    """每个用例执行前：清除登录态，保证从登录页开始。
    若依的 token 存在 Cookie 的 Admin-Token 里（js-cookie），
    只清 localStorage 清不掉，必须连 Cookie 一起删。"""
    try:
        driver.delete_all_cookies()
    except Exception:
        pass
    try:
        driver.execute_script("window.localStorage.clear(); window.sessionStorage.clear();")
    except Exception:
        pass
    yield
    # 用例结束后：按 ESC 关闭可能残留的弹窗，避免影响下一个用例
    try:
        driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
    except Exception:
        pass

@pytest.fixture
def base_url():
    # 被测系统地址可通过环境变量覆盖，默认本地部署的若依前端
    return os.getenv("RUOYI_BASE_URL", "http://localhost:8888/")

# 失败自动截图
import os
from datetime import datetime

@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    if report.when == "call" and report.failed:
        driver = item.funcargs.get("driver")
        if driver:
            os.makedirs("reports/screenshots", exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            driver.save_screenshot(f"reports/screenshots/{item.name}_{ts}.png")