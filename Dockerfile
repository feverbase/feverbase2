FROM python:3.8
LABEL maintainer="Noah Saso <noahsaso@berkeley.edu>"

## Add the wait script to the image
ADD https://github.com/ufoscout/docker-compose-wait/releases/download/2.7.3/wait /wait
RUN chmod +x /wait

RUN apt-get update
RUN apt-get install -y ca-certificates

WORKDIR /app
EXPOSE 5000

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

## Launch the wait tool and then your application
CMD /wait && python serve.py
