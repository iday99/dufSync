#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置管理器 - 负责保存和加载配置
"""

import json
import os
from pathlib import Path

class ConfigManager:
    def __init__(self):
        self.config_dir = Path.home() / '.dufs_sync'
        self.config_file = self.config_dir / 'config.json'
        
        # 确保配置目录存在
        self.config_dir.mkdir(exist_ok=True)
        
    def load_config(self):
        """加载配置"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"加载配置失败: {e}")
            
        # 返回默认配置
        return {
            'server_url': 'http://127.0.0.1:5001',
            'local_folder': '',
            'exclude_rules': ['~$*', '*.tmp', '*.log', '.DS_Store', 'Thumbs.db'],
            'sync_interval': 30,
            'sync_mode': 'mirror',
            'username': '',
            'password': ''
        }
        
    def save_config(self, config):
        """保存配置"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"保存配置失败: {e}")
            return False