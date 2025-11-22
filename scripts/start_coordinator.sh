#!/bin/bash
# Start the Coordinator (Node-1 / node0)

cd "$(dirname "$0")/.."

echo "Starting Coordinator on node0..."
python src/coordinator/coordinator.py config.json
