#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
DHCP配置模块 - 提供DHCP配置能力的适配器
作为设备管理器和DHCPConfigurator之间的桥梁
"""

from .dhcp_configuration import DHCPConfigurator

class DHCPConfig:
    """DHCP配置适配器类"""
    
    def __init__(self):
        """初始化DHCP配置适配器"""
        self.configurator = None
    
    def configure_dhcp(self, device_ip, configs, debug=False, use_test_device=False):
        """配置DHCP
        
        参数:
            device_ip (str): 设备IP地址
            configs (dict): DHCP配置参数
            debug (bool): 是否开启调试模式
            use_test_device (bool): 是否使用测试设备
            
        返回:
            bool: 是否成功
        """
        try:
            print(f"=========================================")
            print(f"DHCP配置开始: 设备={device_ip}, 调试模式={'开启' if debug else '关闭'}, 测试设备={'启用' if use_test_device else '禁用'}")
            print(f"配置参数: {configs}")
            print(f"=========================================")
            
            # 获取参数
            pool_name = configs.get('pool_name')
            network = configs.get('network')
            gateway = configs.get('gateway')
            dns = configs.get('dns')
            domain = configs.get('domain')
            lease_time = configs.get('lease_days', 1)  # 默认1天
            
            # 检查必要参数
            if not pool_name or not network:
                print(f"[ERROR] 缺少必要参数: pool_name={pool_name}, network={network}")
                return False
                
            # 初始化configurator
            if self.configurator is None:
                # 如果使用测试设备模式，导入测试设备模块
                if use_test_device:
                    from .test_device import FakeDevice, patch_netmiko
                    print("[TEST] 使用测试设备模式，替换netmiko连接")
                    # 替换netmiko连接处理器
                    original_handler = patch_netmiko()
                    
                    # 使用测试设备模式创建配置器
                    self.configurator = DHCPConfigurator('huawei_telnet', ip=device_ip)
                    
                    # 配置DHCP
                    result = self.configurator.configure_dhcp(
                        pool_name=pool_name,
                        network=network,
                        gateway=gateway,
                        dns=dns,
                        lease_time=lease_time,
                        debug=debug
                    )
                    
                    # 恢复原始连接处理器
                    from .test_device import unpatch_netmiko
                    unpatch_netmiko(original_handler)
                    
                    return result
                else:
                    # 正常模式创建配置器
                    self.configurator = DHCPConfigurator('huawei_telnet', ip=device_ip)
                    
            # 常规模式配置DHCP
            return self.configurator.configure_dhcp(
                pool_name=pool_name,
                network=network,
                gateway=gateway,
                dns=dns,
                lease_time=lease_time,
                debug=debug
            )
                
        except Exception as e:
            import traceback
            print(f"[ERROR] DHCP配置失败: {str(e)}")
            traceback.print_exc()
            return False 