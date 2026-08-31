# tests/test_user_crud.py
import os
import pytest
import time
from pages.login_page import LoginPage
from pages.user_page import UserPage

USERNAME = os.getenv("RUOYI_USERNAME", "admin")
PASSWORD = os.getenv("RUOYI_PASSWORD", "admin123")

"""用户增删改查自动化测试"""
class TestUserCRUD:

    @pytest.fixture(autouse=True)
    def setup(self, driver, base_url):
        """每个用例执行前：登录系统"""
        LoginPage(driver).open(base_url).login(USERNAME, PASSWORD)
        time.sleep(1)

    def test_add_user_success(self, driver):
        """TC-USER-008：新增用户成功，搜索后应出现在列表中"""
        test_user = f"autotest_{int(time.time())}"
        page = UserPage(driver)

        page.add_user(test_user, "自动化测试", "Test123456")
        msg = page.get_message()
        assert "成功" in msg, f"新增用户应提示成功，实际提示：{msg}"

        # 用搜索定位新用户（规避分页导致新用户在末页看不到的问题）
        page.search_user(test_user)
        assert page.is_user_in_table(test_user), "新增用户应出现在搜索结果列表中"

        # 清理测试数据
        page.delete_user_by_name(test_user)

    def test_add_user_duplicate(self, driver):
        """TC-USER-010：新增重复用户名，应提示已存在"""
        page = UserPage(driver)
        page.navigate()
        page.click_add()
        page.fill_user_form("admin", "重复的", "Test123456")
        page.click_save()

        msg = page.get_message()
        assert "已存在" in msg, f"重复用户名应提示已存在，实际提示：{msg}"
        page.close_dialog()

    @pytest.mark.parametrize("suffix,should_pass", [
        (str(int(time.time() * 1000))[-8:], True),   # 动态后缀，用例内拼成 11 位合法手机号，避免与已有用户重复
        ("123", False),           # 太短
        ("abc12345678", False),   # 含字母
        ("", True),               # 空（非必填）
    ])
    def test_add_user_phone_validation(self, driver, suffix, should_pass):
        """TC-USER-011：手机号校验测试"""
        # 合法场景：手机号=138+后缀，用户名带同一后缀，两者一一对应便于排查；
        # 非法/空场景：后缀无意义，用户名另取新时间戳后缀，保证唯一且避免产生 mtest_ 这种丑用户名；
        # 拦截点在手机号校验，用户名始终合法可提交
        phone = "138" + suffix if should_pass and len(suffix) == 8 else suffix
        name_suffix = suffix if len(suffix) == 8 else str(int(time.time() * 1000))[-8:]
        test_user = f"mtest_{name_suffix}"
        page = UserPage(driver)
        page.navigate()
        page.click_add()
        page.fill_user_form(test_user, "手机号测试", "Test123456", phone=phone)
        page.click_save()

        if should_pass:
            msg = page.get_message()
            assert "成功" in msg, f"合法手机号应新增成功，实际提示：{msg}"
            page.search_user(test_user)
            assert page.is_user_in_table(test_user), "合法手机号新增的用户应存在"
            page.delete_user_by_name(test_user)   # 清理
        else:
            # 非法手机号应被前端校验拦截，弹窗保留并出现内联错误
            err = page.get_form_error()
            assert "手机号码" in err, f"非法手机号应被校验拦截，实际错误提示：{err}"
            page.close_dialog()

    def test_update_user_success(self, driver):
        """TC-USER-016：修改用户：改昵称后列表应显示新昵称"""
        name = f"mtest_upd_{str(int(time.time() * 1000))[-8:]}"
        new_nick = f"已改_{str(int(time.time() * 1000))[-6:]}"
        page = UserPage(driver)

        page.add_user(name, "修改前昵称", "Test123456")
        assert "成功" in page.get_message(), "前置新增用户应成功"
        page.edit_user_nickname(name, new_nick)
        assert "成功" in page.get_message(), f"修改用户应提示成功，实际：{page.get_message()}"
        page.search_user(name)
        assert page.is_text_in_table(new_nick), "修改后的昵称应出现在列表中"
        page.delete_user_by_name(name)   # 清理

    def test_delete_user_verified(self, driver):
        """删除用户：不能只验证点击，必须确认提示成功且列表中已不存在"""
        name = f"mtest_del_{str(int(time.time() * 1000))[-8:]}"
        page = UserPage(driver)

        page.add_user(name, "待删除用户", "Test123456")
        assert "成功" in page.get_message(), "前置新增用户应成功"
        page.delete_user_by_name(name)
        assert "成功" in page.get_message(), "删除应提示成功"
        # 删除后再搜索验证：列表中不应再存在该用户（防止“点击成功”被误当“业务成功”）
        page.search_user(name)
        assert not page.is_user_in_table(name), "删除后列表中不应再存在该用户"
