# Lab 3: 2-Phase Commit Protocol Implementation

## Overview

This project implements a distributed 2-Phase Commit (2PC) protocol for coordinating transactions across multiple nodes. The system simulates a banking scenario with two accounts managed by different participant nodes.

## System Architecture

### Components

1. **Node-1 (Coordinator)** - `coordinator.py`
   - Orchestrates distributed transactions
   - Implements 2PC protocol (Prepare and Commit phases)
   - Manages communication with all participants
   - Port: 8001

2. **Node-2 (Participant A)** - `participant.py 2`
   - Manages Account A
   - Stores account balance in `account_A.txt`
   - Responds to prepare/commit/abort requests
   - Port: 8002

3. **Node-3 (Participant B)** - `participant.py 3`
   - Manages Account B
   - Stores account balance in `account_B.txt`
   - Responds to prepare/commit/abort requests
   - Port: 8003

4. **Client** - `client.py`
   - Interactive client for sending transactions
   - Displays account balances and transaction results

5. **Scenario Runner** - `run_scenarios.py`
   - Automated testing of all required scenarios
   - Simulates normal operations and failure cases

## Transactions

### Transaction 1: Transfer
- Transfers a specified amount from Account A to Account B
- Account A is debited (decreased)
- Account B is credited (increased)

### Transaction 2: Bonus
- Adds 20% bonus to Account A
- Adds the same amount (0.2 * A) to Account B
- Both accounts are credited

## 2PC Protocol Implementation

### Phase 1: Prepare
1. Coordinator sends PREPARE request to all participants
2. Each participant checks if it can execute the transaction
3. Participants vote:
   - VOTE_COMMIT: Can execute (e.g., sufficient balance)
   - VOTE_ABORT: Cannot execute (e.g., would result in negative balance)
4. If all vote COMMIT, proceed to Phase 2 commit
5. If any vote ABORT or timeout, proceed to Phase 2 abort

### Phase 2: Commit or Abort
- **If all voted COMMIT:**
  - Coordinator sends COMMIT to all participants
  - Participants write changes to disk
  - Transaction succeeds

- **If any voted ABORT:**
  - Coordinator sends ABORT to all participants
  - Participants discard prepared changes
  - Transaction fails

## Test Scenarios

### Scenario 1.a: Normal Operation (A=200, B=300)
- Initial: A=200, B=300
- Tests:
  1. Transfer 100 from A to B → Success (A=100, B=400)
  2. 20% Bonus → Success (A=240, B=340 with original balances)
- **Expected Result:** All transactions commit successfully

### Scenario 1.b: Insufficient Funds (A=90, B=50)
- Initial: A=90, B=50
- Tests:
  1. Transfer 100 from A to B → **ABORT** (would make A negative)
  2. 20% Bonus → Success (A=108, B=68)
- **Expected Result:** Transfer aborts, Bonus commits

### Scenario 1.c.i: Node-2 Crashes BEFORE Prepare Response
- Initial: A=200, B=300
- Node-2 sleeps 30 seconds before responding
- Transfer 100 from A to B
- **Expected Result:**
  - Coordinator times out waiting for Node-2
  - Transaction aborts due to timeout
  - Accounts remain unchanged

### Scenario 1.c.ii: Node-2 Crashes AFTER Prepare Response
- Initial: A=200, B=300
- Node-2 sleeps 30 seconds after responding with VOTE_COMMIT
- Transfer 100 from A to B
- **Expected Result:**
  - Node-2 responds before crashing
  - Transaction commits successfully
  - Accounts are updated despite the crash
  - Node-2 recovers after sleep

## Setup and Running

### Prerequisites
- Python 3.6 or higher
- No external dependencies (uses Python standard library)

### Local Testing

#### Method 1: Using Start Script (Recommended)

```bash
# Make scripts executable
chmod +x start_all.sh stop_all.sh

# Start all nodes
./start_all.sh

# In another terminal, run scenarios
python3 run_scenarios.py

# Or use interactive client
python3 client.py

# Stop all nodes when done
./stop_all.sh
```

#### Method 2: Manual Start

**Terminal 1 - Node-2 (Participant A):**
```bash
python3 participant.py 2
```

**Terminal 2 - Node-3 (Participant B):**
```bash
python3 participant.py 3
```

**Terminal 3 - Coordinator:**
```bash
python3 coordinator.py
```

**Terminal 4 - Client/Scenarios:**
```bash
# Run automated scenarios
python3 run_scenarios.py

# Or run interactive client
python3 client.py
```

### Google Cloud VM Deployment

#### 1. Create VM Instances

Create 3 VM instances in Google Cloud:
- **VM 1:** Coordinator (e2-micro or higher)
- **VM 2:** Participant A (e2-micro or higher)
- **VM 3:** Participant B (e2-micro or higher)

#### 2. Configure Firewall Rules

Allow inbound traffic on ports 8001-8003:

```bash
gcloud compute firewall-rules create allow-2pc-ports \
    --allow tcp:8001-8003 \
    --description "Allow 2PC protocol ports"
```

#### 3. Setup Each VM

On each VM:

```bash
# Install Python 3
sudo apt update
sudo apt install python3 python3-pip -y

# Clone/upload the code
# (Upload via scp or clone from git)

# Upload files to VM
cd Advanced_Distributed_Systems_Lab3
```

#### 4. Update Configuration

Edit `config.py` on each VM with the actual IP addresses:

```python
# Use external IPs of your VMs
COORDINATOR_HOST = 'X.X.X.X'  # VM1 external IP
PARTICIPANT_A_HOST = 'Y.Y.Y.Y'  # VM2 external IP
PARTICIPANT_B_HOST = 'Z.Z.Z.Z'  # VM3 external IP
```

Or for internal IPs:
```python
COORDINATOR_HOST = '10.X.X.1'  # VM1 internal IP
PARTICIPANT_A_HOST = '10.X.X.2'  # VM2 internal IP
PARTICIPANT_B_HOST = '10.X.X.3'  # VM3 internal IP
```

#### 5. Start Nodes

**On VM1 (Coordinator):**
```bash
python3 coordinator.py
```

**On VM2 (Participant A):**
```bash
python3 participant.py 2
```

**On VM3 (Participant B):**
```bash
python3 participant.py 3
```

#### 6. Run Tests from Any VM or Your Local Machine

Update your local `config.py` with VM IP addresses, then:

```bash
python3 run_scenarios.py
# or
python3 client.py
```

## File Structure

```
Advanced_Distributed_Systems_Lab3/
├── config.py              # Configuration (ports, hosts)
├── coordinator.py         # Node-1: Coordinator
├── participant.py         # Node-2/3: Participants
├── client.py             # Interactive client
├── run_scenarios.py      # Automated scenario runner
├── start_all.sh          # Start all nodes (local)
├── stop_all.sh           # Stop all nodes (local)
├── requirements.txt      # Python dependencies (none needed)
├── account_A.txt         # Account A balance (auto-created)
├── account_B.txt         # Account B balance (auto-created)
├── logs/                 # Log files (auto-created)
│   ├── coordinator.log
│   ├── node2.log
│   └── node3.log
└── IMPLEMENTATION_README.md  # This file
```

## Usage Examples

### Using the Interactive Client

```bash
$ python3 client.py

2PC Transaction System - Client Menu
==================================================
1. Get Account Balances
2. Execute Transfer Transaction (A -> B)
3. Execute Bonus Transaction (20% bonus)
4. Set Crash Simulation
5. Reset Crash Simulation
0. Exit
==================================================
Enter your choice: 1

=== Current Account Balances ===
  Account A: $200.0
  Account B: $300.0
```

### Running Automated Scenarios

```bash
$ python3 run_scenarios.py

Choose an option:
==================================================
1. Run all scenarios (interactive)
2. Run Scenario 1.a only
3. Run Scenario 1.b only
4. Run Scenario 1.c.i only
5. Run Scenario 1.c.ii only
0. Exit
==================================================
Enter choice: 1
```

## Logging

All nodes generate detailed logs:
- **logs/coordinator.log** - Coordinator activity
- **logs/node2.log** - Node-2 (Account A) activity
- **logs/node3.log** - Node-3 (Account B) activity

Logs include:
- Transaction IDs
- Prepare/Commit/Abort messages
- Vote results
- Account balance changes
- Error and timeout information

## Failure Simulation

The system can simulate node failures:

### Crash Before Prepare Response
```python
coordinator.set_participant_crash('A', crash_before=True)
```
- Node delays 30 seconds before responding
- Coordinator times out (15s)
- Transaction aborts

### Crash After Prepare Response
```python
coordinator.set_participant_crash('A', crash_after=True)
```
- Node responds with vote, then sleeps 30 seconds
- Coordinator proceeds with commit
- Transaction succeeds

## Key Features

1. **ACID Properties:**
   - Atomicity: All-or-nothing transaction execution
   - Consistency: Account balances remain consistent
   - Isolation: Transactions are isolated with locks
   - Durability: Changes persisted to disk files

2. **Fault Tolerance:**
   - Timeout handling for unresponsive participants
   - Automatic abort on failures
   - Crash recovery simulation

3. **Thread Safety:**
   - Locks protect concurrent account access
   - Safe file I/O operations

4. **Comprehensive Logging:**
   - Detailed transaction tracking
   - Debug information for troubleshooting

## Troubleshooting

### Connection Issues
- Verify all nodes are running
- Check firewall rules (especially on GCP)
- Verify IP addresses and ports in config.py
- Check logs for connection errors

### Transaction Failures
- Check account balances (sufficient funds?)
- Review logs for error messages
- Verify participants are responding
- Check timeout settings

### Port Already in Use
```bash
# Find process using port
lsof -i :8001  # or 8002, 8003

# Kill the process
kill -9 <PID>

# Or use stop script
./stop_all.sh
```

## Implementation Notes

### 2PC Protocol
- Uses XML-RPC for inter-node communication
- 15-second timeout for prepare responses
- Automatic abort on any failure or timeout

### Account Storage
- Simple text files for account balances
- File locks prevent concurrent access
- Atomic write operations

### Transaction Validation
- Checks for negative balances
- Validates transaction parameters
- Ensures transaction ID consistency

## Author

Implementation for CISC 5597/6935 Distributed Systems Lab 3

## References

- Two-Phase Commit Protocol
- ACID Properties
- Distributed Transactions
- RPC Communication
