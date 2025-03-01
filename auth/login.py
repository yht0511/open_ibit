import os
import requests
import time
from selenium import webdriver
# 导入BY
from selenium.webdriver.common.by import By
# 导入Keys
from selenium.webdriver.common.keys import Keys
# 导入wait
from selenium.webdriver.support.ui import WebDriverWait
import ddddocr
import os


base_path = os.path.dirname(os.path.abspath(__file__))
def login(username,password,url="https://www.yanhekt.cn"):
    # 启动selenium
    options = webdriver.ChromeOptions()
    # 无头模式
    options.add_argument('headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--log-level=3') # 不要输出日志
    browser = webdriver.Chrome(options=options)
    with open(base_path+'/stealth.min.js', mode='r') as f:
        js = f.read()
    # 关键代码
    browser.execute_cdp_cmd(
        cmd_args={'source': js},
        cmd="Page.addScriptToEvaluateOnNewDocument",
    )
    browser.get(url)
    # 点击登录按钮
    login_button = browser.find_element(By.XPATH,"//span[text()='登 录']")
    login_button.click()
    time.sleep(0.5) # 等待加载
    #　下拉选项框选择
    option_button = browser.find_element(By.CLASS_NAME,"ant-select-selection-search-input")
    option_button.click()
    time.sleep(0.5) # 等待加载
    # 选择北京理工大学
    bit_option = browser.find_elements(By.CLASS_NAME,"ant-select-item")[1]
    bit_option.click()
    time.sleep(0.5) # 等待加载
    # 选择学生登录
    student_option = browser.find_elements(By.CLASS_NAME,"ant-btn-primary")[1]
    student_option.click()
    time.sleep(1) # 等待加载
    # 输入用户名
    username_input = browser.find_element(By.ID,"username")
    username_input.send_keys(username)
    # 输入密码
    password_input = browser.find_element(By.ID,"password")
    password_input.send_keys(password)
    time.sleep(1) # 等待图片加载
    # 检查验证码
    if browser.execute_script('return $(".captcha")[0].style.display') == "block":
        print("检测到验证码,输入中...")
        # 获取验证码图片
        captcha_img = browser.find_element(By.ID,"captchaImg")
        captcha_img.screenshot(base_path+"/captcha.png")
        captcha=get_captcha(base_path+"/captcha.png")
        captcha_input = browser.find_element(By.ID,"captcha")
        captcha_input.send_keys(captcha)
    # 点击登录
    login_button = browser.find_element(By.ID,"login_submit")
    login_button.click()
    time.sleep(1) # 等待登录
    # 点击i比特
    WebDriverWait(browser, 10).until(lambda x: x.find_element(By.ID, "ai-bit-shortcut"))
    ibit_button = browser.find_element(By.ID,"ai-bit-shortcut")
    ibit_button.click()
    # 切换iframe ai-bit-chat-box-dragger-web
    WebDriverWait(browser, 10).until(lambda x: x.find_element(By.CLASS_NAME, "ai-bit-chat-box-dragger-web"))
    iframe = browser.find_element(By.CLASS_NAME,"ai-bit-chat-box-dragger-web")
    browser.switch_to.frame(iframe)
    WebDriverWait(browser, 10).until(lambda x: x.find_element(By.XPATH, "//div[text()='Hi，我是艾比特，你的智慧学伴']"))
    # 尝试获取cookie
    res = browser.execute_script('return document.cookie')
    if res:
        # 关闭浏览器
        browser.quit()
        return res
    # 关闭浏览器
    browser.quit()
    raise Exception("登录失败: "+res)


def get_captcha(img_path):
    # 创建一个ddddocr对象
    ocr = ddddocr.DdddOcr(show_ad=False)

    # 读取验证码图片的字节数据
    with open(img_path, 'rb') as f:
        img_bytes = f.read()

    # 使用ddddocr进行验证码识别
    result = ocr.classification(img_bytes).upper()

    # 返回识别结果
    return result

