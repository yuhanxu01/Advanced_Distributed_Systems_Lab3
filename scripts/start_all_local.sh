#!/bin/bash
# Start all nodes locally for testing (uses localhost)

cd "$(dirname "$0")/.."

# Use local config
cp config_local.json config.json 2>/dev/null || true

echo "Starting all nodes locally..."

# Start Coordinator
echo "Starting Coordinator..."
python src/coordinator/coordinator.py config.json &
COORD_PID=$!
sleep 2

# Start Participant A (leader)
echo "Starting Participant A (leader)..."
python src/participant/participant.py config.json node2 A true &
PART_A_PID=$!
sleep 1

# Start Participant B (leader)
echo "Starting Participant B (leader)..."
python src/participant/participant.py config.json node3 B true &
PART_B_PID=$!
sleep 1

echo ""
echo "All nodes started!"
echo "  Coordinator PID: $COORD_PID"
echo "  Participant A PID: $PART_A_PID"
echo "  Participant B PID: $PART_B_PID"
echo ""
echo "Run the client: python src/client/client.py config.json"
echo "Press Ctrl+C to stop all nodes"

# Wait for any process to exit
wait
