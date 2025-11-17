"""
Configuration file for 2PC Lab3
Defines the network configuration for all nodes
"""

# Node configurations
COORDINATOR_HOST = 'localhost'
COORDINATOR_PORT = 8001

PARTICIPANT_A_HOST = 'localhost'
PARTICIPANT_A_PORT = 8002

PARTICIPANT_B_HOST = 'localhost'
PARTICIPANT_B_PORT = 8003

# Timeout settings (in seconds)
RPC_TIMEOUT = 5
PARTICIPANT_TIMEOUT = 10

# Transaction types
TRANSACTION_TRANSFER = 'transfer'
TRANSACTION_BONUS = 'bonus'
