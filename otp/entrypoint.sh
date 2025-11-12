#!/bin/sh
set -e
NEW_MAP_FLAG="/otp/flags/otp_there_is_new_map"
NEW_GTFS_FLAG="/otp/flags/otp_there_is_new_gtfs"
GRAPH_READY_FLAG="/otp/flags/otp_new_graph_is_ready"
OTP_PID=""


with_rebuilding() {
    REBUILDING=1
    "$@"
    REBUILDING=0
}

otp_echo(){
    echo "[OTP-WATCHDOG] $1"
}

build_street_graph() {
    java $JAVA_OPTS -jar otp-shaded-2.8.1.jar --buildStreet .
    cp ./streetGraph.obj ./graphs/streetGraph.obj
    otp_echo "Street graph rebuild complete. Recreating transit graph..."
    touch "$NEW_GTFS_FLAG"
    rm -f "$NEW_MAP_FLAG"
}

build_transit_graph() {
    java $JAVA_OPTS -jar otp-shaded-2.8.1.jar --loadStreet --save .
    cp ./graph.obj ./graphs/graph.obj
    otp_echo "Transit graph rebuild complete. Creating readiness flag..."
    touch "$GRAPH_READY_FLAG"
    rm -f "$NEW_GTFS_FLAG"
}

serve_transit_graph() {
    PORT=8080
    
    while [ "${REBUILDING:-0}" -eq 1 ]; do
        otp_echo "Graph is rebuilding, waiting..."
        sleep 5
    done
    
    if [ -n "$OTP_PID" ] && kill -0 "$OTP_PID" 2>/dev/null; then
        otp_echo "Stopping old OTP Server (PID: $OTP_PID)..."
        kill -15 "$OTP_PID"
        sleep 5
        if kill -0 "$OTP_PID" 2>/dev/null; then
            otp_echo "Force killing..."
            kill -9 "$OTP_PID"
            sleep 1
        fi
    fi
    
    PID=$(lsof -ti tcp:$PORT || true)
    if [ -n "$PID" ]; then
        otp_echo "Port $PORT is occupied by PID $PID. Killing..."
        kill -15 $PID 2>/dev/null || true
        sleep 2
        kill -9 $PID 2>/dev/null || true
        sleep 1
    fi
    
    otp_echo "Starting OTP Server on port $PORT..."
    java $JAVA_OPTS -jar otp-shaded-2.8.1.jar --load --serve . &
    OTP_PID=$!
    
    rm -f "$GRAPH_READY_FLAG"
    otp_echo "OTP Server started with PID: $OTP_PID"
}

initial_run() {
    if [ -f ./graphs/graph.obj ]; then
        otp_echo "Found transit graph! Serving..."
        cp ./graphs/graph.obj ./graph.obj
        serve_transit_graph
        return
    fi

    otp_echo "No transit graphs from the previous running! Looking for street graph..."

    if [ -f ./graphs/streetGraph.obj ]; then
        otp_echo "Found street graph! Building transit graph..."
        cp ./graphs/streetGraph.obj ./streetGraph.obj
        with_rebuilding build_transit_graph
    fi

    otp_echo "No street graphs from the previous running! Starting flag-files checking..."
}



otp_echo "Watchdog started!"
trap 'echo "Shutting down..."; [ -n "$OTP_PID" ] && kill $OTP_PID 2>/dev/null; exit 0' TERM INT
initial_run

while true; do
    if [ -n "$OTP_PID" ] && ! kill -0 "$OTP_PID" 2>/dev/null; then
        otp_echo "OTP Server (PID: $OTP_PID) stopped unexpectedly"
        OTP_PID=""
    fi
    
    if [ -f "$NEW_MAP_FLAG" ]; then
        otp_echo "Detected MAP flag. Rebuilding street graph..."
        with_rebuilding build_street_graph
    fi
    
    if [ -f "$NEW_GTFS_FLAG" ]; then
        if [ ! -f "/otp/streetGraph.obj" ]; then
            otp_echo "streetGraph.obj not found. Building street graph..."
            with_rebuilding build_street_graph
        fi

        otp_echo "Detected GTFS flag. Rebuilding transit graph..."
        with_rebuilding build_transit_graph
    fi
    
    if [ -f "$GRAPH_READY_FLAG" ]; then
        otp_echo "Detected new graph ready flag. Starting OTP Server..."
        serve_transit_graph
    fi
    
    sleep 10
done