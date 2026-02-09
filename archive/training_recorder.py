#!/usr/bin/env python3
"""
Pacman Training Recorder - Complete Transaction Logging System
Records EVERYTHING about each swap for AI learning loop.
"""

import json
import time
from datetime import datetime
from pathlib import Path
import hashlib

class PacmanTrainingRecorder:
    def __init__(self, training_data_dir="training_data"):
        self.training_dir = Path(training_data_dir)
        self.training_dir.mkdir(exist_ok=True)
        
        # Separate logs for different phases
        self.commands_log = self.training_dir / "commands.jsonl"
        self.executions_log = self.training_dir / "executions.jsonl"
        self.failures_log = self.training_dir / "failures.jsonl"
        
    def start_command_session(self, natural_language_input: str, user_context: dict = None):
        """Start tracking a new command from natural language input."""
        session_id = hashlib.md5(f"{natural_language_input}{time.time()}".encode()).hexdigest()[:8]
        
        command_record = {
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
            "natural_language": natural_language_input,
            "user_context": user_context or {},
            "phase": "command_received"
        }
        
        self._append_to_log(self.commands_log, command_record)
        return session_id
    
    def record_route_planning(self, session_id: str, planned_route: dict, pool_states: dict):
        """Record the AI's route planning decision."""
        planning_record = {
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
            "phase": "route_planned",
            "planned_route": planned_route,
            "pool_states_snapshot": pool_states,
            "planning_confidence": planned_route.get("confidence_score", 0.0)
        }
        
        self._append_to_log(self.commands_log, planning_record)
    
    def record_human_approval(self, session_id: str, approved: bool, modifications: dict = None):
        """Record human approval/rejection and any modifications."""
        approval_record = {
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
            "phase": "human_approval",
            "approved": approved,
            "modifications": modifications or {},
            "final_route": modifications.get("final_route") if modifications else None
        }
        
        self._append_to_log(self.commands_log, approval_record)
    
    def start_execution(self, session_id: str, contract_calls: list, gas_estimate: str):
        """Begin execution phase recording."""
        execution_start = {
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
            "phase": "execution_start",
            "contract_calls": contract_calls,
            "gas_estimate": gas_estimate,
            "execution_start_time": time.time()
        }
        
        self._append_to_log(self.executions_log, execution_start)
        return time.time()  # Return start time for duration calculation
    
    def record_transaction_result(self, session_id: str, start_time: float, result: dict):
        """Record complete transaction execution results."""
        execution_time = time.time() - start_time
        
        result_record = {
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
            "phase": "execution_complete",
            "execution_time_seconds": execution_time,
            "transaction_hash": result.get("transaction_hash"),
            "success": result.get("success", False),
            "actual_output": result.get("actual_output"),
            "actual_fees": result.get("actual_fees"),
            "gas_used": result.get("gas_used"),
            "slippage_actual": result.get("slippage"),
            "error_messages": result.get("error_messages", []),
            "pool_states_after": result.get("pool_states_after", {}),
            "raw_transaction_data": result.get("raw_transaction_data", {})
        }
        
        # Log to executions or failures based on success
        if result.get("success", False):
            self._append_to_log(self.executions_log, result_record)
        else:
            self._append_to_log(self.failures_log, result_record)
    
    def create_training_example(self, session_id: str):
        """Compile a complete training example from all session data."""
        # Read all records for this session
        command_records = self._get_session_records(self.commands_log, session_id)
        execution_records = self._get_session_records(self.executions_log, session_id)
        failure_records = self._get_session_records(self.failures_log, session_id)
        
        # Compile into structured training example
        training_example = {
            "session_id": session_id,
            "natural_language_input": None,
            "route_planning_data": {},
            "human_feedback": {},
            "execution_results": {},
            "success_score": 0.0,
            "learning_notes": []
        }
        
        # Extract data from records
        for record in command_records:
            if record["phase"] == "command_received":
                training_example["natural_language_input"] = record["natural_language"]
            elif record["phase"] == "route_planned":
                training_example["route_planning_data"] = record
            elif record["phase"] == "human_approval":
                training_example["human_feedback"] = record
        
        # Add execution results
        if execution_records:
            training_example["execution_results"] = execution_records[-1]  # Latest execution
            training_example["success_score"] = 1.0 if execution_records[-1].get("success") else 0.0
        elif failure_records:
            training_example["execution_results"] = failure_records[-1]
            training_example["success_score"] = 0.0
        
        # Save as structured training example
        training_file = self.training_dir / f"training_example_{session_id}.json"
        with open(training_file, 'w') as f:
            json.dump(training_example, f, indent=2)
        
        return training_example
    
    def _append_to_log(self, log_file: Path, record: dict):
        """Append a record to JSONL log file."""
        with open(log_file, 'a') as f:
            f.write(json.dumps(record) + '\n')
    
    def _get_session_records(self, log_file: Path, session_id: str) -> list:
        """Get all records for a specific session."""
        records = []
        if log_file.exists():
            with open(log_file, 'r') as f:
                for line in f:
                    record = json.loads(line.strip())
                    if record.get("session_id") == session_id:
                        records.append(record)
        return records
    
    def get_failure_patterns(self, limit: int = 50) -> list:
        """Analyze recent failures for pattern recognition."""
        if not self.failures_log.exists():
            return []
        
        failures = []
        with open(self.failures_log, 'r') as f:
            for line in f:
                failures.append(json.loads(line.strip()))
        
        # Return most recent failures for analysis
        return failures[-limit:]
    
    def get_success_metrics(self) -> dict:
        """Calculate success rate and performance metrics."""
        total_executions = 0
        successful_executions = 0
        total_slippage = []
        total_execution_time = []
        
        # Count successes
        if self.executions_log.exists():
            with open(self.executions_log, 'r') as f:
                for line in f:
                    record = json.loads(line.strip())
                    if record.get("phase") == "execution_complete":
                        successful_executions += 1
                        total_executions += 1
                        if record.get("slippage_actual"):
                            total_slippage.append(float(record["slippage_actual"]))
                        if record.get("execution_time_seconds"):
                            total_execution_time.append(float(record["execution_time_seconds"]))
        
        # Count failures
        if self.failures_log.exists():
            with open(self.failures_log, 'r') as f:
                for line in f:
                    record = json.loads(line.strip())
                    if record.get("phase") == "execution_complete":
                        total_executions += 1
        
        return {
            "total_executions": total_executions,
            "successful_executions": successful_executions,
            "success_rate": successful_executions / max(total_executions, 1),
            "average_slippage": sum(total_slippage) / len(total_slippage) if total_slippage else 0,
            "average_execution_time": sum(total_execution_time) / len(total_execution_time) if total_execution_time else 0
        }


# Example usage for testing
if __name__ == "__main__":
    recorder = PacmanTrainingRecorder()
    
    # Simulate a complete transaction flow
    session_id = recorder.start_command_session("Swap 500 USDC for wBTC", {"balance_usdc": "1000"})
    
    recorder.record_route_planning(session_id, {
        "path": ["USDC", "USDC[hts]", "WBTC[hts]"],
        "estimated_output": "0.007089",
        "confidence_score": 0.92
    }, {"pool_1_liquidity": "500M", "pool_13_liquidity": "12M"})
    
    recorder.record_human_approval(session_id, True)
    
    start_time = recorder.start_execution(session_id, [
        {"function": "swapExactTokensForTokens", "params": {...}},
        {"function": "associateToken", "params": {...}}
    ], "0.05 HBAR")
    
    recorder.record_transaction_result(session_id, start_time, {
        "success": True,
        "actual_output": "0.007085",
        "slippage": "0.056%",
        "gas_used": "0.048 HBAR",
        "transaction_hash": "0xabc123..."
    })
    
    # Create final training example
    training_example = recorder.create_training_example(session_id)
    print("Training example created:", training_example["session_id"])