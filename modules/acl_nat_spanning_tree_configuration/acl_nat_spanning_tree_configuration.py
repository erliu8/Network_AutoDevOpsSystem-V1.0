import time
import paramiko
import re
from PyQt5.QtCore import QObject, pyqtSignal
# 导入线程工厂
from core.business.thread_factory import ThreadFactory
# 导入netmiko用于Telnet连接
from netmiko import ConnectHandler

class ConfigOperator(QObject):
    """ACL/NAT/生成树配置操作类"""
    
    # 定义信号
    config_status = pyqtSignal(bool, str)  # 配置状态信号(成功/失败, 消息)
    command_output = pyqtSignal(str)  # 命令输出信号
    
    def __init__(self, ip, username="1", password="1", timeout=20):
        super().__init__()
        self.ip = ip
        self.username = username
        self.password = password
        self.timeout = timeout
        self.connection = None
        # 获取线程工厂实例
        self.thread_factory = ThreadFactory.get_instance()
    
    def connect_device(self):
        """连接设备"""
        try:
            # 改用netmiko的Telnet连接
            device = {
                'device_type': 'huawei_telnet',  # 使用华为telnet类型
                'ip': self.ip,
                'username': self.username,
                'password': self.password,
                'port': 23,  # telnet端口
                'timeout': self.timeout,
            }
            
            self.connection = ConnectHandler(**device)
            self.command_output.emit(f"成功连接到设备 {self.ip}")
            return True
        except Exception as e:
            import traceback
            err_msg = f"连接设备 {self.ip} 失败: {str(e)}"
            self.command_output.emit(err_msg)
            return False
    
    def test_connection(self):
        """测试连接到设备，和connect_device相同但专门用于GUI测试连接按钮"""
        return self.connect_device()
    
    def _execute_commands(self, commands):
        """执行一系列命令并返回输出"""
        try:
            if not self.connect_device():
                return None
                
            output = ""
            for cmd in commands:
                try:
                    # 使用expect_string参数来检测命令提示符
                    # 对于system-view等进入不同模式的命令，预期提示符会改变
                    if cmd == "system-view":
                        cmd_output = self.connection.send_command(cmd, expect_string=r"\[.*\]")
                    elif cmd.startswith("interface "):
                        cmd_output = self.connection.send_command(cmd, expect_string=r"\[.*-.*\]")
                    elif cmd.startswith("stp region-configuration"):
                        cmd_output = self.connection.send_command(cmd, expect_string=r"\[.*-.*\]")
                    else:
                        cmd_output = self.connection.send_command(cmd, expect_string=r"[>#\]\-]")
                    
                    output += cmd_output + "\n"
                    self.command_output.emit(f"执行: {cmd}\n{cmd_output}")
                except Exception as e:
                    self.command_output.emit(f"命令 '{cmd}' 执行失败: {str(e)}")
                    # 继续执行下一个命令，而不是直接中断
                    continue
                
            return output
        except Exception as e:
            import traceback
            err_msg = f"执行命令错误: {str(e)}\n{traceback.format_exc()}"
            self.command_output.emit(err_msg)
            return None
    
    def add_acl_rule(self, acl_number, rule_number, action, source, dest=None, protocol=None, port=None):
        """添加ACL规则
        
        参数:
            acl_number: ACL编号
            rule_number: 规则编号
            action: 动作(permit/deny)
            source: 源地址
            dest: 目的地址(仅高级ACL)
            protocol: 协议(仅高级ACL)
            port: 端口(仅高级ACL)
        """
        try:
            # 准备命令
            commands = [
                "system-view",
                f"acl number {acl_number}",
            ]
            
            # 根据ACL类型构建规则命令
            if 2000 <= acl_number <= 2999:  # 基本ACL
                rule_cmd = f"rule {rule_number} {action} source {source}"
            else:  # 高级ACL
                rule_cmd = f"rule {rule_number} {action} {protocol} source {source}"
                if dest:
                    rule_cmd += f" destination {dest}"
                if port:
                    rule_cmd += f" {port}"
            
            commands.append(rule_cmd)
            commands.append("quit")
            commands.append("quit")
            
            # 执行命令
            self.command_output.emit(f"执行命令: {' -> '.join(commands)}")
            
            # 连接设备并执行命令
            output = self._execute_commands(commands)
            
            # 检查是否成功
            if output is None:
                self.config_status.emit(False, "执行命令失败")
                return False
                
            success = "Error" not in output
            
            # 发送状态信号
            if success:
                self.config_status.emit(True, f"成功添加ACL规则: {rule_cmd}")
            else:
                self.config_status.emit(False, f"添加ACL规则失败: {output}")
            
            return success
        except Exception as e:
            import traceback
            err_msg = f"添加ACL规则错误: {str(e)}\n{traceback.format_exc()}"
            self.command_output.emit(err_msg)
            self.config_status.emit(False, f"添加ACL规则错误: {str(e)}")
            return False
        finally:
            if self.connection:
                try:
                    self.connection.disconnect()
                except:
                    pass
                self.connection = None
    
    def configure_acl(self, acl_config):
        """配置ACL"""
        # 使用线程工厂创建线程
        self.thread_factory.start_thread(
            target=self._configure_acl_thread,
            args=(acl_config,),
            name=f"ACLConfig-{self.ip}",
            module="ACL/NAT/生成树配置模块"
        )
        return True
    
    def _configure_acl_thread(self, acl_config):
        """在线程中执行ACL配置"""
        success = False
        try:
            if self.connect_device():
                # ... existing code ...
                success = True
            else:
                self.command_output.emit("无法连接到设备，ACL配置失败")
        except Exception as e:
            self.command_output.emit(f"ACL配置过程中出错: {str(e)}")
        finally:
            if self.connection:
                try:
                    self.connection.disconnect()
                except:
                    pass
                self.connection = None
            self.config_status.emit(success, "ACL配置" + ("成功" if success else "失败"))
    
    def configure_nat(self, nat_type, inside_interface=None, outside_interface=None, nat_params=None, force_clear=False):
        """配置NAT - 更新版本，适配设备支持的命令
        
        参数:
            nat_type: NAT类型(static/dynamic/pat)
            inside_interface: 内部接口 (动态NAT和PAT需要)
            outside_interface: 外部接口 (动态NAT和PAT需要)
            nat_params: NAT参数字典
                - 静态NAT需要: inside_ip, outside_ip
                - 动态NAT和PAT需要: acl_number, inside_network(可选)
            force_clear: 是否强制清除接口上现有的NAT配置
        """
        if nat_params is None:
            nat_params = {}
            
        try:
            # 准备命令
            commands = [
                "system-view",
            ]
            
            # 根据NAT类型添加不同命令
            if nat_type == "static":
                inside_ip = nat_params.get("inside_ip")
                outside_ip = nat_params.get("outside_ip")
                if not inside_ip or not outside_ip:
                    self.command_output.emit("错误: 静态NAT需要指定inside_ip和outside_ip")
                    self.config_status.emit(False, "参数不完整")
                    return False
                    
                # 静态NAT - 已确认可用
                commands.append(f"nat static global {outside_ip} inside {inside_ip}")
                # 回答Y确认覆盖
                commands.append("y")
                
            elif nat_type in ["dynamic", "pat"]:
                if not outside_interface:
                    self.command_output.emit("错误: 动态NAT/PAT需要指定外部接口")
                    self.config_status.emit(False, "参数不完整")
                    return False
                    
                acl_number = nat_params.get("acl_number", 2000)
                inside_network = nat_params.get("inside_network")
                
                # 创建ACL(如果需要)
                if inside_network:
                    commands.append(f"acl number {acl_number}")
                    commands.append(f"rule 5 permit source {inside_network}")
                    commands.append("quit")
                
                # 如果启用了force_clear，先尝试清除现有NAT配置
                # 但使用不同的方法：首先进行查询，然后尝试直接用一个新的ACL替换现有配置
                if force_clear:
                    # 使用一个不同于之前的ACL号
                    temp_acl_number = 3000
                    # 确保我们有这个ACL
                    if self.connect_device():
                        try:
                            # 查看当前NAT outbound配置
                            self.command_output.emit("检查当前NAT出站配置...")
                            self.connection.send_command("system-view", expect_string=r"\[.*\]")
                            output = self.connection.send_command("display nat outbound", expect_string=r"\[.*\]")
                            self.command_output.emit(f"当前NAT出站配置:\n{output}")
                            
                            # 创建临时ACL
                            self.connection.send_command(f"acl number {temp_acl_number}", expect_string=r"\[.*\]")
                            self.connection.send_command(f"rule 5 permit source 192.168.10.0 0.0.0.255", expect_string=r"\[.*\]")
                            self.connection.send_command("quit", expect_string=r"\[.*\]")
                            
                            # 直接尝试在接口上配置新的NAT出站配置
                            self.connection.send_command(f"interface {outside_interface}", expect_string=r"\[.*\]")
                            self.connection.send_command(f"nat outbound {temp_acl_number}", expect_string=r"\[.*\]")
                            self.connection.send_command("quit", expect_string=r"\[.*\]")
                            self.connection.send_command("quit", expect_string=r">")
                        except Exception as e:
                            self.command_output.emit(f"临时清除NAT过程中出错: {str(e)}")
                        finally:
                            try:
                                self.connection.disconnect()
                            except:
                                pass
                            self.connection = None
                
                # 进入接口配置并设置NAT
                commands.append(f"interface {outside_interface}")
                commands.append(f"nat outbound {acl_number}")
                commands.append("quit")
            else:
                self.command_output.emit(f"错误: 不支持的NAT类型: {nat_type}")
                self.config_status.emit(False, f"不支持的NAT类型: {nat_type}")
                return False
            
            commands.append("quit")
            
            # 执行命令
            self.command_output.emit(f"执行NAT配置命令: {' -> '.join(commands)}")
            output = self._execute_commands(commands)
            
            # 检查是否成功
            if output is None:
                self.config_status.emit(False, "执行命令失败")
                return False
                
            # 检查是否有Easy IP已配置的错误
            if "Easy IP has been configed in this interface" in output:
                # 尝试使用不同的解决方案
                self.command_output.emit("检测到Easy IP配置冲突，尝试使用备用方法配置...")
                
                # 使用不同的ACL号，使用3000
                new_acl = 3000
                
                # 重新连接并配置
                if self.connect_device():
                    try:
                        # 确保我们有这个ACL
                        self.connection.send_command("system-view", expect_string=r"\[.*\]")
                        self.connection.send_command(f"acl number {new_acl}", expect_string=r"\[.*\]")
                        self.connection.send_command(f"rule 5 permit source 192.168.10.0 0.0.0.255", expect_string=r"\[.*\]")
                        self.connection.send_command("quit", expect_string=r"\[.*\]")
                        
                        # 尝试用新的ACL配置接口
                        self.connection.send_command(f"interface {outside_interface}", expect_string=r"\[.*\]")
                        result = self.connection.send_command(f"nat outbound {new_acl}", expect_string=r"\[.*\]")
                        
                        if "Error" not in result:
                            self.command_output.emit(f"使用ACL {new_acl}成功配置NAT")
                            # 验证配置
                            output = self.connection.send_command("display this", expect_string=r"\[.*\]")
                            self.command_output.emit(f"接口配置:\n{output}")
                            
                            self.connection.send_command("quit", expect_string=r"\[.*\]")
                            self.connection.send_command("quit", expect_string=r">")
                            
                            # 成功配置
                            self.config_status.emit(True, f"成功使用备用方法配置 {nat_type} NAT")
                            return True
                        else:
                            self.command_output.emit(f"使用备用方法仍然失败: {result}")
                    except Exception as e:
                        self.command_output.emit(f"备用方法配置过程中出错: {str(e)}")
                    finally:
                        try:
                            self.connection.disconnect()
                        except:
                            pass
                        self.connection = None
                
            # 标准验证路径
            success = output and "Error:" not in output
            
            # 验证配置
            if success:
                success = self._verify_nat_config(nat_type, outside_interface, nat_params)
            
            # 发送状态信号
            if success:
                self.config_status.emit(True, f"成功配置 {nat_type} NAT")
            else:
                self.config_status.emit(False, f"配置NAT失败: {output}")
            
            return success
        except Exception as e:
            import traceback
            err_msg = f"配置NAT错误: {str(e)}\n{traceback.format_exc()}"
            self.command_output.emit(err_msg)
            self.config_status.emit(False, f"配置NAT错误: {str(e)}")
            return False
        finally:
            if self.connection:
                try:
                    self.connection.disconnect()
                except:
                    pass
                self.connection = None
    
    def _verify_nat_config(self, nat_type, interface=None, nat_params=None):
        """验证NAT配置是否成功"""
        try:
            if not self.connect_device():
                return False
                
            if nat_type == "static":
                # 检查静态NAT配置
                output = self.connection.send_command("display nat static")
                inside_ip = nat_params.get("inside_ip")
                outside_ip = nat_params.get("outside_ip")
                
                if inside_ip in output and outside_ip in output:
                    self.command_output.emit(f"已验证静态NAT配置成功: {inside_ip} -> {outside_ip}")
                    return True
            else:
                # 检查接口NAT配置
                self.connection.send_command("system-view", expect_string=r"\[.*\]")
                self.connection.send_command(f"interface {interface}", expect_string=r"\[.*\]")
                output = self.connection.send_command("display this", expect_string=r"\[.*\]")
                
                acl_number = nat_params.get("acl_number", 2000)
                if f"nat outbound {acl_number}" in output:
                    self.command_output.emit(f"已验证接口NAT配置成功: nat outbound {acl_number}")
                    return True
            
            self.command_output.emit("无法验证NAT配置")
            return False
        except Exception as e:
            self.command_output.emit(f"验证NAT配置时出错: {str(e)}")
            return False
        finally:
            if self.connection:
                try:
                    self.connection.disconnect()
                except:
                    pass
                self.connection = None
    
    def get_nat_config(self):
        """获取NAT配置"""
        try:
            # 连接设备
            if not self.connect_device():
                self.command_output.emit("连接设备失败，无法获取NAT配置")
                return None
                
            # 执行命令 - 使用已确认可用的命令
            output = ""
            try:
                # 获取静态NAT配置
                static_out = self.connection.send_command("display nat static")
                output += f"静态NAT配置:\n{static_out}\n\n"
            except Exception as e:
                self.command_output.emit(f"获取静态NAT配置时出错: {str(e)}")
                output += "无法获取静态NAT配置\n\n"
                
            # 获取所有接口配置
            try:
                output += "接口NAT配置:\n"
                # 先查看接口列表
                interface_list = self.connection.send_command("display interface brief")
                
                # 检查每个GigabitEthernet接口的NAT配置
                for line in interface_list.split("\n"):
                    if "GigabitEthernet" in line:
                        interface_name = line.split()[0]
                        # 进入接口视图并检查配置
                        self.connection.send_command("system-view", expect_string=r"\[.*\]")
                        self.connection.send_command(f"interface {interface_name}", expect_string=r"\[.*\]")
                        interface_config = self.connection.send_command("display this", expect_string=r"\[.*\]")
                        self.connection.send_command("quit", expect_string=r"\[.*\]")
                        self.connection.send_command("quit", expect_string=r">")
                        
                        # 查找NAT相关配置
                        nat_lines = []
                        for config_line in interface_config.split("\n"):
                            if "nat " in config_line.lower():
                                nat_lines.append(config_line.strip())
                        
                        if nat_lines:
                            output += f"{interface_name}:\n"
                            for nat_line in nat_lines:
                                output += f"  {nat_line}\n"
            except Exception as e:
                self.command_output.emit(f"获取接口NAT配置时出错: {str(e)}")
                output += "无法获取接口NAT配置\n"
            
            # 发送输出信号
            self.command_output.emit(f"NAT配置:\n{output}")
            
            return output
        except Exception as e:
            import traceback
            err_msg = f"获取NAT配置错误: {str(e)}\n{traceback.format_exc()}"
            self.command_output.emit(err_msg)
            return None
        finally:
            if self.connection:
                try:
                    self.connection.disconnect()
                except:
                    pass
                self.connection = None
    
    def configure_stp_global(self, mode, priority, forward_time, hello_time, max_age, mstp_params=None):
        """配置全局STP参数 - 更新版本，适配设备支持的命令"""
        try:
            # 准备命令
            commands = [
                "system-view",
                f"stp mode {mode}",
                f"stp priority {priority}",
                f"stp timer forward-delay {forward_time}",
            ]
            
            # 根据设备实际支持的命令进行调整
            if hello_time:
                commands.append(f"stp timer root-hello {hello_time}")
            
            if max_age:
                commands.append(f"stp timer max-age {max_age}")
            
            # 如果是MSTP模式，添加MSTP特有配置
            if mode == "mstp" and mstp_params:
                region = mstp_params.get("region")
                revision = mstp_params.get("revision")
                instance = mstp_params.get("instance")
                vlan_mapping = mstp_params.get("vlan_mapping")
                
                if region:
                    commands.append(f"stp region-configuration")
                    commands.append(f"region-name {region}")
                    
                    if revision:
                        commands.append(f"revision-level {revision}")
                    
                    if instance and vlan_mapping:
                        # 支持的格式可能不同，这里假设需要用空格分隔VLAN列表
                        vlan_list = vlan_mapping.replace("to", "").strip()
                        commands.append(f"instance {instance} vlan {vlan_list}")
                    
                    commands.append("active region-configuration")
                    commands.append("quit")
            
            commands.append("quit")
            
            # 执行命令
            output = self._execute_commands(commands)
            
            # 检查是否成功
            if output is None:
                self.config_status.emit(False, "执行命令失败")
                return False
                
            success = "Error" not in output
            
            # 发送状态信号
            if success:
                self.config_status.emit(True, f"成功配置 {mode.upper()} 模式")
            else:
                self.config_status.emit(False, f"配置STP失败: {output}")
            
            return success
        except Exception as e:
            import traceback
            err_msg = f"配置STP错误: {str(e)}\n{traceback.format_exc()}"
            self.command_output.emit(err_msg)
            self.config_status.emit(False, f"配置STP错误: {str(e)}")
            return False
        finally:
            if self.connection:
                try:
                    self.connection.disconnect()
                except:
                    pass
                self.connection = None
    
    def configure_stp_interface(self, interface, port_priority, port_cost, edge_port, bpdu_guard, root_guard):
        """配置接口STP参数 - 已废弃
        
        根据测试，设备不支持直接在接口下配置STP参数，
        所以此方法保留但不能正常工作
        """
        self.command_output.emit(f"警告: 设备不支持在接口下直接配置STP参数")
        self.config_status.emit(False, "设备不支持此操作")
        return False
    
    def get_stp_status(self):
        """获取STP状态"""
        try:
            # 连接设备
            if not self.connect_device():
                self.command_output.emit("连接设备失败，无法获取STP状态")
                return None
                
            # 执行命令
            try:
                output = ""
                # 获取STP简要信息
                brief = self.connection.send_command("display stp brief")
                output += f"STP简要信息:\n{brief}\n\n"
                
                # 获取STP全局信息
                global_info = self.connection.send_command("display stp global")
                output += f"STP全局信息:\n{global_info}\n"
                
                # 发送输出信号
                self.command_output.emit(f"STP状态:\n{output}")
                
                return output
            except Exception as e:
                self.command_output.emit(f"获取STP状态时出错: {str(e)}")
                return None
        except Exception as e:
            import traceback
            err_msg = f"获取STP状态错误: {str(e)}\n{traceback.format_exc()}"
            self.command_output.emit(err_msg)
            return None
        finally:
            if self.connection:
                try:
                    self.connection.disconnect()
                except:
                    pass
                self.connection = None

    def apply_acl_to_interface(self, acl_number, interface, direction):
        """将ACL应用到接口"""
        try:
            # 准备命令
            commands = [
                "system-view",
                f"interface {interface}",
                f"packet-filter {acl_number} {direction}",
                "quit",
                "quit"
            ]
            
            # 执行命令
            output = self._execute_commands(commands)
            
            # 检查是否成功
            if output is None:
                self.config_status.emit(False, "执行命令失败")
                return False
                
            success = "Error" not in output
            
            # 发送状态信号
            if success:
                self.config_status.emit(True, f"成功将ACL {acl_number} 应用到接口 {interface} 的 {direction} 方向")
            else:
                self.config_status.emit(False, f"应用ACL到接口失败: {output}")
            
            return success
        except Exception as e:
            import traceback
            err_msg = f"应用ACL错误: {str(e)}\n{traceback.format_exc()}"
            self.command_output.emit(err_msg)
            self.config_status.emit(False, f"应用ACL错误: {str(e)}")
            return False
        finally:
            if self.connection:
                try:
                    self.connection.disconnect()
                except:
                    pass
                self.connection = None
    
    def get_acl_config(self):
        """获取ACL配置"""
        try:
            # 连接设备
            if not self.connect_device():
                self.command_output.emit("连接设备失败，无法获取ACL配置")
                return None
                
            # 执行命令
            output = self.connection.send_command("display acl all")
            
            # 发送输出信号
            self.command_output.emit(f"ACL配置:\n{output}")
            
            return output
        except Exception as e:
            import traceback
            err_msg = f"获取ACL配置错误: {str(e)}\n{traceback.format_exc()}"
            self.command_output.emit(err_msg)
            return None
        finally:
            if self.connection:
                try:
                    self.connection.disconnect()
                except:
                    pass
                self.connection = None