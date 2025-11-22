"""
Coordinator Node (Node-1) - Manages 2PC Protocol
CISC 5597/6935 Distributed Systems - Lab 3
"""
import grpc
import sys
import os
import time
import threading
from concurrent import futures

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from proto import two_phase_commit_pb2 as pb2
from proto import two_phase_commit_pb2_grpc as pb2_grpc
from common.utils import (
    setup_logging, load_config, generate_transaction_id,
    save_transaction_log, print_message_exchange
)

class CoordinatorServicer(pb2_grpc.CoordinatorServiceServicer):
    """
    Coordinator implements the 2PC protocol to coordinate distributed transactions
    between participants (Node-2 managing Account A, Node-3 managing Account B).
    """

    def __init__(self, config: dict, node_id: str = "coordinator"):
        self.config = config
        self.node_id = node_id
        self.logger = setup_logging(node_id)
        self.crash_mode = "none"  # For c.iii scenario
        self.data_dir = os.path.join(os.path.dirname(__file__), "../../data")

        # Get participant addresses (leaders of each cluster)
        participant_a = config["participant_a"]["nodes"][config["participant_a"]["leader_index"]]
        participant_b = config["participant_b"]["nodes"][config["participant_b"]["leader_index"]]

        self.participant_a_addr = f"{participant_a['ip']}:{participant_a['port']}"
        self.participant_b_addr = f"{participant_b['ip']}:{participant_b['port']}"

        self.logger.info(f"Coordinator initialized")
        self.logger.info(f"Participant A (Account A): {self.participant_a_addr}")
        self.logger.info(f"Participant B (Account B): {self.participant_b_addr}")

    def _get_participant_stub(self, address: str):
        """Create gRPC stub for participant."""
        channel = grpc.insecure_channel(address)
        return pb2_grpc.ParticipantServiceStub(channel)

    def _execute_transfer(self, txn_id: str) -> pb2.TransactionResponse:
        """
        Execute Transaction 1: Transfer 100 dollars from Account A to Account B.
        Uses 2PC protocol to ensure atomicity.
        """
        self.logger.info(f"[TXN {txn_id}] Starting TRANSFER transaction: A -> B ($100)")
        print(f"\n{'#'*70}")
        print(f"# TRANSACTION: Transfer $100 from Account A to Account B")
        print(f"# Transaction ID: {txn_id}")
        print(f"{'#'*70}\n")

        # Phase 1: PREPARE
        self.logger.info(f"[TXN {txn_id}] === PHASE 1: PREPARE ===")
        print("\n>>> PHASE 1: PREPARE (Voting Phase) <<<\n")

        stub_a = self._get_participant_stub(self.participant_a_addr)
        stub_b = self._get_participant_stub(self.participant_b_addr)

        # Prepare request for A: withdraw 100
        prepare_a = pb2.PrepareRequest(
            transaction_id=txn_id,
            type=pb2.TRANSFER,
            amount=100,
            operation="withdraw"
        )

        # Prepare request for B: deposit 100
        prepare_b = pb2.PrepareRequest(
            transaction_id=txn_id,
            type=pb2.TRANSFER,
            amount=100,
            operation="deposit"
        )

        vote_a = False
        vote_b = False
        balance_a = 0
        balance_b = 0

        # Check for coordinator crash scenario (c.iii)
        if self.crash_mode == "coordinator_crash":
            self.logger.info(f"[TXN {txn_id}] COORDINATOR CRASH: Simulating crash after sending prepare requests...")
            print("\n!!! COORDINATOR CRASH: Simulating crash (long sleep) after sending prepare !!!\n")

        # Send prepare to Participant A
        print_message_exchange("Coordinator", "Participant A (Node-2)", "PREPARE",
                              f"CanCommit? Withdraw $100 from A")
        try:
            timeout = self.config["timeouts"]["prepare_timeout"]
            response_a = stub_a.Prepare(prepare_a, timeout=timeout)
            vote_a = response_a.vote
            balance_a = response_a.current_balance
            print_message_exchange("Participant A (Node-2)", "Coordinator", "VOTE",
                                  f"{'VoteCommit' if vote_a else 'VoteAbort'} - {response_a.message} (Balance: ${balance_a})")
            self.logger.info(f"[TXN {txn_id}] Participant A vote: {vote_a}, balance: {balance_a}")
        except grpc.RpcError as e:
            self.logger.error(f"[TXN {txn_id}] Participant A prepare failed: {e}")
            print(f"!!! ERROR: Participant A failed to respond (timeout or crash) !!!")
            vote_a = False

        # Send prepare to Participant B
        print_message_exchange("Coordinator", "Participant B (Node-3)", "PREPARE",
                              f"CanCommit? Deposit $100 to B")
        try:
            timeout = self.config["timeouts"]["prepare_timeout"]
            response_b = stub_b.Prepare(prepare_b, timeout=timeout)
            vote_b = response_b.vote
            balance_b = response_b.current_balance
            print_message_exchange("Participant B (Node-3)", "Coordinator", "VOTE",
                                  f"{'VoteCommit' if vote_b else 'VoteAbort'} - {response_b.message} (Balance: ${balance_b})")
            self.logger.info(f"[TXN {txn_id}] Participant B vote: {vote_b}, balance: {balance_b}")
        except grpc.RpcError as e:
            self.logger.error(f"[TXN {txn_id}] Participant B prepare failed: {e}")
            print(f"!!! ERROR: Participant B failed to respond (timeout or crash) !!!")
            vote_b = False

        # Coordinator crash after collecting votes
        if self.crash_mode == "coordinator_crash":
            crash_time = self.config["timeouts"]["crash_sleep_time"]
            self.logger.info(f"[TXN {txn_id}] Coordinator sleeping for {crash_time}s to simulate crash...")
            print(f"\n!!! COORDINATOR SLEEPING FOR {crash_time}s !!!")
            print("!!! Participants are now UNCERTAIN about transaction outcome !!!")
            print("!!! In a real system, participants would wait or use termination protocol !!!\n")
            time.sleep(crash_time)
            self.logger.info(f"[TXN {txn_id}] Coordinator recovered from crash")
            print("!!! COORDINATOR RECOVERED - Proceeding with abort for safety !!!\n")
            vote_a = False  # Conservative: abort after recovery

        # Phase 2: COMMIT/ABORT
        self.logger.info(f"[TXN {txn_id}] === PHASE 2: COMMIT/ABORT ===")
        print("\n>>> PHASE 2: COMMIT/ABORT (Decision Phase) <<<\n")

        # Determine decision
        commit = vote_a and vote_b
        decision = "COMMIT" if commit else "ABORT"
        self.logger.info(f"[TXN {txn_id}] Decision: {decision} (vote_a={vote_a}, vote_b={vote_b})")
        print(f"COORDINATOR DECISION: {decision}")
        print(f"  Reason: {'All participants voted commit' if commit else 'At least one participant voted abort or failed'}\n")

        # Save decision to log for durability
        save_transaction_log(self.data_dir, self.node_id, txn_id, decision,
                           {"vote_a": vote_a, "vote_b": vote_b})

        # Send commit/abort to participants
        commit_req = pb2.CommitRequest(transaction_id=txn_id, commit=commit)

        final_balance_a = balance_a
        final_balance_b = balance_b

        # Send to Participant A
        print_message_exchange("Coordinator", "Participant A (Node-2)", "DO" + decision,
                              f"{decision} transaction")
        try:
            response = stub_a.Commit(commit_req, timeout=self.config["timeouts"]["commit_timeout"])
            final_balance_a = response.new_balance
            print_message_exchange("Participant A (Node-2)", "Coordinator", "ACK",
                                  f"Acknowledged - New Balance: ${final_balance_a}")
        except grpc.RpcError as e:
            self.logger.error(f"[TXN {txn_id}] Participant A commit failed: {e}")

        # Send to Participant B
        print_message_exchange("Coordinator", "Participant B (Node-3)", "DO" + decision,
                              f"{decision} transaction")
        try:
            response = stub_b.Commit(commit_req, timeout=self.config["timeouts"]["commit_timeout"])
            final_balance_b = response.new_balance
            print_message_exchange("Participant B (Node-3)", "Coordinator", "ACK",
                                  f"Acknowledged - New Balance: ${final_balance_b}")
        except grpc.RpcError as e:
            self.logger.error(f"[TXN {txn_id}] Participant B commit failed: {e}")

        # Final result
        print(f"\n{'='*70}")
        print(f"TRANSACTION {decision}ED")
        print(f"  Final Balance A: ${final_balance_a}")
        print(f"  Final Balance B: ${final_balance_b}")
        print(f"{'='*70}\n")

        return pb2.TransactionResponse(
            success=commit,
            message=f"Transaction {decision}",
            balance_a=final_balance_a,
            balance_b=final_balance_b
        )

    def _execute_bonus(self, txn_id: str) -> pb2.TransactionResponse:
        """
        Execute Transaction 2: Add 20% bonus to A and add same amount (0.2 * A) to B.
        """
        self.logger.info(f"[TXN {txn_id}] Starting BONUS transaction")
        print(f"\n{'#'*70}")
        print(f"# TRANSACTION: Add 20% bonus to A, and add same amount to B")
        print(f"# Transaction ID: {txn_id}")
        print(f"{'#'*70}\n")

        stub_a = self._get_participant_stub(self.participant_a_addr)
        stub_b = self._get_participant_stub(self.participant_b_addr)

        # First, read current balance of A
        print("\n>>> STEP 0: Reading current balance of A <<<\n")
        try:
            balance_response = stub_a.GetBalance(
                pb2.GetBalanceRequest(transaction_id=txn_id),
                timeout=self.config["timeouts"]["prepare_timeout"]
            )
            current_a = balance_response.balance
            self.logger.info(f"[TXN {txn_id}] Current balance A: {current_a}")
            print(f"Current balance of A: ${current_a}")
        except grpc.RpcError as e:
            self.logger.error(f"[TXN {txn_id}] Failed to read balance A: {e}")
            return pb2.TransactionResponse(success=False, message="Failed to read balance A")

        bonus_amount = current_a * 0.2
        print(f"Bonus amount (20% of A): ${bonus_amount}")

        # Phase 1: PREPARE
        self.logger.info(f"[TXN {txn_id}] === PHASE 1: PREPARE ===")
        print("\n>>> PHASE 1: PREPARE (Voting Phase) <<<\n")

        prepare_a = pb2.PrepareRequest(
            transaction_id=txn_id,
            type=pb2.BONUS,
            amount=bonus_amount,
            operation="deposit",
            bonus_base=current_a
        )

        prepare_b = pb2.PrepareRequest(
            transaction_id=txn_id,
            type=pb2.BONUS,
            amount=bonus_amount,
            operation="deposit",
            bonus_base=current_a
        )

        vote_a = False
        vote_b = False
        balance_a = current_a
        balance_b = 0

        # Coordinator crash check
        if self.crash_mode == "coordinator_crash":
            self.logger.info(f"[TXN {txn_id}] COORDINATOR CRASH simulation")
            print("\n!!! COORDINATOR CRASH: Simulating crash !!!\n")

        # Send prepare to A
        print_message_exchange("Coordinator", "Participant A (Node-2)", "PREPARE",
                              f"CanCommit? Add bonus ${bonus_amount} to A")
        try:
            response_a = stub_a.Prepare(prepare_a, timeout=self.config["timeouts"]["prepare_timeout"])
            vote_a = response_a.vote
            balance_a = response_a.current_balance
            print_message_exchange("Participant A", "Coordinator", "VOTE",
                                  f"{'VoteCommit' if vote_a else 'VoteAbort'} - {response_a.message}")
        except grpc.RpcError as e:
            self.logger.error(f"[TXN {txn_id}] Participant A prepare failed: {e}")
            print(f"!!! ERROR: Participant A failed !!!")

        # Send prepare to B
        print_message_exchange("Coordinator", "Participant B (Node-3)", "PREPARE",
                              f"CanCommit? Add ${bonus_amount} to B")
        try:
            response_b = stub_b.Prepare(prepare_b, timeout=self.config["timeouts"]["prepare_timeout"])
            vote_b = response_b.vote
            balance_b = response_b.current_balance
            print_message_exchange("Participant B", "Coordinator", "VOTE",
                                  f"{'VoteCommit' if vote_b else 'VoteAbort'} - {response_b.message}")
        except grpc.RpcError as e:
            self.logger.error(f"[TXN {txn_id}] Participant B prepare failed: {e}")
            print(f"!!! ERROR: Participant B failed !!!")

        if self.crash_mode == "coordinator_crash":
            crash_time = self.config["timeouts"]["crash_sleep_time"]
            print(f"\n!!! COORDINATOR SLEEPING FOR {crash_time}s !!!\n")
            time.sleep(crash_time)
            print("!!! COORDINATOR RECOVERED !!!\n")
            vote_a = False

        # Phase 2
        print("\n>>> PHASE 2: COMMIT/ABORT <<<\n")
        commit = vote_a and vote_b
        decision = "COMMIT" if commit else "ABORT"
        print(f"COORDINATOR DECISION: {decision}\n")

        save_transaction_log(self.data_dir, self.node_id, txn_id, decision, {})

        commit_req = pb2.CommitRequest(transaction_id=txn_id, commit=commit)

        final_a = balance_a
        final_b = balance_b

        print_message_exchange("Coordinator", "Participant A", "DO" + decision, f"{decision}")
        try:
            resp = stub_a.Commit(commit_req, timeout=self.config["timeouts"]["commit_timeout"])
            final_a = resp.new_balance
            print_message_exchange("Participant A", "Coordinator", "ACK", f"Balance: ${final_a}")
        except:
            pass

        print_message_exchange("Coordinator", "Participant B", "DO" + decision, f"{decision}")
        try:
            resp = stub_b.Commit(commit_req, timeout=self.config["timeouts"]["commit_timeout"])
            final_b = resp.new_balance
            print_message_exchange("Participant B", "Coordinator", "ACK", f"Balance: ${final_b}")
        except:
            pass

        print(f"\n{'='*70}")
        print(f"TRANSACTION {decision}ED - A: ${final_a}, B: ${final_b}")
        print(f"{'='*70}\n")

        return pb2.TransactionResponse(
            success=commit,
            message=f"Transaction {decision}",
            balance_a=final_a,
            balance_b=final_b
        )

    def ExecuteTransaction(self, request, context):
        """Handle transaction request from client."""
        txn_id = request.transaction_id or generate_transaction_id()
        self.logger.info(f"Received transaction request: {request.type}, ID: {txn_id}")

        if request.type == pb2.TRANSFER:
            return self._execute_transfer(txn_id)
        elif request.type == pb2.BONUS:
            return self._execute_bonus(txn_id)
        else:
            return pb2.TransactionResponse(success=False, message="Unknown transaction type")

    def GetBalances(self, request, context):
        """Get current balances from both participants."""
        stub_a = self._get_participant_stub(self.participant_a_addr)
        stub_b = self._get_participant_stub(self.participant_b_addr)

        try:
            bal_a = stub_a.GetBalance(pb2.GetBalanceRequest(), timeout=5).balance
            bal_b = stub_b.GetBalance(pb2.GetBalanceRequest(), timeout=5).balance
            return pb2.BalanceResponse(balance_a=bal_a, balance_b=bal_b)
        except grpc.RpcError as e:
            self.logger.error(f"Failed to get balances: {e}")
            return pb2.BalanceResponse(balance_a=-1, balance_b=-1)

    def SetScenario(self, request, context):
        """Set up scenario with initial values and crash mode."""
        self.logger.info(f"Setting scenario: {request.scenario}, A={request.initial_a}, B={request.initial_b}")

        stub_a = self._get_participant_stub(self.participant_a_addr)
        stub_b = self._get_participant_stub(self.participant_b_addr)

        # Set crash mode on coordinator
        if request.scenario == "coordinator_crash":
            self.crash_mode = "coordinator_crash"
        else:
            self.crash_mode = "none"

        # Set crash mode on participants
        crash_mode_a = "none"
        crash_mode_b = "none"
        if request.scenario == "crash_before":
            crash_mode_a = "before_response"
        elif request.scenario == "crash_after":
            crash_mode_a = "after_response"

        try:
            stub_a.SetBalance(pb2.SetBalanceRequest(balance=request.initial_a), timeout=5)
            stub_a.SetCrashMode(pb2.CrashModeRequest(mode=crash_mode_a), timeout=5)
            stub_b.SetBalance(pb2.SetBalanceRequest(balance=request.initial_b), timeout=5)
            stub_b.SetCrashMode(pb2.CrashModeRequest(mode=crash_mode_b), timeout=5)

            print(f"\n{'='*50}")
            print(f"SCENARIO SET: {request.scenario}")
            print(f"  Initial A: ${request.initial_a}")
            print(f"  Initial B: ${request.initial_b}")
            print(f"{'='*50}\n")

            return pb2.ScenarioResponse(success=True, message="Scenario set successfully")
        except grpc.RpcError as e:
            return pb2.ScenarioResponse(success=False, message=str(e))


def serve(config_path: str = "config.json"):
    """Start the coordinator server."""
    config = load_config(config_path)
    coord_config = config["coordinator"]

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    servicer = CoordinatorServicer(config)
    pb2_grpc.add_CoordinatorServiceServicer_to_server(servicer, server)

    address = f"0.0.0.0:{coord_config['port']}"
    server.add_insecure_port(address)
    server.start()

    print(f"\n{'='*60}")
    print(f"COORDINATOR (Node-1) started on {address}")
    print(f"Waiting for transaction requests...")
    print(f"{'='*60}\n")

    server.wait_for_termination()


if __name__ == "__main__":
    config_file = sys.argv[1] if len(sys.argv) > 1 else "config.json"
    serve(config_file)
