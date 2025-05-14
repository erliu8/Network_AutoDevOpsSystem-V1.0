#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import mysql.connector
from datetime import datetime, timedelta

# 添加父目录到模块搜索路径
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)

# 导入配置
from config.database import DB_CONFIG

def connect_database():
    """连接到数据库"""
    try:
        # 从DB_CONFIG中提取需要的连接参数
        db_params = {
            'host': DB_CONFIG['default']['HOST'],
            'user': DB_CONFIG['default']['USER'],
            'password': DB_CONFIG['default']['PASSWORD'],
            'database': DB_CONFIG['default']['NAME']
        }
        conn = mysql.connector.connect(**db_params)
        return conn
    except Exception as e:
        print(f"连接数据库失败: {e}")
        return None

def cleanup_duplicate_records(conn):
    """清理重复记录，只保留每个设备每分钟最新的一条记录"""
    cursor = conn.cursor()
    
    try:
        # 找出重复记录，按照设备IP和时间(分钟级别)分组
        find_duplicates_query = """
        SELECT device_ip, 
               DATE_FORMAT(collection_time, '%Y-%m-%d %H:%i') as minute_time, 
               COUNT(*) as count
        FROM device_monitor_data
        GROUP BY device_ip, minute_time
        HAVING COUNT(*) > 1
        """
        
        cursor.execute(find_duplicates_query)
        duplicates = cursor.fetchall()
        
        print(f"找到 {len(duplicates)} 组重复记录")
        
        total_deleted = 0
        
        for device_ip, minute_time, count in duplicates:
            # 保留每组中最新的一条记录
            delete_query = """
            DELETE d1 FROM device_monitor_data d1
            JOIN (
                SELECT id, device_ip, collection_time,
                    ROW_NUMBER() OVER (PARTITION BY device_ip, DATE_FORMAT(collection_time, '%Y-%m-%d %H:%i') 
                                      ORDER BY collection_time DESC) as row_num
                FROM device_monitor_data
                WHERE device_ip = %s AND DATE_FORMAT(collection_time, '%Y-%m-%d %H:%i') = %s
            ) d2 ON d1.id = d2.id
            WHERE d2.row_num > 1
            """
            
            cursor.execute(delete_query, (device_ip, minute_time))
            deleted_count = cursor.rowcount
            total_deleted += deleted_count
            
            print(f"设备 {device_ip} 在 {minute_time} 分钟内删除了 {deleted_count} 条重复记录")
        
        conn.commit()
        print(f"总共删除了 {total_deleted} 条重复记录")
        
    except Exception as e:
        print(f"清理重复记录时出错: {e}")
        conn.rollback()
    finally:
        cursor.close()

def cleanup_old_records(conn, days=7):
    """清理指定天数之前的旧记录"""
    cursor = conn.cursor()
    
    try:
        cutoff_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        delete_query = "DELETE FROM device_monitor_data WHERE DATE(collection_time) < %s"
        
        cursor.execute(delete_query, (cutoff_date,))
        deleted_count = cursor.rowcount
        
        conn.commit()
        print(f"删除了 {deleted_count} 条 {cutoff_date} 之前的旧记录")
        
    except Exception as e:
        print(f"清理旧记录时出错: {e}")
        conn.rollback()
    finally:
        cursor.close()

def cleanup_inconsistent_records(conn):
    """清理状态不一致的记录，如接口有活动但状态为unknown的记录"""
    cursor = conn.cursor()
    
    try:
        # 查找并修复inconsistent记录
        fix_query = """
        UPDATE device_monitor_data 
        SET status = 'connected' 
        WHERE status = 'unknown' 
        AND (cpu_usage > 0 OR memory_usage > 0 OR interface_status LIKE '%"status": "up"%')
        """
        
        cursor.execute(fix_query)
        fixed_count = cursor.rowcount
        
        conn.commit()
        print(f"修复了 {fixed_count} 条状态不一致的记录")
        
    except Exception as e:
        print(f"修复状态不一致记录时出错: {e}")
        conn.rollback()
    finally:
        cursor.close()

def generate_statistics(conn):
    """生成数据库统计信息"""
    cursor = conn.cursor()
    
    try:
        # 总记录数
        cursor.execute("SELECT COUNT(*) FROM device_monitor_data")
        total_count = cursor.fetchone()[0]
        
        # 按状态分组
        cursor.execute("SELECT status, COUNT(*) FROM device_monitor_data GROUP BY status")
        status_counts = cursor.fetchall()
        
        # 按设备分组
        cursor.execute("SELECT device_ip, COUNT(*) FROM device_monitor_data GROUP BY device_ip")
        device_counts = cursor.fetchall()
        
        # 按时间段统计
        cursor.execute("""
        SELECT 
            DATE(collection_time) as date, 
            COUNT(*) as count
        FROM device_monitor_data
        GROUP BY DATE(collection_time)
        ORDER BY date DESC
        """)
        date_counts = cursor.fetchall()
        
        print("\n数据库统计信息:")
        print(f"总记录数: {total_count}")
        
        print("\n按状态分组:")
        for status, count in status_counts:
            print(f"  {status}: {count} 条记录")
        
        print("\n按设备分组 (前5个):")
        for device_ip, count in device_counts[:5]:
            print(f"  {device_ip}: {count} 条记录")
        
        print("\n按日期分组 (最近5天):")
        for date, count in date_counts[:5]:
            print(f"  {date}: {count} 条记录")
        
    except Exception as e:
        print(f"生成统计信息时出错: {e}")
    finally:
        cursor.close()

def main():
    """主函数"""
    print("开始清理数据库...")
    
    conn = connect_database()
    if not conn:
        return
    
    try:
        # 先生成清理前的统计信息
        print("\n清理前的统计信息:")
        generate_statistics(conn)
        
        # 执行清理操作
        cleanup_duplicate_records(conn)
        cleanup_inconsistent_records(conn)
        cleanup_old_records(conn, days=3)  # 默认保留3天数据
        
        # 生成清理后的统计信息
        print("\n清理后的统计信息:")
        generate_statistics(conn)
        
    finally:
        conn.close()
    
    print("\n数据库清理完成")

if __name__ == "__main__":
    main() 