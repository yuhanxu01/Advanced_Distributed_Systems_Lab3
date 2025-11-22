"""
Client - Sends transaction requests to the Coordinator
CISC 5597/6935 Distributed Systems - Lab 3
"""
import grpc
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from proto import two_phase_commit_pb2 as pb2
from proto import two_phase_commit_pb2_grpc as pb2_grpc
from common.utils import load_config, generate_transaction_id


class TwoPhaseCommitClient:
    """Client for interacting with the 2PC system."""

    def __init__(self, config_path: str = "config.json"):
        self.config = load_config(config_path)
        coord = self.config["coordinator"]
        self.coordinator_addr = f"{coord['ip']}:{coord['port']}"
        self.channel = grpc.insecure_channel(self.coordinator_addr)
        self.stub = pb2_grpc.CoordinatorServiceStub(self.channel)
        print(f"Client connected to Coordinator at {self.coordinator_addr}")

    def set_scenario(self, scenario: str, initial_a: float, initial_b: float):
        """Set up a test scenario with initial values."""
        request = pb2.ScenarioRequest(
            scenario=scenario,
            initial_a=initial_a,
            initial_b=initial_b
        )
        try:
            response = self.stub.SetScenario(request, timeout=10)
            return response.success
        except grpc.RpcError as e:
            print(f"Failed to set scenario: {e}")
            return False

    def get_balances(self):
        """Get current balances."""
        try:
            response = self.stub.GetBalances(pb2.BalanceRequest(), timeout=10)
            return response.balance_a, response.balance_b
        except grpc.RpcError as e:
            print(f"Failed to get balances: {e}")
            return None, None

    def execute_transfer(self):
        """Execute Transaction 1: Transfer 100 from A to B."""
        request = pb2.TransactionRequest(
            transaction_id=generate_transaction_id(),
            type=pb2.TRANSFER
        )
        try:
            response = self.stub.ExecuteTransaction(request, timeout=60)
            return response
        except grpc.RpcError as e:
            print(f"Transaction failed: {e}")
            return None

    def execute_bonus(self):
        """Execute Transaction 2: Add 20% bonus to A and same amount to B."""
        request = pb2.TransactionRequest(
            transaction_id=generate_transaction_id(),
            type=pb2.BONUS
        )
        try:
            response = self.stub.ExecuteTransaction(request, timeout=60)
            return response
        except grpc.RpcError as e:
            print(f"Transaction failed: {e}")
            return None


def run_scenario_a(client: TwoPhaseCommitClient):
    """
    Scenario 1.a: A=200, B=300, no failures
    Simulate all scenarios with both transaction orderings.
    """
    print("\n" + "="*80)
    print("SCENARIO 1.a: A=200, B=300, No Failures")
    print("="*80)

    # Test T1 then T2
    print("\n--- Test Case: T1 (Transfer) then T2 (Bonus) ---")
    client.set_scenario("normal", 200, 300)
    time.sleep(1)

    print("\n[T1] Executing TRANSFER: Move $100 from A to B")
    result = client.execute_transfer()
    if result:
        print(f"Result: {'SUCCESS' if result.success else 'FAILED'}")
        print(f"Balances: A=${result.balance_a}, B=${result.balance_b}")

    time.sleep(1)

    print("\n[T2] Executing BONUS: Add 20% to A, same amount to B")
    result = client.execute_bonus()
    if result:
        print(f"Result: {'SUCCESS' if result.success else 'FAILED'}")
        print(f"Balances: A=${result.balance_a}, B=${result.balance_b}")

    # Test T2 then T1
    print("\n--- Test Case: T2 (Bonus) then T1 (Transfer) ---")
    client.set_scenario("normal", 200, 300)
    time.sleep(1)

    print("\n[T2] Executing BONUS: Add 20% to A, same amount to B")
    result = client.execute_bonus()
    if result:
        print(f"Result: {'SUCCESS' if result.success else 'FAILED'}")
        print(f"Balances: A=${result.balance_a}, B=${result.balance_b}")

    time.sleep(1)

    print("\n[T1] Executing TRANSFER: Move $100 from A to B")
    result = client.execute_transfer()
    if result:
        print(f"Result: {'SUCCESS' if result.success else 'FAILED'}")
        print(f"Balances: A=${result.balance_a}, B=${result.balance_b}")


def run_scenario_b(client: TwoPhaseCommitClient):
    """
    Scenario 1.b: A=90, B=50, no failures
    Transfer should fail due to insufficient funds.
    """
    print("\n" + "="*80)
    print("SCENARIO 1.b: A=90, B=50, No Failures (Insufficient Funds)")
    print("="*80)

    # Test T1 then T2
    print("\n--- Test Case: T1 (Transfer) then T2 (Bonus) ---")
    client.set_scenario("normal", 90, 50)
    time.sleep(1)

    print("\n[T1] Executing TRANSFER: Move $100 from A to B")
    print("Expected: FAIL (A has only $90, cannot withdraw $100)")
    result = client.execute_transfer()
    if result:
        print(f"Result: {'SUCCESS' if result.success else 'FAILED'} - {result.message}")
        print(f"Balances: A=${result.balance_a}, B=${result.balance_b}")

    time.sleep(1)

    print("\n[T2] Executing BONUS: Add 20% to A (=$18), same amount to B")
    result = client.execute_bonus()
    if result:
        print(f"Result: {'SUCCESS' if result.success else 'FAILED'}")
        print(f"Balances: A=${result.balance_a}, B=${result.balance_b}")

    # Test T2 then T1
    print("\n--- Test Case: T2 (Bonus) then T1 (Transfer) ---")
    client.set_scenario("normal", 90, 50)
    time.sleep(1)

    print("\n[T2] Executing BONUS: Add 20% to A, same amount to B")
    result = client.execute_bonus()
    if result:
        print(f"Result: {'SUCCESS' if result.success else 'FAILED'}")
        print(f"Balances: A=${result.balance_a}, B=${result.balance_b}")

    time.sleep(1)

    print("\n[T1] Executing TRANSFER: Move $100 from A to B")
    print("Expected: SUCCESS (A now has $108 after bonus)")
    result = client.execute_transfer()
    if result:
        print(f"Result: {'SUCCESS' if result.success else 'FAILED'}")
        print(f"Balances: A=${result.balance_a}, B=${result.balance_b}")


def run_scenario_c_i(client: TwoPhaseCommitClient):
    """
    Scenario 1.c.i: Node-2 crashes BEFORE responding to coordinator.
    """
    print("\n" + "="*80)
    print("SCENARIO 1.c.i: Node-2 Crash BEFORE Responding")
    print("="*80)

    client.set_scenario("crash_before", 200, 300)
    time.sleep(1)

    print("\n[T1] Executing TRANSFER with Node-2 crash simulation...")
    print("Expected: Transaction ABORTED due to timeout")
    result = client.execute_transfer()
    if result:
        print(f"Result: {'SUCCESS' if result.success else 'FAILED'}")
        print(f"Balances: A=${result.balance_a}, B=${result.balance_b}")


def run_scenario_c_ii(client: TwoPhaseCommitClient):
    """
    Scenario 1.c.ii: Node-2 crashes AFTER responding to coordinator.
    """
    print("\n" + "="*80)
    print("SCENARIO 1.c.ii: Node-2 Crash AFTER Responding")
    print("="*80)

    client.set_scenario("crash_after", 200, 300)
    time.sleep(1)

    print("\n[T1] Executing TRANSFER with Node-2 crash after vote...")
    result = client.execute_transfer()
    if result:
        print(f"Result: {'SUCCESS' if result.success else 'FAILED'}")
        print(f"Balances: A=${result.balance_a}, B=${result.balance_b}")


def run_scenario_c_iii(client: TwoPhaseCommitClient):
    """
    Scenario 1.c.iii (6935-only): Coordinator crashes after sending request.
    """
    print("\n" + "="*80)
    print("SCENARIO 1.c.iii (6935): Coordinator Crash After Sending Request")
    print("="*80)

    client.set_scenario("coordinator_crash", 200, 300)
    time.sleep(1)

    print("\n[T1] Executing TRANSFER with Coordinator crash simulation...")
    print("Expected: Participants will be in UNCERTAIN state")
    result = client.execute_transfer()
    if result:
        print(f"Result: {'SUCCESS' if result.success else 'FAILED'}")
        print(f"Balances: A=${result.balance_a}, B=${result.balance_b}")


def interactive_mode(client: TwoPhaseCommitClient):
    """Interactive mode for manual testing."""
    while True:
        print("\n" + "="*50)
        print("2PC Client - Interactive Mode")
        print("="*50)
        print("1. Run Scenario 1.a (A=200, B=300, no failures)")
        print("2. Run Scenario 1.b (A=90, B=50, no failures)")
        print("3. Run Scenario 1.c.i (Node-2 crash before response)")
        print("4. Run Scenario 1.c.ii (Node-2 crash after response)")
        print("5. Run Scenario 1.c.iii (Coordinator crash - 6935)")
        print("6. Execute single TRANSFER transaction")
        print("7. Execute single BONUS transaction")
        print("8. Get current balances")
        print("9. Set custom initial values")
        print("0. Exit")
        print("="*50)

        choice = input("Enter choice: ").strip()

        if choice == "1":
            run_scenario_a(client)
        elif choice == "2":
            run_scenario_b(client)
        elif choice == "3":
            run_scenario_c_i(client)
        elif choice == "4":
            run_scenario_c_ii(client)
        elif choice == "5":
            run_scenario_c_iii(client)
        elif choice == "6":
            result = client.execute_transfer()
            if result:
                print(f"Result: {result.message}")
                print(f"Balances: A=${result.balance_a}, B=${result.balance_b}")
        elif choice == "7":
            result = client.execute_bonus()
            if result:
                print(f"Result: {result.message}")
                print(f"Balances: A=${result.balance_a}, B=${result.balance_b}")
        elif choice == "8":
            a, b = client.get_balances()
            print(f"Current Balances: A=${a}, B=${b}")
        elif choice == "9":
            a = float(input("Enter initial A: "))
            b = float(input("Enter initial B: "))
            client.set_scenario("normal", a, b)
        elif choice == "0":
            print("Goodbye!")
            break


def main():
    config_file = sys.argv[1] if len(sys.argv) > 1 else "config.json"
    client = TwoPhaseCommitClient(config_file)

    if len(sys.argv) > 2:
        scenario = sys.argv[2]
        if scenario == "a":
            run_scenario_a(client)
        elif scenario == "b":
            run_scenario_b(client)
        elif scenario == "c1":
            run_scenario_c_i(client)
        elif scenario == "c2":
            run_scenario_c_ii(client)
        elif scenario == "c3":
            run_scenario_c_iii(client)
        elif scenario == "all":
            run_scenario_a(client)
            time.sleep(2)
            run_scenario_b(client)
            time.sleep(2)
            run_scenario_c_i(client)
            time.sleep(2)
            run_scenario_c_ii(client)
            time.sleep(2)
            run_scenario_c_iii(client)
    else:
        interactive_mode(client)


if __name__ == "__main__":
    main()
