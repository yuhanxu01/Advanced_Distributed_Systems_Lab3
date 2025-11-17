"""
Participant Node for 2PC Protocol
Manages account data and participates in distributed transactions
"""

import os
import time
import logging
from xmlrpc.server import SimpleXMLRPCServer
from threading import Lock

class Participant:
    """
    Participant node that manages an account
    Implements prepare-commit protocol
    """

    def __init__(self, node_id, account_name, account_file, host, port):
        """
        Initialize participant node

        Args:
            node_id: Unique identifier for this node (e.g., 'Node-2')
            account_name: Name of the account managed (e.g., 'A')
            account_file: Path to file storing account balance
            host: Host address for RPC server
            port: Port for RPC server
        """
        self.node_id = node_id
        self.account_name = account_name
        self.account_file = account_file
        self.host = host
        self.port = port

        # Lock for thread-safe operations
        self.lock = Lock()

        # Transaction state
        self.prepared_value = None
        self.current_transaction = None

        # Failure simulation flags
        self.crash_before_prepare = False
        self.crash_after_prepare = False

        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format=f'[{self.node_id}] %(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(self.node_id)

        # Initialize account file if it doesn't exist
        self._initialize_account()

    def _initialize_account(self):
        """Initialize account file with default value if not exists"""
        if not os.path.exists(self.account_file):
            with open(self.account_file, 'w') as f:
                f.write('0')
            self.logger.info(f"Created account file: {self.account_file}")

    def _read_account_unsafe(self):
        """
        Read current account balance from file (without lock)
        Internal use only - caller must hold lock

        Returns:
            float: Current account balance
        """
        with open(self.account_file, 'r') as f:
            value = float(f.read().strip())
        return value

    def _write_account_unsafe(self, value):
        """
        Write account balance to file (without lock)
        Internal use only - caller must hold lock

        Args:
            value: New account balance
        """
        with open(self.account_file, 'w') as f:
            f.write(str(value))

    def read_account(self):
        """
        Read current account balance from file

        Returns:
            float: Current account balance
        """
        with self.lock:
            value = self._read_account_unsafe()
            self.logger.info(f"Read account {self.account_name}: {value}")
            return value

    def write_account(self, value):
        """
        Write account balance to file

        Args:
            value: New account balance
        """
        with self.lock:
            self._write_account_unsafe(value)
            self.logger.info(f"Wrote account {self.account_name}: {value}")

    def set_crash_before_prepare(self, crash):
        """Enable/disable crash simulation before prepare response"""
        self.crash_before_prepare = crash
        self.logger.info(f"Crash before prepare set to: {crash}")
        return True

    def set_crash_after_prepare(self, crash):
        """Enable/disable crash simulation after prepare response"""
        self.crash_after_prepare = crash
        self.logger.info(f"Crash after prepare set to: {crash}")
        return True

    def prepare(self, transaction_id, transaction_type, amount):
        """
        Phase 1 of 2PC: Prepare to execute transaction
        Check if transaction can be executed

        Args:
            transaction_id: Unique transaction identifier
            transaction_type: Type of transaction ('transfer', 'bonus')
            amount: Amount to add/subtract (negative for subtract)

        Returns:
            str: 'VOTE_COMMIT' if can execute, 'VOTE_ABORT' otherwise
        """
        self.logger.info(f"Received PREPARE for transaction {transaction_id}, type: {transaction_type}, amount: {amount}")

        # Simulate crash before responding
        if self.crash_before_prepare:
            self.logger.warning("Simulating crash before prepare response - sleeping 30s")
            time.sleep(30)
            return 'VOTE_ABORT'

        try:
            with self.lock:
                current_value = self._read_account_unsafe()
                new_value = current_value + amount

                self.logger.info(f"Current value: {current_value}, Amount: {amount}, New value: {new_value}")

                # Check if transaction is valid (no negative balance)
                if new_value < 0:
                    self.logger.warning(f"Transaction would result in negative balance: {new_value}")
                    return 'VOTE_ABORT'

                # Save prepared state
                self.prepared_value = new_value
                self.current_transaction = transaction_id

                self.logger.info(f"PREPARE successful - Current: {current_value}, Prepared: {new_value}")

                # Simulate crash after responding
                if self.crash_after_prepare:
                    self.logger.warning("Simulating crash after prepare response - sleeping 30s")
                    time.sleep(30)

                return 'VOTE_COMMIT'

        except Exception as e:
            self.logger.error(f"Error in prepare: {e}")
            return 'VOTE_ABORT'

    def commit(self, transaction_id):
        """
        Phase 2 of 2PC: Commit the prepared transaction

        Args:
            transaction_id: Transaction identifier

        Returns:
            str: 'COMMIT_SUCCESS' or 'COMMIT_FAILED'
        """
        self.logger.info(f"Received COMMIT for transaction {transaction_id}")

        try:
            with self.lock:
                if self.current_transaction != transaction_id:
                    self.logger.error(f"Transaction mismatch: expected {self.current_transaction}, got {transaction_id}")
                    return 'COMMIT_FAILED'

                if self.prepared_value is None:
                    self.logger.error("No prepared value found")
                    return 'COMMIT_FAILED'

                # Write the prepared value to disk
                self._write_account_unsafe(self.prepared_value)
                self.logger.info(f"Wrote account {self.account_name}: {self.prepared_value}")

                # Clear prepared state
                self.prepared_value = None
                self.current_transaction = None

                self.logger.info(f"COMMIT successful for transaction {transaction_id}")
                return 'COMMIT_SUCCESS'

        except Exception as e:
            self.logger.error(f"Error in commit: {e}")
            return 'COMMIT_FAILED'

    def abort(self, transaction_id):
        """
        Abort the transaction and clear prepared state

        Args:
            transaction_id: Transaction identifier

        Returns:
            str: 'ABORT_SUCCESS'
        """
        self.logger.info(f"Received ABORT for transaction {transaction_id}")

        with self.lock:
            self.prepared_value = None
            self.current_transaction = None

        self.logger.info(f"ABORT successful for transaction {transaction_id}")
        return 'ABORT_SUCCESS'

    def get_status(self):
        """
        Get current status of the participant

        Returns:
            dict: Status information
        """
        return {
            'node_id': self.node_id,
            'account_name': self.account_name,
            'balance': self.read_account(),
            'prepared': self.prepared_value is not None,
            'current_transaction': self.current_transaction
        }

    def start(self):
        """Start the RPC server"""
        server = SimpleXMLRPCServer((self.host, self.port), allow_none=True, logRequests=False)
        server.register_instance(self)

        self.logger.info(f"Participant {self.node_id} started on {self.host}:{self.port}")
        self.logger.info(f"Managing account {self.account_name} at {self.account_file}")

        try:
            server.serve_forever()
        except KeyboardInterrupt:
            self.logger.info("Shutting down...")


if __name__ == '__main__':
    import sys
    import config

    if len(sys.argv) < 2:
        print("Usage: python participant.py <node_number>")
        print("  node_number: 2 for Node-2 (Account A), 3 for Node-3 (Account B)")
        sys.exit(1)

    node_num = int(sys.argv[1])

    if node_num == 2:
        # Node-2 manages Account A
        participant = Participant(
            node_id='Node-2',
            account_name='A',
            account_file='account_A.txt',
            host=config.PARTICIPANT_A_HOST,
            port=config.PARTICIPANT_A_PORT
        )
    elif node_num == 3:
        # Node-3 manages Account B
        participant = Participant(
            node_id='Node-3',
            account_name='B',
            account_file='account_B.txt',
            host=config.PARTICIPANT_B_HOST,
            port=config.PARTICIPANT_B_PORT
        )
    else:
        print("Invalid node number. Use 2 or 3.")
        sys.exit(1)

    participant.start()
