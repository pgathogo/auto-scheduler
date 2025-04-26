@echo off

if EXIST auto_scheduler.py (
   rename auto_scheduler.py auto_scheduler.pyw
)

start pyw auto_scheduler.pyw
