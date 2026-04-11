#!/bin/bash
# 무협지 뷰어 시작 (Android Termux / Linux)
cd "$(dirname "$0")"
pip install flask -q 2>/dev/null || pip3 install flask -q
python server.py || python3 server.py
