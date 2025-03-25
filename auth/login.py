from auth.login_service import LoginService

IBIT_CALLBACK_SERVICE = "https://ibit.yanhekt.cn/proxy/v1/cas/callback"
def login(username, password) -> dict:
    login_service = LoginService(IBIT_CALLBACK_SERVICE)
    login_service.login(username, password)
    return login_service.get_cookies()
