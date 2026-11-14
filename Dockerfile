FROM python:3.10-slim
WORKDIR /app
COPY . .
# 👇 加上清华源，并且拉长超时时间
RUN pip install --no-cache-dir --default-timeout=100 -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt
RUN pip install --no-cache-dir --default-timeout=100 -i https://pypi.tuna.tsinghua.edu.cn/simple streamlit pymysql scipy numpy pandas
EXPOSE 8501
