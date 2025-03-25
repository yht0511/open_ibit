import re
import requests
import ddddocr
from bs4 import BeautifulSoup
from auth.aes_util import encrypt_password

# 配置日志
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
}
BASE_URL = "https://login.bit.edu.cn"
LOGIN_URL = f"{BASE_URL}/authserver/login"


class LoginService:
    def __init__(self, service_url):
        self.service_url = service_url
        self.session = requests.Session()
        self.session.headers = headers
        self.error_pattern = re.compile(r'<span id="showErrorTip"><span>(.*?)</span>')
        self.ocr = ddddocr.DdddOcr(show_ad=False)
    def _get_html_error(self, html):
        match = self.error_pattern.search(html)
        return match.group(1) if match else ""

    def _get_login_params(self):
        try:
            response = self.session.get(
                LOGIN_URL,
                params={"service": self.service_url}
            )
            if not response.ok:
                raise RuntimeError(f"获取登录页面失败: {response.status_code}")

            soup = BeautifulSoup(response.text, "html.parser")
            form = soup.find(id="pwdFromId")
            if not form:
                raise RuntimeError("找不到登录表单")

            execution = form.find(attrs={"name": "execution"}).get("value")
            pwd_encrypt_salt = soup.find(id="pwdEncryptSalt").get("value")
            return execution, pwd_encrypt_salt

        except Exception as e:
            print(f"[ERROR] 获取登录参数失败: {str(e)}")
            raise

    def check_need_captcha(self, username):
        response = self.session.get(
            f"{BASE_URL}/authserver/checkNeedCaptcha.htl",
            params={"username": username}
        )
        if response.text == '{"isNeed":true}':
            print(f"[INFO] 需要验证码: {username}")
            return True
        else:
            return False

    def _get_captcha(self):
        try:
            # 添加Referer头
            headers = {"Referer": LOGIN_URL}
            response = self.session.get(
                f"{BASE_URL}/authserver/getCaptcha.htl",
                headers=headers
            )
            if not response.ok:
                raise RuntimeError(f"获取验证码失败: {response.status_code}")

            # 保存验证码图片以供手动检查
            with open("captcha.jpg", "wb") as f:
                f.write(response.content)
            print("[INFO] 验证码图片已保存为captcha.jpg")

            captcha = self.ocr.classification(response.content)
            print(f"[INFO] 识别验证码: {captcha}")
            return captcha
        except Exception as e:
            print(f"[ERROR] 获取验证码异常: {str(e)}")
            raise e

    def login(self, username, password):
        try:
            execution, pwd_salt = self._get_login_params()
            encrypted_pwd = encrypt_password(password, pwd_salt)
            captcha = ""
            if self.check_need_captcha(username):
                captcha = self._get_captcha()
            data = {
                "username": username,
                "password": encrypted_pwd,
                "execution": execution,
                "captcha": captcha,
                "_eventId": "submit",
                "cllt": "userNameLogin",
                "dllt": "generalLogin",
                "lt": "",
                "rememberMe": "true",
                "service": self.service_url,
            }

            response = self.session.post(LOGIN_URL, data=data)
            print(f"[INFO] 登录响应状态码: {response.status_code}")

            if not response.ok:
                error_reason = self._get_html_error(response.text)
                print(f"[ERROR] 登录失败: {response.status_code}, 原因: {error_reason}")
                raise RuntimeError(
                    f"登录失败: {response.status_code}, 原因: {error_reason}"
                )

            return self.verify_session()

        except Exception as e:
            print(f"[ERROR] 登录流程异常: {str(e)}")
            raise

    def verify_session(self):
        try:
            response = self.session.get(LOGIN_URL)
            if not response.ok:
                print(f"[ERROR] 会话验证失败: {response.status_code}")
                return False

            soup = BeautifulSoup(response.text, "html.parser")
            pwd_form = soup.find(id="pwdFromId")
            return pwd_form is None

        except Exception as e:
            print(f"[ERROR] 会话验证异常: {str(e)}")
            raise

    def get_cookies(self):
        return self.session.cookies.get_dict()



