"""Run CSP tests in an isolated process group to avoid CTRL_C_EVENT broadcast."""

import subprocess
import sys

CREATE_NEW_PROCESS_GROUP = 0x00000200

result = subprocess.run(
    [
        sys.executable,
        "-m",
        "pytest",
        "tests/test_security_headers_report_only.py",
        "tests/test_security_headers.py",
        "-v",
        "--tb=short",
    ],
    capture_output=True,
    text=True,
    cwd=r"e:\ProjectEPU",
    creationflags=CREATE_NEW_PROCESS_GROUP,
)
output = result.stdout + result.stderr
with open(r"e:\ProjectEPU\pytest_csp_out.txt", "w", encoding="utf-8") as f:
    f.write(f"Return code: {result.returncode}\n")
    f.write(output)

print("Return code:", result.returncode)
print(output[-3000:] if len(output) > 3000 else output)
