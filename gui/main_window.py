#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
主窗口界面
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import threading
import os
from .sync_engine import SyncEngine
from .config_manager import ConfigManager

class MainWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # 窗口配置
        self.title("Dufs文件同步工具")
        self.geometry("1000x750")
        self.minsize(900, 700)
        
        # 设置窗口居中
        self.center_window()
        
        # 配置管理器
        self.config_manager = ConfigManager()
        self.config = self.config_manager.load_config()
        
        # 同步引擎
        self.sync_engine = None
        self.sync_thread = None
        self.is_syncing = False
        self.is_paused = False
        
        # 创建界面
        self.create_widgets()
        self.load_settings()
        
        # 设置窗口关闭协议
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        
    def center_window(self):
        """将窗口居中显示"""
        self.update_idletasks()
        width = 1000
        height = 750
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')
        
    def create_widgets(self):
        # 主框架 - 使用更现代的配色
        self.main_frame = ctk.CTkFrame(self, fg_color=("gray95", "gray10"))
        self.main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # 内容区域 - 包含标题和选项卡
        content_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        content_frame.pack(fill="both", expand=True)
        
        # 标题区域
        title_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        title_frame.pack(fill="x", pady=(20, 25))
        
        title_label = ctk.CTkLabel(
            title_frame, 
            text="🔄 Dufs文件同步工具", 
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=("#2E7D32", "#4CAF50")  # 绿色主题
        )
        title_label.pack()
        
        subtitle_label = ctk.CTkLabel(
            title_frame,
            text="智能双向同步 • 安全可靠 • 简单易用",
            font=ctk.CTkFont(size=12),
            text_color=("gray60", "gray40")
        )
        subtitle_label.pack(pady=(5, 0))
        
        # 创建选项卡 - 使用剩余空间，但为按钮预留固定空间
        self.tabview = ctk.CTkTabview(
            content_frame, 
            fg_color=("gray90", "gray20"),
            segmented_button_fg_color=("#2E7D32", "#1B5E20"),
            segmented_button_selected_color=("#4CAF50", "#2E7D32"),
            segmented_button_selected_hover_color=("#66BB6A", "#388E3C")
        )
        self.tabview.pack(fill="both", expand=True, padx=20, pady=(0, 10))
        
        # 基本设置选项卡
        self.tab_basic = self.tabview.add("基本设置")
        self.create_basic_settings()
        
        # 同步规则选项卡
        self.tab_rules = self.tabview.add("同步规则")
        self.create_sync_rules()
        
        # 状态监控选项卡
        self.tab_status = self.tabview.add("状态监控")
        self.create_status_monitor()
        
        # 底部控制按钮 - 固定在底部
        self.create_control_buttons()
        
    def create_basic_settings(self):
        # 创建滚动框架以适应内容
        scrollable_frame = ctk.CTkScrollableFrame(self.tab_basic, fg_color="transparent")
        scrollable_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # 服务器地址设置
        server_frame = ctk.CTkFrame(scrollable_frame, fg_color=("gray85", "gray25"))
        server_frame.pack(fill="x", padx=5, pady=6)
        
        ctk.CTkLabel(server_frame, text="服务器地址:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=15, pady=(10, 3))
        self.server_entry = ctk.CTkEntry(server_frame, placeholder_text="http://127.0.0.1:5000")
        self.server_entry.pack(fill="x", padx=15, pady=(0, 10))
        
        # 本地文件夹设置
        folder_frame = ctk.CTkFrame(scrollable_frame, fg_color=("gray85", "gray25"))
        folder_frame.pack(fill="x", padx=5, pady=6)
        
        ctk.CTkLabel(folder_frame, text="本地同步文件夹:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=15, pady=(10, 3))
        
        folder_select_frame = ctk.CTkFrame(folder_frame)
        folder_select_frame.pack(fill="x", padx=15, pady=(0, 10))
        
        self.folder_entry = ctk.CTkEntry(folder_select_frame, placeholder_text="选择要同步的文件夹")
        self.folder_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        
        folder_btn = ctk.CTkButton(
            folder_select_frame, 
            text="📁 浏览", 
            width=80, 
            command=self.select_folder,
            fg_color=("#2E7D32", "#1B5E20"),
            hover_color=("#1B5E20", "#0D5016")
        )
        folder_btn.pack(side="right")
        
        # 排除设置
        exclude_frame = ctk.CTkFrame(scrollable_frame, fg_color=("gray85", "gray25"))
        exclude_frame.pack(fill="x", padx=5, pady=6)
        
        ctk.CTkLabel(exclude_frame, text="排除规则:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=15, pady=(10, 3))
        
        help_text = "每行一个规则，支持通配符匹配：\n• ~$* (Office临时文件)  • *.tmp (临时文件)  • .git (Git目录)"
        ctk.CTkLabel(exclude_frame, text=help_text, 
                    font=ctk.CTkFont(size=10), text_color=("gray60", "gray40")).pack(anchor="w", padx=15)
        
        self.exclude_text = ctk.CTkTextbox(exclude_frame, height=60)
        self.exclude_text.pack(fill="x", padx=15, pady=(3, 10))
        
        # 认证设置
        auth_frame = ctk.CTkFrame(scrollable_frame, fg_color=("gray85", "gray25"))
        auth_frame.pack(fill="x", padx=5, pady=6)
        
        ctk.CTkLabel(auth_frame, text="认证设置 (可选):", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=15, pady=(10, 3))
        
        auth_control_frame = ctk.CTkFrame(auth_frame, fg_color="transparent")
        auth_control_frame.pack(fill="x", padx=15, pady=(0, 10))
        
        ctk.CTkLabel(auth_control_frame, text="用户名:").pack(side="left", padx=(0, 5))
        self.username_entry = ctk.CTkEntry(auth_control_frame, width=110, placeholder_text="用户名")
        self.username_entry.pack(side="left", padx=(0, 15))
        
        ctk.CTkLabel(auth_control_frame, text="密码:").pack(side="left", padx=(0, 5))
        self.password_entry = ctk.CTkEntry(auth_control_frame, width=110, placeholder_text="密码", show="*")
        self.password_entry.pack(side="left")
        
        # 同步间隔设置
        interval_frame = ctk.CTkFrame(scrollable_frame, fg_color=("gray85", "gray25"))
        interval_frame.pack(fill="x", padx=5, pady=6)
        
        ctk.CTkLabel(interval_frame, text="同步间隔:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=15, pady=(10, 3))
        
        interval_control_frame = ctk.CTkFrame(interval_frame, fg_color="transparent")
        interval_control_frame.pack(fill="x", padx=15, pady=(0, 10))
        
        self.interval_var = ctk.StringVar(value="30")
        self.interval_entry = ctk.CTkEntry(interval_control_frame, textvariable=self.interval_var, width=80)
        self.interval_entry.pack(side="left", padx=(0, 8))
        
        ctk.CTkLabel(interval_control_frame, text="秒").pack(side="left")
        
    def create_sync_rules(self):
        # 创建滚动框架
        scrollable_frame = ctk.CTkScrollableFrame(self.tab_rules, fg_color="transparent")
        scrollable_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        rules_frame = ctk.CTkFrame(scrollable_frame, fg_color="transparent")
        rules_frame.pack(fill="x")
        
        # 标题
        title_frame = ctk.CTkFrame(rules_frame, fg_color="transparent")
        title_frame.pack(fill="x", pady=(10, 25))
        
        ctk.CTkLabel(
            title_frame, 
            text="🔄 选择同步模式", 
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=("#2E7D32", "#4CAF50")
        ).pack()
        
        self.sync_mode = ctk.StringVar(value="mirror")
        
        # 镜像模式
        mirror_frame = ctk.CTkFrame(rules_frame, fg_color=("gray85", "gray25"))
        mirror_frame.pack(fill="x", padx=5, pady=8)
        
        mirror_radio = ctk.CTkRadioButton(
            mirror_frame, 
            text="🔄 镜像模式（推荐）", 
            variable=self.sync_mode, 
            value="mirror",
            font=ctk.CTkFont(size=14, weight="bold"),
            radiobutton_width=20,
            radiobutton_height=20
        )
        mirror_radio.pack(anchor="w", padx=20, pady=15)
        
        mirror_desc = ctk.CTkLabel(
            mirror_frame, 
            text="智能双向同步：基于文件修改时间判断版本新旧，自动解决冲突",
            font=ctk.CTkFont(size=12), 
            text_color=("gray60", "gray40")
        )
        mirror_desc.pack(anchor="w", padx=40, pady=(0, 15))
        
        # 本地为准模式
        local_frame = ctk.CTkFrame(rules_frame, fg_color=("gray85", "gray25"))
        local_frame.pack(fill="x", padx=5, pady=8)
        
        local_radio = ctk.CTkRadioButton(
            local_frame, 
            text="📤 本地为准", 
            variable=self.sync_mode, 
            value="local",
            font=ctk.CTkFont(size=14, weight="bold"),
            radiobutton_width=20,
            radiobutton_height=20
        )
        local_radio.pack(anchor="w", padx=20, pady=15)
        
        local_desc = ctk.CTkLabel(
            local_frame,
            text="单向上传：本地的任何变化都同步到服务器，适合备份场景",
            font=ctk.CTkFont(size=12), 
            text_color=("gray60", "gray40")
        )
        local_desc.pack(anchor="w", padx=40, pady=(0, 15))
        
        # 服务器为准模式
        server_frame = ctk.CTkFrame(rules_frame, fg_color=("gray85", "gray25"))
        server_frame.pack(fill="x", padx=5, pady=8)
        
        server_radio = ctk.CTkRadioButton(
            server_frame, 
            text="📥 服务器为准", 
            variable=self.sync_mode, 
            value="server",
            font=ctk.CTkFont(size=14, weight="bold"),
            radiobutton_width=20,
            radiobutton_height=20
        )
        server_radio.pack(anchor="w", padx=20, pady=15)
        
        server_desc = ctk.CTkLabel(
            server_frame,
            text="单向下载：服务器的任何变化同步到本地，适合获取更新",
            font=ctk.CTkFont(size=12), 
            text_color=("gray60", "gray40")
        )
        server_desc.pack(anchor="w", padx=40, pady=(0, 15))
        
    def create_status_monitor(self):
        # 状态显示区域 - 使用固定布局确保一致性
        status_frame = ctk.CTkFrame(self.tab_status, fg_color="transparent")
        status_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # 状态信息区域
        info_frame = ctk.CTkFrame(status_frame, fg_color=("gray85", "gray25"), height=80)
        info_frame.pack(fill="x", padx=5, pady=(0, 10))
        info_frame.pack_propagate(False)
        
        # 当前状态
        self.status_label = ctk.CTkLabel(
            info_frame, 
            text="📊 状态: 未启动", 
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=("#2E7D32", "#4CAF50")
        )
        self.status_label.pack(pady=12)
        
        # 统计信息
        self.stats_label = ctk.CTkLabel(
            info_frame, 
            text="📈 统计: 上传 0 | 下载 0 | 删除 0", 
            font=ctk.CTkFont(size=12),
            text_color=("gray60", "gray40")
        )
        self.stats_label.pack(pady=(0, 12))
        
        # 日志显示区域
        log_frame = ctk.CTkFrame(status_frame, fg_color=("gray85", "gray25"))
        log_frame.pack(fill="both", expand=True, padx=5, pady=(0, 5))
        
        # 日志标题栏
        log_header_frame = ctk.CTkFrame(log_frame, fg_color="transparent")
        log_header_frame.pack(fill="x", padx=15, pady=(10, 5))
        
        ctk.CTkLabel(
            log_header_frame, 
            text="📝 同步日志", 
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(side="left")
        
        # 清除日志按钮
        clear_log_btn = ctk.CTkButton(
            log_header_frame, 
            text="🗑️ 清除", 
            command=self.clear_log, 
            width=80, 
            height=28, 
            font=ctk.CTkFont(size=11),
            fg_color=("#D32F2F", "#C62828"),
            hover_color=("#C62828", "#B71C1C")
        )
        clear_log_btn.pack(side="right")
        
        # 日志文本框 - 使用剩余空间
        self.log_text = ctk.CTkTextbox(
            log_frame, 
            font=ctk.CTkFont(family="Consolas", size=11),
            wrap="word"
        )
        self.log_text.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        
    def create_control_buttons(self):
        # 按钮区域 - 固定在底部，确保在所有选项卡中位置一致
        button_frame = ctk.CTkFrame(self.main_frame, fg_color=("gray90", "gray20"), height=70)
        button_frame.pack(fill="x", side="bottom", padx=20, pady=(5, 20))
        button_frame.pack_propagate(False)  # 防止子组件改变框架大小
        
        # 左侧功能按钮组
        left_buttons = ctk.CTkFrame(button_frame, fg_color="transparent")
        left_buttons.pack(side="left", pady=12)
        
        # 保存设置按钮 - 蓝色系
        save_btn = ctk.CTkButton(
            left_buttons, 
            text="💾 保存设置", 
            command=self.save_settings, 
            width=110,
            height=35,
            fg_color=("#1976D2", "#1565C0"),
            hover_color=("#1565C0", "#0D47A1"),
            font=ctk.CTkFont(size=12)
        )
        save_btn.pack(side="left", padx=(0, 10))
        
        # 测试连接按钮 - 紫色系
        test_btn = ctk.CTkButton(
            left_buttons, 
            text="🔗 测试连接", 
            command=self.test_connection, 
            width=110,
            height=35,
            fg_color=("#7B1FA2", "#6A1B9A"),
            hover_color=("#6A1B9A", "#4A148C"),
            font=ctk.CTkFont(size=12)
        )
        test_btn.pack(side="left", padx=(0, 10))
        
        # 手动同步按钮 - 橙色系
        self.manual_sync_btn = ctk.CTkButton(
            left_buttons, 
            text="⚡ 立即同步", 
            command=self.manual_sync, 
            width=110,
            height=35,
            fg_color=("#F57C00", "#EF6C00"),
            hover_color=("#EF6C00", "#E65100"),
            font=ctk.CTkFont(size=12)
        )
        self.manual_sync_btn.pack(side="left", padx=(0, 10))
        
        # 右侧同步控制按钮组
        sync_buttons = ctk.CTkFrame(button_frame, fg_color="transparent")
        sync_buttons.pack(side="right", pady=12)
        
        # 启动同步按钮 - 绿色系
        self.start_btn = ctk.CTkButton(
            sync_buttons, 
            text="▶️ 启动同步", 
            command=self.start_sync, 
            width=110,
            height=35,
            fg_color=("#388E3C", "#2E7D32"),
            hover_color=("#2E7D32", "#1B5E20"),
            font=ctk.CTkFont(size=12)
        )
        self.start_btn.pack(side="left", padx=(0, 8))
        
        # 暂停/继续按钮 - 黄色系
        self.pause_btn = ctk.CTkButton(
            sync_buttons, 
            text="⏸️ 暂停", 
            command=self.toggle_pause, 
            width=85,
            height=35,
            fg_color=("#FFA000", "#FF8F00"),
            hover_color=("#FF8F00", "#FF6F00"),
            font=ctk.CTkFont(size=13, weight="bold"),
            state="disabled"
        )
        self.pause_btn.pack(side="left", padx=(0, 8))
        
        # 停止同步按钮 - 红色系
        self.stop_btn = ctk.CTkButton(
            sync_buttons, 
            text="⏹️ 停止", 
            command=self.stop_sync, 
            width=85,
            height=35,
            fg_color=("#D32F2F", "#C62828"),
            hover_color=("#C62828", "#B71C1C"),
            font=ctk.CTkFont(size=12),
            state="disabled"
        )
        self.stop_btn.pack(side="left")
        
    def select_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.folder_entry.delete(0, tk.END)
            self.folder_entry.insert(0, folder)
            
    def save_settings(self):
        config = {
            'server_url': self.server_entry.get(),
            'local_folder': self.folder_entry.get(),
            'exclude_rules': self.exclude_text.get("1.0", tk.END).strip().split('\n'),
            'sync_interval': int(self.interval_var.get()) if self.interval_var.get().isdigit() else 30,
            'sync_mode': self.sync_mode.get(),
            'username': self.username_entry.get(),
            'password': self.password_entry.get()
        }
        
        self.config_manager.save_config(config)
        self.config = config
        messagebox.showinfo("成功", "设置已保存")
        
    def load_settings(self):
        if self.config:
            self.server_entry.insert(0, self.config.get('server_url', ''))
            self.folder_entry.insert(0, self.config.get('local_folder', ''))
            
            exclude_rules = self.config.get('exclude_rules', [])
            if exclude_rules and exclude_rules != ['']:
                self.exclude_text.insert("1.0", '\n'.join(exclude_rules))
                
            self.interval_var.set(str(self.config.get('sync_interval', 30)))
            self.sync_mode.set(self.config.get('sync_mode', 'mirror'))
            
            self.username_entry.insert(0, self.config.get('username', ''))
            self.password_entry.insert(0, self.config.get('password', ''))
            
    def start_sync(self):
        # 验证设置
        if not self.server_entry.get():
            messagebox.showerror("错误", "请输入服务器地址")
            return
            
        if not self.folder_entry.get():
            messagebox.showerror("错误", "请选择本地同步文件夹")
            return
            
        if not os.path.exists(self.folder_entry.get()):
            messagebox.showerror("错误", "本地文件夹不存在")
            return
            
        # 保存当前设置
        self.save_settings()
        
        # 创建同步引擎
        self.sync_engine = SyncEngine(self.config, self.log_callback, self.stats_callback)
        
        # 启动同步线程
        self.sync_thread = threading.Thread(target=self.sync_engine.start_sync, daemon=True)
        self.sync_thread.start()
        
        self.is_syncing = True
        self.is_paused = False
        
        # 更新按钮状态
        self.start_btn.configure(state="disabled")
        self.pause_btn.configure(state="normal")
        self.stop_btn.configure(state="normal")
        
        self.status_label.configure(text="🔄 状态: 同步中...")
        self.log_message("同步已启动")
        
    def stop_sync(self):
        if self.sync_engine:
            self.sync_engine.stop_sync()
            
        self.is_syncing = False
        self.is_paused = False
        
        # 更新按钮状态
        self.start_btn.configure(state="normal")
        self.pause_btn.configure(state="disabled", text="⏸️ 暂停")
        self.stop_btn.configure(state="disabled")
        
        self.status_label.configure(text="⏹️ 状态: 已停止")
        self.log_message("同步已停止")
        
    def toggle_pause(self):
        """切换暂停/继续状态"""
        if not self.is_syncing:
            return
            
        if not self.is_paused:
            # 暂停同步
            self.is_paused = True
            if self.sync_engine:
                self.sync_engine.pause_sync()
            self.pause_btn.configure(text="▶️ 继续")
            self.status_label.configure(text="⏸️ 状态: 已暂停")
            self.log_message("同步已暂停")
        else:
            # 继续同步
            self.is_paused = False
            if self.sync_engine:
                self.sync_engine.resume_sync()
            self.pause_btn.configure(text="⏸️ 暂停")
            self.status_label.configure(text="🔄 状态: 同步中...")
            self.log_message("同步已继续")
        
    def log_callback(self, message):
        """同步引擎的日志回调"""
        self.after(0, lambda: self.log_message(message))
        
    def stats_callback(self, stats):
        """同步引擎的统计回调"""
        self.after(0, lambda: self.update_stats_display(stats))
        
    def update_stats_display(self, stats):
        """更新统计显示"""
        stats_text = f"统计: 上传 {stats['uploaded']} | 下载 {stats['downloaded']} | 删除 {stats['deleted']}"
        self.stats_label.configure(text=stats_text)
        
    def clear_log(self):
        """清除日志"""
        self.log_text.delete("1.0", tk.END)
        self.log_message("日志已清除")
        
    def manual_sync(self):
        """手动执行一次同步"""
        if not self.server_entry.get():
            messagebox.showerror("错误", "请输入服务器地址")
            return
            
        if not self.folder_entry.get():
            messagebox.showerror("错误", "请选择本地同步文件夹")
            return
            
        if not os.path.exists(self.folder_entry.get()):
            messagebox.showerror("错误", "本地文件夹不存在")
            return
            
        # 保存当前设置
        self.save_settings()
        
        # 禁用手动同步按钮，防止重复点击
        self.manual_sync_btn.configure(state="disabled")
        self.log_message("开始手动同步...")
        
        def run_manual_sync():
            try:
                from .sync_engine import SyncEngine
                temp_engine = SyncEngine(self.config, self.log_callback, self.stats_callback)
                temp_engine.sync_files()
                self.after(0, lambda: self.log_message("手动同步完成"))
            except Exception as e:
                self.after(0, lambda: self.log_message(f"手动同步失败: {str(e)}"))
            finally:
                self.after(0, lambda: self.manual_sync_btn.configure(state="normal"))
        
        # 在后台线程执行手动同步
        threading.Thread(target=run_manual_sync, daemon=True).start()
        
    def test_connection(self):
        """测试服务器连接"""
        server_url = self.server_entry.get()
        if not server_url:
            messagebox.showerror("错误", "请输入服务器地址")
            return
            
        try:
            import requests
            session = requests.Session()
            
            # 设置认证
            username = self.username_entry.get()
            password = self.password_entry.get()
            if username and password:
                session.auth = (username, password)
                
            # 测试健康检查端点
            health_url = f"{server_url.rstrip('/')}/__dufs__/health"
            response = session.get(health_url, timeout=10)
            
            if response.status_code == 200:
                messagebox.showinfo("成功", "服务器连接正常")
                self.log_message("服务器连接测试成功")
            else:
                messagebox.showwarning("警告", f"服务器响应异常: {response.status_code}")
                self.log_message(f"服务器连接测试失败: {response.status_code}")
                
        except requests.exceptions.Timeout:
            messagebox.showerror("错误", "连接超时，请检查服务器地址")
            self.log_message("服务器连接超时")
        except requests.exceptions.ConnectionError:
            messagebox.showerror("错误", "无法连接到服务器，请检查地址和网络")
            self.log_message("服务器连接失败")
        except Exception as e:
            messagebox.showerror("错误", f"连接测试失败: {str(e)}")
            self.log_message(f"服务器连接测试异常: {str(e)}")
    
    def log_message(self, message):
        """添加日志消息"""
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        
        self.log_text.insert(tk.END, log_entry)
        self.log_text.see(tk.END)
        
    def on_closing(self):
        """窗口关闭事件"""
        if self.is_syncing:
            self.stop_sync()
        self.destroy()