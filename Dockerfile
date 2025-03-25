FROM ubuntu:latest
RUN apt-get update && apt-get install -y python3 python3-pip wget unzip wget curl nano git -y

RUN mkdir /Program
COPY . /Program
WORKDIR /Program/
# 安装python依赖包
RUN pip3 install -r requirements.txt --break-system-packages 
ENTRYPOINT [ "python3","server.py"]