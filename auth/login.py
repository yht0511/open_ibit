"""
login.py - 北理工统一身份认证登录模块

本模块封装了 bit_login 库，提供北理工统一身份认证功能。
用于 iBit 平台的登录认证，获取访问凭证（Cookie）。

bit_login 库实现了北理工统一身份认证的完整流程：
1. 访问登录页面获取表单参数
2. 提交用户名密码进行认证
3. 获取并返回认证 Cookie

使用方式：
    from auth.login import login
    result = login(username, password)
    cookies = result["cookie_json"]  # 获取 Cookie 字典
"""

import bit_login  # 北理工统一身份认证第三方库


# 创建 ibit_login 实例并导出 login 方法
# ibit_login 类专门用于 iBit 平台的登录
# login 方法接收用户名和密码，返回包含 cookie_json 的字典
login = bit_login.ibit_login().login