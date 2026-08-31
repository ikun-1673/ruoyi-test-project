-- BUG-001 / BUG-002 并发竞态缺陷的数据库核验脚本
-- 复现后执行：若同一名字出现 >=2 条记录，即证明唯一性校验存在竞态窗口
-- 数据库：ry-vue（若依后端库）

-- 并发重名用户（复现用用户名：verify_dup）
SELECT user_id, user_name, nick_name, create_time
FROM sys_user
WHERE user_name = 'verify_dup';
-- 缺陷成立的表现：返回 2 条（或更多）同名记录

-- 并发重名角色（复现用角色名：验证角色3）
SELECT role_id, role_name, role_key, create_time
FROM sys_role
WHERE role_name = '验证角色3';
-- 缺陷成立的表现：返回 2 条（或更多）同名记录

-- 根因佐证：唯一索引缺失（两条查询结果均为空 = 无唯一约束兜底）
SHOW INDEX FROM sys_user WHERE Non_unique = 0 AND Column_name = 'user_name';
SHOW INDEX FROM sys_role WHERE Non_unique = 0 AND Column_name = 'role_name';
