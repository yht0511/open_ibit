# from auth.login_service import LoginService
import auth.selenium

IBIT_CALLBACK_SERVICE = "https://ibit.yanhekt.cn/proxy/v1/cas/callback"
def login(username, password) -> dict:
    return auth.selenium.login(username, password, IBIT_CALLBACK_SERVICE)
