FROM openjdk:21-jdk-slim

WORKDIR /ors

RUN apt-get update \
    && apt-get install -y curl lsof \
    && curl -L -O https://github.com/GIScience/openrouteservice/releases/download/v8.0.0/ors.jar \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p files graphs_build graphs_ready flags

COPY conf /ors/conf
COPY files /ors/files
COPY graphs_build /ors/graphs_build
COPY graphs_ready /ors/graphs_ready
COPY entrypoint.sh /ors/entrypoint.sh

RUN chmod +x /ors/entrypoint.sh

EXPOSE 8082

ENTRYPOINT ["sh", "/ors/entrypoint.sh"]
