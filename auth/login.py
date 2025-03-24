from auth.login_service import LoginService

def login(username, password) -> dict:
    login_service = LoginService()
    login_service.login(username, password)
    return login_service.get_cookies()
