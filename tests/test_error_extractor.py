"""
Unit tests for ErrorExtractor
"""
import pytest
from src.error_extractor import ErrorExtractor, ErrorRegion


@pytest.fixture
def extractor():
    return ErrorExtractor(pre_context_lines=3, post_context_lines=10)


def test_detect_ecosystem(extractor):
    py_log = "Traceback (most recent call last):\n  File 'test.py', line 10\nAssertionError"
    node_log = "ERROR in ./src/components/Modal.tsx:12:4\nSyntaxError: Unexpected token"
    mvn_log = "[ERROR] /app/src/Main.java:[10,20] cannot find symbol\n[INFO] BUILD FAILURE"
    docker_log = "returned a non-zero code: 137\nOut of memory: Killed process 8421"

    assert extractor.detect_ecosystem(py_log) == "Python"
    assert extractor.detect_ecosystem(node_log) == "Node.js"
    assert extractor.detect_ecosystem(mvn_log) == "Java"
    assert extractor.detect_ecosystem(docker_log) == "Docker"


def test_merge_intervals(extractor):
    intervals = [(5, 15), (12, 22), (30, 40), (41, 50)]
    merged = extractor.merge_intervals(intervals)
    assert merged == [(5, 22), (30, 50)]


def test_extract_python_error_region(extractor):
    log = """
[INFO] Starting tests...
tests/test_cart.py PASSED
tests/test_payment.py FAILED
=================================== FAILURES ===================================
________________________ test_process_stripe_checkout _________________________
src/payment_gateway.py:94: in charge
    return {'status': 'success', 'charge_id': response['stripe_charge_id']}
E   KeyError: 'stripe_charge_id'
src/payment_gateway.py:94: KeyError
=========================== short test summary info ============================
FAILED tests/test_payment.py::test_process_stripe_checkout - KeyError: 'stripe_charge_id'
##[error]Process completed with exit code 1.
"""
    regions = extractor.extract_error_regions(log)
    assert len(regions) >= 1
    reg = regions[0]
    assert reg.ecosystem == "Python"
    assert reg.culprit_file == "src/payment_gateway.py"
    assert reg.culprit_line == 94
    assert "KeyError" in reg.error_type or "PythonException" in reg.error_type
    assert "KeyError" in reg.raw_snippet


def test_extract_node_syntax_error(extractor):
    log = """
> webpack --mode production
ERROR in ./src/components/CheckoutModal.tsx:42:15
TS1005: ',' expected.
> 42 |     dispatch({ type: 'CHECKOUT_SUCCESS' payload: token });
SyntaxError: Unexpected token, expected "," (42:40)
npm ERR! command failed with exit code 2
"""
    regions = extractor.extract_error_regions(log)
    assert len(regions) >= 1
    reg = regions[0]
    assert reg.ecosystem == "Node.js"
    assert "./src/components/CheckoutModal.tsx" in reg.culprit_file or "CheckoutModal.tsx" in reg.culprit_file
    assert reg.culprit_line == 42


def test_extract_docker_oom(extractor):
    log = """
Step 6/12 : RUN cargo build --release
kernel: [ 3491.291044] Out of memory: Killed process 8421 (rustc)
error: could not compile `heavy-graph-engine` due to signal: 9, SIGKILL: kill
The command '/bin/sh -c cargo build --release' returned a non-zero code: 137
Container runtime fatal: Process killed by cgroup OOM-killer
"""
    regions = extractor.extract_error_regions(log)
    assert len(regions) >= 1
    reg = regions[0]
    assert reg.ecosystem == "Docker"
    assert "OOM" in reg.error_type or "137" in reg.raw_snippet
