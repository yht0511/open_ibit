# 百丽宫的Deepseek R1

## 项目简介

你梨居然上新了满血版的r1 671b模型!可喜可贺~
正愁找不到免费可靠的api吗?刚好来白嫖学校的!

## 食用方法
```bash
# 不需要验证的情况
docker run -d -p 8000:8000 --name OpeniBIT \
    -e BIT_USERNAME = 统一身份验证用户名 \
    -e BIT_PASSWORD = 统一身份验证密码 \
    yht0511/open_ibit:latest
# 需要设置api_key
docker run -d -p 8000:8000 --name OpeniBIT \
    -e BIT_USERNAME = 统一身份验证用户名 \
    -e BIT_PASSWORD = 统一身份验证密码 \
    -e API_KEY = 你想设置的api_key \
    yht0511/open_ibit:latest
```