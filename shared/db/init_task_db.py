#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
初始化任务数据库和任务表
这个脚本用于创建任务数据库和相关表，支持Flask和PyQt应用之间的任务共享
"""

import sqlite3
import os
import sys
import json
from pathlib import Path
from datetime import datetime

# 添加项目根目录到系统路径
sys.path.append(str(Path(__file__).parent.parent.parent))

# 数据库文件路径
DB_DIR = Path(__file__).parent.parent.parent / "data"
DB_FILE = DB_DIR / "tasks.db"

def init_database():
    """初始化数据库和任务表"""
    print(f"数据库路径: {DB_FILE}")
    
    # 确保目录存在
    if not DB_DIR.exists():
        print(f"创建数据目录: {DB_DIR}")
        DB_DIR.mkdir(parents=True, exist_ok=True)
    
    # 连接数据库
    print("连接数据库...")
    conn = sqlite3.connect(str(DB_FILE))
    cursor = conn.cursor()
    
    # 创建任务表
    print("创建任务表...")
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS tasks (
        task_id TEXT PRIMARY KEY,
        task_type TEXT NOT NULL,
        params TEXT NOT NULL,
        status TEXT NOT NULL,
        result TEXT,
        error TEXT,
        created_at TEXT NOT NULL,
        started_at TEXT,
        completed_at TEXT,
        assigned_to TEXT,
        priority INTEGER DEFAULT 0,
        notifications_sent INTEGER DEFAULT 0
    )
    ''')
    
    # 创建任务状态变更历史表
    print("创建任务状态历史表...")
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS task_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        task_id TEXT NOT NULL,
        old_status TEXT,
        new_status TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        changed_by TEXT,
        FOREIGN KEY (task_id) REFERENCES tasks(task_id)
    )
    ''')
    
    # 创建通知表
    print("创建通知表...")
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        task_id TEXT NOT NULL,
        message TEXT NOT NULL,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL,
        read_at TEXT,
        FOREIGN KEY (task_id) REFERENCES tasks(task_id)
    )
    ''')
    
    # 提交更改
    conn.commit()
    print("数据库初始化完成!")
    
    # 关闭连接
    conn.close()

def test_database():
    """测试数据库连接和表是否正确创建"""
    try:
        # 连接数据库
        conn = sqlite3.connect(str(DB_FILE))
        cursor = conn.cursor()
        
        # 检查表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print(f"数据库中的表: {[table[0] for table in tables]}")
        
        # 关闭连接
        conn.close()
        
        print("数据库测试成功!")
        return True
        
    except Exception as e:
        print(f"数据库测试失败: {str(e)}")
        return False

if __name__ == "__main__":
    print("开始初始化任务数据库...")
    init_database()
    test_database() 