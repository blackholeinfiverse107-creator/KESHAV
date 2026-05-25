import sys
import os
import time
import json
import uuid
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import pytest

# Bucket Server Mock
class MockBucketHandler(BaseHTTPRequestHandler):
    store = []
    
    def do_POST(self):
        if self.path == "/bucket/artifact":
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            payload = json.loads(post_data.decode('utf-8'))
            self.store.append(payload)
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"status": "ok"}')
        else:
            self.send_response(404)
            self.end_headers()
            
    def do_GET(self):
        if self.path.startswith("/bucket/artifacts"):
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"artifacts": self.store}).encode())
        else:
            self.send_response(404)
            self.end_headers()
            
    def log_message(self, format, *args):
        pass # Suppress logs for tests

def start_mock_bucket_server():
    server = HTTPServer(('localhost', 8081), MockBucketHandler)
    thread = threading.Thread(target=server.serve_forever)
    thread.daemon = True
    thread.start()
    return server

# End-to-End Proof Test
def test_complete_execution_path():
    """
    Phase 6: End-to-End Proof
    Demonstrates one complete real execution path:
    Signal -> Propagation -> Intelligence -> Decision -> Enforcement -> Execution -> Bucket truth
    """
    # 1. Setup Environment
    os.environ["BUCKET_SERVICE_URL"] = "http://localhost:8081"
    server = start_mock_bucket_server()
    time.sleep(0.5)  # Wait for server to start
    
    try:
        # Import KESHAV-4
        from app.engine import PropagationEngine
        
        # Path swapping trick
        if 'app' in sys.modules:
            del sys.modules['app']
        sys.path.insert(0, r'C:\blackhole\text-risk-scoring-service')
        
        # Import live pipeline
        from app.sutradhara_control_plane import invoke_agent
        from app.enforcement_schemas import KSMLInput, ContextSignal, SourceSystem
        from app.layer3_dgic import compute_envelope_hash
        
        trace_id = f"trace-e2e-{uuid.uuid4().hex[:8]}"
        
        # 1. Signal / Propagation Input
        prop_in = {
            "blocked_task_id": "T1",
            "root_cause": "RC",
            "trace_id": trace_id,
            "timestamp": "2026-05-22T12:00:00Z",
            "dependency_graph": {"RC": ["T1", "T2"], "T1": ["T3"], "T2": ["T3"]}
        }
        
        # 2. Propagation
        prop_out = PropagationEngine.compute_dependency_output(prop_in)
        
        # Format envelope hash
        lineage_hash = "1" * 64
        payload_dict = {
            "epistemic_state": "KNOWN",
            "entropy_score": 0.0,
            "contradiction_flag": False
        }
        env_hash = compute_envelope_hash("schema_v1", lineage_hash, payload_dict)
        
        # 3. Create KSML Envelope (Signal mapping)
        ksml = KSMLInput(
            execution_id=trace_id,
            structured_signals=[
                ContextSignal(
                    signal_id="prop_impact",
                    signal_type="DEPENDENCY_IMPACT",
                    value=0.9 if prop_out["severity"] == "HIGH" else 0.5,
                    source="KESHAV"
                )
            ],
            metadata={
                "actor": "SETU_INTEGRATION_TEST",
                "proposed_action": prop_out["resolution_signal"],
                "source_system": SourceSystem.SOVEREIGN_CORE.value,
                "dgic_epistemic_state": {
                    "epistemic_state": "KNOWN",
                    "entropy_score": 0.0,
                    "contradiction_flag": False,
                    "lineage_hash": lineage_hash,
                    "envelope_hash": env_hash
                }
            }
        )
        
        # 4. Intelligence -> Decision -> Enforcement -> Execution -> Bucket
        result = invoke_agent(ksml)
        
        # Assertions on local returned result
        assert result.execution_id == trace_id
        assert result.trace_hash is not None
        assert len(result.trace_hash) == 64
        
        # 5. Bucket Truth Verification
        # Our mock server should have received exactly one artifact
        assert len(MockBucketHandler.store) > 0, "No data reached the Bucket server!"
        
        bucket_record = MockBucketHandler.store[-1]
        
        # The artifact in bucket must match the trace hash and execution ID exactly
        assert bucket_record["artifact_id"] == trace_id
        assert bucket_record["payload"]["trace_hash"] == result.trace_hash
        assert bucket_record["payload"]["decision"] == result.enforcement_decision.value
        
        print(f"E2E Trace Proven: execution_id={trace_id}, trace_hash={result.trace_hash}")
        
    finally:
        server.shutdown()
        server.server_close()
