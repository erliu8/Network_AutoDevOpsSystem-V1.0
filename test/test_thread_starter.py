#!/usr/bin/env python
# test_thread_starter.py - 启动测试线程，用于测试线程监控器
import threading
import time
import sys
import os

# 添加项目根目录到系统路径
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = current_dir
sys.path.append(root_dir)

# 导入线程工厂
from core.business.thread_factory import ThreadFactory

def test_thread_function(name, sleep_time):
    """测试线程函数"""
    print(f"测试线程 {name} 启动，休眠时间: {sleep_time}秒")
    thread_id = threading.current_thread().ident
    print(f"线程 {name} 的系统ID: {thread_id}")
    
    # 模拟线程工作
    for i in range(30):
        print(f"线程 {name} 正在工作: {i+1}/30")
        time.sleep(sleep_time)
    print(f"测试线程 {name} 完成工作")

def create_test_threads():
    """创建测试线程"""
    thread_factory = ThreadFactory.get_instance()
    
    # 创建不同类型的测试线程
    modules = [
        "dhcp_configuration", 
        "vpn_deploy", 
        "route_configuration",
        "Batch_configuration_of_addresses", 
        "network_monitor"
    ]
    
    print("正在创建测试线程...")
    
    # 打印当前所有线程
    print("\n启动前的Python线程:")
    threads = threading.enumerate()
    for t in threads:
        print(f"- {t.name} (ID: {t.ident})")
    
    # 创建测试线程
    for i, module in enumerate(modules):
        thread_name = f"{module.capitalize()}_TestThread_{i+1}"
        # 使用普通的threading.Thread而不是线程工厂，确保线程一定会创建
        thread = threading.Thread(
            target=test_thread_function,
            args=(thread_name, i+1),
            name=thread_name,
            daemon=True
        )
        thread.start()
        print(f"启动测试线程: {thread_name}, ID: {thread.ident}")
    
    # 再次打印所有线程
    print("\n创建后的Python线程:")
    threads = threading.enumerate()
    for t in threads:
        print(f"- {t.name} (ID: {t.ident})")
    
    # 这个线程工厂中应该没有线程
    print("\n线程工厂中注册的线程:")
    for thread_id, info in thread_factory.threads.items():
        print(f"- {info['name']} (ID: {thread_id}, 模块: {info['module']})")
    
    # 注册线程到线程工厂
    print("\n开始向线程工厂注册线程...")
    for t in threading.enumerate():
        if t.name.startswith("MainThread"):
            continue
        if any(m in t.name for m in [mod.split('_')[0] for mod in modules]):
            # 找到对应的模块
            for mod in modules:
                if mod.split('_')[0] in t.name:
                    module_name = mod
                    break
            else:
                module_name = "未知"
            # 创建一个伪造的UUID
            import uuid
            fake_uuid = str(uuid.uuid4())
            # 在线程工厂中手动注册线程
            thread_factory.threads[fake_uuid] = {
                "id": fake_uuid,
                "name": t.name,
                "module": module_name,
                "created_at": time.time(),
                "status": "created"
            }
            # 假装这个线程是通过工厂创建的
            thread_factory.active_threads[fake_uuid] = t
            print(f"注册线程 {t.name} 到工厂, ID: {fake_uuid}, 真实线程ID: {t.ident}")
    
    # 再次打印线程工厂中的线程
    print("\n注册后线程工厂中的线程:")
    for thread_id, info in thread_factory.threads.items():
        print(f"- {info['name']} (ID: {thread_id}, 模块: {info['module']})")

if __name__ == "__main__":
    create_test_threads()
    # 保持脚本运行，让测试线程有时间工作
    try:
        print("\n脚本将保持运行，按 Ctrl+C 终止...")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("脚本终止") 