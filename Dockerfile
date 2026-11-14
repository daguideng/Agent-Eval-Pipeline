FROM python:3.10-slim
WORKDIR /app
COPY . .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install streamlit pymysql scipy numpy pandas
EXPOSE 8501
