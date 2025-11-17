"""
Script to run all test scenarios for Lab 3
Automates testing of different 2PC scenarios
"""

import time
from xmlrpc.client import ServerProxy
import config


class ScenarioRunner:
    """Runner for automated test scenarios"""

    def __init__(self):
        """Initialize scenario runner"""
        self.coordinator_url = f"http://{config.COORDINATOR_HOST}:{config.COORDINATOR_PORT}"
        self.coordinator = ServerProxy(self.coordinator_url, allow_none=True)
        print(f"Connected to coordinator at {self.coordinator_url}")

    def set_initial_balances(self, a_balance, b_balance):
        """Set initial account balances"""
        print(f"\n{'='*60}")
        print(f"Setting initial balances: A=${a_balance}, B=${b_balance}")
        print('='*60)

        # Write directly to account files
        with open('account_A.txt', 'w') as f:
            f.write(str(a_balance))
        with open('account_B.txt', 'w') as f:
            f.write(str(b_balance))

        time.sleep(1)
        self.print_balances()

    def print_balances(self):
        """Print current account balances"""
        balances = self.coordinator.get_account_balances()
        print(f"\nCurrent Balances: A=${balances['A']}, B=${balances['B']}")
        return balances

    def execute_transfer(self, amount):
        """Execute transfer transaction"""
        print(f"\n{'*'*60}")
        print(f"TRANSACTION: Transfer ${amount} from A to B")
        print('*'*60)

        result = self.coordinator.execute_transaction('transfer', {'amount': amount})
        self.print_result(result)
        return result

    def execute_bonus(self):
        """Execute bonus transaction"""
        print(f"\n{'*'*60}")
        print(f"TRANSACTION: Add 20% bonus to A and same amount to B")
        print('*'*60)

        result = self.coordinator.execute_transaction('bonus', {})
        self.print_result(result)
        return result

    def print_result(self, result):
        """Print transaction result"""
        print(f"\n--- Transaction Result ---")
        print(f"Status: {result['status']}")
        print(f"Transaction ID: {result['transaction_id']}")

        if 'prepare_votes' in result:
            print(f"Prepare Votes: {result['prepare_votes']}")

        if result['status'] == 'COMMITTED':
            print(f"Commit Results: {result['commit_results']}")
        elif result['status'] == 'ABORTED':
            print(f"Reason: {result.get('reason', 'Unknown')}")
            if 'abort_results' in result:
                print(f"Abort Results: {result['abort_results']}")

        self.print_balances()

    def scenario_1a(self):
        """
        Scenario 1.a: A=200, B=300, normal operation
        Execute both transactions
        """
        print("\n" + "="*60)
        print("SCENARIO 1.a: A=200, B=300 - Normal Operation")
        print("="*60)

        self.set_initial_balances(200, 300)

        # Transaction 1: Transfer 100 from A to B
        print("\n--- Test Transaction 1: Transfer ---")
        self.execute_transfer(100)

        time.sleep(2)

        # Reset balances
        self.set_initial_balances(200, 300)

        # Transaction 2: Bonus
        print("\n--- Test Transaction 2: Bonus ---")
        self.execute_bonus()

        print("\n" + "="*60)
        print("SCENARIO 1.a COMPLETED")
        print("="*60)

    def scenario_1b(self):
        """
        Scenario 1.b: A=90, B=50, normal operation
        Transfer should fail (insufficient funds)
        """
        print("\n" + "="*60)
        print("SCENARIO 1.b: A=90, B=50 - Normal Operation")
        print("="*60)

        self.set_initial_balances(90, 50)

        # Transaction 1: Transfer 100 from A to B (should fail)
        print("\n--- Test Transaction 1: Transfer (Expected to ABORT) ---")
        self.execute_transfer(100)

        time.sleep(2)

        # Reset balances
        self.set_initial_balances(90, 50)

        # Transaction 2: Bonus (should succeed)
        print("\n--- Test Transaction 2: Bonus (Expected to COMMIT) ---")
        self.execute_bonus()

        print("\n" + "="*60)
        print("SCENARIO 1.b COMPLETED")
        print("="*60)

    def scenario_1c_i(self):
        """
        Scenario 1.c.i: Node-2 crashes BEFORE responding to coordinator
        """
        print("\n" + "="*60)
        print("SCENARIO 1.c.i: Node-2 Crash BEFORE Prepare Response")
        print("="*60)

        self.set_initial_balances(200, 300)

        # Set crash flag for participant A (Node-2)
        print("\nSetting Node-2 (Account A) to crash BEFORE prepare response...")
        self.coordinator.set_participant_crash('A', crash_before=True, crash_after=False)

        time.sleep(1)

        # Try transfer transaction (should timeout and abort)
        print("\n--- Test Transaction: Transfer (Expected to TIMEOUT and ABORT) ---")
        print("Note: This will take ~15 seconds due to timeout...")
        self.execute_transfer(100)

        # Reset crash flag
        print("\nResetting crash flags...")
        self.coordinator.reset_participant_crash('A')

        print("\n" + "="*60)
        print("SCENARIO 1.c.i COMPLETED")
        print("="*60)

    def scenario_1c_ii(self):
        """
        Scenario 1.c.ii: Node-2 crashes AFTER responding to coordinator
        """
        print("\n" + "="*60)
        print("SCENARIO 1.c.ii: Node-2 Crash AFTER Prepare Response")
        print("="*60)

        self.set_initial_balances(200, 300)

        # Set crash flag for participant A (Node-2)
        print("\nSetting Node-2 (Account A) to crash AFTER prepare response...")
        self.coordinator.set_participant_crash('A', crash_before=False, crash_after=True)

        time.sleep(1)

        # Try transfer transaction
        print("\n--- Test Transaction: Transfer ---")
        print("Note: Node-2 will sleep after responding, but transaction should complete...")
        self.execute_transfer(100)

        # Reset crash flag
        print("\nResetting crash flags...")
        self.coordinator.reset_participant_crash('A')

        # Wait for participant to recover from sleep
        print("\nWaiting 35 seconds for participant to recover...")
        time.sleep(35)

        print("\n" + "="*60)
        print("SCENARIO 1.c.ii COMPLETED")
        print("="*60)

    def run_all_scenarios(self):
        """Run all test scenarios"""
        print("\n" + "#"*60)
        print("# Running All Test Scenarios for Lab 3")
        print("#"*60)

        try:
            input("\nPress Enter to start Scenario 1.a...")
            self.scenario_1a()

            input("\nPress Enter to start Scenario 1.b...")
            self.scenario_1b()

            input("\nPress Enter to start Scenario 1.c.i...")
            self.scenario_1c_i()

            input("\nPress Enter to start Scenario 1.c.ii...")
            self.scenario_1c_ii()

            print("\n" + "#"*60)
            print("# All Scenarios Completed!")
            print("#"*60)

        except KeyboardInterrupt:
            print("\n\nScenario testing interrupted by user.")
        except Exception as e:
            print(f"\n\nError during scenario testing: {e}")


def main():
    """Main entry point"""
    print("2PC Lab 3 - Scenario Runner")
    print("Make sure coordinator and participants are running!")

    runner = ScenarioRunner()

    print("\n" + "="*60)
    print("Choose an option:")
    print("="*60)
    print("1. Run all scenarios (interactive)")
    print("2. Run Scenario 1.a only")
    print("3. Run Scenario 1.b only")
    print("4. Run Scenario 1.c.i only")
    print("5. Run Scenario 1.c.ii only")
    print("0. Exit")
    print("="*60)

    choice = input("Enter choice: ").strip()

    if choice == '1':
        runner.run_all_scenarios()
    elif choice == '2':
        runner.scenario_1a()
    elif choice == '3':
        runner.scenario_1b()
    elif choice == '4':
        runner.scenario_1c_i()
    elif choice == '5':
        runner.scenario_1c_ii()
    elif choice == '0':
        print("Exiting...")
    else:
        print("Invalid choice")


if __name__ == '__main__':
    main()
