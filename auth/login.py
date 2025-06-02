import bit_login
import requests
import urllib.parse

def login(username, password):
    login_client = bit_login.login()
    data = login_client.login(username, password,callback_url="https://ibit.yanhekt.cn/proxy/v1/cas/callback")
    cookies = data['cookie_json']
    headers={
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'zh-CN,zh;q=0.9',
        'Connection': 'keep-alive',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Upgrade-Insecure-Requests': '1',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36 Edg/136.0.0.0',
        'sec-ch-ua': '"Chromium";v="136", "Microsoft Edge";v="136", "Not.A/Brand";v="99"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
    }
    badge = requests.get(data["callback"],headers=headers,allow_redirects=0).headers["Location"].split("badgeFromPc=")[1]
    badge = urllib.parse.unquote(badge)
    cookies["badge_2"] = badge
    return cookies
    
