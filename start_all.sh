#!/bin/bash
# Start all nodes for 2PC system

echo "Starting 2PC Distributed System..."
echo "==================================="

# Kill any existing processes
echo "Cleaning up old processes..."
pkill -f "python.*participant.py" 2>/dev/null
pkill -f "python.*coordinator.py" 2>/dev/null
sleep 2

# Create log directory
mkdir -p logs

# Start Node-2 (Participant A)
echo "Starting Node-2 (Participant A) on port 8002..."
python3 participant.py 2 > logs/node2.log 2>&1 &
NODE2_PID=$!
sleep 1

# Start Node-3 (Participant B)
echo "Starting Node-3 (Participant B) on port 8003..."
python3 participant.py 3 > logs/node3.log 2>&1 &
NODE3_PID=$!
sleep 1

# Start Node-1 (Coordinator)
echo "Starting Node-1 (Coordinator) on port 8001..."
python3 coordinator.py > logs/coordinator.log 2>&1 &
COORDINATOR_PID=$!
sleep 2

echo ""
echo "==================================="
echo "All nodes started!"
echo "==================================="
echo "Node-1 (Coordinator): PID $COORDINATOR_PID, Port 8001"
echo "Node-2 (Participant A): PID $NODE2_PID, Port 8002"
echo "Node-3 (Participant B): PID $NODE3_PID, Port 8003"
echo ""
echo "Logs are in the logs/ directory:"
echo "  - logs/coordinator.log"
echo "  - logs/node2.log"
echo "  - logs/node3.log"
echo ""
echo "To run scenarios: python3 run_scenarios.py"
echo "To run interactive client: python3 client.py"
echo ""
echo "To stop all nodes: ./stop_all.sh"
echo "==================================="
