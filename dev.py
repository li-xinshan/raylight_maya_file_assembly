"""
Lookdev动画组装工具 Maya插件
版本：1.1
作者：Maya Pipeline Team
"""

import maya.cmds as cmds
import maya.mel as mel
import maya.OpenMaya as om
import maya.OpenMayaMPx as omm
import os
import functools
import xgenm


class LookdevAnimationSetupUI:
    """
    Lookdev和动画组装工具 - UI版本
    """

    def __init__(self):
        # 窗口名称
        self.window_name = "LookdevAnimationSetup"
        self.window_title = "Lookdev动画组装工具 v1.1"

        # 默认配置
        self.lookdev_file = "P:/lhsn/lookdev/LHSN_chr_dwl_shaoweimin_ldv_v008.ma"
        self.animation_abc_file = "P:/lhsn/ani/cache/v002/LHSN_s310_c0990_ani_ani_v002-chr_dwl_01.abc"
        self.camera_abc_file = "P:/lhsn/ani/cache/v002/LHSN_s310_c0990_ani_cam_v002.abc"
        self.hair_cache_template = "P:/LHSN/cache/dcc/shot/s310/c0990/cfx/alembic/hair/dwl_01/outcurve/cache_${DESC}.0001.abc"
        self.lookdev_namespace = "dwl_lookdev"
        self.start_frame = 1001
        self.end_frame = 1100

        # UI控件变量
        self.ui = {}

        # 核心工具类
        self.tool = LookdevAnimationSetup()

    def show_ui(self):
        """显示UI界面"""
        # 删除已存在的窗口
        if cmds.window(self.window_name, exists=True):
            cmds.deleteUI(self.window_name, window=True)

        # 创建窗口
        self.ui['window'] = cmds.window(
            self.window_name,
            title=self.window_title,
            widthHeight=(500, 900),
            resizeToFitChildren=True,
            menuBar=True
        )

        # 创建菜单
        self.create_menu()

        # 创建主布局
        main_layout = cmds.columnLayout(adjustableColumn=True, rowSpacing=5, columnOffset=('both', 10))

        # 标题
        cmds.text(label="Lookdev动画组装工具", font="boldLabelFont", height=30, backgroundColor=[0.3, 0.5, 0.7])
        cmds.separator(height=10)

        # 文件路径设置区域
        self.create_file_path_section()

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
        self.update_file_status()

    def create_menu(self):
        """创建菜单栏"""
        # 文件菜单
        file_menu = cmds.menu(label="文件")
        cmds.menuItem(label="保存配置", command=self.save_config)
        cmds.menuItem(label="加载配置", command=self.load_config)
        cmds.menuItem(divider=True)
        cmds.menuItem(label="退出", command=self.close_window)

        # 工具菜单
        tools_menu = cmds.menu(label="工具")
        cmds.menuItem(label="刷新文件状态", command=lambda x: self.update_file_status())
        cmds.menuItem(label="清理场景", command=self.clean_scene)
        cmds.menuItem(divider=True)
        cmds.menuItem(label="重载插件", command=self.reload_plugins)

        # 帮助菜单
        help_menu = cmds.menu(label="帮助")
        cmds.menuItem(label="关于", command=self.show_about)
        cmds.menuItem(label="使用说明", command=self.show_help)

    def create_file_path_section(self):
        """创建文件路径设置区域"""
        cmds.frameLayout(label="文件路径设置", collapsable=True, collapse=False, marginWidth=10, marginHeight=10)

        # Lookdev文件
        cmds.text(label="Lookdev文件:", align="left", font="boldLabelFont")
        row1 = cmds.rowLayout(numberOfColumns=3, adjustableColumn=2, columnWidth3=(400, 60, 30))
        self.ui['lookdev_path'] = cmds.textField(text=self.lookdev_file, changeCommand=self.on_lookdev_path_changed)
        cmds.button(label="浏览", command=self.browse_lookdev_file, width=60)
        self.ui['lookdev_status'] = cmds.text(label="●", width=30, backgroundColor=[0.8, 0.3, 0.3])
        cmds.setParent('..')

        cmds.separator(height=5)

        # 动画ABC文件
        cmds.text(label="动画ABC缓存文件:", align="left", font="boldLabelFont")
        row2 = cmds.rowLayout(numberOfColumns=3, adjustableColumn=2, columnWidth3=(400, 60, 30))
        self.ui['animation_abc_path'] = cmds.textField(text=self.animation_abc_file, changeCommand=self.on_animation_abc_path_changed)
        cmds.button(label="浏览", command=self.browse_animation_abc_file, width=60)
        self.ui['animation_abc_status'] = cmds.text(label="●", width=30, backgroundColor=[0.8, 0.3, 0.3])
        cmds.setParent('..')

        cmds.separator(height=5)

        # 相机ABC文件
        cmds.text(label="动画相机ABC文件:", align="left", font="boldLabelFont")
        row3 = cmds.rowLayout(numberOfColumns=3, adjustableColumn=2, columnWidth3=(400, 60, 30))
        self.ui['camera_abc_path'] = cmds.textField(text=self.camera_abc_file, changeCommand=self.on_camera_abc_path_changed)
        cmds.button(label="浏览", command=self.browse_camera_abc_file, width=60)
        self.ui['camera_abc_status'] = cmds.text(label="●", width=30, backgroundColor=[0.8, 0.3, 0.3])
        cmds.setParent('..')

        cmds.separator(height=5)

        # 毛发缓存路径模板
        cmds.text(label="毛发缓存路径模板:", align="left", font="boldLabelFont")
        row4 = cmds.rowLayout(numberOfColumns=2, adjustableColumn=2, columnWidth2=(400, 60))
        self.ui['hair_cache_template'] = cmds.textField(text=self.hair_cache_template, changeCommand=self.on_hair_cache_template_changed)
        cmds.button(label="重置", command=self.reset_hair_cache_template, width=60)
        cmds.setParent('..')

        cmds.text(label="注意: ${DESC}会被替换为实际的XGen描述名称", align="left", font="smallObliqueLabelFont")

        cmds.setParent('..')  # frameLayout

    def create_settings_section(self):
        """创建设置参数区域"""
        cmds.frameLayout(label="参数设置", collapsable=True, collapse=False, marginWidth=10, marginHeight=10)

        # 命名空间设置
        cmds.rowLayout(numberOfColumns=2, adjustableColumn=2, columnWidth2=(120, 300))
        cmds.text(label="Lookdev命名空间:", align="left")
        self.ui['namespace'] = cmds.textField(text=self.lookdev_namespace, changeCommand=self.on_namespace_changed)
        cmds.setParent('..')

        cmds.separator(height=10)

        # 时间范围设置
        cmds.text(label="时间范围设置:", align="left", font="boldLabelFont")

        time_row = cmds.rowLayout(numberOfColumns=6, adjustableColumn=6,
                                 columnWidth6=(80, 80, 20, 80, 80, 120))
        cmds.text(label="开始帧:")
        self.ui['start_frame'] = cmds.intField(value=self.start_frame, changeCommand=self.on_time_changed)
        cmds.text(label=" - ")
        cmds.text(label="结束帧:")
        self.ui['end_frame'] = cmds.intField(value=self.end_frame, changeCommand=self.on_time_changed)
        cmds.button(label="从相机ABC获取", command=self.get_time_from_camera_abc)
        cmds.setParent('..')

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
            text="准备就绪，请选择文件并执行操作...\n",
            editable=False,
            wordWrap=True,
            height=120,
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
        cmds.button(label="选择ABC节点", command=self.select_abc_nodes, width=100)
        cmds.text(label="")
        cmds.setParent('..')

        # 第三行工具
        tools_row3 = cmds.rowLayout(numberOfColumns=4, adjustableColumn=4)
        cmds.button(label="检查XGen", command=self.check_xgen, width=100)
        cmds.button(label="打开文件夹", command=self.open_folder, width=100)
        cmds.button(label="场景信息", command=self.show_scene_info, width=100)
        cmds.button(label="导出报告", command=self.export_report, width=100)
        cmds.setParent('..')

        cmds.setParent('..')  # frameLayout

    # ===== 事件处理函数 =====

    def on_lookdev_path_changed(self, *args):
        """Lookdev路径改变时的回调"""
        self.lookdev_file = cmds.textField(self.ui['lookdev_path'], query=True, text=True)
        self.tool.lookdev_file = self.lookdev_file
        self.update_file_status()

    def on_animation_abc_path_changed(self, *args):
        """动画ABC路径改变时的回调"""
        self.animation_abc_file = cmds.textField(self.ui['animation_abc_path'], query=True, text=True)
        self.tool.animation_abc_file = self.animation_abc_file
        self.update_file_status()

    def on_camera_abc_path_changed(self, *args):
        """相机ABC路径改变时的回调"""
        self.camera_abc_file = cmds.textField(self.ui['camera_abc_path'], query=True, text=True)
        self.tool.camera_abc_file = self.camera_abc_file
        self.update_file_status()

    def on_hair_cache_template_changed(self, *args):
        """毛发缓存模板改变时的回调"""
        self.hair_cache_template = cmds.textField(self.ui['hair_cache_template'], query=True, text=True)
        self.tool.hair_cache_template = self.hair_cache_template

    def on_namespace_changed(self, *args):
        """命名空间改变时的回调"""
        self.lookdev_namespace = cmds.textField(self.ui['namespace'], query=True, text=True)
        self.tool.lookdev_namespace = self.lookdev_namespace

    def on_time_changed(self, *args):
        """时间范围改变时的回调"""
        self.start_frame = cmds.intField(self.ui['start_frame'], query=True, value=True)
        self.end_frame = cmds.intField(self.ui['end_frame'], query=True, value=True)
        self.tool.start_frame = self.start_frame
        self.tool.end_frame = self.end_frame

    def reset_hair_cache_template(self, *args):
        """重置毛发缓存模板"""
        default_template = "P:/LHSN/cache/dcc/shot/s310/c0990/cfx/alembic/hair/dwl_01/outcurve/cache_${DESC}.0001.abc"
        cmds.textField(self.ui['hair_cache_template'], edit=True, text=default_template)
        self.hair_cache_template = default_template
        self.tool.hair_cache_template = default_template

    def browse_lookdev_file(self, *args):
        """浏览Lookdev文件"""
        file_filter = "Maya ASCII (*.ma);;Maya Binary (*.mb);;All Files (*.*)"
        files = cmds.fileDialog2(fileFilter=file_filter, dialogStyle=2, fileMode=1)
        if files:
            self.lookdev_file = files[0]
            cmds.textField(self.ui['lookdev_path'], edit=True, text=self.lookdev_file)
            self.tool.lookdev_file = self.lookdev_file
            self.update_file_status()

    def browse_animation_abc_file(self, *args):
        """浏览动画ABC文件"""
        file_filter = "Alembic (*.abc);;All Files (*.*)"
        files = cmds.fileDialog2(fileFilter=file_filter, dialogStyle=2, fileMode=1)
        if files:
            self.animation_abc_file = files[0]
            cmds.textField(self.ui['animation_abc_path'], edit=True, text=self.animation_abc_file)
            self.tool.animation_abc_file = self.animation_abc_file
            self.update_file_status()

    def browse_camera_abc_file(self, *args):
        """浏览相机ABC文件"""
        file_filter = "Alembic (*.abc);;All Files (*.*)"
        files = cmds.fileDialog2(fileFilter=file_filter, dialogStyle=2, fileMode=1)
        if files:
            self.camera_abc_file = files[0]
            cmds.textField(self.ui['camera_abc_path'], edit=True, text=self.camera_abc_file)
            self.tool.camera_abc_file = self.camera_abc_file
            self.update_file_status()

    def get_time_from_camera_abc(self, *args):
        """从相机ABC文件获取时间范围"""
        try:
            if not os.path.exists(self.camera_abc_file):
                self.log_message("相机ABC文件不存在，请先选择有效的文件")
                return

            self.log_message(f"正在从相机ABC获取时间范围: {os.path.basename(self.camera_abc_file)}")

            # 临时导入相机ABC来获取时间范围
            temp_success, start_frame, end_frame = self.tool.get_time_range_from_camera_abc()

            if temp_success:
                # 更新UI中的时间范围
                cmds.intField(self.ui['start_frame'], edit=True, value=int(start_frame))
                cmds.intField(self.ui['end_frame'], edit=True, value=int(end_frame))

                # 更新内部变量
                self.start_frame = int(start_frame)
                self.end_frame = int(end_frame)
                self.tool.start_frame = self.start_frame
                self.tool.end_frame = self.end_frame

                self.log_message(f"✅ 时间范围已更新: {self.start_frame} - {self.end_frame}")
            else:
                self.log_message("❌ 无法从相机ABC获取时间范围")

        except Exception as e:
            self.log_message(f"获取时间范围失败: {str(e)}")

    # ===== 执行步骤函数 =====

    def step1_import_lookdev(self, *args):
        """步骤1: 导入Lookdev文件"""
        self.log_message("\n=== 步骤1: 导入Lookdev文件 ===")
        self.update_progress(1)

        try:
            success = self.tool.import_lookdev()
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
            success = self.tool.import_and_connect_animation_abc()
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
            success = self.tool.import_camera_abc()
            if success:
                self.log_message("✅ 动画相机ABC导入成功")
                self.update_button_state('step3_btn', True)
                # 自动获取时间范围
                temp_success, start_frame, end_frame = self.tool.get_time_range_from_imported_camera()
                if temp_success:
                    cmds.intField(self.ui['start_frame'], edit=True, value=int(start_frame))
                    cmds.intField(self.ui['end_frame'], edit=True, value=int(end_frame))
                    self.start_frame = int(start_frame)
                    self.end_frame = int(end_frame)
                    self.log_message(f"时间范围已自动更新: {self.start_frame} - {self.end_frame}")
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
            # 更新工具类的模板路径
            self.tool.hair_cache_template = self.hair_cache_template
            success = self.tool.setup_hair_cache()
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
            self.tool.check_and_fix_materials()
            self.log_message("✅ 材质检查修复完成")
            self.update_button_state('step5_btn', True)
        except Exception as e:
            self.log_message(f"❌ 步骤5执行出错: {str(e)}")
            self.update_button_state('step5_btn', False)

    def step6_setup_scene(self, *args):
        """步骤6: 设置场景参数"""
        self.log_message("\n=== 步骤6: 设置场景参数 ===")
        self.update_progress(6)

        try:
            self.tool.setup_scene_settings()
            self.log_message("✅ 场景参数设置完成")
            self.update_button_state('step6_btn', True)
        except Exception as e:
            self.log_message(f"❌ 步骤6执行出错: {str(e)}")
            self.update_button_state('step6_btn', False)

    def execute_all_steps(self, *args):
        """一键执行所有步骤"""
        self.log_message("\n" + "="*50)
        self.log_message("开始一键执行所有步骤")
        self.log_message("="*50)

        # 重置进度
        self.update_progress(0)
        self.reset_button_states()

        # 执行所有步骤
        steps = [
            (self.step1_import_lookdev, "步骤1"),
            (self.step2_import_and_connect_animation_abc, "步骤2"),
            (self.step3_import_camera_abc, "步骤3"),
            (self.step4_setup_hair_cache, "步骤4"),
            (self.step5_fix_materials, "步骤5"),
            (self.step6_setup_scene, "步骤6")
        ]

        success_count = 0
        for step_func, step_name in steps:
            try:
                step_func()
                success_count += 1
            except Exception as e:
                self.log_message(f"❌ {step_name}执行失败: {str(e)}")
                break

        if success_count == len(steps):
            self.log_message("\n🎉 所有步骤执行完成！")
            self.tool.final_check()
            self.log_message("准备就绪，可以播放动画查看效果。")
        else:
            self.log_message(f"\n⚠️  执行中断，完成了{success_count}/{len(steps)}个步骤")

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
            self.tool.check_unmaterialized_objects()
        except Exception as e:
            self.log_message(f"材质检查失败: {str(e)}")

    def check_textures(self, *args):
        """检查纹理"""
        self.log_message("\n=== 纹理检查 ===")
        try:
            self.tool.fix_missing_textures()
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

    def check_xgen(self, *args):
        """检查XGen状态"""
        self.log_message("\n=== XGen检查 ===")
        try:
            self.tool.check_xgen_status()
        except Exception as e:
            self.log_message(f"XGen检查失败: {str(e)}")

    def open_folder(self, *args):
        """打开文件夹"""
        import subprocess
        folder_path = os.path.dirname(self.lookdev_file)
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
                    f.write("="*50 + "\n")
                    f.write(f"生成时间: {cmds.date()}\n")
                    f.write(f"场景文件: {cmds.file(query=True, sceneName=True)}\n")
                    f.write("="*50 + "\n\n")
                    f.write(log_content)

                self.log_message(f"报告已保存: {report_file[0]}")
            except Exception as e:
                self.log_message(f"保存报告失败: {str(e)}")

    # ===== UI辅助函数 =====

    def update_file_status(self):
        """更新文件状态指示器"""
        # 检查Lookdev文件
        if os.path.exists(self.lookdev_file):
            cmds.text(self.ui['lookdev_status'], edit=True, backgroundColor=[0.3, 0.8, 0.3])
        else:
            cmds.text(self.ui['lookdev_status'], edit=True, backgroundColor=[0.8, 0.3, 0.3])

        # 检查动画ABC文件
        if os.path.exists(self.animation_abc_file):
            cmds.text(self.ui['animation_abc_status'], edit=True, backgroundColor=[0.3, 0.8, 0.3])
        else:
            cmds.text(self.ui['animation_abc_status'], edit=True, backgroundColor=[0.8, 0.3, 0.3])

        # 检查相机ABC文件
        if os.path.exists(self.camera_abc_file):
            cmds.text(self.ui['camera_abc_status'], edit=True, backgroundColor=[0.3, 0.8, 0.3])
        else:
            cmds.text(self.ui['camera_abc_status'], edit=True, backgroundColor=[0.8, 0.3, 0.3])

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
        config_data = {
            'lookdev_file': self.lookdev_file,
            'animation_abc_file': self.animation_abc_file,
            'camera_abc_file': self.camera_abc_file,
            'hair_cache_template': self.hair_cache_template,
            'namespace': self.lookdev_namespace,
            'start_frame': self.start_frame,
            'end_frame': self.end_frame
        }

        config_file = cmds.fileDialog2(
            fileFilter="JSON Files (*.json)",
            dialogStyle=2,
            fileMode=0,
            caption="保存配置"
        )

        if config_file:
            try:
                import json
                with open(config_file[0], 'w', encoding='utf-8') as f:
                    json.dump(config_data, f, indent=4, ensure_ascii=False)
                self.log_message(f"配置已保存: {config_file[0]}")
            except Exception as e:
                self.log_message(f"保存配置失败: {str(e)}")

    def load_config(self, *args):
        """加载配置"""
        config_file = cmds.fileDialog2(
            fileFilter="JSON Files (*.json)",
            dialogStyle=2,
            fileMode=1,
            caption="加载配置"
        )

        if config_file:
            try:
                import json
                with open(config_file[0], 'r', encoding='utf-8') as f:
                    config_data = json.load(f)

                # 更新UI
                cmds.textField(self.ui['lookdev_path'], edit=True, text=config_data.get('lookdev_file', ''))
                cmds.textField(self.ui['animation_abc_path'], edit=True, text=config_data.get('animation_abc_file', ''))
                cmds.textField(self.ui['camera_abc_path'], edit=True, text=config_data.get('camera_abc_file', ''))
                cmds.textField(self.ui['hair_cache_template'], edit=True, text=config_data.get('hair_cache_template', ''))
                cmds.textField(self.ui['namespace'], edit=True, text=config_data.get('namespace', 'dwl_lookdev'))
                cmds.intField(self.ui['start_frame'], edit=True, value=config_data.get('start_frame', 1001))
                cmds.intField(self.ui['end_frame'], edit=True, value=config_data.get('end_frame', 1100))

                # 更新变量
                self.lookdev_file = config_data.get('lookdev_file', '')
                self.animation_abc_file = config_data.get('animation_abc_file', '')
                self.camera_abc_file = config_data.get('camera_abc_file', '')
                self.hair_cache_template = config_data.get('hair_cache_template', '')
                self.lookdev_namespace = config_data.get('namespace', 'dwl_lookdev')
                self.start_frame = config_data.get('start_frame', 1001)
                self.end_frame = config_data.get('end_frame', 1100)

                # 更新工具类
                self.tool.lookdev_file = self.lookdev_file
                self.tool.animation_abc_file = self.animation_abc_file
                self.tool.camera_abc_file = self.camera_abc_file
                self.tool.hair_cache_template = self.hair_cache_template
                self.tool.lookdev_namespace = self.lookdev_namespace
                self.tool.start_frame = self.start_frame
                self.tool.end_frame = self.end_frame

                self.update_file_status()
                self.log_message(f"配置已加载: {config_file[0]}")

            except Exception as e:
                self.log_message(f"加载配置失败: {str(e)}")

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
        about_text = """Lookdev动画组装工具 v1.1

功能：
• 自动导入Lookdev文件
• 导入动画ABC缓存并连接到Lookdev几何体
• 导入动画相机ABC
• 从相机ABC自动获取时间范围
• 设置XGen毛发缓存路径
• 材质检查和修复
• 场景参数设置

作者：Maya Pipeline Team
版本：1.1"""

        cmds.confirmDialog(
            title="关于",
            message=about_text,
            button=["确定"],
            defaultButton="确定"
        )

    def show_help(self, *args):
        """显示帮助信息"""
        help_text = """使用说明：

1. 设置文件路径
   - 选择Lookdev文件(.ma/.mb)
   - 选择动画ABC缓存文件(.abc)
   - 选择动画相机ABC文件(.abc)
   - 设置毛发缓存路径模板

2. 调整参数
   - 设置命名空间
   - 设置时间范围（可从相机ABC自动获取）

3. 执行操作
   - 可以分步执行各个步骤
   - 也可以一键完成所有操作

4. 检查结果
   - 查看状态日志
   - 使用附加工具检查

注意事项：
• 确保文件路径正确
• 检查文件权限
• 备份重要场景
• ABC几何体会被隐藏但保留
• Lookdev几何体连接ABC动画数据
• 毛发缓存路径中的${DESC}会被自动替换"""

        cmds.confirmDialog(
            title="使用说明",
            message=help_text,
            button=["确定"],
            defaultButton="确定"
        )


class LookdevAnimationSetup:
    """
    核心工具类 - 处理Lookdev和动画组装
    """

    def __init__(self):
        # 文件路径配置
        self.lookdev_file = "P:/lhsn/lookdev/LHSN_chr_dwl_shaoweimin_ldv_v008.ma"
        self.animation_abc_file = "P:/lhsn/ani/cache/v002/LHSN_s310_c0990_ani_ani_v002-chr_dwl_01.abc"
        self.camera_abc_file = "P:/lhsn/ani/cache/v002/LHSN_s310_c0990_ani_cam_v002.abc"
        self.hair_cache_template = "P:/LHSN/cache/dcc/shot/s310/c0990/cfx/alembic/hair/dwl_01/outcurve/cache_${DESC}.0001.abc"
        self.lookdev_namespace = "dwl_lookdev"

        # 时间范围设置
        self.start_frame = 1001
        self.end_frame = 1100

    def get_time_range_from_camera_abc(self):
        """从相机ABC文件获取时间范围（临时导入）"""
        try:
            if not os.path.exists(self.camera_abc_file):
                return False, None, None

            # 确保ABC插件已加载
            if not cmds.pluginInfo('AbcImport', query=True, loaded=True):
                cmds.loadPlugin('AbcImport')

            # 记录当前场景状态
            current_cameras = cmds.ls(type="camera")
            current_abc_nodes = cmds.ls(type="AlembicNode")

            # 临时导入相机ABC
            mel.eval(f'AbcImport -mode import "{self.camera_abc_file}"')

            # 查找新导入的ABC节点
            new_abc_nodes = cmds.ls(type="AlembicNode")
            temp_abc_nodes = [node for node in new_abc_nodes if node not in current_abc_nodes]

            if temp_abc_nodes:
                # 从第一个ABC节点获取时间范围
                abc_node = temp_abc_nodes[0]
                start_frame = cmds.getAttr(f"{abc_node}.startFrame")
                end_frame = cmds.getAttr(f"{abc_node}.endFrame")

                # 删除临时导入的内容
                for node in temp_abc_nodes:
                    try:
                        cmds.delete(node)
                    except:
                        pass

                # 删除临时导入的相机
                new_cameras = cmds.ls(type="camera")
                temp_cameras = [cam for cam in new_cameras if cam not in current_cameras]
                for cam in temp_cameras:
                    cam_transform = cmds.listRelatives(cam, parent=True, type="transform")
                    if cam_transform:
                        try:
                            cmds.delete(cam_transform[0])
                        except:
                            pass

                return True, start_frame, end_frame
            else:
                return False, None, None

        except Exception as e:
            print(f"从相机ABC获取时间范围失败: {str(e)}")
            return False, None, None

    def get_time_range_from_imported_camera(self):
        """从已导入的相机ABC节点获取时间范围"""
        try:
            abc_nodes = cmds.ls(type="AlembicNode")
            if abc_nodes:
                # 从最后导入的ABC节点获取时间范围
                abc_node = abc_nodes[-1]
                start_frame = cmds.getAttr(f"{abc_node}.startFrame")
                end_frame = cmds.getAttr(f"{abc_node}.endFrame")

                # 更新内部时间范围
                self.start_frame = start_frame
                self.end_frame = end_frame

                return True, start_frame, end_frame
            else:
                return False, None, None

        except Exception as e:
            print(f"从已导入相机获取时间范围失败: {str(e)}")
            return False, None, None

    def import_lookdev(self):
        """导入lookdev文件"""
        try:
            # 检查文件是否存在
            if not os.path.exists(self.lookdev_file):
                cmds.error(f"Lookdev文件不存在: {self.lookdev_file}")
                return False

            # 导入文件
            cmds.file(
                self.lookdev_file,
                i=True,
                type="mayaAscii",
                ignoreVersion=True,
                ra=True,
                mergeNamespacesOnClash=False,
                namespace=self.lookdev_namespace,
                pr=True
            )

            print(f"已导入Lookdev文件: {self.lookdev_file}")
            print(f"命名空间: {self.lookdev_namespace}")

            # 列出导入的主要节点
            imported_nodes = cmds.ls(f"{self.lookdev_namespace}:*", type="transform")
            print(f"导入节点数量: {len(imported_nodes)}")

            return True

        except Exception as e:
            cmds.warning(f"导入Lookdev文件时出错: {str(e)}")
            return False

    def import_and_connect_animation_abc(self):
        """导入动画ABC缓存并连接到lookdev几何体"""
        try:
            # 检查ABC文件
            if not os.path.exists(self.animation_abc_file):
                cmds.error(f"动画ABC文件不存在: {self.animation_abc_file}")
                return False

            # 确保ABC插件已加载
            if not cmds.pluginInfo('AbcImport', query=True, loaded=True):
                cmds.loadPlugin('AbcImport')
                print("已加载AbcImport插件")

            print(f"导入ABC文件: {self.animation_abc_file}")

            # 记录导入前的场景状态
            transforms_before = set(cmds.ls(type='transform'))
            abc_nodes_before = set(cmds.ls(type="AlembicNode"))

            # 使用MEL导入ABC
            mel_command = f'AbcImport -mode import "{self.animation_abc_file}";'
            result = mel.eval(mel_command)
            print(f"MEL导入结果: {result}")

            # 查找新创建的ABC节点
            abc_nodes_after = set(cmds.ls(type="AlembicNode"))
            new_abc_nodes = abc_nodes_after - abc_nodes_before

            if not new_abc_nodes:
                raise Exception("没有找到新的ABC节点")

            abc_node = list(new_abc_nodes)[-1]
            print(f"ABC节点: {abc_node}")

            # 设置时间范围
            self.set_time_range(abc_node)

            # 查找新创建的transform
            transforms_after = set(cmds.ls(type='transform'))
            new_transforms = transforms_after - transforms_before

            print(f"新创建了 {len(new_transforms)} 个transform节点")

            # 找到ABC几何体
            abc_meshes = self.find_abc_meshes(new_transforms, abc_node)
            print(f"找到 {len(abc_meshes)} 个ABC几何体")

            # 显示ABC几何体详情
            for name, data in abc_meshes.items():
                print(f"  ABC: {name} -> {data['transform']}")

            # 获取lookdev几何体
            lookdev_meshes = self.find_lookdev_meshes()
            print(f"找到 {len(lookdev_meshes)} 个lookdev几何体")

            # 连接ABC到lookdev（不删除ABC几何体）
            self.connect_abc_to_lookdev_keep_all(abc_meshes, lookdev_meshes)

            # 隐藏ABC几何体（可选）
            self.hide_abc_meshes(abc_meshes)

            return True

        except Exception as e:
            cmds.warning(f"导入动画ABC时出错: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    def find_abc_meshes(self, new_transforms, abc_node):
        """查找ABC创建的mesh"""
        abc_meshes = {}

        # 通过ABC节点的连接查找
        abc_connections = cmds.listConnections(abc_node, type='transform') or []

        for transform in abc_connections:
            if cmds.objExists(transform):
                shapes = cmds.listRelatives(transform, shapes=True, type='mesh') or []
                if shapes:
                    shape = shapes[0]
                    # 获取ABC的输出连接
                    input_connections = cmds.listConnections(shape + '.inMesh', source=True, plugs=True)
                    if input_connections:
                        base_name = transform.split('|')[-1].lower()
                        abc_meshes[base_name] = {
                            'transform': transform,
                            'shape': shape,
                            'abc_connection': input_connections[0]
                        }

        # 如果通过连接找不到，尝试通过新创建的transform查找
        if not abc_meshes:
            print("  通过连接未找到ABC几何体，尝试通过新transform查找...")
            for transform in new_transforms:
                if cmds.objExists(transform) and not transform.startswith(f'{self.lookdev_namespace}:'):
                    shapes = cmds.listRelatives(transform, shapes=True, type='mesh') or []
                    if shapes:
                        shape = shapes[0]
                        # 检查是否有ABC输入
                        input_connections = cmds.listConnections(shape + '.inMesh', source=True, plugs=True)
                        if input_connections:
                            # 检查输入是否来自ABC节点
                            source_node = input_connections[0].split('.')[0]
                            if cmds.nodeType(source_node) == 'AlembicNode':
                                base_name = transform.split('|')[-1].lower()
                                abc_meshes[base_name] = {
                                    'transform': transform,
                                    'shape': shape,
                                    'abc_connection': input_connections[0]
                                }

        return abc_meshes

    def find_lookdev_meshes(self):
        """查找lookdev mesh"""
        lookdev_meshes = {}

        lookdev_transforms = cmds.ls(f"{self.lookdev_namespace}:*", type='transform') or []

        for transform in lookdev_transforms:
            shapes = cmds.listRelatives(transform, shapes=True, type='mesh') or []
            if shapes:
                base_name = transform.split(':')[-1].lower()
                lookdev_meshes[base_name] = {
                    'transform': transform,
                    'shape': shapes[0]
                }

        return lookdev_meshes

    def connect_abc_to_lookdev_keep_all(self, abc_meshes, lookdev_meshes):
        """连接ABC到lookdev - 保留所有几何体"""
        print("  开始连接ABC到lookdev（保留所有几何体）...")

        if not abc_meshes:
            print("  警告: 没有找到ABC几何体")
            return

        connected = 0

        print("  ABC几何体:")
        for name in abc_meshes.keys():
            print(f"    {name}")

        print("  开始匹配和连接...")

        for abc_name, abc_data in abc_meshes.items():
            # 寻找最佳匹配
            best_match = self.find_best_match_name(abc_name, lookdev_meshes.keys())

            if best_match:
                lookdev_data = lookdev_meshes[best_match]

                try:
                    # 获取ABC输出连接
                    abc_output = abc_data['abc_connection']
                    lookdev_shape = lookdev_data['shape']

                    # 断开lookdev原有连接（如果有）
                    existing_connections = cmds.listConnections(lookdev_shape + '.inMesh', source=True, plugs=True)
                    if existing_connections:
                        cmds.disconnectAttr(existing_connections[0], lookdev_shape + '.inMesh')

                    # 连接ABC输出到lookdev
                    cmds.connectAttr(abc_output, lookdev_shape + '.inMesh', force=True)
                    print(f"    连接成功: {abc_name} -> {best_match}")
                    connected += 1

                except Exception as e:
                    print(f"    连接失败 {abc_name} -> {best_match}: {e}")
            else:
                print(f"    未找到匹配: {abc_name}")

        print(f"  总共连接了 {connected} 个几何体")
        print("  所有ABC几何体和lookdev几何体都保留在场景中")

    def find_best_match_name(self, abc_name, lookdev_names):
        """查找最佳匹配名称"""
        abc_clean = self.clean_mesh_name(abc_name)

        # 1. 直接匹配
        for lookdev_name in lookdev_names:
            lookdev_clean = self.clean_mesh_name(lookdev_name)
            if abc_clean == lookdev_clean:
                return lookdev_name

        # 2. 部分匹配
        for lookdev_name in lookdev_names:
            lookdev_clean = self.clean_mesh_name(lookdev_name)
            if abc_clean in lookdev_clean or lookdev_clean in abc_clean:
                return lookdev_name

        # 3. 关键词匹配
        abc_keywords = self.extract_keywords(abc_clean)
        best_match = None
        max_common = 0

        for lookdev_name in lookdev_names:
            lookdev_clean = self.clean_mesh_name(lookdev_name)
            lookdev_keywords = self.extract_keywords(lookdev_clean)

            # 计算共同关键词数量
            common_keywords = abc_keywords & lookdev_keywords
            if len(common_keywords) > max_common:
                max_common = len(common_keywords)
                best_match = lookdev_name

        return best_match if max_common > 0 else None

    def clean_mesh_name(self, name):
        """清理mesh名称"""
        name = name.lower()
        # 移除常见前缀后缀
        name = name.replace('dwl_', '').replace('chr_', '').replace('_grp', '')
        name = name.replace('dwl', '').replace('chr', '').replace('grp', '')

        # 移除数字后缀
        import re
        name = re.sub(r'_?\d+$', '', name)
        name = re.sub(r'\d+$', '', name)

        return name

    def extract_keywords(self, name):
        """提取关键词"""
        keywords = set()

        # 身体部位关键词
        body_parts = ['body', 'head', 'eye', 'eyel', 'eyer', 'eyebrow', 'eyelash',
                     'hair', 'face', 'hand', 'leg', 'arm', 'foot', 'teeth', 'lowteeth',
                     'upteeth', 'tongue', 'tail', 'fur']

        # 服装关键词
        clothing = ['skirt', 'gauntlets', 'necklace', 'rope', 'belt', 'beltrope']

        # 其他关键词
        others = ['vitreous', 'ball', 'grow', 'blend']

        all_keywords = body_parts + clothing + others

        for keyword in all_keywords:
            if keyword in name:
                keywords.add(keyword)

        # 特殊处理
        if 'vitreous' in name or ('ball' in name and 'eye' in name):
            keywords.add('eye')

        return keywords

    def hide_abc_meshes(self, abc_meshes):
        """隐藏ABC几何体（可选）"""
        print("  隐藏ABC几何体...")

        for name, data in abc_meshes.items():
            transform = data['transform']
            try:
                if cmds.objExists(transform):
                    cmds.setAttr(transform + '.visibility', 0)
                    print(f"    隐藏: {transform}")
            except Exception as e:
                print(f"    隐藏失败 {transform}: {e}")

    def set_time_range(self, abc_node):
        """设置时间范围"""
        try:
            start_frame = cmds.getAttr(abc_node + '.startFrame')
            end_frame = cmds.getAttr(abc_node + '.endFrame')

            # 更新内部变量
            self.start_frame = start_frame
            self.end_frame = end_frame

            cmds.playbackOptions(min=start_frame, max=end_frame)
            cmds.currentTime(start_frame)

            print(f"  设置时间范围: {start_frame} - {end_frame}")
        except Exception as e:
            print(f"  设置时间范围失败: {e}")

    def import_camera_abc(self):
        """导入动画相机ABC"""
        try:
            # 检查相机ABC文件
            if not os.path.exists(self.camera_abc_file):
                cmds.warning(f"相机ABC文件不存在: {self.camera_abc_file}")
                return False

            # 确保ABC插件已加载
            if not cmds.pluginInfo('AbcImport', query=True, loaded=True):
                cmds.loadPlugin('AbcImport')
                print("已加载AbcImport插件")

            # 导入相机ABC
            mel.eval(f'AbcImport -mode import "{self.camera_abc_file}"')
            print(f"已导入相机ABC: {os.path.basename(self.camera_abc_file)}")

            # 检查导入的相机
            cameras = cmds.ls(type="camera")
            animation_cameras = [cam for cam in cameras if "persp" not in cam and "top" not in cam and "front" not in cam and "side" not in cam]

            if animation_cameras:
                print(f"找到{len(animation_cameras)}个动画相机:")
                for cam in animation_cameras:
                    transform = cmds.listRelatives(cam, parent=True, type="transform")
                    if transform:
                        print(f"  - {transform[0]}")

                # 设置活动相机
                if animation_cameras:
                    cam_transform = cmds.listRelatives(animation_cameras[0], parent=True, type="transform")
                    if cam_transform:
                        # 获取当前面板并设置相机
                        panel = cmds.getPanel(withFocus=True)
                        if panel and cmds.modelPanel(panel, query=True, exists=True):
                            cmds.modelEditor(panel, edit=True, camera=cam_transform[0])
                            print(f"已设置活动相机: {cam_transform[0]}")

                return True
            else:
                print("未找到动画相机，但ABC导入成功")
                return True

        except Exception as e:
            cmds.warning(f"导入相机ABC时出错: {str(e)}")
            return False

    def setup_hair_cache(self):
        """设置毛发缓存路径"""
        try:
            print("开始设置XGen毛发缓存路径...")

            # 确保XGen插件已加载
            if not cmds.pluginInfo('xgenToolkit', query=True, loaded=True):
                cmds.loadPlugin('xgenToolkit')
                print("已加载xgenToolkit插件")

            # 获取所有XGen调色板
            palettes = xgenm.palettes()
            if not palettes:
                print("  场景中没有找到XGen调色板")
                return True

            print(f"  找到 {len(palettes)} 个XGen调色板")

            total_descriptions = 0
            updated_descriptions = 0

            obj = 'SplinePrimitive'

            for palette in palettes:
                descriptions = xgenm.descriptions(palette)
                print(f"  调色板 '{palette}' 包含 {len(descriptions)} 个描述")

                for desc in descriptions:
                    total_descriptions += 1
                    desc_name = desc.split(':')[-1]

                    # 将${DESC}替换为实际的描述名称
                    cache_path = self.hair_cache_template.replace('${DESC}', desc_name)

                    try:
                        # 设置XGen属性
                        if os.path.exists(cache_path):
                            xgenm.setAttr('useCache', 'true', palette, desc, obj)
                            xgenm.setAttr('liveMode', 'false', palette, desc, obj)
                            xgenm.setAttr('cacheFileName', cache_path, palette, desc, obj)

                            print(f"    描述 '{desc_name}' 缓存路径已设置: {cache_path}")
                            updated_descriptions += 1

                    except Exception as e:
                        print(f"    描述 '{desc_name}' 设置失败: {str(e)}")

            print(f"  毛发缓存设置完成: {updated_descriptions}/{total_descriptions} 个描述已更新")

            if updated_descriptions > 0:
                return True
            else:
                print("  警告: 没有成功设置任何毛发缓存")
                return False

        except Exception as e:
            print(f"设置毛发缓存路径失败: {str(e)}")
            return False

    def check_xgen_status(self):
        """检查XGen状态"""
        try:
            palettes = xgenm.palettes()
            if not palettes:
                print("场景中没有XGen调色板")
                return

            print(f"XGen调色板数量: {len(palettes)}")

            for palette in palettes:
                descriptions = xgenm.descriptions(palette)
                print(f"\n调色板: {palette}")
                print(f"  描述数量: {len(descriptions)}")

                for desc in descriptions:
                    desc_name = desc.split(':')[-1]

                    try:
                        use_cache = xgenm.getAttr('useCache', palette, desc, 'SplinePrimitive')
                        live_mode = xgenm.getAttr('liveMode', palette, desc, 'SplinePrimitive')
                        cache_file = xgenm.getAttr('cacheFileName', palette, desc, 'SplinePrimitive')

                        print(f"  描述: {desc_name}")
                        print(f"    使用缓存: {use_cache}")
                        print(f"    实时模式: {live_mode}")
                        print(f"    缓存文件: {cache_file}")

                        # 检查缓存文件是否存在
                        if cache_file and os.path.exists(cache_file):
                            print(f"    缓存文件状态: ✅ 存在")
                        elif cache_file:
                            print(f"    缓存文件状态: ❌ 不存在")
                        else:
                            print(f"    缓存文件状态: ⚠️  未设置")

                    except Exception as e:
                        print(f"  描述 {desc_name} 检查失败: {str(e)}")

        except Exception as e:
            print(f"检查XGen状态失败: {str(e)}")

    def check_and_fix_materials(self):
        """检查和修复材质问题"""
        print("\n检查材质状态...")

        # 检查缺失的纹理
        self.fix_missing_textures()

        # 检查没有材质的对象
        self.check_unmaterialized_objects()

    def fix_missing_textures(self):
        """修复缺失的纹理路径"""
        file_nodes = cmds.ls(type="file")
        missing_count = 0
        fixed_count = 0

        for node in file_nodes:
            texture_path = cmds.getAttr(f"{node}.fileTextureName")
            if texture_path and not os.path.exists(texture_path):
                missing_count += 1
                print(f"  缺失纹理: {os.path.basename(texture_path)}")

                # 尝试修复路径
                possible_paths = [
                    texture_path.replace("P:/LTT", "//192.168.50.250/public/LTT"),
                    os.path.join(cmds.workspace(query=True, rootDirectory=True), "sourceimages", os.path.basename(texture_path))
                ]

                for new_path in possible_paths:
                    if os.path.exists(new_path):
                        cmds.setAttr(f"{node}.fileTextureName", new_path, type="string")
                        print(f"    ✅ 已修复: {os.path.basename(new_path)}")
                        fixed_count += 1
                        break

        if missing_count > 0:
            print(f"\n纹理状态: {missing_count}个缺失, {fixed_count}个已修复")

    def check_unmaterialized_objects(self):
        """检查没有材质的对象"""
        all_meshes = cmds.ls(type="mesh", noIntermediate=True)
        no_material = []

        for mesh in all_meshes:
            shading_groups = cmds.listConnections(mesh, type="shadingEngine")
            if not shading_groups or shading_groups[0] == "initialShadingGroup":
                transform = cmds.listRelatives(mesh, parent=True, type="transform")
                if transform:
                    no_material.append(transform[0])

        if no_material:
            print(f"\n警告: {len(no_material)}个对象没有材质")
            for obj in no_material[:10]:  # 只显示前10个
                print(f"  - {obj}")
            if len(no_material) > 10:
                print(f"  ... 还有{len(no_material)-10}个")

    def setup_scene_settings(self):
        """设置场景参数"""
        print("\n设置场景参数...")

        # 设置时间范围
        cmds.playbackOptions(min=self.start_frame, max=self.end_frame)
        cmds.currentTime(self.start_frame)
        print(f"时间范围: {self.start_frame} - {self.end_frame}")

        # 设置单位
        cmds.currentUnit(linear="cm", time="film")

        # 设置视口显示
        panel = cmds.getPanel(withFocus=True)
        if panel:
            model_panel = cmds.modelPanel(panel, query=True, exists=True)
            if model_panel:
                cmds.modelEditor(panel, edit=True, displayTextures=True, displayLights="all")
                print("视口显示已更新")

        # 优化场景
        self.optimize_scene()

    def optimize_scene(self):
        """场景优化"""
        if cmds.objExists(f"{self.lookdev_namespace}:Master"):
            cmds.select(f"{self.lookdev_namespace}:Master", replace=True)
            print("  已选择lookdev根节点")

        cmds.refresh(currentView=True)
        print("  场景优化完成")

    def final_check(self):
        """最终检查"""
        print("\n" + "="*30)
        print("最终检查")
        print("="*30)

        # 检查ABC节点
        abc_nodes = cmds.ls(type="AlembicNode")
        print(f"AlembicNode数量: {len(abc_nodes)}")

        # 检查着色组
        shading_groups = cmds.ls(f"{self.lookdev_namespace}:*SG")
        print(f"着色组数量: {len(shading_groups)}")

        # 检查可见的几何体
        visible_meshes = []
        all_meshes = cmds.ls(type="mesh", noIntermediate=True)
        for mesh in all_meshes:
            transform = cmds.listRelatives(mesh, parent=True, type="transform")
            if transform and cmds.getAttr(f"{transform[0]}.visibility"):
                visible_meshes.append(transform[0])

        print(f"可见几何体数量: {len(visible_meshes)}")

        # 检查相机
        cameras = cmds.ls(type="camera")
        animation_cameras = [cam for cam in cameras if "persp" not in cam and "top" not in cam and "front" not in cam and "side" not in cam]
        print(f"动画相机数量: {len(animation_cameras)}")

        # 检查XGen
        try:
            palettes = xgenm.palettes()
            total_descriptions = 0
            for palette in palettes:
                descriptions = xgenm.descriptions(palette)
                total_descriptions += len(descriptions)
            print(f"XGen调色板数量: {len(palettes)}")
            print(f"XGen描述数量: {total_descriptions}")
        except:
            print("XGen状态: 未检测到或出错")

        print("\n✅ 构建完成！")
        print("ABC几何体和lookdev几何体都保留在场景中")
        print("lookdev几何体已连接ABC动画数据")
        print("XGen毛发缓存路径已设置")
        print("准备就绪！可以按空格键播放动画查看效果。")


# ===== 插件功能函数 =====

def show_lookdev_animation_setup_ui(*args):
    """显示Lookdev动画组装工具UI"""
    ui = LookdevAnimationSetupUI()
    ui.show_ui()
    return ui

def quick_setup_lookdev_animation(*args):
    """快速设置Lookdev动画"""
    # 获取选择的文件
    selected = cmds.ls(selection=True)
    if len(selected) >= 2:
        tool = LookdevAnimationSetup()
        # 这里可以添加快速设置逻辑
        cmds.headsUpMessage("快速设置功能开发中...")
    else:
        cmds.warning("请选择Lookdev文件和ABC文件")

def get_time_from_selected_abc(*args):
    """从选择的ABC文件获取时间范围"""
    selected = cmds.ls(selection=True)
    if selected:
        # 检查是否选择了ABC文件节点
        abc_nodes = [node for node in selected if cmds.nodeType(node) == "AlembicNode"]
        if abc_nodes:
            abc_node = abc_nodes[0]
            start_frame = cmds.getAttr(f"{abc_node}.startFrame")
            end_frame = cmds.getAttr(f"{abc_node}.endFrame")

            # 设置时间范围
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
    mplugin = omm.MFnPlugin(mobject, "LookdevAnimationTools", "1.1", "any")

    # 删除已存在的菜单
    if cmds.menu("menuLookdevAnimation", exists=True):
        cmds.deleteUI("menuLookdevAnimation", menu=True)

    # 获取主窗口
    gMainWindow = mel.eval("global string $gMainWindow;$temp = $gMainWindow")

    # 创建主菜单
    cmds.menu("menuLookdevAnimation",
              label="Lookdev动画工具",
              parent=gMainWindow,
              tearOff=True)

    # 添加菜单项
    cmds.menuItem(label="显示主界面",
                 command=show_lookdev_animation_setup_ui,
                 annotation="打开Lookdev动画组装工具主界面")

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
                 command=lambda x: cmds.select(cmds.ls(type="AlembicNode")) if cmds.ls(type="AlembicNode") else cmds.warning("没有ABC节点"),
                 annotation="选择场景中的所有ABC节点")

    cmds.menuItem(label="检查材质",
                 command=lambda x: LookdevAnimationSetup().check_unmaterialized_objects(),
                 annotation="检查没有材质的对象")

    cmds.menuItem(label="检查XGen",
                 command=lambda x: LookdevAnimationSetup().check_xgen_status(),
                 annotation="检查XGen毛发状态")

    # 子菜单 - 帮助
    help_submenu = cmds.menuItem(label="帮助", subMenu=True)

    cmds.menuItem(label="关于",
                 command=lambda x: cmds.confirmDialog(
                     title="关于",
                     message="Lookdev动画组装工具 v1.1\n\n功能：\n• 自动导入Lookdev文件\n• 导入动画ABC缓存并连接到Lookdev几何体\n• 导入动画相机ABC并自动获取时间范围\n• 设置XGen毛发缓存路径\n• 材质检查和修复\n• 场景参数设置\n\n作者：Maya Pipeline Team",
                     button=["确定"]),
                 annotation="显示关于信息")

    cmds.menuItem(label="使用说明",
                 command=lambda x: cmds.confirmDialog(
                     title="使用说明",
                     message="使用说明：\n\n1. 打开主界面\n2. 设置文件路径\n3. 点击'从相机ABC获取'自动设置时间范围\n4. 执行组装操作\n\n详细说明请查看主界面的帮助菜单。",
                     button=["确定"]),
                 annotation="显示使用说明")

    print("Lookdev动画工具插件已加载 v1.1")

def uninitializePlugin(mobject):
    """Uninitialize the script plug-in"""
    # 删除菜单
    if cmds.menu("menuLookdevAnimation", exists=True):
        cmds.deleteUI("menuLookdevAnimation", menu=True)

    print("Lookdev动画工具插件已卸载")

# 主函数 - 直接运行时使用
def main():
    """主函数 - 用于直接运行脚本"""
    return show_lookdev_animation_setup_ui()

# 如果直接运行此脚本
if __name__ == "__main__":
    show_lookdev_animation_setup_ui()