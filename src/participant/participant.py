"""
Participant Node - Manages Account A or B with Raft consensus
CISC 5597/6935 Distributed Systems - Lab 3
"""
import grpc
import sys
import os
import time
import json
import threading
from concurrent import futures

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from proto import two_phase_commit_pb2 as pb2
from proto import two_phase_commit_pb2_grpc as pb2_grpc
from common.utils import (
    setup_logging, load_config, save_balance, load_balance,
    save_transaction_log, print_message_exchange
)

class ParticipantServicer(pb2_grpc.ParticipantServiceServicer):
    """
    Participant handles 2PC messages from coordinator and manages account balance.
    Integrates with Raft for replication across cluster.
    """

    def __init__(self, config: dict, node_id: str, account: str, cluster_config: dict):
        self.config = config
        self.node_id = node_id
        self.account = account
        self.cluster_config = cluster_config
        self.logger = setup_logging(f"{node_id}_{account}")
        self.data_dir = os.path.join(os.path.dirname(__file__), "../../data", node_id)

        # Crash simulation mode
        self.crash_mode = "none"  # "none", "before_response", "after_response"
        self.crash_sleep_time = config["timeouts"]["crash_sleep_time"]

        # Transaction state (for 2PC)
        self.pending_transactions = {}  # txn_id -> {operation, amount, prepared_value}

        # Raft state
        self.is_leader = False
        self.current_term = 0
        self.voted_for = None
        self.log = []  # Raft log entries
        self.commit_index = 0
        self.last_applied = 0

        # Initialize balance from disk or default
        self.balance = load_balance(self.data_dir, self.account, default=0.0)

        # Lock for thread safety
        self.lock = threading.Lock()

        self.logger.info(f"Participant {node_id} initialized for Account {account}")
        self.logger.info(f"Initial balance: ${self.balance}")

    def _replicate_to_followers(self, command: dict) -> bool:
        """
        Replicate command to Raft followers.
        Returns True if majority acknowledged (consensus reached).
        """
        if not self.is_leader:
            return True  # Non-leaders don't replicate

        nodes = self.cluster_config["nodes"]
        success_count = 1  # Count self
        majority = len(nodes) // 2 + 1

        self.logger.info(f"[RAFT] Replicating to followers, need {majority} for majority")

        for node in nodes:
            if node["id"] == self.node_id:
                continue

            try:
                channel = grpc.insecure_channel(f"{node['ip']}:{node['raft_port']}")
                stub = pb2_grpc.RaftServiceStub(channel)

                entry = pb2.RaftLogEntry(
                    term=self.current_term,
                    index=len(self.log),
                    command=json.dumps(command)
                )

                request = pb2.AppendEntriesRequest(
                    term=self.current_term,
                    leader_id=self.node_id,
                    prev_log_index=len(self.log) - 1 if self.log else -1,
                    prev_log_term=self.log[-1].term if self.log else 0,
                    entries=[entry],
                    leader_commit=self.commit_index
                )

                response = stub.AppendEntries(request, timeout=2)
                if response.success:
                    success_count += 1
                    self.logger.info(f"[RAFT] Follower {node['id']} acknowledged")

            except Exception as e:
                self.logger.warning(f"[RAFT] Failed to replicate to {node['id']}: {e}")

        consensus = success_count >= majority
        self.logger.info(f"[RAFT] Consensus: {consensus} ({success_count}/{len(nodes)})")
        return consensus

    def Prepare(self, request, context):
        """
        Handle Phase 1 (Prepare) from coordinator.
        Check if transaction can be committed and prepare to execute.
        """
        txn_id = request.transaction_id
        self.logger.info(f"[TXN {txn_id}] Received PREPARE: {request.operation}, amount={request.amount}")

        # Simulate crash BEFORE responding (c.i scenario)
        if self.crash_mode == "before_response":
            self.logger.info(f"[TXN {txn_id}] CRASH SIMULATION: Sleeping before response...")
            print(f"\n!!! NODE {self.node_id} CRASH: Sleeping for {self.crash_sleep_time}s BEFORE responding !!!")
            print(f"!!! Coordinator will timeout waiting for response !!!\n")
            time.sleep(self.crash_sleep_time)
            print(f"!!! NODE {self.node_id} RECOVERED !!!\n")

        with self.lock:
            current_balance = self.balance
            can_commit = True
            message = ""

            # Check if operation is valid
            if request.operation == "withdraw":
                if current_balance >= request.amount:
                    prepared_value = current_balance - request.amount
                    message = f"Can withdraw ${request.amount}, balance sufficient"
                else:
                    can_commit = False
                    message = f"INSUFFICIENT FUNDS: Balance ${current_balance} < ${request.amount}"
                    self.logger.warning(f"[TXN {txn_id}] {message}")
            elif request.operation == "deposit":
                prepared_value = current_balance + request.amount
                message = f"Can deposit ${request.amount}"
            elif request.operation == "read":
                prepared_value = current_balance
                message = f"Read balance: ${current_balance}"
            else:
                can_commit = False
                message = f"Unknown operation: {request.operation}"

            # Store pending transaction
            if can_commit:
                self.pending_transactions[txn_id] = {
                    "operation": request.operation,
                    "amount": request.amount,
                    "prepared_value": prepared_value,
                    "original_value": current_balance
                }

                # Replicate prepare to Raft followers
                if self.is_leader:
                    consensus = self._replicate_to_followers({
                        "type": "prepare",
                        "txn_id": txn_id,
                        "operation": request.operation,
                        "amount": request.amount
                    })
                    if not consensus:
                        can_commit = False
                        message = "Failed to reach Raft consensus"

            # Save to transaction log
            save_transaction_log(self.data_dir, self.node_id, txn_id,
                               "VOTE_COMMIT" if can_commit else "VOTE_ABORT",
                               {"balance": current_balance, "operation": request.operation})

            self.logger.info(f"[TXN {txn_id}] Vote: {'COMMIT' if can_commit else 'ABORT'} - {message}")

        # Simulate crash AFTER responding (c.ii scenario)
        if self.crash_mode == "after_response" and can_commit:
            # Start crash simulation in background after sending response
            def delayed_crash():
                time.sleep(0.1)  # Small delay to ensure response is sent
                print(f"\n!!! NODE {self.node_id} CRASH: Sleeping for {self.crash_sleep_time}s AFTER responding !!!")
                print(f"!!! Node received DoCommit but crashed before applying !!!\n")
                time.sleep(self.crash_sleep_time)
                print(f"!!! NODE {self.node_id} RECOVERED !!!\n")

            threading.Thread(target=delayed_crash).start()

        return pb2.PrepareResponse(
            vote=can_commit,
            message=message,
            current_balance=current_balance
        )

    def Commit(self, request, context):
        """
        Handle Phase 2 (Commit/Abort) from coordinator.
        Apply or rollback the prepared transaction.
        """
        txn_id = request.transaction_id
        self.logger.info(f"[TXN {txn_id}] Received {'COMMIT' if request.commit else 'ABORT'}")

        with self.lock:
            if txn_id not in self.pending_transactions:
                self.logger.warning(f"[TXN {txn_id}] No pending transaction found")
                return pb2.CommitResponse(
                    success=False,
                    message="No pending transaction",
                    new_balance=self.balance
                )

            txn = self.pending_transactions[txn_id]

            if request.commit:
                # Apply the prepared value
                old_balance = self.balance
                self.balance = txn["prepared_value"]

                # Persist to disk
                save_balance(self.data_dir, self.account, self.balance)

                # Replicate commit to followers
                if self.is_leader:
                    self._replicate_to_followers({
                        "type": "commit",
                        "txn_id": txn_id,
                        "new_balance": self.balance
                    })

                self.logger.info(f"[TXN {txn_id}] COMMITTED: ${old_balance} -> ${self.balance}")
                message = f"Committed: {txn['operation']} ${txn['amount']}"
            else:
                # Abort - keep original value
                self.logger.info(f"[TXN {txn_id}] ABORTED: Balance remains ${self.balance}")
                message = "Aborted"

            # Clean up pending transaction
            del self.pending_transactions[txn_id]

            save_transaction_log(self.data_dir, self.node_id, txn_id,
                               "COMMITTED" if request.commit else "ABORTED",
                               {"balance": self.balance})

        return pb2.CommitResponse(
            success=True,
            message=message,
            new_balance=self.balance
        )

    def GetBalance(self, request, context):
        """Get current balance."""
        with self.lock:
            return pb2.GetBalanceResponse(balance=self.balance, success=True)

    def SetBalance(self, request, context):
        """Set balance (for scenario setup)."""
        with self.lock:
            self.balance = request.balance
            save_balance(self.data_dir, self.account, self.balance)
            self.logger.info(f"Balance set to ${self.balance}")

            # Replicate to followers
            if self.is_leader:
                self._replicate_to_followers({
                    "type": "set_balance",
                    "balance": self.balance
                })

        return pb2.SetBalanceResponse(success=True)

    def SetCrashMode(self, request, context):
        """Set crash simulation mode."""
        self.crash_mode = request.mode
        self.logger.info(f"Crash mode set to: {self.crash_mode}")
        return pb2.CrashModeResponse(success=True)


class RaftServicer(pb2_grpc.RaftServiceServicer):
    """Raft consensus service for replication."""

    def __init__(self, participant: ParticipantServicer):
        self.participant = participant

    def AppendEntries(self, request, context):
        """Handle AppendEntries RPC from leader."""
        self.participant.logger.info(f"[RAFT] Received AppendEntries from {request.leader_id}")

        with self.participant.lock:
            # Update term if needed
            if request.term > self.participant.current_term:
                self.participant.current_term = request.term
                self.participant.is_leader = False

            # Apply entries
            for entry in request.entries:
                command = json.loads(entry.command)
                if command["type"] == "set_balance":
                    self.participant.balance = command["balance"]
                    save_balance(self.participant.data_dir, self.participant.account,
                               self.participant.balance)
                elif command["type"] == "commit":
                    self.participant.balance = command["new_balance"]
                    save_balance(self.participant.data_dir, self.participant.account,
                               self.participant.balance)

        return pb2.AppendEntriesResponse(
            term=self.participant.current_term,
            success=True,
            match_index=len(self.participant.log)
        )

    def RequestVote(self, request, context):
        """Handle RequestVote RPC."""
        self.participant.logger.info(f"[RAFT] Received RequestVote from {request.candidate_id}")

        with self.participant.lock:
            vote_granted = False
            if request.term > self.participant.current_term:
                self.participant.current_term = request.term
                self.participant.voted_for = None

            if (self.participant.voted_for is None or
                self.participant.voted_for == request.candidate_id):
                vote_granted = True
                self.participant.voted_for = request.candidate_id

        return pb2.RequestVoteResponse(
            term=self.participant.current_term,
            vote_granted=vote_granted
        )


def serve(config_path: str, node_id: str, account: str, is_leader: bool = False):
    """Start the participant server."""
    config = load_config(config_path)

    # Find cluster config for this account
    if account == "A":
        cluster_config = config["participant_a"]
    else:
        cluster_config = config["participant_b"]

    # Find this node's config
    node_config = None
    for node in cluster_config["nodes"]:
        if node["id"] == node_id:
            node_config = node
            break

    if not node_config:
        print(f"Error: Node {node_id} not found in config")
        return

    # Create participant servicer
    participant = ParticipantServicer(config, node_id, account, cluster_config)
    participant.is_leader = is_leader

    # Start gRPC server
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))

    # Add participant service
    pb2_grpc.add_ParticipantServiceServicer_to_server(participant, server)

    # Add Raft service
    raft_servicer = RaftServicer(participant)
    pb2_grpc.add_RaftServiceServicer_to_server(raft_servicer, server)

    # Bind to ports
    participant_addr = f"0.0.0.0:{node_config['port']}"
    raft_addr = f"0.0.0.0:{node_config['raft_port']}"

    server.add_insecure_port(participant_addr)
    server.add_insecure_port(raft_addr)

    server.start()

    role = "LEADER" if is_leader else "FOLLOWER"
    print(f"\n{'='*60}")
    print(f"PARTICIPANT {node_id} ({role}) - Account {account}")
    print(f"  2PC Port: {participant_addr}")
    print(f"  Raft Port: {raft_addr}")
    print(f"  Initial Balance: ${participant.balance}")
    print(f"{'='*60}\n")

    server.wait_for_termination()


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python participant.py <config_file> <node_id> <account> [is_leader]")
        print("Example: python participant.py config.json node2 A true")
        sys.exit(1)

    config_file = sys.argv[1]
    node_id = sys.argv[2]
    account = sys.argv[3]
    is_leader = len(sys.argv) > 4 and sys.argv[4].lower() == "true"

    serve(config_file, node_id, account, is_leader)
