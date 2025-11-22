"""
Common utilities for the 2PC system.
"""
import json
import os
import logging
import uuid
from datetime import datetime

# Configure logging
def setup_logging(node_id: str, log_dir: str = "logs"):
    """Setup logging configuration for a node."""
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f"{node_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

    logging.basicConfig(
        level=logging.INFO,
        format=f'[%(asctime)s] [{node_id}] [%(levelname)s] %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(node_id)

def load_config(config_path: str = "config.json") -> dict:
    """Load configuration from JSON file."""
    with open(config_path, 'r') as f:
        return json.load(f)

def generate_transaction_id() -> str:
    """Generate a unique transaction ID."""
    return f"txn_{uuid.uuid4().hex[:8]}_{int(datetime.now().timestamp())}"

def save_balance(data_dir: str, account: str, balance: float):
    """Save account balance to disk file."""
    os.makedirs(data_dir, exist_ok=True)
    file_path = os.path.join(data_dir, f"account_{account}.txt")
    with open(file_path, 'w') as f:
        f.write(str(balance))

def load_balance(data_dir: str, account: str, default: float = 0.0) -> float:
    """Load account balance from disk file."""
    file_path = os.path.join(data_dir, f"account_{account}.txt")
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            return float(f.read().strip())
    return default

def save_transaction_log(data_dir: str, node_id: str, txn_id: str, state: str, details: dict):
    """Save transaction state to disk for recovery."""
    os.makedirs(data_dir, exist_ok=True)
    log_file = os.path.join(data_dir, f"{node_id}_txn_log.json")

    logs = []
    if os.path.exists(log_file):
        with open(log_file, 'r') as f:
            logs = json.load(f)

    logs.append({
        "transaction_id": txn_id,
        "state": state,
        "timestamp": datetime.now().isoformat(),
        "details": details
    })

    with open(log_file, 'w') as f:
        json.dump(logs, f, indent=2)

def print_message_exchange(sender: str, receiver: str, message_type: str, content: str):
    """Print formatted message exchange for demonstration."""
    print(f"\n{'='*60}")
    print(f"MESSAGE EXCHANGE")
    print(f"  From: {sender}")
    print(f"  To:   {receiver}")
    print(f"  Type: {message_type}")
    print(f"  Content: {content}")
    print(f"{'='*60}\n")
