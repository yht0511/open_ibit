FROM ubuntu:latest
RUN apt-get update && apt-get install -y python3 python3-pip wget unzip wget curl nano git -y
# 安装chrome
RUN wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
RUN dpkg -i google-chrome*.deb || true
RUN apt-get install -f -y
RUN rm google-chrome*.deb
# 安装chrome-driver
RUN wget https://storage.googleapis.com/chrome-for-testing-public/136.0.7103.113/linux64/chromedriver-linux64.zip && unzip chromedriver-linux64.zip && mv chromedriver-linux64/chromedriver /usr/bin/ && rm chromedriver-linux64.zip chromedriver-linux64/ -r && chmod +x /usr/bin/chromedriver

RUN mkdir /Program
COPY . /Program
WORKDIR /Program/
# 安装python依赖包
RUN pip3 install -r requirements.txt --break-system-packages 
ENTRYPOINT [ "python3","server.py"]