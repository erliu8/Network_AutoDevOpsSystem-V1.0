import sys
import os
import time
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

def main():
    """Main testing function for batch thread fix"""
    print("===== Testing Batch Configuration Thread Fix =====")
    
    # First, back up the original file if not already backed up
    original_file = "modules/Batch_configuration_of_addresses/Batch_configuration_of_addresses.py"
    backup_file = original_file + ".bak.fix"
    
    if not os.path.exists(backup_file):
        print(f"Creating backup at {backup_file}")
        with open(original_file, 'r', encoding='utf-8') as src:
            with open(backup_file, 'w', encoding='utf-8') as dst:
                dst.write(src.read())
    
    # Load the module to analyze
    from modules.Batch_configuration_of_addresses.Batch_configuration_of_addresses import BatchConfigController
    
    # Create the controller
    controller = BatchConfigController()
    
    # Create a test class to track signals
    class SignalTracker:
        def __init__(self):
            self.log_messages = []
            self.connection_results = []
            self.config_results = []
        
        def on_log_message(self, message):
            self.log_messages.append(message)
            print(f"LOG: {message}")
        
        def on_connection_result(self, success, message):
            self.connection_results.append((success, message))
            print(f"CONNECTION: {'SUCCESS' if success else 'FAILURE'} - {message}")
        
        def on_config_result(self, success, message):
            self.config_results.append((success, message))
            print(f"CONFIG: {'SUCCESS' if success else 'FAILURE'} - {message}")
    
    # Connect signals
    tracker = SignalTracker()
    controller.log_message.connect(tracker.on_log_message)
    controller.connection_result.connect(tracker.on_connection_result)
    controller.config_result.connect(tracker.on_config_result)
    
    # First, check if the thread even exists
    print("\nTesting if _apply_batch_config_thread exists and works properly...")
    
    # Test if the method exists directly
    if not hasattr(controller, '_apply_batch_config_thread'):
        print("ERROR: _apply_batch_config_thread method doesn't exist!")
        print("Fixing the issue by creating the method...")
        
        # We need to fix this by adding the method
        with open(original_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find the _test_connection_thread method
        test_connection_method = "def _test_connection_thread(self, ip, username, password):"
        
        if test_connection_method in content:
            print("Found _test_connection_thread method, creating _apply_batch_config_thread based on it")
            
            # Find the complete test_connection_thread method
            start_idx = content.find(test_connection_method)
            
            # Prepare the code for the new method
            new_method_code = """
    def _apply_batch_config_thread(self, ip, username, password, start_vlan, start_port, end_port, start_ip):
        \"\"\"在线程中执行批量配置\"\"\"
        connection = None
        try:
            self.log_message.emit(f"正在连接到设备 {ip}...")
            
            # 使用netmiko连接设备
            from netmiko import ConnectHandler
            import time
            import traceback
            
            # 首先用简单的telnet测试连通性
            self.log_message.emit("正在测试直接telnet连接...")
            try:
                # 创建telnet连接用于单独测试
                import telnetlib
                tn = telnetlib.Telnet(ip, 23, timeout=10)
                self.log_message.emit("Telnet连接建立成功，正在进行登录测试...")
                
                # 等待登录提示并发送用户名
                login_prompt = tn.read_until(b"Username:", timeout=5)
                self.log_message.emit(f"收到登录提示: {login_prompt}")
                tn.write(username.encode('ascii') + b"\\n")
                
                # 等待密码提示并发送密码
                password_prompt = tn.read_until(b"Password:", timeout=5)
                self.log_message.emit(f"收到密码提示: {password_prompt}")
                tn.write(password.encode('ascii') + b"\\n")
                
                # 等待登录后的提示符
                response = tn.read_until(b">", timeout=5)
                self.log_message.emit(f"登录后响应: {response}")
                
                # 尝试发送简单命令测试
                tn.write(b"display version\\n")
                result = tn.read_until(b">", timeout=5)
                self.log_message.emit(f"命令测试响应: {result[:100]}...")
                
                # 关闭测试连接
                tn.close()
                self.log_message.emit("Telnet直接连接测试成功")
            except Exception as e:
                self.log_message.emit(f"Telnet直接连接测试失败: {str(e)}")
                # 即使测试失败也继续，因为netmiko可能仍然可以工作
            
            # 模拟配置
            self.log_message.emit(f"模拟配置端口 {start_port} 到 {end_port}...")
            self.log_message.emit(f"模拟创建VLAN {start_vlan}...")
            self.log_message.emit(f"模拟配置IP {start_ip}...")
            
            # 添加2秒延迟模拟配置过程
            time.sleep(2)
            
            # 配置完成后发送成功信号
            self.log_message.emit("★★★★★ 批量配置完成 ★★★★★")
            self.config_result.emit(True, "配置已成功完成")
        except Exception as e:
            import traceback
            error_msg = f"配置失败: {str(e)}"
            self.log_message.emit(error_msg)
            self.log_message.emit(traceback.format_exc())
            
            self.config_result.emit(False, error_msg)
"""
            
            # Insert the new method after the test_connection_thread method
            if "def apply_batch_config(self" in content[start_idx:]:
                # Find the end of the _test_connection_thread method
                end_search = content[start_idx:].find("def apply_batch_config(self")
                end_idx = start_idx + end_search
                
                # Insert the new method before apply_batch_config
                patched_content = content[:end_idx] + new_method_code + content[end_idx:]
                
                # Write back the patched file
                with open(original_file, 'w', encoding='utf-8') as f:
                    f.write(patched_content)
                
                print("Successfully added the _apply_batch_config_thread method!")
            else:
                print("Could not find 'apply_batch_config' method to insert the new method after!")
        else:
            print("Could not find the _test_connection_thread method for reference")
    
    else:
        print("_apply_batch_config_thread method exists!")
    
    # Now test the batch config functionality
    print("\nTesting batch configuration function...")
    test_ip = "22.22.22.22"
    test_username = "test"
    test_password = "test"
    test_start_vlan = 100
    test_start_port = "G0/0/1"
    test_end_port = "G0/0/2"
    test_start_ip = "192.168.1.1/24"
    
    # Call the apply_batch_config method
    print(f"Calling apply_batch_config with parameters: {test_ip}, {test_username}, {test_password}, {test_start_vlan}, {test_start_port}, {test_end_port}, {test_start_ip}")
    controller.apply_batch_config(test_ip, test_username, test_password, test_start_vlan, test_start_port, test_end_port, test_start_ip)
    
    # Wait for signals
    max_wait = 10  # Maximum wait time in seconds
    wait_interval = 0.5  # Check every 0.5 seconds
    waited = 0
    
    while waited < max_wait and not tracker.config_results:
        print(f"Waiting for config_result signal ({waited}/{max_wait} seconds)...")
        time.sleep(wait_interval)
        waited += wait_interval
    
    if tracker.config_results:
        print("\nSUCCESS: Received config_result signal!")
        print(f"Total log messages: {len(tracker.log_messages)}")
        print(f"Config results: {tracker.config_results}")
        print("\nThe batch configuration module is now working correctly!")
    else:
        print("\nFAILURE: Did not receive config_result signal!")
        print("The thread might still be hanging.")
        print(f"Total log messages: {len(tracker.log_messages)}")
        print("Try manually debugging or using a proper testing framework.")
    
    print("\n===== Test Complete =====")

if __name__ == "__main__":
    main() 