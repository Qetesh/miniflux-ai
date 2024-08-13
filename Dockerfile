FROM python:3.9-alpine
LABEL authors="qetesh"
WORKDIR /app
COPY requirements.txt ./
RUN pip3 install --no-cache-dir -r requirements.txt
COPY . .
CMD [ "python3","-u","main.py" ]