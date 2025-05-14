# vpn_service.py
import sys
import os
from pathlib import Path

# 添加模块路径
sys.path.append(str(Path(__file__).parent.parent.parent))
from modules.vpn_deploy.vpn_deploy import NetworkDeviceConfig


class VPNService:
    """VPN配置服务类，作为GUI和网络设备配置之间的桥梁"""
    
    def __init__(self):
        # 设备IP地址映射
        self.device_map = {
            "地域1出口路由器": "10.1.200.1",
            "地域2出口路由器": "10.1.18.1"
        }
        
        # 设备凭据 - 应该从配置或安全存储中获取
        self.credentials = {
            "10.1.200.1": {"username": "1", "password": "1"},
            "10.1.18.1": {"username": "1", "password": "1"}
        }
        
    def configure_vpn(self, device_name, vpn_config, output_callback=None):
        """
        配置VPN实例和接口
        
        参数:
            device_name (str): 设备名称
            vpn_config (dict): VPN配置参数，包含以下键:
                - vpn_name: VPN实例名称
                - vlan: VLAN ID
                - rt: Route Target
                - rd: Route Distinguisher
                - ip_address: IP地址
                - subnet_mask: 子网掩码
            output_callback (function): 可选的回调函数，用于接收命令输出
                
        返回:
            tuple: (成功标志, 消息)
        """
        try:
            # 获取设备IP
            device_ip = self._get_device_ip(device_name)
            if not device_ip:
                return False, f"未知设备: {device_name}"
            
            # 获取设备凭据
            credentials = self.credentials.get(device_ip, {"username": "1", "password": "1"})
            
            # 验证配置参数
            if not self._validate_config(vpn_config):
                return False, "配置参数无效"
            
            # 创建设备配置实例 - 确保传递所有必要参数
            device = NetworkDeviceConfig(
                ip=device_ip,
                username=credentials["username"],
                password=credentials["password"],
                device_name=device_name
            )
            
            # 如果提供了输出回调，连接命令输出信号
            if output_callback is not None:
                device.command_output.connect(output_callback)
            
            # 配置完成结果变量
            from PyQt5.QtCore import QEventLoop, QTimer
            
            # 创建事件循环等待配置完成
            loop = QEventLoop()
            result = [False, "配置超时"]
            
            # 连接配置完成信号
            def on_config_completed(success, message):
                nonlocal result
                result = [success, message]
                # 退出事件循环
                loop.quit()
                
            # 设置配置超时
            timer = QTimer()
            timer.setSingleShot(True)
            timer.timeout.connect(loop.quit)
            
            # 连接信号并启动超时计时器
            device.configuration_completed.connect(on_config_completed)
            
            # 执行配置
            device.configure_device(vpn_config)
            
            # 启动超时计时器（120秒超时）
            timer.start(120000)
            
            # 等待配置完成或超时
            loop.exec_()
            
            # 停止计时器
            timer.stop()
            
            # 断开信号连接
            device.configuration_completed.disconnect(on_config_completed)
            if output_callback is not None:
                try:
                    device.command_output.disconnect(output_callback)
                except:
                    pass
            
            # 返回配置结果
            return result[0], result[1]
            
        except Exception as e:
            return False, f"配置失败: {str(e)}"
    
    def _get_device_ip(self, device_name):
        """根据设备名称获取IP地址"""
        for name, ip in self.device_map.items():
            if name in device_name:
                return ip
        return None
    
    def _validate_config(self, config):
        """验证配置参数"""
        required_keys = ['vpn_name', 'vlan', 'rt', 'rd', 'ip_address', 'subnet_mask']
        
        # 检查必要的键是否存在
        if not all(key in config for key in required_keys):
            return False
            
        # 检查值是否为空
        if not all(config[key] for key in required_keys):
            return False
            
        # VLAN ID验证
        try:
            vlan = int(config['vlan'])
            if not 2 <= vlan <= 4094:
                return False
        except ValueError:
            return False
            
        # RT/RD格式验证
        if ':' not in config['rt'] or ':' not in config['rd']:
            return False
            
        return True