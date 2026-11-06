"""
Generates highly realistic CI/CD build logs containing authentic noise,
ANSI terminal codes, download spinners, timestamps, and genuine stack traces.
"""
import os

def create_sample_logs(base_dir: str):
    os.makedirs(base_dir, exist_ok=True)

    # 1. Python Pytest Failure Log
    py_lines = []
    py_lines.append("\x1b[34m[INFO] 2026-11-06T10:00:01.102Z Initiating CI build on runner-ubuntu-22.04\x1b[0m")
    py_lines.append("[INFO] Checking out commit 4c89a7f (branch: main)")
    py_lines.append("[INFO] Setting up Python 3.11.5 environment...")
    for i in range(1, 45):
        py_lines.append(f"\x1b[32m[pip]\x1b[0m Downloading dependency pkg-{i}-1.{i}.0-py3-none-any.whl ({i*120} kB)")
        py_lines.append(f"  \x1b[33m[=========================>            ]\x1b[0m {i*2}% eta 00:0{50-i}")
        py_lines.append(f"Installing collected packages: pkg-{i} (version 1.{i}.0)")
    py_lines.append("[INFO] Dependencies successfully installed. Total 44 packages verified.")
    py_lines.append("[INFO] Running database migrations...")
    for m in range(1, 20):
        py_lines.append(f"Applying core.000{m}_auto_migration... OK")
    py_lines.append("\x1b[1m\x1b[36m============================= test session starts ==============================\x1b[0m")
    py_lines.append("platform linux -- Python 3.11.5, pytest-8.1.1, pluggy-1.4.0")
    py_lines.append("rootdir: /home/runner/work/ecommerce-api/ecommerce-api")
    py_lines.append("collected 18 items\n")
    for t in range(1, 15):
        py_lines.append(f"tests/test_cart.py::test_cart_item_{t} \x1b[32mPASSED\x1b[0m [ {int(t/18*100)}%]")
    py_lines.append("tests/test_payment.py::test_process_stripe_checkout \x1b[31mFAILED\x1b[0m [ 83%]")
    py_lines.append("tests/test_payment.py::test_refund_transaction \x1b[32mPASSED\x1b[0m [ 88%]")
    py_lines.append("tests/test_user.py::test_user_profile \x1b[32mPASSED\x1b[0m [ 94%]")
    py_lines.append("tests/test_user.py::test_user_auth \x1b[32mPASSED\x1b[0m [100%]\n")
    py_lines.append("\x1b[31m\x1b[1m=================================== FAILURES ===================================\x1b[0m")
    py_lines.append("\x1b[31m\x1b[1m________________________ test_process_stripe_checkout _________________________\x1b[0m")
    py_lines.append("payment_gateway = <src.payment_gateway.StripeGateway object at 0x7f9a8820f850>")
    py_lines.append("order_payload = {'amount': 4999, 'currency': 'usd', 'customer_id': 'cust_99812'}")
    py_lines.append("")
    py_lines.append("    def test_process_stripe_checkout():")
    py_lines.append("        gateway = StripeGateway(api_key='sk_test_mock_token')")
    py_lines.append(">       result = gateway.charge(amount=4999, currency='usd', customer_id='cust_99812')")
    py_lines.append("")
    py_lines.append("tests/test_payment.py:42: ")
    py_lines.append("_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ ")
    py_lines.append("src/payment_gateway.py:94: in charge")
    py_lines.append("    return {'status': 'success', 'charge_id': response['stripe_charge_id']}")
    py_lines.append("_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ ")
    py_lines.append("")
    py_lines.append("response = {'id': 'ch_3Mv67aLkdIwHu7ix0rW7q', 'status': 'succeeded', 'tx_id': 'ch_3Mv67a'}")
    py_lines.append("")
    py_lines.append("\x1b[31m\x1b[1mE   KeyError: 'stripe_charge_id'\x1b[0m")
    py_lines.append("\x1b[31m\x1b[1mE   Note: The mock Stripe API response uses 'id' or 'tx_id', but source accessed 'stripe_charge_id'.\x1b[0m")
    py_lines.append("")
    py_lines.append("src/payment_gateway.py:94: KeyError")
    py_lines.append("\x1b[31m\x1b[1m=========================== short test summary info ============================\x1b[0m")
    py_lines.append("FAILED tests/test_payment.py::test_process_stripe_checkout - KeyError: 'stripe_charge_id'")
    py_lines.append("\x1b[31m========================= 1 failed, 17 passed in 4.12s =========================\x1b[0m")
    for i in range(1, 20):
        py_lines.append(f"[DEBUG] Cleaning up temporary test fixture_{i} on /tmp/pytest-cache-{i}")
    py_lines.append("##[error]Process completed with exit code 1.")

    with open(os.path.join(base_dir, "python_pytest_failure.log"), "w", encoding="utf-8") as f:
        f.write("\n".join(py_lines))

    # 2. Node.js Syntax & Webpack Compilation Error
    node_lines = []
    node_lines.append("[INFO] Running GitHub Action step: Build Webpack Client Assets")
    node_lines.append("Node version: v18.19.0, npm version: 9.2.0")
    for i in range(1, 40):
        node_lines.append(f"npm http fetch GET 200 https://registry.npmjs.org/@core/ui-kit-{i} 142ms (from cache)")
        node_lines.append(f"  \x1b[2K\x1b[1G⠋ reify:@core/ui-kit-{i}: timing reifyNode:node_modules/@core/ui-kit-{i}")
    node_lines.append("added 842 packages in 14.3s")
    node_lines.append("> client-portal@2.4.0 build")
    node_lines.append("> webpack --mode production --config webpack.prod.js")
    for i in range(1, 25):
        node_lines.append(f"[webpack] Compiling chunk {i}/35: asset-bundle-{i}.js (optimized)")
    node_lines.append("\x1b[31mERROR in ./src/components/CheckoutModal.tsx:42:15\x1b[0m")
    node_lines.append("TS1005: ',' expected.")
    node_lines.append("  40 |   const handleConfirm = (token: string) => {")
    node_lines.append("  41 |     if (!token) return;")
    node_lines.append("\x1b[31m> 42 |     dispatch({ type: 'CHECKOUT_SUCCESS' payload: token });\x1b[0m")
    node_lines.append("     |                                         ^")
    node_lines.append("  43 |     onClose();")
    node_lines.append("  44 |   };")
    node_lines.append("\x1b[31mSyntaxError: Unexpected token, expected \",\" (42:40)\x1b[0m")
    node_lines.append("    at Parser.raise (/home/runner/work/app/node_modules/@babel/parser/lib/index.js:522:17)")
    node_lines.append("    at Parser.unexpected (/home/runner/work/app/node_modules/@babel/parser/lib/index.js:9642:16)")
    node_lines.append("    at Parser.parseExprSubscripts (/home/runner/work/app/node_modules/@babel/parser/lib/index.js:10620:17)")
    node_lines.append("webpack 5.89.0 compiled with 1 error and 0 warnings in 3820 ms")
    node_lines.append("npm ERR! Lifecycle script `build` failed with error:")
    node_lines.append("npm ERR! Error: command failed with exit code 2")
    node_lines.append("##[error]Process completed with exit code 2.")

    with open(os.path.join(base_dir, "node_build_syntax_error.log"), "w", encoding="utf-8") as f:
        f.write("\n".join(node_lines))

    # 3. Docker Out Of Memory (OOMKilled - Exit code 137)
    docker_lines = []
    docker_lines.append("Step 1/12 : FROM rust:1.75-slim AS builder")
    for i in range(1, 15):
        docker_lines.append(f" ---> Pulling layer sha256:d84e{i*234:04x} [====================] 14.8MB/14.8MB")
    docker_lines.append("Step 5/12 : COPY Cargo.toml Cargo.lock ./")
    docker_lines.append("Step 6/12 : RUN cargo build --release")
    for i in range(1, 35):
        docker_lines.append(f"   Compiling crate-dep-v{i} v0.{i}.2")
    docker_lines.append("   Compiling heavy-graph-engine v2.1.0 (/usr/src/app)")
    docker_lines.append("kernel: [ 3491.291044] Out of memory: Killed process 8421 (rustc) total-vm:14820120kB, anon-rss:7894210kB, file-rss:0kB, shmem-rss:0kB, UID:0 pgtables:18440kB oom_score_adj:0")
    docker_lines.append("\x1b[31merror: could not compile `heavy-graph-engine` (bin \"heavy-graph-engine\") due to signal: 9, SIGKILL: kill\x1b[0m")
    docker_lines.append("\x1b[31mThe command '/bin/sh -c cargo build --release' returned a non-zero code: 137\x1b[0m")
    docker_lines.append("Container runtime fatal: Process killed by cgroup OOM-killer (Out of memory: memory limit 8192MB exceeded)")
    docker_lines.append("##[error]Process completed with exit code 137.")

    with open(os.path.join(base_dir, "docker_oom_exit.log"), "w", encoding="utf-8") as f:
        f.write("\n".join(docker_lines))

    # 4. Maven Java ClassNotFound Compilation Error
    mvn_lines = []
    mvn_lines.append("[INFO] Scanning for projects...")
    mvn_lines.append("[INFO] Building enterprise-auth-service 1.4.0-SNAPSHOT")
    for i in range(1, 45):
        mvn_lines.append(f"[INFO] Downloaded from central: https://repo.maven.apache.org/maven2/org/apache/commons/commons-lang3/3.{i}.0/commons-lang3-3.{i}.0.jar (504 kB at 2.4 MB/s)")
        mvn_lines.append(f"Progress ({i}/45): {i*2.2:.1f}%")
    mvn_lines.append("[INFO] --- maven-compiler-plugin:3.11.0:compile (default-compile) @ auth-service ---")
    mvn_lines.append("[INFO] Changes detected - recompiling the module!")
    mvn_lines.append("[INFO] Compiling 42 source files to /app/target/classes")
    mvn_lines.append("[ERROR] /app/src/main/java/com/jain/auth/TokenValidator.java:[28,32] cannot find symbol")
    mvn_lines.append("[ERROR]   symbol:   class JWTVerifier")
    mvn_lines.append("[ERROR]   location: package com.auth0.jwt")
    mvn_lines.append("[ERROR] /app/src/main/java/com/jain/auth/TokenValidator.java:[34,19] cannot find symbol")
    mvn_lines.append("[ERROR]   symbol:   class DecodedJWT")
    mvn_lines.append("[ERROR]   location: package com.auth0.jwt.interfaces")
    mvn_lines.append("[INFO] 2 errors")
    mvn_lines.append("[INFO] -------------------------------------------------------------")
    mvn_lines.append("[ERROR] COMPILATION ERROR : ")
    mvn_lines.append("[INFO] -------------------------------------------------------------")
    mvn_lines.append("[ERROR] Failed to execute goal org.apache.maven.plugins:maven-compiler-plugin:3.11.0:compile (default-compile) on project enterprise-auth-service: Compilation failure: Compilation failure")
    mvn_lines.append("[INFO] ------------------------------------------------------------------------")
    mvn_lines.append("[INFO] BUILD FAILURE")
    mvn_lines.append("[INFO] ------------------------------------------------------------------------")
    mvn_lines.append("[INFO] Total time:  28.452 s")
    mvn_lines.append("[ERROR] Failed to execute goal org.apache.maven.plugins:maven-compiler-plugin:3.11.0:compile: Execution default-compile of goal org.apache.maven.plugins:maven-compiler-plugin:3.11.0:compile failed: Missing dependency 'com.auth0:java-jwt:4.4.0' in pom.xml -> [Help 1]")
    mvn_lines.append("##[error]Process completed with exit code 1.")

    with open(os.path.join(base_dir, "maven_java_compilation.log"), "w", encoding="utf-8") as f:
        f.write("\n".join(mvn_lines))

    print(f"Generated 4 realistic sample logs in: {base_dir}")

if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    create_sample_logs(current_dir)
