# 百丽宫的Deepseek R1

## 项目简介

你梨居然上新了满血版的r1 671b模型!可喜可贺~
正愁找不到免费可靠的api吗?刚好来白嫖学校的!

## 食用方法
```bash
# 不需要验证的情况
docker run -d -p 8000:8000 --name OpeniBIT \
    -e BIT_USERNAME=统一身份验证用户名 \
    -e BIT_PASSWORD=统一身份验证密码 \
    -e TZ=Asia/Shanghai \
    yht0511/open_ibit:latest
# 需要设置api_key
docker run -d -p 8000:8000 --name OpeniBIT \
    -e BIT_USERNAME=统一身份验证用户名 \
    -e BIT_PASSWORD=统一身份验证密码 \
    -e API_KEY=你想设置的api_key \
    -e TZ=Asia/Shanghai \
    yht0511/open_ibit:latest
```

现在,你已经获得了一个免费的ds接口!你现在可以使用openai等库对接该接口,或是简单地使用nextchat: 在设置里填入接口地址和api_key(没有设置则随便输入)即可享用!


## 2025.6.8更新
现在支持智能体广场的模型,设置环境变量`AGENT_APP_KEY`和`AGENT_VISITOR_KEY`即可使用。
默认模型名称:"deepseek-r1",ibit模型名称:"ibit"。