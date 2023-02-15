FROM ubuntu

USER root

COPY requirements.txt .

RUN apt update -y
RUN apt install python3 pip -y

RUN pip install --upgrade pip
RUN pip install --user -r requirements.txt

# CMD ["python3", "/src/msg_listen.py"]
