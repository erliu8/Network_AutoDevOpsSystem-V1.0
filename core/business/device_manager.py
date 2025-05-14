#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PyQt5.QtCore import QObject, pyqtSignal
import importlib
import sys
import os

# 导入线程工厂
from core.business.thread_factory import ThreadFactory

class DeviceManager(QObject):
    """设备管理业务类 - 整合所有网络配置模块的操作"""
    
    # 定义信号
    operation_status = pyqtSignal(bool, str)  # 操作状态信号(成功/失败, 消息)
    operation_log = pyqtSignal(str)  # 操作日志信号
    
    def __init__(self):
        super().__init__()
        self.thread_factory = ThreadFactory.get_instance()
        
        # 存储各种配置对象
        self._config_operators = {}
        self._monitor_operators = {}
        
        # 初始化模块映射表 - 用于记录模块和类的对应关系
        self._module_map = {
            # 批量地址配置
            'batch_address': {
                'module_path': 'modules.Batch_configuration_of_addresses.batch_config',
                'class_name': 'BatchConfig'
            },
            # DHCP配置
            'dhcp': {
                'module_path': 'modules.dhcp_configuration.dhcp_config',
                'class_name': 'DHCPConfig'
            },
            # 路由配置
            'route': {
                'module_path': 'modules.route_configuration.route_config',
                'class_name': 'RouteConfig'
            },
            # ACL/NAT/生成树配置
            'acl_nat_stp': {
                'module_path': 'modules.acl_nat_spanning_tree_configuration.acl_nat_spanning_tree_configuration',
                'class_name': 'ConfigOperator'
            },
            # VPN部署
            'vpn': {
                'module_path': 'modules.vpn_deploy.vpn_config',
                'class_name': 'VPNConfig'
            },
            # 网络监控
            'network_monitor': {
                'module_path': 'modules.network_monitor.network_monitor',
                'class_name': 'NetworkMonitor'
            },
            # 流量监控
            'traffic_monitor': {
                'module_path': 'modules.internet_traffic_monitor.internet_traffic_monitor',
                'class_name': 'ENSPMonitor'
            }
        }
    
    def _load_module(self, module_type):
        """动态加载模块
        
        参数:
            module_type: 模块类型，例如'batch_address', 'dhcp'等
            
        返回:
            加载的类，如果失败则返回None
        """
        if module_type not in self._module_map:
            self.operation_log.emit(f"错误: 未知的模块类型 '{module_type}'")
            return None
            
        try:
            module_info = self._module_map[module_type]
            module = importlib.import_module(module_info['module_path'])
            class_obj = getattr(module, module_info['class_name'])
            self.operation_log.emit(f"成功加载模块: {module_type}")
            return class_obj
        except Exception as e:
            self.operation_log.emit(f"加载模块 '{module_type}' 失败: {str(e)}")
            return None
    
    def _get_config_operator(self, module_type, device_ip, username=None, password=None):
        """获取或创建配置操作对象
        
        参数:
            module_type: 模块类型，例如'batch_address', 'dhcp'等
            device_ip: 设备IP地址
            username: 用户名，可选
            password: 密码，可选
            
        返回:
            配置操作对象，如果失败则返回None
        """
        key = f"{module_type}_{device_ip}"
        
        # 如果已存在配置操作对象，直接返回
        if key in self._config_operators:
            return self._config_operators[key]
            
        # 动态加载模块
        class_obj = self._load_module(module_type)
        if not class_obj:
            return None
            
        try:
            # 根据不同模块创建不同的配置操作对象
            if module_type in ['acl_nat_stp', 'network_monitor', 'traffic_monitor']:
                # 这些模块需要设备IP、用户名和密码
                # 如果用户名和密码未提供，使用默认值"1"
                username = username or "1"
                password = password or "1"
                operator = class_obj(device_ip, username, password)
            else:
                # 其他模块可能有不同的初始化参数
                operator = class_obj()
                
            # 如果对象有connect_signals方法，连接信号
            if hasattr(operator, 'connect_signals'):
                operator.connect_signals(self._forward_signals)
                
            # 保存配置操作对象
            self._config_operators[key] = operator
            return operator
        except Exception as e:
            self.operation_log.emit(f"创建 {module_type} 操作对象失败: {str(e)}")
            return None
    
    def _forward_signals(self, signal_name, *args):
        """转发模块信号
        
        参数:
            signal_name: 信号名称
            args: 信号参数
        """
        if signal_name == 'status':
            self.operation_status.emit(*args)
        elif signal_name == 'log':
            self.operation_log.emit(*args)
    
    # ======== 批量地址配置 ========
    
    def batch_configure_addresses(self, devices, vlan_configs):
        """批量配置设备地址
        
        参数:
            devices: 设备列表，每个设备包含ip, username, password等信息
            vlan_configs: VLAN配置列表
        """
        self.operation_log.emit("开始批量配置设备地址...")
        
        # 获取批量地址配置操作对象
        batch_config = self._get_config_operator('batch_address', 'common')
        if not batch_config:
            self.operation_status.emit(False, "无法创建批量地址配置操作对象")
            return
            
        # 使用线程工厂创建线程执行批量配置
        self.thread_factory.start_thread(
            target=self._batch_configure_thread,
            args=(batch_config, devices, vlan_configs),
            name="BatchAddressConfig",
            module="批量地址配置"
        )
    
    def _batch_configure_thread(self, batch_config, devices, vlan_configs):
        """在线程中执行批量配置
        
        参数:
            batch_config: 批量配置对象
            devices: 设备列表
            vlan_configs: VLAN配置列表
        """
        try:
            success = batch_config.configure_all_devices(devices, vlan_configs)
            self.operation_status.emit(success, "批量配置设备地址" + ("成功" if success else "失败"))
        except Exception as e:
            self.operation_log.emit(f"批量配置过程出错: {str(e)}")
            self.operation_status.emit(False, f"批量配置设备地址失败: {str(e)}")
    
    # ======== DHCP配置 ========
    
    def configure_dhcp(self, device_ip, username, password, dhcp_configs, use_test_device=False):
        """配置DHCP
        
        参数:
            device_ip: 设备IP地址
            username: 用户名
            password: 密码
            dhcp_configs: DHCP配置信息
            use_test_device: 是否使用测试设备，默认False
        """
        self.operation_log.emit(f"开始配置DHCP，设备: {device_ip}...")
        
        # 获取DHCP配置操作对象
        dhcp_operator = self._get_config_operator('dhcp', device_ip, username, password)
        if not dhcp_operator:
            self.operation_status.emit(False, "无法创建DHCP配置操作对象")
            return
            
        # 使用线程工厂创建线程执行DHCP配置
        self.thread_factory.start_thread(
            target=self._configure_dhcp_thread,
            args=(dhcp_operator, device_ip, dhcp_configs, use_test_device),
            name=f"DHCPConfig_{device_ip}",
            module="DHCP配置"
        )
    
    def _configure_dhcp_thread(self, dhcp_operator, device_ip, dhcp_configs, use_test_device=False):
        """在线程中执行DHCP配置
        
        参数:
            dhcp_operator: DHCP配置操作对象
            device_ip: 设备IP地址
            dhcp_configs: DHCP配置信息
            use_test_device: 是否使用测试设备模式
        """
        try:
            # 确保从dhcp_configs中获取debug参数
            debug_mode = dhcp_configs.get('debug', False)
            self.operation_log.emit(f"配置DHCP，调试模式: {'开启' if debug_mode else '关闭'}, 测试设备模式: {'开启' if use_test_device else '关闭'}")
            
            # 确保正确传递所有参数，包括debug参数和use_test_device参数
            success = dhcp_operator.configure_dhcp(
                device_ip, 
                dhcp_configs,
                debug=debug_mode,  # 明确传递debug参数
                use_test_device=use_test_device  # 明确传递测试设备模式参数
            )
            self.operation_status.emit(success, "配置DHCP")
            return success
            
        except Exception as e:
            error_msg = f"配置DHCP时出错: {str(e)}"
            print(f"[ERROR] {error_msg}")
            self.operation_log.emit(error_msg)
            self.operation_status.emit(False, "配置DHCP")
            return False
    
    # ======== 路由配置 ========
    
    def configure_route(self, device_ip, username, password, route_configs):
        """配置路由
        
        参数:
            device_ip: 设备IP地址
            username: 用户名
            password: 密码
            route_configs: 路由配置信息
        """
        self.operation_log.emit(f"开始配置路由，设备: {device_ip}...")
        
        # 获取路由配置操作对象
        route_operator = self._get_config_operator('route', device_ip, username, password)
        if not route_operator:
            self.operation_status.emit(False, "无法创建路由配置操作对象")
            return
            
        # 使用线程工厂创建线程执行路由配置
        self.thread_factory.start_thread(
            target=self._configure_route_thread,
            args=(route_operator, device_ip, route_configs),
            name=f"RouteConfig_{device_ip}",
            module="路由配置"
        )
    
    def _configure_route_thread(self, route_operator, device_ip, route_configs):
        """在线程中执行路由配置
        
        参数:
            route_operator: 路由配置操作对象
            device_ip: 设备IP地址
            route_configs: 路由配置信息
        """
        try:
            success = route_operator.configure_route(device_ip, route_configs)
            self.operation_status.emit(success, "配置路由" + ("成功" if success else "失败"))
        except Exception as e:
            self.operation_log.emit(f"路由配置过程出错: {str(e)}")
            self.operation_status.emit(False, f"配置路由失败: {str(e)}")
    
    # ======== ACL/NAT/生成树配置 ========
    
    def configure_acl(self, device_ip, username, password, acl_configs):
        """配置ACL
        
        参数:
            device_ip: 设备IP地址
            username: 用户名
            password: 密码
            acl_configs: ACL配置信息，包含acl_number, rule_number, action, source等
        """
        self.operation_log.emit(f"开始配置ACL，设备: {device_ip}...")
        
        # 获取ACL/NAT/STP配置操作对象
        config_operator = self._get_config_operator('acl_nat_stp', device_ip, username, password)
        if not config_operator:
            self.operation_status.emit(False, "无法创建ACL配置操作对象")
            return
            
        # 连接信号
        config_operator.config_status.connect(
            lambda success, msg: self.operation_status.emit(success, msg)
        )
        config_operator.command_output.connect(
            lambda msg: self.operation_log.emit(msg)
        )
        
        # 配置ACL
        config_operator.add_acl_rule(
            acl_number=acl_configs.get('acl_number'),
            rule_number=acl_configs.get('rule_number'),
            action=acl_configs.get('action'),
            source=acl_configs.get('source'),
            dest=acl_configs.get('dest'),
            protocol=acl_configs.get('protocol'),
            port=acl_configs.get('port')
        )
    
    def configure_nat(self, device_ip, username, password, nat_configs):
        """配置NAT
        
        参数:
            device_ip: 设备IP地址
            username: 用户名
            password: 密码
            nat_configs: NAT配置信息，包含nat_type, inside_interface, outside_interface等
        """
        self.operation_log.emit(f"开始配置NAT，设备: {device_ip}...")
        
        # 获取ACL/NAT/STP配置操作对象
        config_operator = self._get_config_operator('acl_nat_stp', device_ip, username, password)
        if not config_operator:
            self.operation_status.emit(False, "无法创建NAT配置操作对象")
            return
            
        # 连接信号
        config_operator.config_status.connect(
            lambda success, msg: self.operation_status.emit(success, msg)
        )
        config_operator.command_output.connect(
            lambda msg: self.operation_log.emit(msg)
        )
        
        # 配置NAT
        config_operator.configure_nat(
            nat_type=nat_configs.get('nat_type'),
            inside_interface=nat_configs.get('inside_interface'),
            outside_interface=nat_configs.get('outside_interface'),
            nat_params=nat_configs.get('nat_params'),
            force_clear=nat_configs.get('force_clear', False)
        )
    
    def configure_stp(self, device_ip, username, password, stp_configs):
        """配置生成树
        
        参数:
            device_ip: 设备IP地址
            username: 用户名
            password: 密码
            stp_configs: STP配置信息，包含mode, priority, forward_time等
        """
        self.operation_log.emit(f"开始配置生成树，设备: {device_ip}...")
        
        # 获取ACL/NAT/STP配置操作对象
        config_operator = self._get_config_operator('acl_nat_stp', device_ip, username, password)
        if not config_operator:
            self.operation_status.emit(False, "无法创建STP配置操作对象")
            return
            
        # 连接信号
        config_operator.config_status.connect(
            lambda success, msg: self.operation_status.emit(success, msg)
        )
        config_operator.command_output.connect(
            lambda msg: self.operation_log.emit(msg)
        )
        
        # 配置全局STP
        config_operator.configure_stp_global(
            mode=stp_configs.get('mode'),
            priority=stp_configs.get('priority'),
            forward_time=stp_configs.get('forward_time'),
            hello_time=stp_configs.get('hello_time'),
            max_age=stp_configs.get('max_age'),
            mstp_params=stp_configs.get('mstp_params')
        )
        
        # 如果有接口STP配置，配置接口STP
        interface_stp = stp_configs.get('interface_stp')
        if interface_stp:
            config_operator.configure_stp_interface(
                interface=interface_stp.get('interface'),
                port_priority=interface_stp.get('port_priority'),
                port_cost=interface_stp.get('port_cost'),
                edge_port=interface_stp.get('edge_port'),
                bpdu_guard=interface_stp.get('bpdu_guard'),
                root_guard=interface_stp.get('root_guard')
            )
    
    # ======== VPN配置 ========
    
    def configure_vpn(self, device_ip, username, password, vpn_configs):
        """配置VPN
        
        参数:
            device_ip: 设备IP地址
            username: 用户名
            password: 密码
            vpn_configs: VPN配置信息
        """
        self.operation_log.emit(f"开始配置VPN，设备: {device_ip}...")
        
        # 获取VPN配置操作对象
        vpn_operator = self._get_config_operator('vpn', device_ip, username, password)
        if not vpn_operator:
            self.operation_status.emit(False, "无法创建VPN配置操作对象")
            return
            
        # 使用线程工厂创建线程执行VPN配置
        self.thread_factory.start_thread(
            target=self._configure_vpn_thread,
            args=(vpn_operator, device_ip, vpn_configs),
            name=f"VPNConfig_{device_ip}",
            module="VPN配置"
        )
    
    def _configure_vpn_thread(self, vpn_operator, device_ip, vpn_configs):
        """在线程中执行VPN配置
        
        参数:
            vpn_operator: VPN配置操作对象
            device_ip: 设备IP地址
            vpn_configs: VPN配置信息
        """
        try:
            success = vpn_operator.configure_vpn(device_ip, vpn_configs)
            self.operation_status.emit(success, "配置VPN" + ("成功" if success else "失败"))
        except Exception as e:
            self.operation_log.emit(f"VPN配置过程出错: {str(e)}")
            self.operation_status.emit(False, f"配置VPN失败: {str(e)}")
    
    # ======== 网络监控 ========
    
    def start_network_monitor(self, device_ip, username, password, monitor_interval=30):
        """启动网络监控
        
        参数:
            device_ip: 设备IP地址
            username: 用户名
            password: 密码
            monitor_interval: 监控间隔(秒)
        """
        self.operation_log.emit(f"启动网络监控，设备: {device_ip}...")
        
        # 获取网络监控操作对象
        monitor = self._get_config_operator('network_monitor', device_ip, username, password)
        if not monitor:
            self.operation_status.emit(False, "无法创建网络监控对象")
            return
            
        # 连接信号
        if hasattr(monitor, 'monitor_status'):
            monitor.monitor_status.connect(
                lambda success, msg: self.operation_status.emit(success, msg)
            )
        if hasattr(monitor, 'monitor_data'):
            monitor.monitor_data.connect(
                lambda data: self.operation_log.emit(f"监控数据: {data}")
            )
            
        # 启动监控
        monitor.start_monitor(interval=monitor_interval)
        self.operation_status.emit(True, f"已启动对设备 {device_ip} 的监控")
    
    def stop_network_monitor(self, device_ip):
        """停止网络监控
        
        参数:
            device_ip: 设备IP地址
        """
        key = f"network_monitor_{device_ip}"
        if key in self._config_operators:
            monitor = self._config_operators[key]
            if hasattr(monitor, 'stop_monitor'):
                monitor.stop_monitor()
                self.operation_log.emit(f"已停止对设备 {device_ip} 的监控")
                self.operation_status.emit(True, f"已停止对设备 {device_ip} 的监控")
    
    # ======== 流量监控 ========
    
    def start_traffic_monitor(self, device_ip, username=None, password=None, interfaces=None, monitor_interval=5):
        """启动流量监控
        
        参数:
            device_ip: 设备IP地址
            username: 用户名，可选，默认为"1"
            password: 密码，可选，默认为"1"
            interfaces: 要监控的接口列表，可选
            monitor_interval: 监控间隔（秒），默认5秒
        """
        self.operation_log.emit(f"开始流量监控，设备: {device_ip}...")
        
        # 获取流量监控操作对象
        monitor = self._get_config_operator('traffic_monitor', device_ip, username, password)
        if not monitor:
            self.operation_status.emit(False, "无法创建流量监控操作对象")
            return False
        
        try:
            # 连接设备
            if not monitor.connect_device():
                self.operation_status.emit(False, f"连接设备 {device_ip} 失败")
                return False
            
            # 启动监控
            success = monitor.start_monitoring()
            if success:
                self.operation_log.emit(f"流量监控已启动: {device_ip}")
                self.operation_status.emit(True, "启动流量监控成功")
            else:
                self.operation_log.emit(f"启动流量监控失败: {device_ip}")
                self.operation_status.emit(False, "启动流量监控失败")
            
            return success
        except Exception as e:
            self.operation_log.emit(f"启动流量监控时出错: {str(e)}")
            self.operation_status.emit(False, f"启动流量监控失败: {str(e)}")
            return False
    
    def stop_traffic_monitor(self, device_ip):
        """停止流量监控
        
        参数:
            device_ip: 设备IP地址
        """
        key = f"traffic_monitor_{device_ip}"
        if key in self._config_operators:
            try:
                monitor = self._config_operators[key]
                monitor.stop_monitoring()
                del self._config_operators[key]
                self.operation_log.emit(f"已停止设备 {device_ip} 的流量监控")
                self.operation_status.emit(True, "停止流量监控成功")
                return True
            except Exception as e:
                self.operation_log.emit(f"停止流量监控时出错: {str(e)}")
                self.operation_status.emit(False, f"停止流量监控失败: {str(e)}")
                return False
        else:
            self.operation_log.emit(f"设备 {device_ip} 未在监控中")
            return True
    
    # ======== 公共方法 ========
    
    def test_device_connection(self, device_ip, username, password):
        """测试设备连接
        
        参数:
            device_ip: 设备IP地址
            username: 用户名
            password: 密码
            
        返回:
            连接成功返回True，否则返回False
        """
        self.operation_log.emit(f"测试连接到设备 {device_ip}...")
        
        # 尝试创建ACL/NAT/STP配置操作对象并测试连接
        config_operator = self._get_config_operator('acl_nat_stp', device_ip, username, password)
        if not config_operator:
            self.operation_status.emit(False, f"无法创建配置操作对象，连接设备 {device_ip} 失败")
            return False
            
        result = config_operator.test_connection()
        status_msg = f"连接设备 {device_ip} " + ("成功" if result else "失败")
        self.operation_log.emit(status_msg)
        self.operation_status.emit(result, status_msg)
        
        return result
    
    def get_device_info(self, device_ip, username, password):
        """获取设备信息
        
        参数:
            device_ip: 设备IP地址
            username: 用户名
            password: 密码
            
        返回:
            设备信息字典
        """
        self.operation_log.emit(f"获取设备 {device_ip} 的信息...")
        
        # 获取查询设备信息的操作对象
        query_operator = self._get_config_operator('network_monitor', device_ip, username, password)
        if not query_operator:
            self.operation_status.emit(False, "无法创建设备查询对象")
            return None
            
        # 使用线程工厂创建线程获取设备信息
        self.thread_factory.start_thread(
            target=self._get_device_info_thread,
            args=(query_operator, device_ip),
            name=f"DeviceInfo_{device_ip}",
            module="设备信息查询"
        )
    
    def _get_device_info_thread(self, query_operator, device_ip):
        """在线程中获取设备信息
        
        参数:
            query_operator: 查询操作对象
            device_ip: 设备IP地址
        """
        try:
            device_info = query_operator.get_device_info()
            if device_info:
                self.operation_log.emit(f"设备 {device_ip} 信息: {device_info}")
                self.operation_status.emit(True, f"成功获取设备 {device_ip} 信息")
            else:
                self.operation_status.emit(False, f"获取设备 {device_ip} 信息失败")
        except Exception as e:
            self.operation_log.emit(f"获取设备信息过程出错: {str(e)}")
            self.operation_status.emit(False, f"获取设备 {device_ip} 信息失败: {str(e)}")

# 单例模式 - 获取DeviceManager实例
_device_manager_instance = None

def get_device_manager():
    """获取DeviceManager单例"""
    global _device_manager_instance
    if not _device_manager_instance:
        _device_manager_instance = DeviceManager()
    return _device_manager_instance
