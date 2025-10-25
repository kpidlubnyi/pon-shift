FROM openrouteservice/openrouteservice:v8.0.0

COPY conf/ors-config.yml home/ors/config/ors-config.yml

COPY files/*.osm.pbf /home/ors/files/

RUN mkdir -p /home/ors/graphs /home/ors/elevation_cache /home/ors/logs \
    && chown -R 1000:1000 /home/ors

ENV REBUILD_GRAPHS=TRUE
ENV CONTAINER_LOG_LEVEL=INFO
ENV XMS=3g
ENV XMX=4g
