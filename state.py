"""Shared state accessed by multiple modules.

Lives in its own module to avoid circular imports between main.py
and worker modules (ultrasonic, etc.) that need to check for shutdown.
"""

# Set to True by the main thread on Ctrl+C to signal all worker
# threads to exit their loops. Workers check this each iteration.
shutdown_flag = False