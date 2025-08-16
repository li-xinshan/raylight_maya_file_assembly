"""
Lookdev动画组装工具 Maya插件 - 模块化版本
版本：2.0
作者：Maya Pipeline Team

功能特性：
- JSON配置系统，支持多资产处理
- 自动查找lookdev文件和版本管理
- 智能相机路径推导
- 模块化架构，便于维护和扩展
"""

import maya.cmds as cmds
import maya.mel as mel
import maya.OpenMaya as om
import maya.OpenMayaMPx as omm
import os
import functools
import xgenm

# 导入模块化组件
from core_assembler import CoreAssembler
from config_manager import ConfigManager
from file_manager import FileManager
from path_utils import PathUtils


class LookdevAnimationSetupUI:
    """
    Lookdev和动画组装工具 - UI界面
    """

    def __init__(self, config_file=None):
        # 窗口配置
        self.window_name = "LookdevAnimationSetup"
        self.window_title = "Lookdev动画组装工具 v2.0"
        
        # UI控件变量
        self.ui = {}
        
        # 初始化核心组装器
        self.core = CoreAssembler(config_file)
        
        # 当前资产状态
        self.current_asset = None
        self.available_assets = []
        
        # 项目扫描数据
        self.project_shots = {}
        self.current_shot_key = None

    def show_ui(self):
        """显示UI界面"""
        # 删除已存在的窗口
        if cmds.window(self.window_name, exists=True):
            cmds.deleteUI(self.window_name, window=True)

        # 创建窗口
        self.ui['window'] = cmds.window(
            self.window_name,
            title=self.window_title,
            widthHeight=(520, 1200),
            resizeToFitChildren=True,
            menuBar=True
        )

        # 创建菜单
        self.create_menu()

        # 创建主布局
        main_layout = cmds.columnLayout(adjustableColumn=True, rowSpacing=5, columnOffset=('both', 10))

        # 标题
        cmds.text(label="Lookdev动画组装工具 v2.0", font="boldLabelFont", height=30, backgroundColor=[0.2, 0.7, 0.4])
        cmds.separator(height=10)

        # 配置设置区域
        self.create_config_section()
        cmds.separator(height=15)

        # 设置参数区域
        self.create_settings_section()
        cmds.separator(height=15)

        # 执行操作区域
        self.create_execution_section()
        cmds.separator(height=15)

        # 状态显示区域
        self.create_status_section()
        cmds.separator(height=15)

        # 工具按钮区域
        self.create_tools_section()

        # 显示窗口
        cmds.showWindow(self.ui['window'])

        # 更新初始状态
        self.update_asset_list()
        
        # 异步启动项目扫描（避免阻塞UI）
        cmds.evalDeferred(self.scan_project_shots)

    def create_config_section(self):
        """创建配置设置区域"""
        cmds.frameLayout(label="配置设置", collapsable=True, collapse=False, marginWidth=10, marginHeight=10)

        # 项目扫描模式
        cmds.text(label="项目动画选择:", align="left", font="boldLabelFont")
        
        # 场次镜头选择
        shot_row = cmds.rowLayout(numberOfColumns=4, adjustableColumn=2, columnWidth4=(120, 250, 80, 70))
        cmds.text(label="场次/镜头:")
        self.ui['shot_list'] = cmds.optionMenu(label="", changeCommand=self.on_shot_changed)
        cmds.menuItem(label="扫描中...")
        cmds.button(label="扫描项目", command=self.scan_project_shots, width=80)
        cmds.button(label="加载配置", command=self.load_shot_config, width=70)
        cmds.setParent('..')

        cmds.separator(height=10)

        # 或者使用JSON配置文件
        cmds.text(label="或使用JSON配置文件:", align="left", font="boldLabelFont")
        config_row = cmds.rowLayout(numberOfColumns=3, adjustableColumn=2, columnWidth3=(400, 60, 30))
        self.ui['config_path'] = cmds.textField(text="", changeCommand=self.on_config_path_changed)
        cmds.button(label="浏览", command=self.browse_config_file, width=60)
        self.ui['config_status'] = cmds.text(label="●", width=30, backgroundColor=[0.8, 0.3, 0.3])
        cmds.setParent('..')

        cmds.separator(height=10)

        # 资产选择
        cmds.text(label="选择资产:", align="left", font="boldLabelFont")
        asset_row = cmds.rowLayout(numberOfColumns=3, adjustableColumn=2, columnWidth3=(400, 80, 40))
        self.ui['asset_list'] = cmds.optionMenu(label="", changeCommand=self.on_asset_changed)
        cmds.menuItem(label="请先选择场次镜头或加载配置文件")
        cmds.button(label="刷新资产", command=self.refresh_assets, width=80)
        cmds.button(label="详情", command=self.show_asset_details, width=40)
        cmds.setParent('..')

        cmds.separator(height=10)

        # 当前资产信息显示
        cmds.text(label="当前资产信息:", align="left", font="boldLabelFont")
        self.ui['asset_info'] = cmds.scrollField(
            text="请选择场次镜头或加载配置文件...\n",
            editable=False,
            wordWrap=True,
            height=120,
            backgroundColor=[0.25, 0.25, 0.25],
            font="smallFixedWidthFont"
        )

        cmds.setParent('..')  # frameLayout

    def create_settings_section(self):
        """创建设置参数区域"""
        cmds.frameLayout(label="参数设置", collapsable=True, collapse=False, marginWidth=10, marginHeight=10)

        # 命名空间设置
        cmds.rowLayout(numberOfColumns=2, adjustableColumn=2, columnWidth2=(120, 300))
        cmds.text(label="命名空间:", align="left")
        self.ui['namespace'] = cmds.textField(text="asset_lookdev", changeCommand=self.on_namespace_changed)
        cmds.setParent('..')

        cmds.separator(height=10)

        # 相机文件设置
        cmds.text(label="相机文件设置:", align="left", font="boldLabelFont")
        camera_row = cmds.rowLayout(numberOfColumns=3, adjustableColumn=2, columnWidth3=(350, 60, 60))
        self.ui['camera_path'] = cmds.textField(text="", placeholderText="自动查找相机文件...", changeCommand=self.on_camera_path_changed)
        cmds.button(label="浏览", command=self.browse_camera_file, width=60)
        cmds.button(label="清除", command=self.clear_camera_file, width=60)
        cmds.setParent('..')
        
        cmds.separator(height=10)

        cmds.setParent('..')  # frameLayout

    def create_execution_section(self):
        """创建执行操作区域"""
        cmds.frameLayout(label="执行操作", collapsable=True, collapse=False, marginWidth=10, marginHeight=10)

        # 单步执行按钮
        cmds.text(label="分步执行:", align="left", font="boldLabelFont")

        step_col = cmds.columnLayout(adjustableColumn=True, rowSpacing=5)

        self.ui['step1_btn'] = cmds.button(label="步骤1: 导入Lookdev文件",
                                           command=self.step1_import_lookdev,
                                           backgroundColor=[0.4, 0.6, 0.8], height=35)

        self.ui['step2_btn'] = cmds.button(label="步骤2: 导入动画ABC并连接",
                                           command=self.step2_import_and_connect_animation_abc,
                                           backgroundColor=[0.4, 0.6, 0.8], height=35)

        self.ui['step3_btn'] = cmds.button(label="步骤3: 导入动画相机ABC",
                                           command=self.step3_import_camera_abc,
                                           backgroundColor=[0.4, 0.6, 0.8], height=35)

        self.ui['step4_btn'] = cmds.button(label="步骤4: 设置毛发缓存路径",
                                           command=self.step4_setup_hair_cache,
                                           backgroundColor=[0.4, 0.6, 0.8], height=35)

        self.ui['step5_btn'] = cmds.button(label="步骤5: 检查修复材质",
                                           command=self.step5_fix_materials,
                                           backgroundColor=[0.4, 0.6, 0.8], height=35)

        self.ui['step6_btn'] = cmds.button(label="步骤6: 设置场景参数",
                                           command=self.step6_setup_scene,
                                           backgroundColor=[0.4, 0.6, 0.8], height=35)

        cmds.setParent('..')  # step_col

        cmds.separator(height=10)

        # 一键执行
        cmds.text(label="一键执行:", align="left", font="boldLabelFont")

        execute_row = cmds.rowLayout(numberOfColumns=2, adjustableColumn=2, columnWidth2=(200, 200))

        self.ui['execute_all_btn'] = cmds.button(label="🚀 一键完成所有步骤",
                                                 command=self.execute_all_steps,
                                                 backgroundColor=[0.2, 0.8, 0.4], height=45)

        self.ui['reset_btn'] = cmds.button(label="🔄 重置场景",
                                           command=self.reset_scene,
                                           backgroundColor=[0.8, 0.4, 0.2], height=45)

        cmds.setParent('..')  # execute_row
        cmds.setParent('..')  # frameLayout

    def create_status_section(self):
        """创建状态显示区域"""
        cmds.frameLayout(label="状态信息", collapsable=True, collapse=False, marginWidth=10, marginHeight=10)

        # 进度显示
        progress_row = cmds.rowLayout(numberOfColumns=2, adjustableColumn=2, columnWidth2=(80, 320))
        cmds.text(label="执行进度:")
        self.ui['progress'] = cmds.progressBar(maxValue=6, width=320)
        cmds.setParent('..')

        cmds.separator(height=5)

        # 状态文本
        self.ui['status_text'] = cmds.scrollField(
            text="准备就绪，请加载配置文件并选择资产...\n",
            editable=False,
            wordWrap=True,
            height=300,
            backgroundColor=[0.2, 0.2, 0.2],
            font="fixedWidthFont"
        )

        # 状态按钮
        status_btn_row = cmds.rowLayout(numberOfColumns=3, adjustableColumn=3)
        cmds.button(label="清空日志", command=self.clear_log, width=80)
        cmds.button(label="保存日志", command=self.save_log, width=80)
        cmds.text(label="")  # 占位符
        cmds.setParent('..')

        cmds.setParent('..')  # frameLayout

    def create_tools_section(self):
        """创建工具按钮区域"""
        cmds.frameLayout(label="附加工具", collapsable=True, collapse=True, marginWidth=10, marginHeight=10)

        # 第一行工具
        tools_row1 = cmds.rowLayout(numberOfColumns=4, adjustableColumn=4)
        cmds.button(label="播放动画", command=self.play_animation, width=100)
        cmds.button(label="停止动画", command=self.stop_animation, width=100)
        cmds.button(label="适配视图", command=self.fit_view, width=100)
        cmds.text(label="")
        cmds.setParent('..')

        # 第二行工具
        tools_row2 = cmds.rowLayout(numberOfColumns=4, adjustableColumn=4)
        cmds.button(label="检查材质", command=self.check_materials, width=100)
        cmds.button(label="检查纹理", command=self.check_textures, width=100)
        cmds.button(label="处理特殊组", command=self.handle_special_groups, width=100)
        cmds.button(label="修复布料驱动", command=self.handle_cloth_blendshapes, width=100, backgroundColor=[0.8, 0.6, 0.4])
        cmds.setParent('..')

        # 第三行工具
        tools_row3 = cmds.rowLayout(numberOfColumns=4, adjustableColumn=4)
        cmds.button(label="检查XGen", command=self.check_xgen, width=100)
        cmds.button(label="打开文件夹", command=self.open_folder, width=100)
        cmds.button(label="场景信息", command=self.show_scene_info, width=100)
        cmds.button(label="导出报告", command=self.export_report, width=100)
        cmds.setParent('..')

        cmds.setParent('..')  # frameLayout

    def create_menu(self):
        """创建菜单栏"""
        # 文件菜单
        file_menu = cmds.menu(label="文件")
        cmds.menuItem(label="加载JSON配置", command=self.load_json_config)
        cmds.menuItem(label="保存配置", command=self.save_config)
        cmds.menuItem(divider=True)
        cmds.menuItem(label="退出", command=self.close_window)

        # 工具菜单
        tools_menu = cmds.menu(label="工具")
        cmds.menuItem(label="刷新资产列表", command=lambda x: self.update_asset_list())
        cmds.menuItem(label="验证配置", command=self.validate_config)
        cmds.menuItem(label="清理场景", command=self.clean_scene)
        cmds.menuItem(divider=True)
        cmds.menuItem(label="重载插件", command=self.reload_plugins)

        # 帮助菜单
        help_menu = cmds.menu(label="帮助")
        cmds.menuItem(label="关于", command=self.show_about)
        cmds.menuItem(label="使用说明", command=self.show_help)

    # ===== 事件处理函数 =====

    def on_config_path_changed(self, *args):
        """配置文件路径改变时的回调"""
        config_path = cmds.textField(self.ui['config_path'], query=True, text=True)
        if config_path and os.path.exists(config_path):
            success = self.core.load_config(config_path)
            if success:
                self.update_asset_list()
                cmds.text(self.ui['config_status'], edit=True, backgroundColor=[0.3, 0.8, 0.3])
            else:
                cmds.text(self.ui['config_status'], edit=True, backgroundColor=[0.8, 0.3, 0.3])
        else:
            cmds.text(self.ui['config_status'], edit=True, backgroundColor=[0.8, 0.3, 0.3])

    def browse_config_file(self, *args):
        """浏览JSON配置文件"""
        file_filter = "JSON Files (*.json);;All Files (*.*)"
        files = cmds.fileDialog2(fileFilter=file_filter, dialogStyle=2, fileMode=1)
        if files:
            config_file = files[0]
            cmds.textField(self.ui['config_path'], edit=True, text=config_file)
            self.on_config_path_changed()

    def on_asset_changed(self, *args):
        """资产选择改变时的回调"""
        selected_asset = cmds.optionMenu(self.ui['asset_list'], query=True, value=True)
        if selected_asset and selected_asset != "请先加载配置文件" and selected_asset != "请先选择场次镜头或加载配置文件":
            # 解析资产名称：从 "dwl (chr)" 提取 "dwl"
            if " (" in selected_asset and selected_asset.endswith(")"):
                asset_name = selected_asset.split(" (")[0]
            else:
                asset_name = selected_asset
            
            print(f"选择资产: {selected_asset} -> 解析为: {asset_name}")
            success = self.core.set_current_asset(asset_name)
            if success:
                self.update_asset_info()
                self.update_namespace()

    def refresh_assets(self, *args):
        """刷新资产列表"""
        self.update_asset_list()

    def show_asset_details(self, *args):
        """显示资产详情"""
        if self.core.current_asset:
            summary = self.core.get_current_config_summary()
            details = f"""当前资产详情：

资产名称: {summary['asset']}
Lookdev文件: {summary['lookdev_file']}
动画文件数量: {summary['animation_files_count']}
相机文件: {summary['camera_file']}
命名空间: {summary['namespace']}
时间范围: {summary['time_range']}

执行状态:"""
            
            for step, status in summary['status'].items():
                status_icon = "✅" if status else "❌"
                details += f"\n{step}: {status_icon}"
            
            cmds.confirmDialog(
                title="资产详情",
                message=details,
                button=["确定"],
                defaultButton="确定"
            )

    def update_asset_list(self):
        """更新资产列表"""
        # 清除现有选项
        menu_items = cmds.optionMenu(self.ui['asset_list'], query=True, itemListLong=True)
        if menu_items:
            cmds.deleteUI(menu_items)

        # 添加新选项
        assets_data = self.core.config_manager.get_assets_data()
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
            self.log_message(f"已加载 {len(assets_data)} 个资产配置")
        else:
            cmds.menuItem(parent=self.ui['asset_list'], label="请先选择场次镜头或加载配置文件")

    def update_asset_info(self):
        """更新资产信息显示"""
        if not self.core.current_asset:
            return
            
        asset_name = self.core.current_asset['asset_name']
        asset_type = self.core.current_asset['asset_type']
        outputs = self.core.current_asset.get('outputs', [])
        
        info_text = f"资产名称: {asset_name}\n"
        info_text += f"资产类型: {asset_type}\n"
        info_text += f"Lookdev文件: {os.path.basename(self.core.current_lookdev_file) if self.core.current_lookdev_file else '未找到'}\n"
        info_text += f"动画文件数: {len(self.core.current_animation_files)}\n"
        
        # 显示相机文件信息
        if self.core.current_camera_file:
            camera_info = os.path.basename(self.core.current_camera_file)
            if self.core.manual_camera_file:
                camera_info += " (手动)"
            else:
                camera_info += " (自动)"
        else:
            camera_info = "未找到"
        info_text += f"相机文件: {camera_info}\n"
        
        info_text += f"命名空间:\n"
        info_text += f"  Lookdev: {self.core.lookdev_namespace}\n"
        info_text += f"  动画: {self.core.animation_namespace}\n"
        info_text += f"  毛发: {self.core.fur_namespace}\n"
        info_text += f"  布料: {self.core.cloth_namespace}\n"
        
        cmds.scrollField(self.ui['asset_info'], edit=True, text=info_text)
        
        # 更新相机路径文本框
        if self.core.current_camera_file and not self.core.manual_camera_file:
            cmds.textField(self.ui['camera_path'], edit=True, text="")

    def update_namespace(self):
        """更新命名空间显示"""
        if self.core.current_asset:
            namespace = self.core.lookdev_namespace
            cmds.textField(self.ui['namespace'], edit=True, text=namespace)

    def on_camera_path_changed(self, *args):
        """相机文件路径改变时的回调"""
        camera_path = cmds.textField(self.ui['camera_path'], query=True, text=True)
        if camera_path:
            success = self.core.set_manual_camera_file(camera_path)
            if success:
                self.log_message(f"✅ 手动设置相机文件: {os.path.basename(camera_path)}")
            else:
                self.log_message(f"❌ 相机文件无效或不存在")
    
    def browse_camera_file(self, *args):
        """浏览相机ABC文件"""
        file_filter = "Alembic Files (*.abc);;All Files (*.*)"
        files = cmds.fileDialog2(fileFilter=file_filter, dialogStyle=2, fileMode=1)
        if files:
            camera_file = files[0]
            cmds.textField(self.ui['camera_path'], edit=True, text=camera_file)
            self.on_camera_path_changed()
    
    def clear_camera_file(self, *args):
        """清除手动指定的相机文件"""
        cmds.textField(self.ui['camera_path'], edit=True, text="")
        self.core.manual_camera_file = None
        self.log_message("已清除手动指定的相机文件，将使用自动查找")
        # 重新查找相机文件
        self.core._find_camera_file()
        if self.core.current_camera_file:
            self.log_message(f"自动找到相机文件: {os.path.basename(self.core.current_camera_file)}")
        else:
            self.log_message("未能自动找到相机文件")


    def load_json_config(self, *args):
        """加载JSON配置菜单命令"""
        self.browse_config_file()

    def validate_config(self, *args):
        """验证配置"""
        result = self.core.config_manager.validate_config()
        
        if result['valid']:
            message = "配置验证成功！\n\n"
            if result['warnings']:
                message += "警告：\n"
                for warning in result['warnings']:
                    message += f"• {warning}\n"
        else:
            message = "配置验证失败！\n\n错误：\n"
            for error in result['errors']:
                message += f"• {error}\n"
                
            if result['warnings']:
                message += "\n警告：\n"
                for warning in result['warnings']:
                    message += f"• {warning}\n"
        
        cmds.confirmDialog(
            title="配置验证结果",
            message=message,
            button=["确定"],
            defaultButton="确定"
        )

    def on_namespace_changed(self, *args):
        """命名空间改变时的回调"""
        namespace = cmds.textField(self.ui['namespace'], query=True, text=True)
        if hasattr(self.core, 'lookdev_namespace'):
            self.core.lookdev_namespace = namespace


    # ===== 执行步骤函数 =====

    def step1_import_lookdev(self, *args):
        """步骤1: 导入Lookdev文件"""
        self.log_message("\n=== 步骤1: 导入Lookdev文件 ===")
        self.update_progress(1)

        try:
            success = self.core.step1_import_lookdev()
            
            if success:
                self.log_message("✅ Lookdev文件导入成功")
                self.update_button_state('step1_btn', True)
            else:
                self.log_message("❌ Lookdev文件导入失败")
                self.update_button_state('step1_btn', False)
        except Exception as e:
            self.log_message(f"❌ 步骤1执行出错: {str(e)}")
            self.update_button_state('step1_btn', False)

    def step2_import_and_connect_animation_abc(self, *args):
        """步骤2: 导入动画ABC并连接"""
        self.log_message("\n=== 步骤2: 导入动画ABC并连接 ===")
        self.update_progress(2)

        try:
            success = self.core.step2_import_and_connect_animation_abc()
            
            if success:
                self.log_message("✅ 动画ABC缓存导入并连接成功")
                self.update_button_state('step2_btn', True)
            else:
                self.log_message("❌ 动画ABC缓存导入失败")
                self.update_button_state('step2_btn', False)
        except Exception as e:
            self.log_message(f"❌ 步骤2执行出错: {str(e)}")
            self.update_button_state('step2_btn', False)

    def step3_import_camera_abc(self, *args):
        """步骤3: 导入动画相机ABC"""
        self.log_message("\n=== 步骤3: 导入动画相机ABC ===")
        self.update_progress(3)

        try:
            success = self.core.step3_import_camera_abc()
            
            if success:
                self.log_message("✅ 动画相机ABC导入成功")
                self.update_button_state('step3_btn', True)
            else:
                self.log_message("❌ 动画相机ABC导入失败")
                self.update_button_state('step3_btn', False)
        except Exception as e:
            self.log_message(f"❌ 步骤3执行出错: {str(e)}")
            self.update_button_state('step3_btn', False)

    def step4_setup_hair_cache(self, *args):
        """步骤4: 设置毛发缓存路径"""
        self.log_message("\n=== 步骤4: 设置毛发缓存路径 ===")
        self.update_progress(4)

        try:
            success = self.core.step4_setup_hair_cache()
            
            if success:
                self.log_message("✅ 毛发缓存路径设置成功")
                self.update_button_state('step4_btn', True)
            else:
                self.log_message("❌ 毛发缓存路径设置失败")
                self.update_button_state('step4_btn', False)
        except Exception as e:
            self.log_message(f"❌ 步骤4执行出错: {str(e)}")
            self.update_button_state('step4_btn', False)

    def step5_fix_materials(self, *args):
        """步骤5: 检查修复材质"""
        self.log_message("\n=== 步骤5: 检查修复材质 ===")
        self.update_progress(5)

        try:
            success = self.core.step5_fix_materials()
                
            if success:
                self.log_message("✅ 材质检查修复完成")
                self.update_button_state('step5_btn', True)
            else:
                self.update_button_state('step5_btn', False)
        except Exception as e:
            self.log_message(f"❌ 步骤5执行出错: {str(e)}")
            self.update_button_state('step5_btn', False)

    def step6_setup_scene(self, *args):
        """步骤6: 设置场景参数"""
        self.log_message("\n=== 步骤6: 设置场景参数 ===")
        self.update_progress(6)

        try:
            success = self.core.step6_setup_scene()
                
            if success:
                self.log_message("✅ 场景参数设置完成")
                self.update_button_state('step6_btn', True)
            else:
                self.update_button_state('step6_btn', False)
        except Exception as e:
            self.log_message(f"❌ 步骤6执行出错: {str(e)}")
            self.update_button_state('step6_btn', False)

    def execute_all_steps(self, *args):
        """一键执行所有步骤"""
        self.log_message("\n" + "=" * 50)
        self.log_message("开始一键执行所有步骤")
        self.log_message("=" * 50)

        # 重置进度
        self.update_progress(0)
        self.reset_button_states()

        try:
            # 检查是否选择了资产
            if not self.core.current_asset:
                self.log_message("❌ 请先选择资产")
                return
            
            success = self.core.execute_all_steps()
            if success:
                self.log_message("\n🎉 所有步骤执行完成！")
                self.update_progress(6)
                # 更新所有按钮状态为成功
                for btn in ['step1_btn', 'step2_btn', 'step3_btn', 'step4_btn', 'step5_btn', 'step6_btn']:
                    self.update_button_state(btn, True)
            else:
                self.log_message("\n⚠️  执行过程中遇到问题")
                    
        except Exception as e:
            self.log_message(f"❌ 执行过程出错: {str(e)}")

    def reset_scene(self, *args):
        """重置场景"""
        result = cmds.confirmDialog(
            title="确认重置",
            message="这将删除所有引用和导入的内容，是否继续？",
            button=["确定", "取消"],
            defaultButton="取消",
            cancelButton="取消",
            dismissString="取消"
        )

        if result == "确定":
            self.log_message("\n=== 重置场景 ===")
            try:
                # 删除所有引用
                refs = cmds.ls(type="reference")
                for ref in refs:
                    if ref != "sharedReferenceNode":
                        try:
                            cmds.file(removeReference=True, referenceNode=ref)
                        except:
                            pass

                # 删除所有ABC节点
                abc_nodes = cmds.ls(type="AlembicNode")
                for node in abc_nodes:
                    try:
                        cmds.delete(node)
                    except:
                        pass

                # 重置UI状态
                self.update_progress(0)
                self.reset_button_states()
                self.log_message("✅ 场景重置完成")

                # 重置组装状态
                self.core.reset_assembly_status()

            except Exception as e:
                self.log_message(f"❌ 场景重置失败: {str(e)}")

    # ===== 工具函数 =====

    def play_animation(self, *args):
        """播放动画"""
        cmds.play(forward=True)
        self.log_message("开始播放动画")

    def stop_animation(self, *args):
        """停止动画"""
        cmds.play(state=False)
        self.log_message("停止播放动画")

    def fit_view(self, *args):
        """适配视图"""
        cmds.select(all=True)
        cmds.viewFit()
        cmds.select(clear=True)
        self.log_message("视图已适配")

    def check_materials(self, *args):
        """检查材质"""
        self.log_message("\n=== 材质检查 ===")
        try:
            self.core._check_unmaterialized_objects()
        except Exception as e:
            self.log_message(f"材质检查失败: {str(e)}")

    def check_textures(self, *args):
        """检查纹理"""
        self.log_message("\n=== 纹理检查 ===")
        try:
            self.core._fix_missing_textures()
        except Exception as e:
            self.log_message(f"纹理检查失败: {str(e)}")

    def select_abc_nodes(self, *args):
        """选择ABC节点"""
        abc_nodes = cmds.ls(type="AlembicNode")
        if abc_nodes:
            cmds.select(abc_nodes)
            self.log_message(f"已选择{len(abc_nodes)}个ABC节点")
        else:
            self.log_message("场景中没有ABC节点")

    def handle_special_groups(self, *args):
        """处理特殊组的blendShape连接"""
        self.log_message("\n=== 手动处理特殊组 ===")
        try:
            if not self.core.current_asset:
                self.log_message("❌ 请先选择资产")
                return
            
            success = self.core._handle_special_groups_blendshape()
            if success:
                self.log_message("✅ 特殊组处理完成")
            else:
                self.log_message("⚠️  特殊组处理未完成或无需处理")
        except Exception as e:
            self.log_message(f"❌ 特殊组处理失败: {str(e)}")
    
    def handle_cloth_blendshapes(self, *args):
        """手动处理布料blendShape连接"""
        self.log_message("\n=== 手动处理布料BlendShape ===")
        try:
            if not self.core.current_asset:
                self.log_message("❌ 请先选择资产")
                return
            
            # 获取当前资产名称
            asset_name = self.core.current_asset.get('asset_name', '')
            self.log_message(f"当前资产: {asset_name}")
            
            # 查找cloth组和clothes组
            cloth_group = None
            clothes_group = None
            
            # 查找cloth组（可能在cloth命名空间下）
            if hasattr(self.core, 'actual_cloth_namespace'):
                namespace = self.core.actual_cloth_namespace
            else:
                namespace = self.core.cloth_namespace
                
            # 查找cloth组 - 优先查找包含资产名称的组
            cloth_transforms = cmds.ls(f"{namespace}:*", type='transform', long=True) or []
            for transform in cloth_transforms:
                if not cmds.listRelatives(transform, parent=True):  # 顶层组
                    transform_name = transform.split('|')[-1].split(':')[-1]
                    if asset_name and asset_name.lower() in transform_name.lower():
                        cloth_group = transform
                        break
            
            # 如果没找到包含资产名的组，使用第一个顶层组
            if not cloth_group:
                for transform in cloth_transforms:
                    if not cmds.listRelatives(transform, parent=True):  # 顶层组
                        cloth_group = transform
                        break
            
            if not cloth_group:
                # 尝试不带命名空间查找
                all_transforms = cmds.ls(type='transform', long=True)
                for transform in all_transforms:
                    if 'cloth' in transform.lower() and not cmds.listRelatives(transform, parent=True):
                        transform_name = transform.split('|')[-1]
                        if (namespace in transform or 'cloth' in transform_name.lower()) and \
                           (not asset_name or asset_name.lower() in transform_name.lower()):
                            cloth_group = transform
                            break
            
            if not cloth_group:
                self.log_message("❌ 未找到cloth组")
                return
                
            self.log_message(f"找到cloth组: {cloth_group}")
            
            # 查找clothes组 - 优先查找包含资产名称的组
            clothes_group = self.core._find_clothes_group(asset_name)
            
            if not clothes_group:
                self.log_message("❌ 未找到clothes组")
                return
                
            self.log_message(f"找到clothes组: {clothes_group}")
            
            # 创建blendShape连接
            success = self.core._create_cloth_blendshapes(cloth_group, clothes_group)
            
            if success:
                self.log_message("✅ 布料BlendShape处理完成")
                # 隐藏cloth组
                try:
                    cmds.setAttr(cloth_group + '.visibility', 0)
                    self.log_message(f"已隐藏cloth组")
                except:
                    pass
            else:
                self.log_message("❌ 布料BlendShape处理失败")
                
        except Exception as e:
            self.log_message(f"❌ 布料BlendShape处理失败: {str(e)}")

    def check_xgen(self, *args):
        """检查XGen状态"""
        self.log_message("\n=== XGen检查 ===")
        try:
            if hasattr(self.core, 'check_xgen_status'):
                self.core.check_xgen_status()
            else:
                self.log_message("XGen检查功能不可用")
        except Exception as e:
            self.log_message(f"XGen检查失败: {str(e)}")

    def open_folder(self, *args):
        """打开文件夹"""
        import subprocess
        
        if self.core.current_lookdev_file:
            folder_path = os.path.dirname(self.core.current_lookdev_file)
        else:
            self.log_message("没有可打开的文件夹")
            return
            
        if os.path.exists(folder_path):
            if os.name == 'nt':  # Windows
                subprocess.Popen(['explorer', folder_path])
            else:  # macOS/Linux
                subprocess.Popen(['open', folder_path])
            self.log_message(f"已打开文件夹: {folder_path}")
        else:
            self.log_message("文件夹不存在")

    def show_scene_info(self, *args):
        """显示场景信息"""
        self.log_message("\n=== 场景信息 ===")
        try:
            # 统计信息
            all_meshes = cmds.ls(type="mesh", noIntermediate=True)
            abc_nodes = cmds.ls(type="AlembicNode")
            shading_groups = cmds.ls(type="shadingEngine")

            self.log_message(f"几何体数量: {len(all_meshes)}")
            self.log_message(f"ABC节点数量: {len(abc_nodes)}")
            self.log_message(f"材质组数量: {len(shading_groups)}")

            # XGen信息
            try:
                palettes = xgenm.palettes()
                total_descriptions = 0
                for palette in palettes:
                    descriptions = xgenm.descriptions(palette)
                    total_descriptions += len(descriptions)

                self.log_message(f"XGen调色板数量: {len(palettes)}")
                self.log_message(f"XGen描述数量: {total_descriptions}")
            except:
                self.log_message("XGen信息获取失败")

            # 时间范围
            min_time = cmds.playbackOptions(query=True, min=True)
            max_time = cmds.playbackOptions(query=True, max=True)
            current_time = cmds.currentTime(query=True)
            self.log_message(f"时间范围: {min_time} - {max_time} (当前: {current_time})")

        except Exception as e:
            self.log_message(f"获取场景信息失败: {str(e)}")

    def export_report(self, *args):
        """导出报告"""
        # 获取日志内容
        log_content = cmds.scrollField(self.ui['status_text'], query=True, text=True)

        # 保存到文件
        report_file = cmds.fileDialog2(
            fileFilter="Text Files (*.txt)",
            dialogStyle=2,
            fileMode=0,
            caption="保存报告"
        )

        if report_file:
            try:
                with open(report_file[0], 'w', encoding='utf-8') as f:
                    f.write("Lookdev动画组装工具 - 执行报告\n")
                    f.write("=" * 50 + "\n")
                    f.write(f"生成时间: {cmds.date()}\n")
                    f.write(f"场景文件: {cmds.file(query=True, sceneName=True)}\n")
                    f.write(f"工具版本: v2.0 (模块化)\n")
                    f.write("=" * 50 + "\n\n")
                    f.write(log_content)

                self.log_message(f"报告已保存: {report_file[0]}")
            except Exception as e:
                self.log_message(f"保存报告失败: {str(e)}")

    # ===== UI辅助函数 =====

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

    def clear_log(self, *args):
        """清空日志"""
        cmds.scrollField(self.ui['status_text'], edit=True, text="日志已清空\n")

    def save_log(self, *args):
        """保存日志"""
        log_content = cmds.scrollField(self.ui['status_text'], query=True, text=True)
        log_file = cmds.fileDialog2(
            fileFilter="Text Files (*.txt)",
            dialogStyle=2,
            fileMode=0,
            caption="保存日志"
        )

        if log_file:
            try:
                with open(log_file[0], 'w', encoding='utf-8') as f:
                    f.write(log_content)
                self.log_message(f"日志已保存: {log_file[0]}")
            except Exception as e:
                self.log_message(f"保存日志失败: {str(e)}")

    # ===== 菜单功能 =====

    def save_config(self, *args):
        """保存配置"""
        config_file = cmds.fileDialog2(
            fileFilter="JSON Files (*.json)",
            dialogStyle=2,
            fileMode=0,
            caption="保存配置"
        )
        
        if config_file:
            success = self.core.config_manager.export_config(config_file[0])
            if success:
                self.log_message(f"配置已保存: {config_file[0]}")
            else:
                self.log_message("保存配置失败")

    def clean_scene(self, *args):
        """清理场景"""
        result = cmds.confirmDialog(
            title="清理场景",
            message="这将删除未使用的节点，是否继续？",
            button=["确定", "取消"],
            defaultButton="取消"
        )

        if result == "确定":
            try:
                mel.eval("MLdeleteUnused")
                self.log_message("场景清理完成")
            except Exception as e:
                self.log_message(f"场景清理失败: {str(e)}")

    def reload_plugins(self, *args):
        """重新加载插件"""
        plugins = ['AbcImport', 'AbcExport', 'xgenToolkit']
        for plugin in plugins:
            try:
                if cmds.pluginInfo(plugin, query=True, loaded=True):
                    cmds.unloadPlugin(plugin)
                cmds.loadPlugin(plugin)
                self.log_message(f"插件 {plugin} 重新加载成功")
            except Exception as e:
                self.log_message(f"插件 {plugin} 重新加载失败: {str(e)}")

    def close_window(self, *args):
        """关闭窗口"""
        if cmds.window(self.window_name, exists=True):
            cmds.deleteUI(self.window_name, window=True)

    def show_about(self, *args):
        """显示关于信息"""
        about_text = """Lookdev动画组装工具 v2.0

✅ 模块化系统

功能：
• 自动导入Lookdev文件
• 导入动画ABC缓存并连接到Lookdev几何体
• 导入动画相机ABC
• 从相机ABC自动获取时间范围
• 设置XGen毛发缓存路径
• 材质检查和修复
• 场景参数自动设置

新功能 (v2.0):
• JSON配置文件支持
• 自动Lookdev文件查找
• 智能相机路径推导
• 模块化架构

作者：Maya Pipeline Team
版本：2.0"""

        cmds.confirmDialog(
            title="关于",
            message=about_text,
            button=["确定"],
            defaultButton="确定"
        )

    def show_help(self, *args):
        """显示帮助信息"""
        help_text = """使用说明 (v2.0 模块化系统)：

1. 加载JSON配置文件
   - 点击"浏览"选择JSON配置文件
   - 配置文件格式参考 example_config.json

2. 选择资产
   - 从下拉列表中选择要处理的资产
   - 系统会自动查找对应的文件

3. 调整参数
   - 设置命名空间
   - 设置时间范围（可从资产自动获取）

4. 执行操作
   - 可以分步执行各个步骤
   - 也可以一键完成所有操作

5. 检查结果
   - 查看状态日志
   - 使用附加工具检查

新功能：
• JSON配置文件：支持多资产批量处理
• 自动文件查找：智能定位Lookdev和相机文件
• 版本管理：自动选择最新版本文件
• 路径推导：从动画文件自动推导相机路径

注意事项：
• 确保JSON配置文件格式正确
• Lookdev文件路径结构需符合规范
• 动画和相机文件需在预期位置"""

        cmds.confirmDialog(
            title="使用说明",
            message=help_text,
            button=["确定"],
            defaultButton="确定"
        )
    
    # 项目扫描相关方法
    def scan_project_shots(self, *args):
        """扫描项目场次镜头"""
        try:
            self.log_message("开始多线程扫描项目动画文件...")
            
            # 定义进度回调函数
            def progress_callback(current, total, message):
                progress = int((current / total) * 100) if total > 0 else 0
                self.log_message(f"📊 扫描进度 {progress}%: {message}")
            
            # 获取扫描数据（支持进度回调）
            self.project_shots = self.core.config_manager.scan_project_animation_files(progress_callback)
            
            # 更新combobox
            self.update_shot_list()
            
            if self.project_shots:
                self.log_message(f"✅ 扫描完成，找到 {len(self.project_shots)} 个完整场次/镜头")
            else:
                self.log_message("❌ 未找到任何完整的场次/镜头")
                
        except Exception as e:
            self.log_message(f"❌ 扫描项目失败: {str(e)}")
    
    def update_shot_list(self):
        """更新场次镜头列表"""
        # 清除现有选项
        menu_items = cmds.optionMenu(self.ui['shot_list'], query=True, itemListLong=True)
        if menu_items:
            cmds.deleteUI(menu_items)
        
        # 添加新选项
        if self.project_shots:
            # 按场次镜头排序
            sorted_shots = sorted(self.project_shots.keys())
            
            for shot_key in sorted_shots:
                shot_data = self.project_shots[shot_key]
                file_count = len(shot_data['animation_files'])
                asset_count = len(shot_data['assets'])
                
                # 格式：s310_c0990 (5文件, 3资产)
                display_text = f"{shot_key} ({file_count}文件, {asset_count}资产)"
                cmds.menuItem(parent=self.ui['shot_list'], label=display_text)
        else:
            cmds.menuItem(parent=self.ui['shot_list'], label="未找到场次镜头")
    
    def on_shot_changed(self, *args):
        """场次镜头选择变化回调 - 直接加载配置"""
        try:
            selected_item = cmds.optionMenu(self.ui['shot_list'], query=True, value=True)
            
            if selected_item and "未找到" not in selected_item and "扫描中" not in selected_item:
                # 提取场次镜头key（格式：s310_c0990 (5文件, 3资产)）
                shot_key = selected_item.split(' ')[0]  # 取第一部分 s310_c0990
                
                if shot_key in self.project_shots:
                    self.current_shot_key = shot_key
                    shot_data = self.project_shots[shot_key]
                    
                    self.log_message(f"选择场次镜头: {shot_key}")
                    
                    # 直接加载配置
                    self._load_shot_config_internal(shot_key, shot_data)
                    
        except Exception as e:
            self.log_message(f"❌ 场次镜头选择失败: {str(e)}")
    
    def _load_shot_config_internal(self, shot_key, shot_data):
        """内部方法：加载场次镜头配置"""
        try:
            # 提取场次和镜头
            sequence, shot = shot_key.split('_')
            
            # 使用配置管理器创建配置（传递已有的扫描数据避免重复扫描）
            success = self.core.config_manager.create_config_from_shot_data(sequence, shot, None, self.project_shots)
            
            if success:
                # 更新UI
                self.update_asset_list()
                
                # 更新状态指示器
                cmds.text(self.ui['config_status'], edit=True, backgroundColor=[0.3, 0.8, 0.3])
                
                # 显示配置信息
                assets_data = self.core.config_manager.get_assets_data()
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
                
                cmds.scrollField(self.ui['asset_info'], edit=True, text=info_text)
                
                self.log_message(f"✅ 已自动加载 {sequence}_{shot} 配置，包含 {len(assets_data)} 个资产")
                
            else:
                self.log_message(f"❌ 加载 {shot_key} 配置失败")
                cmds.text(self.ui['config_status'], edit=True, backgroundColor=[0.8, 0.3, 0.3])
                
        except Exception as e:
            self.log_message(f"❌ 加载配置时出错: {str(e)}")
            cmds.text(self.ui['config_status'], edit=True, backgroundColor=[0.8, 0.3, 0.3])
    
    def load_shot_config(self, *args):
        """加载选中场次镜头的配置"""
        try:
            if not self.current_shot_key:
                self.log_message("❌ 请先选择场次镜头")
                return
            
            if self.current_shot_key not in self.project_shots:
                self.log_message("❌ 场次镜头数据无效")
                return
            
            shot_data = self.project_shots[self.current_shot_key]
            self.log_message(f"手动加载 {self.current_shot_key} 的配置...")
            
            # 调用内部方法
            self._load_shot_config_internal(self.current_shot_key, shot_data)
                
        except Exception as e:
            self.log_message(f"❌ 加载场次镜头配置失败: {str(e)}")


# ===== 插件功能函数 =====

def show_lookdev_animation_setup_ui(config_file=None, *args):
    """显示Lookdev动画组装工具UI"""
    ui = LookdevAnimationSetupUI(config_file)
    ui.show_ui()
    return ui


def quick_setup_lookdev_animation(*args):
    """快速设置Lookdev动画"""
    selected = cmds.ls(selection=True)
    if len(selected) >= 2:
        core = CoreAssembler()
        cmds.headsUpMessage("快速设置功能开发中...")
    else:
        cmds.warning("请选择Lookdev文件和ABC文件")


def get_time_from_selected_abc(*args):
    """从选择的ABC文件获取时间范围"""
    selected = cmds.ls(selection=True)
    if selected:
        abc_nodes = [node for node in selected if cmds.nodeType(node) == "AlembicNode"]
        if abc_nodes:
            abc_node = abc_nodes[0]
            start_frame = cmds.getAttr(f"{abc_node}.startFrame")
            end_frame = cmds.getAttr(f"{abc_node}.endFrame")

            cmds.playbackOptions(min=start_frame, max=end_frame)
            cmds.currentTime(start_frame)

            cmds.headsUpMessage(f"时间范围已设置: {start_frame} - {end_frame}")
        else:
            cmds.warning("请选择ABC节点")
    else:
        cmds.warning("请选择ABC节点")


# ===== 插件初始化和清理 =====

def initializePlugin(mobject):
    """Initialize the script plug-in"""
    mplugin = omm.MFnPlugin(mobject, "LookdevAnimationTools", "2.0", "any")

    # 删除已存在的菜单
    if cmds.menu("menuLookdevAnimation", exists=True):
        cmds.deleteUI("menuLookdevAnimation", menu=True)

    # 获取主窗口
    gMainWindow = mel.eval("global string $gMainWindow;$temp = $gMainWindow")

    # 创建主菜单
    cmds.menu("menuLookdevAnimation",
              label="Lookdev动画工具 v2.0",
              parent=gMainWindow,
              tearOff=True)

    # 添加菜单项
    cmds.menuItem(label="显示主界面",
                  command=show_lookdev_animation_setup_ui,
                  annotation="打开Lookdev动画组装工具主界面")

    cmds.menuItem(label="显示主界面 (带配置)",
                  command=lambda x: show_lookdev_animation_setup_ui("example_config.json"),
                  annotation="打开主界面并加载示例配置")

    cmds.menuItem(divider=True)

    cmds.menuItem(label="快速设置",
                  command=quick_setup_lookdev_animation,
                  annotation="快速设置Lookdev和动画")

    cmds.menuItem(label="从选择ABC获取时间",
                  command=get_time_from_selected_abc,
                  annotation="从选择的ABC节点获取时间范围")

    cmds.menuItem(divider=True)

    # 子菜单 - 工具
    tools_submenu = cmds.menuItem(label="工具", subMenu=True)

    cmds.menuItem(label="播放动画",
                  command=lambda x: cmds.play(forward=True),
                  annotation="播放动画")

    cmds.menuItem(label="停止动画",
                  command=lambda x: cmds.play(state=False),
                  annotation="停止动画")

    cmds.menuItem(label="适配视图",
                  command=lambda x: (cmds.select(all=True), cmds.viewFit(), cmds.select(clear=True)),
                  annotation="适配视图到所有对象")

    cmds.menuItem(divider=True)

    cmds.menuItem(label="选择ABC节点",
                  command=lambda x: cmds.select(cmds.ls(type="AlembicNode")) if cmds.ls(
                      type="AlembicNode") else cmds.warning("没有ABC节点"),
                  annotation="选择场景中的所有ABC节点")

    # 子菜单 - 帮助
    help_submenu = cmds.menuItem(label="帮助", subMenu=True)

    cmds.menuItem(label="关于",
                  command=lambda x: cmds.confirmDialog(
                      title="关于",
                      message="Lookdev动画组装工具 v2.0 (模块化)\n\n功能：\n• 自动导入Lookdev文件\n• 导入动画ABC缓存并连接到Lookdev几何体\n• 导入动画相机ABC并自动获取时间范围\n• 设置XGen毛发缓存路径\n• 材质检查和修复\n• 场景参数设置\n\n新功能 (v2.0):\n• JSON配置文件支持\n• 自动Lookdev文件查找\n• 智能相机路径推导\n• 模块化架构\n\n作者：Maya Pipeline Team",
                      button=["确定"]),
                  annotation="显示关于信息")

    cmds.menuItem(label="使用说明",
                  command=lambda x: cmds.confirmDialog(
                      title="使用说明",
                      message="使用说明 (v2.0 模块化系统)：\n\n1. 加载JSON配置文件并选择资产\n2. 调整参数\n3. 执行操作\n4. 检查结果\n\n详细说明请查看主界面的帮助菜单。",
                      button=["确定"]),
                  annotation="显示使用说明")

    print("Lookdev动画工具插件已加载 v2.0 (模块化)")


def uninitializePlugin(mobject):
    """Uninitialize the script plug-in"""
    if cmds.menu("menuLookdevAnimation", exists=True):
        cmds.deleteUI("menuLookdevAnimation", menu=True)

    print("Lookdev动画工具插件已卸载")


# 主函数
def main():
    """主函数 - 用于直接运行脚本"""
    return show_lookdev_animation_setup_ui()


# 如果直接运行此脚本
if __name__ == "__main__":
    show_lookdev_animation_setup_ui()