FROM eclipse-temurin:21-jdk-jammy

WORKDIR /otp
RUN apt-get update && apt-get install -y curl lsof \
    && curl -L -o otp-shaded-2.8.1.jar https://repo1.maven.org/maven2/org/opentripplanner/otp-shaded/2.8.1/otp-shaded-2.8.1.jar \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir flags

COPY ./config/* .
COPY ./entrypoint.sh .

EXPOSE 8080

ENTRYPOINT ["sh", "entrypoint.sh"]