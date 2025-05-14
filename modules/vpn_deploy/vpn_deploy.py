import re
import time
import telnetlib  # Replace paramiko with telnetlib
from PyQt5.QtCore import QObject, pyqtSignal  # 添加必要的导入
import threading
# 导入线程工厂
from core.business.thread_factory import ThreadFactory

class VPNDeployer(QObject):
    # 定义信号
    deploy_status = pyqtSignal(str, bool)  # 部署状态信号(消息, 成功/失败)
    command_output = pyqtSignal(str)  # 命令输出信号
    
    def __init__(self, ip, username, password, device_name=""):
        super().__init__()
        self.device_info = {
            'ip': ip,
            'username': username,
            'password': password,
            'device_name': device_name
        }
        self.tn = None
        # 获取线程工厂实例
        self.thread_factory = ThreadFactory.get_instance()
    
    def connect_device(self):
        """连接设备"""
        try:
            self.tn = telnetlib.Telnet(self.device_info['ip'], timeout=10)
            
            # 等待用户名提示
            self.tn.read_until(b"Username:", timeout=5)
            # 使用 1 作为用户名
            self.tn.write(b"1\r\n")
            
            # 等待密码提示
            self.tn.read_until(b"Password:", timeout=5)
            # 使用 1 作为密码
            self.tn.write(b"1\r\n")
            
            # 等待登录成功提示
            login_result = self.tn.read_until(b">", timeout=5).decode('ascii', errors='ignore')
            
            self.command_output.emit(f"成功连接到设备 {self.device_info['ip']}")
            return True
        except Exception as e:
            self.command_output.emit(f"连接设备失败: {str(e)}")
            return False
    
    def deploy_vpn(self, vpn_config):
        """部署VPN配置"""
        # 使用线程工厂创建线程
        self.thread_factory.start_thread(
            target=self._deploy_vpn_thread,
            args=(vpn_config,),
            name=f"VPNDeploy-{self.device_info['ip']}",
            module="VPN配置模块"
        )
        return True
    
    def _deploy_vpn_thread(self, vpn_config):
        """在线程中执行VPN部署"""
        success = False
        try:
            if self.connect_device():
                # 执行VPN配置命令
                self.command_output.emit("开始配置VPN...")
                
                # 进入系统视图
                self._execute_command("system-view")
                
                # 配置VPN实例
                vpn_name = vpn_config.get('vpn_name', 'VPN1')
                self._execute_command(f"ip vpn-instance {vpn_name}")
                
                # 配置RD值
                rd_value = vpn_config.get('rd_value', '100:1')
                self._execute_command(f"route-distinguisher {rd_value}")
                
                # 配置VPN目标
                vpn_target = vpn_config.get('vpn_target', '100:1')
                self._execute_command(f"vpn-target {vpn_target} both")
                
                # 退出VPN实例配置
                self._execute_command("quit")
                
                # 配置接口
                interface = vpn_config.get('interface', 'GigabitEthernet0/0/0')
                self._execute_command(f"interface {interface}")
                
                # 绑定VPN实例
                self._execute_command(f"ip binding vpn-instance {vpn_name}")
                
                # 配置IP地址
                ip_address = vpn_config.get('ip_address', '192.168.1.1 255.255.255.0')
                self._execute_command(f"ip address {ip_address}")
                
                # 启用接口
                self._execute_command("undo shutdown")
                
                # 退出接口配置
                self._execute_command("quit")
                
                # 保存配置
                self._execute_command("return")
                save_output = self._execute_command("save", expect_prompt=True)
                
                if "Y/N" in save_output:
                    save_confirm = self._execute_command("y", expect_prompt=True)
                    success = "successfully" in save_confirm or "成功" in save_confirm
                
                self.command_output.emit("VPN配置完成")
                
            else:
                self.command_output.emit("无法连接到设备，VPN配置失败")
        except Exception as e:
            self.command_output.emit(f"VPN配置过程中出错: {str(e)}")
        finally:
            if self.tn:
                self.tn.close()
            self.deploy_status.emit("VPN配置" + ("成功" if success else "失败"), success)
    
    def _execute_command(self, command, expect_prompt=False):
        """执行命令并返回输出"""
        if not self.tn:
            return ""
        
        try:
            # 发送命令
            self.command_output.emit(f"执行命令: {command}")
            self.tn.write(command.encode('ascii') + b"\r\n")
            
            # 等待命令执行，增加等待时间
            time.sleep(3)  # 增加到3秒
            
            # 接收输出（等待提示符）
            pattern_list = [b">", b"#", b"]"]
            
            # 使用更长的超时时间
            index, match, response = self.tn.expect(pattern_list, timeout=20)
            
            if index == -1:
                # 如果超时，尝试读取所有可用数据
                self.command_output.emit("命令超时，尝试读取可用数据")
                response = self.tn.read_very_eager()
                
            output = response.decode('ascii', errors='ignore')
            
            self.command_output.emit(f"命令执行结果: {output}")
            return output
        except Exception as e:
            self.command_output.emit(f"执行命令 {command} 失败: {str(e)}")
            return ""

# 网络设备配置类
class NetworkDeviceConfig(QObject):
    config_status = pyqtSignal(str, bool)  # 配置状态信号(消息, 成功/失败)
    command_output = pyqtSignal(str)  # 命令输出信号
    configuration_completed = pyqtSignal(bool, str)  # 配置完成信号(成功/失败, 消息)
    
    def __init__(self, ip, username, password, device_name=""):
        super().__init__()
        self.device_info = {
            'ip': ip,
            'username': username,
            'password': password,
            'device_name': device_name
        }
        self.tn = None
        # 获取线程工厂实例
        self.thread_factory = ThreadFactory.get_instance()
        # 设置超时
        self.timeout = 10
        # 子接口计数器初始化
        self.subif_counters = {
            "10.1.200.1": 100,
            "10.1.18.1": 100
        }
        # 初始化日志
        self.log(f"初始化网络设备配置 - 设备: {device_name}, IP: {ip}")
    
    def log(self, message):
        """记录日志并发送信号"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] {message}"
        print(log_message)
        self.command_output.emit(log_message)
    
    def connect(self):
        """设备连接方法"""
        try:
            # 增加超时时间
            self.timeout = 30
            self.tn = telnetlib.Telnet(self.device_info['ip'], timeout=self.timeout)
            
            self.log(f"正在尝试连接 {self.device_info['ip']}...")
            
            # 等待用户名提示
            response = self.tn.read_until(b"Username:", timeout=10)
            self.log(f"收到提示: {response.decode('ascii', 'ignore')}")
            # 使用 1 作为用户名
            self.tn.write(b"1\r\n")
            
            # 等待密码提示
            response = self.tn.read_until(b"Password:", timeout=10)
            self.log(f"收到提示: {response.decode('ascii', 'ignore')}")
            # 使用 1 作为密码
            self.tn.write(b"1\r\n")
            
            # 等待登录成功提示 (等待更长时间)
            response = self.tn.read_until(b">", timeout=15)
            login_result = response.decode('ascii', errors='ignore')
            self.log(f"登录结果: {login_result}")
            
            self.log(f"成功连接到设备 {self.device_info['ip']}")
            return True

        except Exception as e:
            self.log(f"连接错误: {str(e)}")
            raise

    def send_command(self, cmd, wait_time=1):
        """命令发送方法"""
        try:
            if not hasattr(self, 'tn') or not self.tn:
                raise ConnectionError("未连接到设备")
                
            self.log(f"发送命令: {cmd}")
            self.tn.write(cmd.encode('ascii') + b"\r\n")
            
            # 增加等待时间，确保命令完全执行
            time.sleep(wait_time * 2)
            
            # 等待更长时间获取响应，支持多种提示符
            pattern_list = [b">", b"#", b"]"]
            
            # 使用expect方法，增加超时时间
            index, match, response = self.tn.expect(pattern_list, timeout=20)
            
            if index == -1:
                self.log("命令等待超时，尝试读取可用数据")
                # 如果超时，尝试读取缓冲区中的所有数据
                response = self.tn.read_very_eager()
                
            output = response.decode('ascii', 'ignore')
            
            # 记录命令输出（如果输出很长，可能需要适当截断）
            if len(output) > 500:
                self.log(f"命令输出 (已截断): {output[:500]}...")
            else:
                self.log(f"命令输出: {output}")
            
            return output
        except Exception as e:
            error_msg = f"命令执行失败: {str(e)}"
            self.log(error_msg)
            raise

    def configure_device(self, config_params):
        """统一配置方法"""
        # 使用线程工厂创建线程执行配置
        self.thread_factory.start_thread(
            target=self._configure_device_thread,
            args=(config_params,),
            name=f"VPNConfig-{self.device_info['ip']}",
            module="VPN部署模块"
        )
        return True

    def _configure_device_thread(self, config_params):
        """在线程中执行设备配置"""
        success = False
        message = ""
        try:
            self.log("开始配置设备，正在连接...")
            self.connect()
            self.log(f"连接成功，开始配置VPN实例 {config_params['vpn_name']} 和子接口")

            subif_num = self.subif_counters[self.device_info['ip']]
            self.subif_counters[self.device_info['ip']] += 10  # 递增计数器

            # 创建VPN实例
            self.log(f"步骤1: 创建VPN实例 {config_params['vpn_name']}")
            self._create_vpn_instance(config_params)
            
            # 配置子接口
            self.log(f"步骤2: 配置子接口")
            self._configure_subinterface(config_params, subif_num)
            
            # 保存配置
            self.log(f"步骤3: 保存配置")
            self._save_config()
            
            success = True
            message = "VPN配置成功完成"
            self.log(message)

        except Exception as e:
            message = f"配置设备 {self.device_info['ip']} 失败: {str(e)}"
            self.log(message)
            import traceback
            tb = traceback.format_exc()
            self.log(f"错误详情:\n{tb}")
            success = False
        finally:
            try:
                if hasattr(self, 'tn') and self.tn:
                    self.log("关闭设备连接")
                    self.tn.close()
            except Exception as e:
                self.log(f"关闭连接时出错: {str(e)}")
                
            # 发送配置完成信号
            self.configuration_completed.emit(success, message)

    def _create_vpn_instance(self, params):
        """创建VPN实例"""
        cmds = [
            "system-view",
            f"ip vpn-instance {params['vpn_name']}",
            "ipv4-family",
            f"route-distinguisher {params['rd']}",
            f"vpn-target {params['rt']} both",
            "quit",
            "quit"
        ]

        self.log(f"正在创建VPN实例 {params['vpn_name']}")
        for cmd in cmds:
            self.send_command(cmd, 1)

    def _configure_subinterface(self, params, subif_num):
        """配置子接口"""
        if self.device_info['ip'] == "10.1.200.1":
            base_interface = "GigabitEthernet0/0/1"
        else:
            base_interface = "GigabitEthernet0/0/0"

        subif_name = f"{base_interface}.{subif_num}"

        cmds = [
            "system-view",
            f"interface {subif_name}",
            f"dot1q termination vid {params['vlan']}",
            f"ip binding vpn-instance {params['vpn_name']}",
            f"ip address {params['ip_address']} {params['subnet_mask']}",
            "arp broadcast enable",
            "quit"
        ]

        self.log(f"正在配置子接口 {subif_name}")
        for cmd in cmds:
            self.send_command(cmd, 1)

    def _save_config(self):
        """保存配置"""
        self.send_command("return")
        save_output = self.send_command("save", 3)
        if "Are you sure" in save_output:
            self.send_command("n", 5)
        self.log(f"{self.device_info['ip']} 配置已保存")

