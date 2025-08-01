#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
同步引擎 - 负责文件同步逻辑
"""

import os
import time
import requests
import hashlib
import json
import threading
from pathlib import Path
import fnmatch
from urllib.parse import urljoin, quote

class SyncEngine:
    def __init__(self, config, log_callback, stats_callback=None):
        self.config = config
        self.log_callback = log_callback
        self.stats_callback = stats_callback
        self.running = False
        self.paused = False
        self.session = requests.Session()
        
        # 统计信息
        self.stats = {
            'uploaded': 0,
            'downloaded': 0,
            'deleted': 0
        }
        
        # 设置认证（如果需要）
        if config.get('username') and config.get('password'):
            self.session.auth = (config['username'], config['password'])
            
    def start_sync(self):
        """启动同步"""
        self.running = True
        self.log_callback("开始文件同步...")
        
        while self.running:
            try:
                if not self.paused:
                    self.sync_files()
                time.sleep(self.config.get('sync_interval', 30))
            except Exception as e:
                self.log_callback(f"同步出错: {str(e)}")
                time.sleep(5)  # 出错后短暂等待
                
    def stop_sync(self):
        """停止同步"""
        self.running = False
        self.paused = False
        
    def pause_sync(self):
        """暂停同步"""
        self.paused = True
        
    def resume_sync(self):
        """继续同步"""
        self.paused = False
        
    def sync_files(self):
        """执行文件同步"""
        try:
            sync_mode = self.config.get('sync_mode', 'mirror')
            self.log_callback(f"开始同步检查 - 模式: {sync_mode}")
            
            # 验证排除规则
            self.validate_exclude_rules()
            
            if sync_mode == 'mirror':
                self.mirror_sync()
            elif sync_mode == 'local':
                self.local_to_server_sync()
            elif sync_mode == 'server':
                self.server_to_local_sync()
                
            self.log_callback("同步检查完成")
            
        except Exception as e:
            self.log_callback(f"同步过程出错: {str(e)}")
            
    def mirror_sync(self):
        """镜像同步模式 - 改进版本"""
        self.log_callback("开始智能镜像同步...")
        
        # 获取本地文件列表
        self.log_callback("获取本地文件列表...")
        local_files = self.get_local_files()
        self.log_callback(f"本地文件数量: {len(local_files)}")
        
        # 获取服务器文件列表
        self.log_callback("获取服务器文件列表...")
        server_files = self.get_server_files()
        self.log_callback(f"服务器文件数量: {len(server_files)}")
        
        if not server_files and not local_files:
            self.log_callback("本地和服务器都没有文件")
            return
        
        # 创建文件状态映射
        all_files = set()
        local_file_map = {f['path']: f for f in local_files}
        server_file_map = server_files
        
        # 收集所有文件路径
        all_files.update(local_file_map.keys())
        all_files.update(server_file_map.keys())
        
        sync_actions = {
            'upload': [],
            'download': [],
            'skip': [],
            'conflict': []
        }
        
        # 分析每个文件的同步策略
        for file_path in all_files:
            local_file = local_file_map.get(file_path)
            server_file = server_file_map.get(file_path)
            
            action = self.determine_sync_action(file_path, local_file, server_file)
            sync_actions[action['type']].append({
                'path': file_path,
                'action': action,
                'local': local_file,
                'server': server_file
            })
        
        # 执行同步操作
        self.execute_sync_actions(sync_actions)
        
        # 统计结果
        upload_count = len(sync_actions['upload'])
        download_count = len(sync_actions['download'])
        skip_count = len(sync_actions['skip'])
        conflict_count = len(sync_actions['conflict'])
        
        self.log_callback(f"镜像同步完成 - 上传:{upload_count}, 下载:{download_count}, 跳过:{skip_count}, 冲突:{conflict_count}")
        
    def determine_sync_action(self, file_path, local_file, server_file):
        """确定文件的同步操作"""
        
        # 情况1: 只存在于本地
        if local_file and not server_file:
            return {
                'type': 'upload',
                'reason': '本地新文件，需要上传到服务器'
            }
        
        # 情况2: 只存在于服务器
        if server_file and not local_file:
            return {
                'type': 'download',
                'reason': '服务器新文件，需要下载到本地'
            }
        
        # 情况3: 两边都存在
        if local_file and server_file:
            local_hash = local_file.get('hash')
            server_hash = server_file.get('hash')
            
            # 文件内容相同，无需同步
            if local_hash and server_hash and local_hash == server_hash:
                return {
                    'type': 'skip',
                    'reason': '文件内容相同，跳过同步'
                }
            
            # 文件内容不同，需要判断哪个更新
            local_mtime = local_file.get('mtime', 0)
            server_mtime = server_file.get('mtime', 0)
            
            # 如果能获取到修改时间，以更新的为准
            if local_mtime and server_mtime:
                if local_mtime > server_mtime:
                    return {
                        'type': 'upload',
                        'reason': f'本地文件更新 (本地:{local_mtime} > 服务器:{server_mtime})'
                    }
                elif server_mtime > local_mtime:
                    return {
                        'type': 'download',
                        'reason': f'服务器文件更新 (服务器:{server_mtime} > 本地:{local_mtime})'
                    }
                else:
                    # 修改时间相同但内容不同，标记为冲突
                    return {
                        'type': 'conflict',
                        'reason': '修改时间相同但内容不同，需要手动处理'
                    }
            
            # 无法获取修改时间，默认以本地为准（保守策略）
            return {
                'type': 'upload',
                'reason': '无法确定文件新旧，以本地版本为准'
            }
        
        # 不应该到达这里
        return {
            'type': 'skip',
            'reason': '未知情况，跳过处理'
        }
    
    def execute_sync_actions(self, sync_actions):
        """执行同步操作"""
        
        # 1. 先处理上传
        for item in sync_actions['upload']:
            self.log_callback(f"上传: {item['path']} - {item['action']['reason']}")
            self.upload_file(item['local']['full_path'], item['path'])
        
        # 2. 再处理下载
        for item in sync_actions['download']:
            self.log_callback(f"下载: {item['path']} - {item['action']['reason']}")
            self.download_file(item['path'])
        
        # 3. 跳过的文件
        for item in sync_actions['skip']:
            self.log_callback(f"跳过: {item['path']} - {item['action']['reason']}")
        
        # 4. 冲突的文件
        for item in sync_actions['conflict']:
            self.log_callback(f"⚠️ 冲突: {item['path']} - {item['action']['reason']}")
            # 对于冲突文件，可以选择保守策略：不做任何操作，或者以本地为准
            # 这里选择以本地为准
            self.log_callback(f"冲突解决: 以本地版本为准，上传 {item['path']}")
            self.upload_file(item['local']['full_path'], item['path'])
                
    def local_to_server_sync(self):
        """本地到服务器同步"""
        local_files = self.get_local_files()
        server_files = self.get_server_files()
        
        # 上传本地文件
        for local_file in local_files:
            rel_path = local_file['path']
            if rel_path not in server_files or local_file['hash'] != server_files[rel_path].get('hash'):
                self.upload_file(local_file['full_path'], rel_path)
                
        # 删除服务器上本地不存在的文件
        for server_path in server_files:
            if not any(f['path'] == server_path for f in local_files):
                self.delete_server_file(server_path)
                
    def server_to_local_sync(self):
        """服务器到本地同步"""
        local_files = self.get_local_files()
        server_files = self.get_server_files()
        
        # 下载服务器文件
        for server_path, server_info in server_files.items():
            local_file = next((f for f in local_files if f['path'] == server_path), None)
            if not local_file or local_file['hash'] != server_info.get('hash'):
                self.download_file(server_path)
                
        # 删除本地服务器不存在的文件
        for local_file in local_files:
            if local_file['path'] not in server_files:
                self.delete_local_file(local_file['full_path'])
                
    def get_local_files(self):
        """获取本地文件列表"""
        local_folder = Path(self.config['local_folder'])
        files = []
        
        for file_path in local_folder.rglob('*'):
            if file_path.is_file() and not self.is_excluded(file_path.name):
                rel_path = file_path.relative_to(local_folder).as_posix()
                file_hash = self.get_file_hash(file_path)
                
                # 获取文件修改时间（毫秒时间戳）
                try:
                    mtime = int(file_path.stat().st_mtime * 1000)
                except:
                    mtime = 0
                
                files.append({
                    'path': rel_path,
                    'full_path': str(file_path),
                    'hash': file_hash,
                    'mtime': mtime,
                    'size': file_path.stat().st_size if file_path.exists() else 0
                })
                
        return files
        
    def get_server_files(self):
        """获取服务器文件列表（递归获取所有文件）"""
        try:
            files = {}
            self._get_server_files_recursive('', files)
            return files
            
        except Exception as e:
            self.log_callback(f"获取服务器文件列表失败: {str(e)}")
            return {}
            
    def _get_server_files_recursive(self, path, files):
        """递归获取服务器文件列表"""
        try:
            # 构建URL，根目录时不需要路径
            if path:
                url = urljoin(self.config['server_url'], f"{quote(path)}?json")
            else:
                url = urljoin(self.config['server_url'], "?json")
                
            self.log_callback(f"获取目录列表: {path if path else '根目录'}")
            response = self.session.get(url)
            response.raise_for_status()
            
            server_data = response.json()
            paths = server_data.get('paths', [])
            self.log_callback(f"找到 {len(paths)} 个项目")
            
            for item in paths:
                item_name = item['name']
                item_path = f"{path}/{item_name}" if path else item_name
                
                if item.get('path_type') == 'File':
                    # 跳过被排除的文件
                    if self.is_excluded(item_name):
                        self.log_callback(f"跳过被排除的文件: {item_name}")
                        continue
                        
                    # 获取文件hash
                    try:
                        hash_url = urljoin(self.config['server_url'], f"{quote(item_path)}?hash")
                        hash_response = self.session.get(hash_url, timeout=10)
                        file_hash = hash_response.text.strip() if hash_response.status_code == 200 else None
                    except Exception as e:
                        self.log_callback(f"获取文件hash失败 {item_path}: {str(e)}")
                        file_hash = None
                    
                    files[item_path] = {
                        'hash': file_hash,
                        'size': item.get('size', 0),
                        'mtime': item.get('mtime', 0)  # dufs提供的修改时间
                    }
                    self.log_callback(f"发现文件: {item_path} (大小: {item.get('size', 0)} 字节, 修改时间: {item.get('mtime', 0)})")
                    
                elif item.get('path_type') == 'Dir':
                    # 递归获取子目录
                    self.log_callback(f"进入子目录: {item_path}")
                    self._get_server_files_recursive(item_path, files)
                    
        except Exception as e:
            self.log_callback(f"获取目录 {path if path else '根目录'} 失败: {str(e)}")
            
    def upload_file(self, local_path, remote_path):
        """上传文件到服务器"""
        try:
            # 确保远程目录存在
            remote_dir = '/'.join(remote_path.split('/')[:-1])
            if remote_dir:
                self.create_remote_directory(remote_dir)
            
            url = urljoin(self.config['server_url'], quote(remote_path))
            
            with open(local_path, 'rb') as f:
                response = self.session.put(url, data=f)
                response.raise_for_status()
                
            self.log_callback(f"上传成功: {remote_path}")
            self.stats['uploaded'] += 1
            self.update_stats()
            
        except Exception as e:
            self.log_callback(f"上传失败 {remote_path}: {str(e)}")
            
    def create_remote_directory(self, remote_dir):
        """创建远程目录"""
        try:
            url = urljoin(self.config['server_url'], quote(remote_dir))
            response = self.session.request('MKCOL', url)
            # 目录已存在时返回405，这是正常的
            if response.status_code not in [201, 405]:
                response.raise_for_status()
        except Exception as e:
            self.log_callback(f"创建目录失败 {remote_dir}: {str(e)}")
            
    def download_file(self, remote_path):
        """从服务器下载文件"""
        try:
            # 构建下载URL
            url = urljoin(self.config['server_url'], quote(remote_path))
            self.log_callback(f"开始下载: {remote_path}")
            
            # 发送下载请求
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            # 确保本地目录存在
            local_path = Path(self.config['local_folder']) / remote_path
            local_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 写入文件
            with open(local_path, 'wb') as f:
                f.write(response.content)
                
            self.log_callback(f"下载成功: {remote_path} ({len(response.content)} 字节)")
            self.stats['downloaded'] += 1
            self.update_stats()
            
        except requests.exceptions.Timeout:
            self.log_callback(f"下载超时 {remote_path}")
        except requests.exceptions.RequestException as e:
            self.log_callback(f"下载网络错误 {remote_path}: {str(e)}")
        except OSError as e:
            self.log_callback(f"下载文件写入错误 {remote_path}: {str(e)}")
        except Exception as e:
            self.log_callback(f"下载失败 {remote_path}: {str(e)}")
            
    def delete_server_file(self, remote_path):
        """删除服务器文件"""
        try:
            url = urljoin(self.config['server_url'], quote(remote_path))
            response = self.session.delete(url)
            response.raise_for_status()
            
            self.log_callback(f"服务器删除成功: {remote_path}")
            self.stats['deleted'] += 1
            self.update_stats()
            
        except Exception as e:
            self.log_callback(f"服务器删除失败 {remote_path}: {str(e)}")
            
    def delete_local_file(self, local_path):
        """删除本地文件"""
        try:
            os.remove(local_path)
            self.log_callback(f"本地删除成功: {local_path}")
            self.stats['deleted'] += 1
            self.update_stats()
            
        except Exception as e:
            self.log_callback(f"本地删除失败 {local_path}: {str(e)}")
            
    def get_file_hash(self, file_path):
        """计算文件SHA256哈希值"""
        try:
            hash_sha256 = hashlib.sha256()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        except Exception:
            return None
            
    def is_excluded(self, filename):
        """检查文件是否被排除"""
        exclude_rules = self.config.get('exclude_rules', [])
        
        for rule in exclude_rules:
            rule = rule.strip()
            if not rule:
                continue
                
            # 使用fnmatch进行模式匹配
            if fnmatch.fnmatch(filename, rule):
                self.log_callback(f"文件被排除: {filename} (匹配规则: {rule})")
                return True
                
        return False
        
    def validate_exclude_rules(self):
        """验证和修复排除规则"""
        exclude_rules = self.config.get('exclude_rules', [])
        fixed_rules = []
        
        for rule in exclude_rules:
            rule = rule.strip()
            if not rule:
                continue
                
            # 常见规则修复建议
            if rule == "~$.*":
                self.log_callback(f"⚠️ 排除规则建议: '{rule}' 可能不会按预期工作，建议使用 '~$*' 或 '~$*.*'")
                
            fixed_rules.append(rule)
            
        return fixed_rules
        
    def update_stats(self):
        """更新统计信息"""
        if self.stats_callback:
            self.stats_callback(self.stats)