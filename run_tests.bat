@echo off
e:\ProjectEPU\venv\Scripts\python.exe -m pytest tests/test_security_headers_report_only.py tests/test_security_headers.py -v --tb=short > e:\ProjectEPU\pytest_csp_out.txt 2>&1
