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


ors_echo "Watchdog started!"
ors_echo "Initial run..."

if [ ! -d "./graphs_ready" ] || [ ! "$(ls -A ./graphs_ready)" ]; then
    ors_echo "No graphs to run, rebuilding..."
    download_new_map
    build_new_graphs
    restart_ors_server
    sleep 1
else
    ors_echo "Found graph! Starting..."
    download_new_map
    restart_ors_server
    sleep 1
fi    

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
