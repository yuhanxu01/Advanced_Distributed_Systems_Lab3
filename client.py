"""
Client for 2PC System
Sends transaction requests to the coordinator
"""

import sys
from xmlrpc.client import ServerProxy
import config


class Client:
    """
    Client that sends transaction requests to coordinator
    """

    def __init__(self, coordinator_host, coordinator_port):
        """
        Initialize client

        Args:
            coordinator_host: Coordinator host address
            coordinator_port: Coordinator port
        """
        self.coordinator_url = f"http://{coordinator_host}:{coordinator_port}"
        self.coordinator = ServerProxy(self.coordinator_url, allow_none=True)
        print(f"Connected to coordinator at {self.coordinator_url}")

    def get_balances(self):
        """Get current account balances"""
        try:
            balances = self.coordinator.get_account_balances()
            print("\n=== Current Account Balances ===")
            for account, balance in balances.items():
                print(f"  Account {account}: ${balance}")
            print()
            return balances
        except Exception as e:
            print(f"Error getting balances: {e}")
            return None

    def execute_transfer(self, amount):
        """
        Execute transfer transaction

        Args:
            amount: Amount to transfer from A to B
        """
        print(f"\n=== Executing TRANSFER Transaction ===")
        print(f"  Transfer ${amount} from Account A to Account B")

        try:
            result = self.coordinator.execute_transaction('transfer', {'amount': amount})
            self._print_result(result)
            return result
        except Exception as e:
            print(f"Error executing transfer: {e}")
            return None

    def execute_bonus(self):
        """Execute bonus transaction (20% bonus to A and same amount to B)"""
        print(f"\n=== Executing BONUS Transaction ===")
        print(f"  Add 20% bonus to Account A and same amount to Account B")

        try:
            result = self.coordinator.execute_transaction('bonus', {})
            self._print_result(result)
            return result
        except Exception as e:
            print(f"Error executing bonus: {e}")
            return None

    def _print_result(self, result):
        """Print transaction result"""
        print(f"\nTransaction Result:")
        print(f"  Status: {result['status']}")
        print(f"  Transaction ID: {result['transaction_id']}")

        if 'prepare_votes' in result:
            print(f"  Prepare Votes:")
            for participant, vote in result['prepare_votes'].items():
                print(f"    {participant}: {vote}")

        if 'commit_results' in result:
            print(f"  Commit Results:")
            for participant, res in result['commit_results'].items():
                print(f"    {participant}: {res}")

        if 'abort_results' in result:
            print(f"  Abort Results:")
            for participant, res in result['abort_results'].items():
                print(f"    {participant}: {res}")

        if 'reason' in result:
            print(f"  Reason: {result['reason']}")

    def set_crash(self, participant, before=False, after=False):
        """Set crash simulation for a participant"""
        try:
            self.coordinator.set_participant_crash(participant, before, after)
            if before:
                print(f"Set {participant} to crash BEFORE prepare response")
            if after:
                print(f"Set {participant} to crash AFTER prepare response")
        except Exception as e:
            print(f"Error setting crash: {e}")

    def reset_crash(self, participant):
        """Reset crash simulation for a participant"""
        try:
            self.coordinator.reset_participant_crash(participant)
            print(f"Reset crash flags for {participant}")
        except Exception as e:
            print(f"Error resetting crash: {e}")


def print_menu():
    """Print interactive menu"""
    print("\n" + "=" * 50)
    print("2PC Transaction System - Client Menu")
    print("=" * 50)
    print("1. Get Account Balances")
    print("2. Execute Transfer Transaction (A -> B)")
    print("3. Execute Bonus Transaction (20% bonus)")
    print("4. Set Crash Simulation")
    print("5. Reset Crash Simulation")
    print("0. Exit")
    print("=" * 50)


def main():
    """Main interactive client"""
    client = Client(config.COORDINATOR_HOST, config.COORDINATOR_PORT)

    while True:
        print_menu()
        choice = input("Enter your choice: ").strip()

        if choice == '0':
            print("Exiting...")
            break

        elif choice == '1':
            client.get_balances()

        elif choice == '2':
            try:
                amount = float(input("Enter transfer amount: "))
                client.get_balances()
                client.execute_transfer(amount)
                client.get_balances()
            except ValueError:
                print("Invalid amount")

        elif choice == '3':
            client.get_balances()
            client.execute_bonus()
            client.get_balances()

        elif choice == '4':
            participant = input("Enter participant (A or B): ").strip().upper()
            when = input("Crash before or after prepare? (before/after): ").strip().lower()

            if when == 'before':
                client.set_crash(participant, before=True)
            elif when == 'after':
                client.set_crash(participant, after=True)
            else:
                print("Invalid choice")

        elif choice == '5':
            participant = input("Enter participant (A or B): ").strip().upper()
            client.reset_crash(participant)

        else:
            print("Invalid choice")


if __name__ == '__main__':
    main()
