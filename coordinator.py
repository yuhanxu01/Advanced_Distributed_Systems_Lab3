"""
Coordinator Node for 2PC Protocol
Coordinates distributed transactions across participants
"""

import logging
import time
import uuid
from xmlrpc.server import SimpleXMLRPCServer
from xmlrpc.client import ServerProxy
import socket

class Coordinator:
    """
    Coordinator node that orchestrates 2PC protocol
    Manages transaction execution across multiple participants
    """

    def __init__(self, host, port, participants_config):
        """
        Initialize coordinator node

        Args:
            host: Host address for RPC server
            port: Port for RPC server
            participants_config: List of (name, host, port) tuples for participants
        """
        self.host = host
        self.port = port
        self.participants_config = participants_config

        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='[Coordinator] %(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger('Coordinator')

        # Connect to participants
        self.participants = {}
        self._connect_participants()

    def _connect_participants(self):
        """Establish RPC connections to all participants"""
        for name, host, port in self.participants_config:
            try:
                url = f"http://{host}:{port}"
                self.participants[name] = ServerProxy(url, allow_none=True)
                self.logger.info(f"Connected to participant {name} at {url}")
            except Exception as e:
                self.logger.error(f"Failed to connect to {name}: {e}")

    def _generate_transaction_id(self):
        """Generate unique transaction ID"""
        return str(uuid.uuid4())

    def execute_transaction(self, transaction_type, params):
        """
        Execute a distributed transaction using 2PC protocol

        Args:
            transaction_type: Type of transaction ('transfer' or 'bonus')
            params: Transaction parameters

        Returns:
            dict: Transaction result with status and details
        """
        transaction_id = self._generate_transaction_id()
        self.logger.info(f"Starting transaction {transaction_id}: {transaction_type}")
        self.logger.info(f"Parameters: {params}")

        # Calculate transaction amounts for each participant
        amounts = self._calculate_amounts(transaction_type, params)
        if amounts is None:
            return {
                'status': 'FAILED',
                'reason': 'Invalid transaction parameters',
                'transaction_id': transaction_id
            }

        # Phase 1: Prepare
        prepare_result = self._prepare_phase(transaction_id, transaction_type, amounts)

        if prepare_result['all_voted_commit']:
            # Phase 2: Commit
            commit_result = self._commit_phase(transaction_id)
            return {
                'status': 'COMMITTED',
                'transaction_id': transaction_id,
                'prepare_votes': prepare_result['votes'],
                'commit_results': commit_result
            }
        else:
            # Phase 2: Abort
            abort_result = self._abort_phase(transaction_id)
            return {
                'status': 'ABORTED',
                'transaction_id': transaction_id,
                'reason': 'Not all participants voted commit',
                'prepare_votes': prepare_result['votes'],
                'abort_results': abort_result
            }

    def _calculate_amounts(self, transaction_type, params):
        """
        Calculate transaction amounts for each participant

        Args:
            transaction_type: 'transfer' or 'bonus'
            params: Transaction parameters

        Returns:
            dict: Amounts for each participant, or None if invalid
        """
        if transaction_type == 'transfer':
            # Transfer amount from A to B
            amount = params.get('amount', 0)
            return {
                'A': -amount,  # Subtract from A
                'B': amount    # Add to B
            }

        elif transaction_type == 'bonus':
            # Add 20% bonus to A and add same amount to B
            # Need to read current value of A
            try:
                current_a = self.participants['A'].read_account()
                bonus_amount = current_a * 0.2
                return {
                    'A': bonus_amount,   # Add 20% to A
                    'B': bonus_amount    # Add same amount to B
                }
            except Exception as e:
                self.logger.error(f"Failed to read account A: {e}")
                return None

        else:
            self.logger.error(f"Unknown transaction type: {transaction_type}")
            return None

    def _prepare_phase(self, transaction_id, transaction_type, amounts):
        """
        Phase 1 of 2PC: Send PREPARE to all participants

        Args:
            transaction_id: Transaction identifier
            transaction_type: Type of transaction
            amounts: Dict of amounts for each participant

        Returns:
            dict: Prepare phase results
        """
        self.logger.info(f"[{transaction_id}] Phase 1: PREPARE")

        votes = {}
        all_voted_commit = True

        for name, amount in amounts.items():
            try:
                self.logger.info(f"[{transaction_id}] Sending PREPARE to {name} with amount {amount}")

                # Set socket timeout for RPC call
                participant = self.participants[name]
                participant._ServerProxy__transport.timeout = 15  # 15 second timeout

                vote = participant.prepare(transaction_id, transaction_type, amount)
                votes[name] = vote

                self.logger.info(f"[{transaction_id}] {name} voted: {vote}")

                if vote != 'VOTE_COMMIT':
                    all_voted_commit = False

            except socket.timeout:
                self.logger.error(f"[{transaction_id}] Timeout waiting for {name} - assuming VOTE_ABORT")
                votes[name] = 'TIMEOUT'
                all_voted_commit = False

            except Exception as e:
                self.logger.error(f"[{transaction_id}] Error from {name}: {e}")
                votes[name] = 'ERROR'
                all_voted_commit = False

        return {
            'votes': votes,
            'all_voted_commit': all_voted_commit
        }

    def _commit_phase(self, transaction_id):
        """
        Phase 2 of 2PC: Send COMMIT to all participants

        Args:
            transaction_id: Transaction identifier

        Returns:
            dict: Commit results from participants
        """
        self.logger.info(f"[{transaction_id}] Phase 2: COMMIT")

        results = {}
        for name in self.participants.keys():
            try:
                result = self.participants[name].commit(transaction_id)
                results[name] = result
                self.logger.info(f"[{transaction_id}] {name} commit result: {result}")
            except Exception as e:
                self.logger.error(f"[{transaction_id}] Error committing {name}: {e}")
                results[name] = 'ERROR'

        return results

    def _abort_phase(self, transaction_id):
        """
        Phase 2 of 2PC: Send ABORT to all participants

        Args:
            transaction_id: Transaction identifier

        Returns:
            dict: Abort results from participants
        """
        self.logger.info(f"[{transaction_id}] Phase 2: ABORT")

        results = {}
        for name in self.participants.keys():
            try:
                result = self.participants[name].abort(transaction_id)
                results[name] = result
                self.logger.info(f"[{transaction_id}] {name} abort result: {result}")
            except Exception as e:
                self.logger.error(f"[{transaction_id}] Error aborting {name}: {e}")
                results[name] = 'ERROR'

        return results

    def get_account_balances(self):
        """
        Get current balances from all participants

        Returns:
            dict: Account balances
        """
        balances = {}
        for name in self.participants.keys():
            try:
                balance = self.participants[name].read_account()
                balances[name] = balance
            except Exception as e:
                self.logger.error(f"Error reading {name}: {e}")
                balances[name] = 'ERROR'

        return balances

    def set_participant_crash(self, participant_name, crash_before=False, crash_after=False):
        """
        Configure crash simulation for a participant

        Args:
            participant_name: Name of participant ('A' or 'B')
            crash_before: Crash before prepare response
            crash_after: Crash after prepare response

        Returns:
            bool: Success
        """
        try:
            if crash_before:
                self.participants[participant_name].set_crash_before_prepare(True)
                self.logger.info(f"Set {participant_name} to crash BEFORE prepare")
            if crash_after:
                self.participants[participant_name].set_crash_after_prepare(True)
                self.logger.info(f"Set {participant_name} to crash AFTER prepare")
            return True
        except Exception as e:
            self.logger.error(f"Error setting crash for {participant_name}: {e}")
            return False

    def reset_participant_crash(self, participant_name):
        """Reset crash simulation flags for a participant"""
        try:
            self.participants[participant_name].set_crash_before_prepare(False)
            self.participants[participant_name].set_crash_after_prepare(False)
            self.logger.info(f"Reset crash flags for {participant_name}")
            return True
        except Exception as e:
            self.logger.error(f"Error resetting crash for {participant_name}: {e}")
            return False

    def start(self):
        """Start the RPC server"""
        server = SimpleXMLRPCServer((self.host, self.port), allow_none=True, logRequests=False)
        server.register_instance(self)

        self.logger.info(f"Coordinator started on {self.host}:{self.port}")

        try:
            server.serve_forever()
        except KeyboardInterrupt:
            self.logger.info("Shutting down...")


if __name__ == '__main__':
    import config

    # Configure participants
    participants_config = [
        ('A', config.PARTICIPANT_A_HOST, config.PARTICIPANT_A_PORT),
        ('B', config.PARTICIPANT_B_HOST, config.PARTICIPANT_B_PORT)
    ]

    coordinator = Coordinator(
        host=config.COORDINATOR_HOST,
        port=config.COORDINATOR_PORT,
        participants_config=participants_config
    )

    coordinator.start()
