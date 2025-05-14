#!/usr/bin/env python
# test_acl_nat_stp.py - 测试ACL/NAT/生成树配置模块
import sys
import time
from pathlib import Path

# 添加项目根目录到系统路径
root_dir = str(Path(__file__).parent)
sys.path.append(root_dir)

from PyQt5.QtWidgets import QApplication
from modules.acl_nat_spanning_tree_configuration.gui import ConfigurationWindow
from modules.acl_nat_spanning_tree_configuration.acl_nat_spanning_tree_configuration import ConfigOperator

def test_gui():
    """测试GUI界面"""
    print("============================================")
    print("       ACL/NAT/生成树配置模块GUI测试         ")
    print("============================================")
    
    # 创建QApplication实例
    app = QApplication(sys.argv)
    
    # 创建配置窗口
    window = ConfigurationWindow()
    
    # 显示窗口
    window.show()
    
    # 打印提示
    print("测试界面已准备就绪。")
    print("请按照以下步骤测试:")
    print("1. 从下拉菜单中选择一个网络设备")
    print("2. 点击\"测试连接\"按钮确认可以连接到设备")
    print("3. 选择一个配置选项卡(ACL/NAT/生成树)")
    print("4. 填写配置参数并执行相应操作")
    print("5. 检查操作日志区域查看结果")
    
    # 执行应用程序主循环
    sys.exit(app.exec_())

def test_acl(device_ip="10.1.200.1", username="1", password="1"):
    """测试ACL配置功能"""
    print("============================================")
    print("          ACL配置功能测试                  ")
    print("============================================")
    
    print(f"测试设备: {device_ip}")
    print(f"用户名: {username}")
    print(f"密码: {password}")
    print("============================================")
    
    try:
        # 创建配置操作实例
        config_operator = ConfigOperator(device_ip, username, password)
        
        # 定义回调函数处理信号
        def on_config_status(success, message):
            print(f"配置状态: {'成功' if success else '失败'} - {message}")
        
        def on_command_output(output):
            print(f"命令输出: {output}")
        
        # 连接信号
        config_operator.config_status.connect(on_config_status)
        config_operator.command_output.connect(on_command_output)
        
        # 连接设备
        print("尝试连接设备...")
        if config_operator.connect_device():
            print("连接成功!")
            
            # 测试获取ACL配置
            print("\n查看当前ACL配置:")
            acl_config = config_operator.get_acl_config()
            if acl_config:
                print(acl_config)
            else:
                print("未能获取ACL配置")
                
            # 测试配置基本ACL
            print("\n配置基本ACL:")
            acl_config = {
                "acl_number": 2000,
                "rule_number": 5,
                "action": "permit",
                "source": "192.168.10.0 0.0.0.255",
                "protocol": "ip"
            }
            
            # 等待连接准备完成
            time.sleep(1)
            
            # 添加ACL规则
            print("添加ACL规则...")
            config_operator.configure_acl(acl_config)
            
            # 等待配置完成
            time.sleep(3)
            
            # 查看更新后的ACL配置
            print("\n查看更新后的ACL配置:")
            acl_config = config_operator.get_acl_config()
            if acl_config:
                print(acl_config)
            else:
                print("未能获取ACL配置")
                
        else:
            print("连接失败，无法进行测试")
            
    except Exception as e:
        import traceback
        print(f"测试过程中出错: {str(e)}")
        print(traceback.format_exc())
    
    print("ACL配置测试完成.")

def test_nat(device_ip="10.1.200.1", username="1", password="1"):
    """测试NAT配置功能"""
    print("============================================")
    print("          NAT配置功能测试                  ")
    print("============================================")
    
    print(f"测试设备: {device_ip}")
    print(f"用户名: {username}")
    print(f"密码: {password}")
    print("============================================")
    
    try:
        # 创建配置操作实例
        config_operator = ConfigOperator(device_ip, username, password)
        
        # 定义回调函数处理信号
        def on_config_status(success, message):
            print(f"配置状态: {'成功' if success else '失败'} - {message}")
        
        def on_command_output(output):
            print(f"命令输出: {output}")
        
        # 连接信号
        config_operator.config_status.connect(on_config_status)
        config_operator.command_output.connect(on_command_output)
        
        # 连接设备
        print("尝试连接设备...")
        if config_operator.connect_device():
            print("连接成功!")
            
            # 测试配置静态NAT
            print("\n配置静态NAT:")
            nat_params = {
                "inside_ip": "192.168.10.10",
                "outside_ip": "20.1.1.10"
            }
            
            # 等待连接准备完成
            time.sleep(1)
            
            # 配置NAT
            print("配置静态NAT...")
            config_operator.configure_nat("static", "GigabitEthernet0/0/0", "GigabitEthernet0/0/1", nat_params)
            
            # 等待配置完成
            time.sleep(3)
            
            # 查看NAT配置
            print("\n查看NAT配置:")
            nat_config = config_operator.get_nat_config()
            if nat_config:
                print(nat_config)
            else:
                print("未能获取NAT配置")
                
        else:
            print("连接失败，无法进行测试")
            
    except Exception as e:
        import traceback
        print(f"测试过程中出错: {str(e)}")
        print(traceback.format_exc())
    
    print("NAT配置测试完成.")

def test_stp(device_ip="10.1.0.3", username="1", password="1"):
    """测试生成树配置功能"""
    print("============================================")
    print("          生成树配置功能测试                ")
    print("============================================")
    
    print(f"测试设备: {device_ip}")
    print(f"用户名: {username}")
    print(f"密码: {password}")
    print("============================================")
    
    try:
        # 创建配置操作实例
        config_operator = ConfigOperator(device_ip, username, password)
        
        # 定义回调函数处理信号
        def on_config_status(success, message):
            print(f"配置状态: {'成功' if success else '失败'} - {message}")
        
        def on_command_output(output):
            print(f"命令输出: {output}")
        
        # 连接信号
        config_operator.config_status.connect(on_config_status)
        config_operator.command_output.connect(on_command_output)
        
        # 连接设备
        print("尝试连接设备...")
        if config_operator.connect_device():
            print("连接成功!")
            
            # 测试获取STP状态
            print("\n查看当前STP状态:")
            stp_status = config_operator.get_stp_status()
            if stp_status:
                print(stp_status)
            else:
                print("未能获取STP状态")
                
            # 测试配置全局STP
            print("\n配置全局STP参数:")
            
            # 等待连接准备完成
            time.sleep(1)
            
            # 配置STP
            print("配置STP模式为MSTP，优先级为4096...")
            config_operator.configure_stp_global(
                mode="mstp",
                priority=4096,
                forward_time=15,
                hello_time=2,
                max_age=20
            )
            
            # 等待配置完成
            time.sleep(3)
            
            # 测试配置接口STP
            print("\n配置接口STP参数:")
            config_operator.configure_stp_interface(
                interface="GigabitEthernet0/0/1",
                port_priority=128,
                port_cost=200000,
                edge_port=True,
                bpdu_guard=True,
                root_guard=False
            )
            
            # 等待配置完成
            time.sleep(3)
            
            # 查看更新后的STP状态
            print("\n查看更新后的STP状态:")
            stp_status = config_operator.get_stp_status()
            if stp_status:
                print(stp_status)
            else:
                print("未能获取STP状态")
                
        else:
            print("连接失败，无法进行测试")
            
    except Exception as e:
        import traceback
        print(f"测试过程中出错: {str(e)}")
        print(traceback.format_exc())
    
    print("生成树配置测试完成.")

def main():
    print("============================================")
    print("       ACL/NAT/生成树配置模块测试程序       ")
    print("============================================")
    
    # 解析命令行参数
    if len(sys.argv) > 1:
        test_type = sys.argv[1].lower()
        if test_type == "gui":
            test_gui()
        elif test_type == "acl":
            test_acl()
        elif test_type == "nat":
            test_nat()
        elif test_type == "stp":
            test_stp()
        else:
            print("未知的测试类型。请使用: gui, acl, nat 或 stp")
    else:
        # 默认显示GUI
        print("请指定测试类型: gui, acl, nat 或 stp")
        print("例如: python test_acl_nat_stp.py gui")

if __name__ == "__main__":
    main() 