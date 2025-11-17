# Lab 3: 2-Phase Commit Protocol

Implementation of a distributed 2-Phase Commit (2PC) protocol for CISC 5597/6935 Distributed Systems.

## Quick Start

### Local Testing

```bash
# Make scripts executable
chmod +x start_all.sh stop_all.sh

# Start all nodes (Coordinator + 2 Participants)
./start_all.sh

# In another terminal, run automated scenarios
python3 run_scenarios.py

# Or use interactive client
python3 client.py

# Stop all nodes
./stop_all.sh
```

### Google Cloud VM

See [IMPLEMENTATION_README.md](IMPLEMENTATION_README.md) for detailed deployment instructions.

## System Components

- **Node-1 (Coordinator):** Orchestrates transactions (Port 8001)
- **Node-2 (Participant A):** Manages Account A (Port 8002)
- **Node-3 (Participant B):** Manages Account B (Port 8003)

## Test Scenarios

1. **Scenario 1.a:** A=200, B=300 - Normal operation
2. **Scenario 1.b:** A=90, B=50 - Insufficient funds test
3. **Scenario 1.c.i:** Node-2 crash before prepare response
4. **Scenario 1.c.ii:** Node-2 crash after prepare response

## Documentation

See [IMPLEMENTATION_README.md](IMPLEMENTATION_README.md) for complete documentation including:
- Architecture details
- 2PC protocol implementation
- Google Cloud VM deployment guide
- Troubleshooting guide