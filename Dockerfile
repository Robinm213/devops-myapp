FROM python:3.10

WORKDIR /app
COPY . .

RUN pip install --upgrade pip
RUN pip install numpy==1.26.4 pyarrow==15.0.2 streamlit pandas

EXPOSE 8501
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
