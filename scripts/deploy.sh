#!/bin/bash
# Deployment script for Google Cloud VMs
# Run this on each node to set up the environment

set -e

echo "=== Setting up 2PC Lab Environment ==="

# Install Python dependencies
pip install grpcio grpcio-tools protobuf

# Navigate to project directory
cd "$(dirname "$0")/.."

# Compile protocol buffers
echo "Compiling protocol buffers..."
bash scripts/compile_proto.sh

echo "=== Setup Complete ==="
echo "Now run the appropriate script for this node:"
echo "  Coordinator (node0): bash scripts/start_coordinator.sh"
echo "  Participant A leader (node2): bash scripts/start_participant.sh node2 A true"
echo "  Participant B leader (node3): bash scripts/start_participant.sh node3 B true"
echo "  Client: python src/client/client.py config.json"
