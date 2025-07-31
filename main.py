#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dufs同步工具 - 主程序入口
"""

import customtkinter as ctk
from gui.main_window import MainWindow
import sys
import os

def main():
    # 设置customtkinter主题 - 使用现代化配色
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("green")  # 改为绿色主题，更现代
    
    # 创建主窗口
    app = MainWindow()
    
    # 运行应用
    app.mainloop()

if __name__ == "__main__":
    main()