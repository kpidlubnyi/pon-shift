#!/bin/sh
set -e

ORS_NEW_MAP_FLAG="./flags/ors_there_is_new_map" 

ors_echo(){
    echo "[ORS-WATCHDOG] $1"
}

download_new_map(){
    ors_echo "Downloading new map..."
    curl -L -o ./files/mazowieckie-latest.osm.pbf https://download.geofabrik.de/europe/poland/mazowieckie-latest.osm.pbf
}

build_new_graphs(){
    ors_echo "Building new graphs..."
    java $JAVA_OPTS -jar ors.jar ./conf/ors-config-build.yml
    rm -rf ./graphs_ready/walking
    mv ./graphs_build/walking ./graphs_ready/
    rm -f $ORS_NEW_MAP_FLAG
}

restart_ors_server(){
    ors_echo "Restarting ORS server..."
    pkill -f 'java.*ors.jar' || true
    java $JAVA_OPTS -jar ors.jar ./conf/ors-config-serve.yml &
}


ors_echo "Wathdog started!"

while true; do
    if [ -f "$ORS_NEW_MAP_FLAG" ]; then
        ors_echo "Detected new map flag!"
        download_new_map
        build_new_graphs
        restart_ors_server
        ors_echo "ORS server restarted with new graphs!"
    fi
    sleep 5
done
