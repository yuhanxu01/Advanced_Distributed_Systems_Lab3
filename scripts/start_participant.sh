#!/bin/bash
# Start a Participant node
# Usage: ./start_participant.sh <node_id> <account> [is_leader]
# Example: ./start_participant.sh node2 A true

cd "$(dirname "$0")/.."

NODE_ID=${1:-node2}
ACCOUNT=${2:-A}
IS_LEADER=${3:-false}

echo "Starting Participant $NODE_ID for Account $ACCOUNT (Leader: $IS_LEADER)..."
python src/participant/participant.py config.json "$NODE_ID" "$ACCOUNT" "$IS_LEADER"
