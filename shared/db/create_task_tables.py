#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
在MySQL数据库中创建任务相关表
这个脚本用于创建MySQL中的任务表、任务历史表和通知表，支持Flask和PyQt应用之间的任务共享
"""

import sys
import os
from pathlib import Path
import pymysql
import traceback

# 添加项目根目录到系统路径
sys.path.append(str(Path(__file__).parent.parent.parent))

# 导入数据库配置
from config.database import DB_CONFIG

def create_task_tables():
    """创建任务相关表"""
    try:
        # 获取数据库配置
        db_config = DB_CONFIG['default']
        
        # 检查数据库类型
        if db_config['ENGINE'] != 'mysql':
            print(f"警告: 当前数据库类型不是MySQL ({db_config['ENGINE']})")
            proceed = input("是否继续? (y/n): ")
            if proceed.lower() != 'y':
                print("操作已取消")
                return False
        
        # 连接MySQL数据库
        print(f"连接到MySQL数据库 {db_config['HOST']}:{db_config['PORT']}...")
        conn = pymysql.connect(
            host=db_config['HOST'],
            port=int(db_config['PORT']),
            user=db_config['USER'],
            password=db_config['PASSWORD'],
            database=db_config['NAME'],
            charset='utf8mb4'
        )
        
        cursor = conn.cursor()
        
        # 创建任务表
        print("创建任务表...")
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            task_id VARCHAR(50) PRIMARY KEY,
            task_type VARCHAR(50) NOT NULL,
            params TEXT NOT NULL,
            status VARCHAR(20) NOT NULL,
            result TEXT,
            error TEXT,
            created_at DATETIME NOT NULL,
            started_at DATETIME,
            completed_at DATETIME,
            assigned_to VARCHAR(50),
            priority INT DEFAULT 0,
            notifications_sent INT DEFAULT 0,
            INDEX idx_status (status),
            INDEX idx_task_type (task_type)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        ''')
        
        # 创建任务状态变更历史表
        print("创建任务状态历史表...")
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS task_history (
            id INT AUTO_INCREMENT PRIMARY KEY,
            task_id VARCHAR(50) NOT NULL,
            old_status VARCHAR(20),
            new_status VARCHAR(20) NOT NULL,
            timestamp DATETIME NOT NULL,
            changed_by VARCHAR(50),
            FOREIGN KEY (task_id) REFERENCES tasks(task_id) ON DELETE CASCADE,
            INDEX idx_task_id (task_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        ''')
        
        # 创建通知表
        print("创建通知表...")
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS notifications (
            id INT AUTO_INCREMENT PRIMARY KEY,
            task_id VARCHAR(50) NOT NULL,
            message TEXT NOT NULL,
            status VARCHAR(20) NOT NULL,
            created_at DATETIME NOT NULL,
            read_at DATETIME,
            FOREIGN KEY (task_id) REFERENCES tasks(task_id) ON DELETE CASCADE,
            INDEX idx_task_id (task_id),
            INDEX idx_status (status)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        ''')
        
        # 提交更改
        conn.commit()
        print("数据库表创建完成!")
        
        # 关闭连接
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"创建表失败: {str(e)}")
        traceback.print_exc()
        return False

def verify_tables():
    """验证表是否已创建"""
    try:
        # 获取数据库配置
        db_config = DB_CONFIG['default']
        
        # 连接MySQL数据库
        conn = pymysql.connect(
            host=db_config['HOST'],
            port=int(db_config['PORT']),
            user=db_config['USER'],
            password=db_config['PASSWORD'],
            database=db_config['NAME'],
            charset='utf8mb4'
        )
        
        cursor = conn.cursor()
        
        # 检查表是否存在
        cursor.execute('''
        SELECT TABLE_NAME FROM information_schema.TABLES 
        WHERE TABLE_SCHEMA = %s AND TABLE_NAME IN ('tasks', 'task_history', 'notifications')
        ''', (db_config['NAME'],))
        
        tables = cursor.fetchall()
        table_names = [table[0] for table in tables]
        
        print(f"已创建的表: {table_names}")
        
        # 验证所有表是否都已创建
        all_tables_exist = all(table in table_names for table in ['tasks', 'task_history', 'notifications'])
        
        # 关闭连接
        cursor.close()
        conn.close()
        
        if all_tables_exist:
            print("所有表已成功创建!")
        else:
            missing_tables = [table for table in ['tasks', 'task_history', 'notifications'] if table not in table_names]
            print(f"缺少以下表: {missing_tables}")
        
        return all_tables_exist
        
    except Exception as e:
        print(f"验证表失败: {str(e)}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("开始创建任务表...")
    if create_task_tables():
        verify_tables() 