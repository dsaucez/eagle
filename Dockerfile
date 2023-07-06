FROM python:3.9.17-slim
COPY tester.py upf.py
ENTRYPOINT python3 upf.py -l
