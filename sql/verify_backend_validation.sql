-- BUG-003 ~ BUG-006 后端校验缺失缺陷的数据库核验脚本
-- 绕过前端直调接口写入非法数据后执行：能查到记录 = 后端未校验，缺陷成立
-- 数据库：ry-vue（若依后端库）

-- BUG-003 用户名长度（规则 2-20 位，复现值：'v'，1 位）
SELECT user_id, user_name, nick_name FROM sys_user WHERE user_name = 'v';

-- BUG-004 密码长度（规则 6-20 位，复现用户：v_pwd4，密码仅 4 位）
SELECT user_id, user_name, nick_name FROM sys_user WHERE user_name = 'v_pwd4';

-- BUG-005 密码非法字符（黑名单 < > " ' \ |，复现用户：v_illegal，密码含反斜杠）
SELECT user_id, user_name, nick_name FROM sys_user WHERE user_name = 'v_illegal';

-- BUG-006 手机号格式（规则 11 位数字，复现用户：v_phone，存入了 '!@#123'）
SELECT user_id, user_name, phonenumber FROM sys_user WHERE user_name = 'v_phone';
-- 缺陷成立的表现：phonenumber 字段原样存入非法值

-- 核验后清理（测试数据不留痕）
-- DELETE FROM sys_user WHERE user_name IN ('v','v_pwd4','v_illegal','v_phone');
