# CISC 5597/6935 Distributed Systems - Lab 3
## Two-Phase Commit Protocol with Raft Consensus

### Overview
This project implements a distributed transaction system using the Two-Phase Commit (2PC) protocol. The system manages bank account transactions between two accounts (A and B) across multiple nodes, ensuring ACID properties.

### Architecture

```
                    ┌─────────┐
                    │  Client │
                    └────┬────┘
                         │
                    ┌────▼────┐
                    │Coordinator│ (Node-1 / node0)
                    │  (2PC)   │
                    └────┬────┘
           ┌─────────────┴─────────────┐
           │                           │
    ┌──────▼──────┐             ┌──────▼──────┐
    │Participant A│             │Participant B│
    │  (Account A)│             │  (Account B)│
    │  5-node Raft│             │  5-node Raft│
    └─────────────┘             └─────────────┘
```

### Node Mapping (Google Cloud)
- **node0** (10.128.0.5): Coordinator
- **Cluster A** (Account A, 5 nodes with Raft):
  - node1 (10.128.0.2), node2 (10.128.0.3, Leader), node4 (10.128.0.6), node5 (10.128.0.8), node6 (10.128.0.10)
- **Cluster B** (Account B, 5 nodes with Raft):
  - node3 (10.128.0.4, Leader), node7 (10.128.0.11), node8 (10.128.0.20), node9 (10.128.0.21), node10 (10.128.0.22)

### Transactions
1. **Transfer**: Move $100 from Account A to Account B
2. **Bonus**: Add 20% bonus to A, and add the same amount (0.2 * A) to B

### Scenarios Implemented

#### 1.a - Normal Operation (A=200, B=300)
Both transactions execute successfully with proper 2PC coordination.

#### 1.b - Insufficient Funds (A=90, B=50)
Transfer fails due to insufficient funds, demonstrating automatic abort when a participant cannot commit.

#### 1.c.i - Participant Crash Before Response
Node-2 crashes (simulated by sleep) before responding to coordinator's prepare request. Coordinator times out and aborts.

#### 1.c.ii - Participant Crash After Response
Node-2 crashes after voting commit but before receiving the final decision.

#### 1.c.iii - Coordinator Crash (6935 only)
Coordinator crashes after sending prepare requests. Participants enter UNCERTAIN state.

### Setup Instructions

#### 1. Install Dependencies
```bash
pip install grpcio grpcio-tools protobuf
```

#### 2. Compile Protocol Buffers
```bash
bash scripts/compile_proto.sh
```

#### 3. Start Nodes (on Google Cloud)

**On node0 (Coordinator):**
```bash
python src/coordinator/coordinator.py config.json
```

**On node2 (Participant A Leader):**
```bash
python src/participant/participant.py config.json node2 A true
```

**On node3 (Participant B Leader):**
```bash
python src/participant/participant.py config.json node3 B true
```

**On other nodes (Raft followers):**
```bash
# For Account A followers (node1, node4, node5, node6)
python src/participant/participant.py config.json node1 A false

# For Account B followers (node7, node8, node9, node10)
python src/participant/participant.py config.json node7 B false
```

#### 4. Run Client
```bash
# Interactive mode
python src/client/client.py config.json

# Run specific scenario
python src/client/client.py config.json a   # Scenario 1.a
python src/client/client.py config.json b   # Scenario 1.b
python src/client/client.py config.json c1  # Scenario 1.c.i
python src/client/client.py config.json c2  # Scenario 1.c.ii
python src/client/client.py config.json c3  # Scenario 1.c.iii
python src/client/client.py config.json all # Run all scenarios
```

### Local Testing
For testing on a single machine:
```bash
# Copy local config
cp config_local.json config.json

# Start all nodes
bash scripts/start_all_local.sh

# In another terminal, run client
python src/client/client.py config.json
```

### Project Structure
```
├── config.json              # Google Cloud configuration
├── config_local.json        # Local testing configuration
├── proto/
│   ├── two_phase_commit.proto    # Protocol definitions
│   ├── two_phase_commit_pb2.py   # Generated Python code
│   └── two_phase_commit_pb2_grpc.py
├── src/
│   ├── coordinator/
│   │   └── coordinator.py   # 2PC Coordinator
│   ├── participant/
│   │   └── participant.py   # Participant with Raft
│   ├── client/
│   │   └── client.py        # Transaction client
│   └── common/
│       └── utils.py         # Utilities
├── scripts/
│   ├── deploy.sh            # Deployment script
│   ├── start_coordinator.sh
│   ├── start_participant.sh
│   └── start_all_local.sh
└── data/                    # Account data storage
```

### 2PC Protocol Flow

```
Phase 1 (Prepare/Vote):
1. Coordinator → Participants: "CanCommit?"
2. Participants check if operation is valid
3. Participants → Coordinator: "VoteCommit" or "VoteAbort"

Phase 2 (Commit/Abort):
4. If all voted commit: Coordinator → Participants: "DoCommit"
   If any voted abort:  Coordinator → Participants: "DoAbort"
5. Participants apply or rollback changes
6. Participants → Coordinator: "Acknowledge"
```

### Raft Integration
Each participant cluster uses Raft consensus to replicate account values:
- Leader handles 2PC messages from coordinator
- Leader replicates prepare/commit decisions to followers
- Majority acknowledgment required for consensus

### Message Exchange Output
The system prints detailed message exchanges for demonstration:
```
============================================================
MESSAGE EXCHANGE
  From: Coordinator
  To:   Participant A (Node-2)
  Type: PREPARE
  Content: CanCommit? Withdraw $100 from A
============================================================
```

### Authors
CISC 5597/6935 Distributed Systems - Lab 3
