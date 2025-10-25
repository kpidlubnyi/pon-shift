#!/bin/sh
set -e
NEW_MAP_FLAG="new_map_is_available"
NEW_GTFS_FLAG="there_is_new_gtfs"
GRAPH_READY_FLAG="new_graph_is_ready"
OTP_PID=""

with_rebuilding() {
    REBUILDING=1
    "$@"
    REBUILDING=0
}

build_street_graph() {
    java -Xmx5G -Xms3G -jar otp-shaded-2.8.1.jar --buildStreet .
    echo "Street graph rebuild complete. Recreating transit graph..."
    touch "$NEW_GTFS_FLAG"
    rm -f "$NEW_MAP_FLAG"
}

build_transit_graph() {
    java -Xmx5G -Xms3G -jar otp-shaded-2.8.1.jar --loadStreet --save .
    echo "Transit graph rebuild complete. Creating readiness flag..."
    touch "$GRAPH_READY_FLAG"
    rm -f "$NEW_GTFS_FLAG"
}

serve_transit_graph() {
    PORT=8080
    
    while [ "${REBUILDING:-0}" -eq 1 ]; do
        echo "Graph is rebuilding, waiting..."
        sleep 5
    done
    
    if [ -n "$OTP_PID" ] && kill -0 "$OTP_PID" 2>/dev/null; then
        echo "Stopping old OTP Server (PID: $OTP_PID)..."
        kill -15 "$OTP_PID"
        sleep 5
        if kill -0 "$OTP_PID" 2>/dev/null; then
            echo "Force killing..."
            kill -9 "$OTP_PID"
            sleep 1
        fi
    fi
    
    PID=$(lsof -ti tcp:$PORT || true)
    if [ -n "$PID" ]; then
        echo "Port $PORT is occupied by PID $PID. Killing..."
        kill -15 $PID 2>/dev/null || true
        sleep 2
        kill -9 $PID 2>/dev/null || true
        sleep 1
    fi
    
    echo "Starting OTP Server on port $PORT..."
    java -Xmx5G -Xms3G -jar otp-shaded-2.8.1.jar --load --serve . &
    OTP_PID=$!
    
    rm -f "$GRAPH_READY_FLAG"
    echo "[INFO] OTP Server started with PID: $OTP_PID"
}

trap 'echo "Shutting down..."; [ -n "$OTP_PID" ] && kill $OTP_PID 2>/dev/null; exit 0' TERM INT

echo "Building street graph..."
with_rebuilding build_street_graph
echo "Street graph has been built successfully!"

while true; do
    if [ -n "$OTP_PID" ] && ! kill -0 "$OTP_PID" 2>/dev/null; then
        echo "[WARNING] OTP Server (PID: $OTP_PID) stopped unexpectedly"
        OTP_PID=""
    fi
    
    if [ -f "$NEW_MAP_FLAG" ]; then
        echo "Detected MAP flag. Rebuilding street graph..."
        with_rebuilding build_street_graph
    fi
    
    if [ -f "$NEW_GTFS_FLAG" ]; then
        echo "Detected GTFS flag. Rebuilding transit graph..."
        with_rebuilding build_transit_graph
    fi
    
    if [ -f "$GRAPH_READY_FLAG" ]; then
        echo "Detected new graph ready flag. Starting OTP Server..."
        serve_transit_graph
    fi
    
    sleep 10
done