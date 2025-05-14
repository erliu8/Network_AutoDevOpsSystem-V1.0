import sys
import time
import threading
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

# Import the BatchConfigController
from modules.Batch_configuration_of_addresses.Batch_configuration_of_addresses import BatchConfigController

def log_thread_status():
    """Print all running threads to diagnose issues"""
    print("\n===== ACTIVE THREADS =====")
    for thread in threading.enumerate():
        print(f"Thread Name: {thread.name}")
        print(f"Thread ID: {thread.ident}")
        print(f"Thread is daemon: {thread.daemon}")
        print(f"Thread is alive: {thread.is_alive()}")
        print("-----------------------")
    print("=========================\n")

class TestController:
    def __init__(self):
        self.controller = BatchConfigController()
        # Connect signals to test handlers
        self.controller.connection_result.connect(self.handle_connection_result)
        self.controller.config_result.connect(self.handle_config_result)
        self.controller.log_message.connect(self.handle_log)
        
        # Track number of received signals
        self.connection_signals = 0
        self.config_signals = 0
        self.log_signals = 0
    
    def handle_connection_result(self, success, message):
        self.connection_signals += 1
        print(f"CONNECTION RESULT: {'SUCCESS' if success else 'FAIL'} - {message}")
    
    def handle_config_result(self, success, message):
        self.config_signals += 1
        print(f"CONFIG RESULT: {'SUCCESS' if success else 'FAIL'} - {message}")
        print(f"Received config result signal #{self.config_signals}")
    
    def handle_log(self, message):
        self.log_signals += 1
        print(f"LOG: {message}")

def main():
    print("Starting Debug Script for Batch Configuration Module")
    
    # Create a test controller
    test = TestController()
    
    # Log initial thread status
    log_thread_status()
    
    # Test parameters
    ip = "22.22.22.22"  # Use a test IP
    username = "admin"
    password = "password"
    start_vlan = 100
    start_port = "G0/0/1"
    end_port = "G0/0/2"
    start_ip = "192.168.30.2/24"
    
    print(f"\nTesting connection to {ip}...")
    test.controller.test_connection(ip, username, password)
    
    # Wait for connection test to complete
    time.sleep(5)
    log_thread_status()
    
    print(f"\nTesting batch configuration on {ip}...")
    test.controller.apply_batch_config(ip, username, password, start_vlan, start_port, end_port, start_ip)
    
    # Monitor threads and signal counts
    max_wait = 20  # Max wait time in seconds
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        log_thread_status()
        print(f"Connection signals: {test.connection_signals}")
        print(f"Config signals: {test.config_signals}")
        print(f"Log signals: {test.log_signals}")
        
        # If we received a config result signal, we can exit
        if test.config_signals > 0:
            print("Configuration completed successfully!")
            break
            
        # Sleep for a bit before checking again
        time.sleep(2)
    
    if test.config_signals == 0:
        print("ERROR: Configuration did not complete in the expected time!")
        print("This indicates the module is hanging and not emitting the config_result signal.")
    
    # Final thread status
    log_thread_status()
    
    print("Debug script completed")

if __name__ == "__main__":
    main() 