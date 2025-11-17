#!/bin/bash
# Stop all nodes for 2PC system

echo "Stopping all 2PC nodes..."

pkill -f "python.*participant.py"
pkill -f "python.*coordinator.py"

echo "All nodes stopped."
