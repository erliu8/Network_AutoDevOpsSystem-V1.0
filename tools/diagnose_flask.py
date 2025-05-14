#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
from pathlib import Path
import requests
from bs4 import BeautifulSoup
import json

# 添加项目根目录到系统路径
sys.path.append(str(Path(__file__).parent.parent))

def check_flask_app(url="http://localhost:5000"):
    """检查Flask应用状态"""
    print(f"检查Flask应用: {url}")
    
    try:
        # 检查主页
        print("\n检查主页...")
        response = requests.get(url, timeout=5)
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            # 解析HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 检查页面标题
            title = soup.title.string if soup.title else "无标题"
            print(f"页面标题: {title}")
            
            # 检查是否有JavaScript错误标记
            js_errors = soup.find_all(class_='js-error')
            if js_errors:
                print(f"发现JavaScript错误: {len(js_errors)}个")
                for error in js_errors:
                    print(f"- {error.text}")
            
            # 检查CSS加载情况
            css_links = soup.find_all('link', rel='stylesheet')
            print(f"\n检查CSS文件 ({len(css_links)}个):")
            for link in css_links:
                href = link.get('href')
                if href.startswith('http'):
                    css_url = href
                else:
                    css_url = url.rstrip('/') + href if href.startswith('/') else url.rstrip('/') + '/' + href
                
                try:
                    css_response = requests.head(css_url, timeout=3)
                    status = f"[{'✓' if css_response.status_code == 200 else '✗'}] {css_response.status_code}"
                except Exception as e:
                    status = f"[✗] 错误: {str(e)}"
                
                print(f"- {href}: {status}")
            
            # 检查JS加载情况
            scripts = soup.find_all('script', src=True)
            print(f"\n检查JS文件 ({len(scripts)}个):")
            for script in scripts:
                src = script.get('src')
                if src.startswith('http'):
                    js_url = src
                else:
                    js_url = url.rstrip('/') + src if src.startswith('/') else url.rstrip('/') + '/' + src
                
                try:
                    js_response = requests.head(js_url, timeout=3)
                    status = f"[{'✓' if js_response.status_code == 200 else '✗'}] {js_response.status_code}"
                except Exception as e:
                    status = f"[✗] 错误: {str(e)}"
                
                print(f"- {src}: {status}")
        
        # 检查API端点
        print("\n检查API端点...")
        api_endpoints = [
            "/dhcp/pending",
            "/dashboard"
        ]
        
        for endpoint in api_endpoints:
            endpoint_url = url.rstrip('/') + endpoint
            try:
                api_response = requests.get(endpoint_url, timeout=3)
                status = f"[{'✓' if api_response.status_code == 200 else '✗'}] {api_response.status_code}"
                try:
                    # 尝试解析JSON
                    if 'application/json' in api_response.headers.get('Content-Type', ''):
                        data = api_response.json()
                        data_summary = json.dumps(data, ensure_ascii=False)[:100] + "..." if len(json.dumps(data)) > 100 else json.dumps(data)
                    else:
                        data_summary = f"非JSON响应 ({len(api_response.text)} 字节)"
                except Exception:
                    data_summary = "无法解析响应数据"
            except Exception as e:
                status = f"[✗] 错误: {str(e)}"
                data_summary = "请求失败"
            
            print(f"- {endpoint}: {status}")
            print(f"  响应: {data_summary}")
    
    except Exception as e:
        print(f"检查过程中发生错误: {str(e)}")

if __name__ == "__main__":
    # 默认检查本地5000端口
    url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:5000"
    check_flask_app(url) 