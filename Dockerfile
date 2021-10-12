FROM edemineduc/etl
LABEL maintainer="Miguel Aedo Pino - Centro de Innovación (Mineduc) <miguel.aedo@mineduc.cl>"
RUN apt-get install -y cron

# Allow statements and log messages to immediately appear in the Knative logs
ENV PYTHONUNBUFFERED True
ENV MONGO_URL mongodb://mongo:27017/reportdb
ENV PORT 8080
ENV DEBUG False
ENV OTP_SERVICE << URL del servicio del verificador de indentidad >>
ENV X_API_KEY << API KEY del servicio del verificador de identidad >>

#Configure cron
COPY cron-test /etc/cron.d/cron-test
RUN chmod 0644 /etc/cron.d/cron-test 
RUN crontab /etc/cron.d/cron-test
# Copy local code to the container image.
RUN mkdir /app
ENV APP_HOME /app
WORKDIR $APP_HOME
COPY . .

RUN pip install --no-cache-dir -r requirements.txt
RUN chmod +x ./entrypoint.sh

ENTRYPOINT ["sh", "entrypoint.sh"]