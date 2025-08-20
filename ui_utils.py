"""
UI工具函数模块
负责UI状态管理、进度更新、日志记录等功能
"""

import maya.cmds as cmds
import os


class UIUtils:
    """UI工具函数类"""
    
    def __init__(self, ui_dict):
        self.ui = ui_dict
    
    def update_progress(self, value):
        """更新进度条"""
        cmds.progressBar(self.ui['progress'], edit=True, progress=value)

    def update_button_state(self, button_name, success):
        """更新按钮状态"""
        if success:
            color = [0.3, 0.8, 0.3]  # 绿色表示成功
        else:
            color = [0.8, 0.3, 0.3]  # 红色表示失败

        cmds.button(self.ui[button_name], edit=True, backgroundColor=color)

    def reset_button_states(self):
        """重置所有按钮状态"""
        buttons = ['step1_btn', 'step2_btn', 'step3_btn', 'step4_btn', 'step5_btn', 'step6_btn']
        for btn in buttons:
            if btn in self.ui:
                cmds.button(self.ui[btn], edit=True, backgroundColor=[0.4, 0.6, 0.8])

    def log_message(self, message):
        """添加日志消息"""
        timestamp = cmds.date(format="hh:mm:ss")
        formatted_message = f"[{timestamp}] {message}\n"

        current_text = cmds.scrollField(self.ui['status_text'], query=True, text=True)
        new_text = current_text + formatted_message

        cmds.scrollField(self.ui['status_text'], edit=True, text=new_text)
        
        # 滚动到底部显示最新内容
        try:
            # 获取文本行数
            lines = new_text.count('\n')
            if lines > 10:  # 当行数超过10行时，滚动到底部
                cmds.scrollField(self.ui['status_text'], edit=True, scrollPosition=lines)
        except:
            pass

        # 同时打印到Maya的Script Editor
        print(formatted_message.strip())

    def update_asset_list(self, assets_data):
        """更新资产列表"""
        # 清除现有选项
        menu_items = cmds.optionMenu(self.ui['asset_list'], query=True, itemListLong=True)
        if menu_items:
            cmds.deleteUI(menu_items)

        # 添加新选项
        if assets_data:
            # 调试：打印每个资产的详细信息
            print(f"\n=== 资产列表调试信息 ===")
            print(f"总数据量: {len(assets_data)} 个资产")
            
            for i, asset in enumerate(assets_data, 1):
                asset_name = asset.get('asset_name', 'Unknown')
                asset_type = asset.get('asset_type', 'Unknown')
                outputs = asset.get('outputs', [])
                
                print(f"{i}. {asset_name} (类型: {asset_type})")
                print(f"   输出文件数: {len(outputs)}")
                for j, output in enumerate(outputs, 1):
                    print(f"     {j}. {output}")
                
                # 添加到UI
                display_name = f"{asset_name} ({asset_type})"
                cmds.menuItem(parent=self.ui['asset_list'], label=display_name)
            
            print(f"=== 调试信息结束 ===\n")
            return len(assets_data)
        else:
            cmds.menuItem(parent=self.ui['asset_list'], label="请先选择场次镜头或加载配置文件")
            return 0

    def update_asset_info(self, core):
        """更新资产信息显示"""
        if not core.current_asset:
            return
            
        asset_name = core.current_asset['asset_name']
        asset_type = core.current_asset['asset_type']
        outputs = core.current_asset.get('outputs', [])
        
        info_text = f"资产名称: {asset_name}\n"
        info_text += f"资产类型: {asset_type}\n"
        info_text += f"Lookdev文件: {os.path.basename(core.current_lookdev_file) if core.current_lookdev_file else '未找到'}\n"
        info_text += f"动画文件数: {len(core.current_animation_files)}\n"
        
        # 显示相机文件信息
        if core.current_camera_file:
            camera_info = os.path.basename(core.current_camera_file)
            if core.manual_camera_file:
                camera_info += " (手动)"
            else:
                camera_info += " (自动)"
        else:
            camera_info = "未找到"
        info_text += f"相机文件: {camera_info}\n"
        
        info_text += f"命名空间:\n"
        info_text += f"  Lookdev: {core.lookdev_namespace}\n"
        info_text += f"  动画: {core.animation_namespace}\n"
        info_text += f"  毛发: {core.fur_namespace}\n"
        info_text += f"  布料: {core.cloth_namespace}\n"
        
        cmds.scrollField(self.ui['asset_info'], edit=True, text=info_text)
        
        # 更新相机路径文本框
        if core.current_camera_file and not core.manual_camera_file:
            cmds.textField(self.ui['camera_path'], edit=True, text="")

    def update_namespace(self, core):
        """更新命名空间显示"""
        if core.current_asset:
            namespace = core.lookdev_namespace
            cmds.textField(self.ui['namespace'], edit=True, text=namespace)

    def update_shot_list(self, project_shots):
        """更新场次镜头列表"""
        # 清除现有选项
        menu_items = cmds.optionMenu(self.ui['shot_list'], query=True, itemListLong=True)
        if menu_items:
            cmds.deleteUI(menu_items)
        
        # 添加新选项
        if project_shots:
            # 按场次镜头排序
            sorted_shots = sorted(project_shots.keys())
            
            for shot_key in sorted_shots:
                shot_data = project_shots[shot_key]
                file_count = len(shot_data['animation_files'])
                asset_count = len(shot_data['assets'])
                
                # 格式：s310_c0990 (5文件, 3资产)
                display_text = f"{shot_key} ({file_count}文件, {asset_count}资产)"
                cmds.menuItem(parent=self.ui['shot_list'], label=display_text)
        else:
            cmds.menuItem(parent=self.ui['shot_list'], label="未找到场次镜头")

    def update_config_status(self, success):
        """更新配置状态指示器"""
        if success:
            cmds.text(self.ui['config_status'], edit=True, backgroundColor=[0.3, 0.8, 0.3])
        else:
            cmds.text(self.ui['config_status'], edit=True, backgroundColor=[0.8, 0.3, 0.3])

    def show_confirmation_dialog(self, title, message, buttons=None):
        """显示确认对话框"""
        if buttons is None:
            buttons = ["确定", "取消"]
        
        return cmds.confirmDialog(
            title=title,
            message=message,
            button=buttons,
            defaultButton=buttons[0],
            cancelButton=buttons[-1] if len(buttons) > 1 else buttons[0],
            dismissString=buttons[-1] if len(buttons) > 1 else buttons[0]
        )

    def show_info_dialog(self, title, message):
        """显示信息对话框"""
        return cmds.confirmDialog(
            title=title,
            message=message,
            button=["确定"],
            defaultButton="确定"
        )

    def browse_file_dialog(self, file_filter, caption="选择文件"):
        """显示文件浏览对话框"""
        files = cmds.fileDialog2(
            fileFilter=file_filter,
            dialogStyle=2,
            fileMode=1,
            caption=caption
        )
        return files[0] if files else None

    def save_file_dialog(self, file_filter, caption="保存文件"):
        """显示文件保存对话框"""
        files = cmds.fileDialog2(
            fileFilter=file_filter,
            dialogStyle=2,
            fileMode=0,
            caption=caption
        )
        return files[0] if files else None

    def get_text_field_value(self, field_name):
        """获取文本框值"""
        if field_name in self.ui:
            return cmds.textField(self.ui[field_name], query=True, text=True)
        return ""

    def set_text_field_value(self, field_name, value):
        """设置文本框值"""
        if field_name in self.ui:
            cmds.textField(self.ui[field_name], edit=True, text=value)

    def get_option_menu_value(self, menu_name):
        """获取下拉菜单值"""
        if menu_name in self.ui:
            return cmds.optionMenu(self.ui[menu_name], query=True, value=True)
        return ""

    def clear_option_menu(self, menu_name):
        """清除下拉菜单选项"""
        if menu_name in self.ui:
            menu_items = cmds.optionMenu(self.ui[menu_name], query=True, itemListLong=True)
            if menu_items:
                cmds.deleteUI(menu_items)

    def add_menu_item(self, menu_name, label):
        """添加菜单项"""
        if menu_name in self.ui:
            cmds.menuItem(parent=self.ui[menu_name], label=label)

    def validate_ui_state(self):
        """验证UI状态"""
        validation = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        # 检查必要的UI控件是否存在
        required_controls = [
            'config_path', 'asset_list', 'namespace', 
            'status_text', 'progress'
        ]
        
        for control in required_controls:
            if control not in self.ui:
                validation['errors'].append(f"缺少UI控件: {control}")
                validation['valid'] = False
        
        return validation

    def get_ui_values(self):
        """获取所有UI控件的值"""
        values = {}
        
        # 文本框值
        text_fields = ['config_path', 'namespace', 'camera_path']
        for field in text_fields:
            values[field] = self.get_text_field_value(field)
        
        # 下拉菜单值
        option_menus = ['asset_list', 'shot_list']
        for menu in option_menus:
            values[menu] = self.get_option_menu_value(menu)
        
        # 进度条值
        if 'progress' in self.ui:
            values['progress'] = cmds.progressBar(self.ui['progress'], query=True, progress=True)
        
        return values

    def set_ui_values(self, values):
        """设置UI控件的值"""
        # 文本框值
        text_fields = ['config_path', 'namespace', 'camera_path']
        for field in text_fields:
            if field in values:
                self.set_text_field_value(field, values[field])
        
        # 进度条值
        if 'progress' in values and 'progress' in self.ui:
            cmds.progressBar(self.ui['progress'], edit=True, progress=values['progress'])

    def format_asset_display_info(self, shot_key, assets_data):
        """格式化资产显示信息"""
        if not assets_data:
            return "请选择场次镜头或加载配置文件...\n"
        
        # 提取场次和镜头
        sequence, shot = shot_key.split('_') if '_' in shot_key else ('', shot_key)
        
        info_text = f"已加载 {sequence}_{shot} 配置\n"
        info_text += f"资产数量: {len(assets_data)}\n"
        info_text += f"场次: {sequence}\n"
        info_text += f"镜头: {shot}\n\n"
        
        # 列出资产
        info_text += "包含资产:\n"
        for asset in assets_data:
            asset_name = asset['asset_name']
            asset_type = asset['asset_type']
            file_count = len(asset.get('outputs', []))
            info_text += f"• {asset_name} ({asset_type}) - {file_count}文件\n"
        
        return info_text

    def cleanup_ui(self, window_name):
        """清理UI资源"""
        try:
            if cmds.window(window_name, exists=True):
                cmds.deleteUI(window_name, window=True)
            print("UI清理完成")
        except Exception as e:
            print(f"UI清理失败: {str(e)}")

    def refresh_ui(self):
        """刷新UI显示"""
        try:
            # 刷新窗口
            if 'window' in self.ui:
                cmds.refresh(self.ui['window'])
        except Exception as e:
            print(f"刷新UI失败: {str(e)}")

    def get_window_size(self):
        """获取窗口大小"""
        if 'window' in self.ui:
            try:
                width = cmds.window(self.ui['window'], query=True, width=True)
                height = cmds.window(self.ui['window'], query=True, height=True)
                return width, height
            except:
                pass
        return None, None

    def set_window_size(self, width, height):
        """设置窗口大小"""
        if 'window' in self.ui:
            try:
                cmds.window(self.ui['window'], edit=True, widthHeight=(width, height))
            except Exception as e:
                print(f"设置窗口大小失败: {str(e)}")

    def center_window(self):
        """居中显示窗口"""
        if 'window' in self.ui:
            try:
                # 获取屏幕尺寸
                screen_width = cmds.window(self.ui['window'], query=True, topEdge=True)
                screen_height = cmds.window(self.ui['window'], query=True, leftEdge=True)
                
                # 获取窗口尺寸
                window_width = cmds.window(self.ui['window'], query=True, width=True)
                window_height = cmds.window(self.ui['window'], query=True, height=True)
                
                # 计算居中位置
                x = (screen_width - window_width) // 2
                y = (screen_height - window_height) // 2
                
                cmds.window(self.ui['window'], edit=True, topLeftCorner=(x, y))
            except Exception as e:
                print(f"居中窗口失败: {str(e)}")

    def save_ui_preferences(self, prefs_file):
        """保存UI偏好设置"""
        try:
            prefs = {
                'window_size': self.get_window_size(),
                'ui_values': self.get_ui_values()
            }
            
            import json
            with open(prefs_file, 'w', encoding='utf-8') as f:
                json.dump(prefs, f, indent=2, ensure_ascii=False)
            
            return True
        except Exception as e:
            print(f"保存UI偏好设置失败: {str(e)}")
            return False

    def load_ui_preferences(self, prefs_file):
        """加载UI偏好设置"""
        try:
            if os.path.exists(prefs_file):
                import json
                with open(prefs_file, 'r', encoding='utf-8') as f:
                    prefs = json.load(f)
                
                # 恢复窗口大小
                if 'window_size' in prefs and prefs['window_size'][0]:
                    self.set_window_size(*prefs['window_size'])
                
                # 恢复UI值
                if 'ui_values' in prefs:
                    self.set_ui_values(prefs['ui_values'])
                
                return True
        except Exception as e:
            print(f"加载UI偏好设置失败: {str(e)}")
            return False