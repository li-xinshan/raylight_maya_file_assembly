"""
UI组件创建模块
负责创建所有UI界面组件
"""

import maya.cmds as cmds


class UIComponents:
    """UI组件创建器"""
    
    def __init__(self, ui_dict, event_handler):
        self.ui = ui_dict
        self.handler = event_handler
    
    def create_main_window(self, window_name, window_title):
        """创建主窗口"""
        # 删除已存在的窗口
        if cmds.window(window_name, exists=True):
            cmds.deleteUI(window_name, window=True)

        # 创建窗口
        self.ui['window'] = cmds.window(
            window_name,
            title=window_title,
            width=520,
            height=800,
            sizeable=True,
            menuBar=True
        )

        # 创建菜单
        self.create_menu()

        # 创建可滚动的主布局
        scroll_layout = cmds.scrollLayout(
            horizontalScrollBarThickness=0,
            verticalScrollBarThickness=16,
            childResizable=True
        )

        # 创建主列布局
        main_layout = cmds.columnLayout(
            adjustableColumn=False, 
            width=500,
            rowSpacing=5, 
            columnOffset=('both', 10)
        )

        # 标题
        cmds.text(label="Lookdev动画组装工具 v2.0", font="boldLabelFont", height=30, 
                 backgroundColor=[0.2, 0.7, 0.4], width=480)
        cmds.separator(height=10, width=480)
        
        return self.ui['window']
    
    def create_config_section(self, section_collapse_states):
        """创建配置设置区域"""
        cmds.frameLayout(label="配置设置", collapsable=True, collapse=section_collapse_states['config'], 
                        marginWidth=10, marginHeight=10, width=480,
                        borderStyle='etchedIn', font='boldLabelFont',
                        backgroundColor=[0.35, 0.35, 0.38])

        # 项目扫描模式
        cmds.text(label="项目动画选择:", align="left", font="boldLabelFont")
        
        # 场次镜头选择
        shot_row = cmds.rowLayout(numberOfColumns=4, adjustableColumn=2, columnWidth4=(80, 200, 80, 70))
        cmds.text(label="场次/镜头:")
        self.ui['shot_list'] = cmds.optionMenu(label="", changeCommand=self.handler.on_shot_changed)
        cmds.menuItem(label="扫描中...")
        cmds.button(label="扫描项目", command=self.handler.scan_project_shots, width=80)
        cmds.button(label="加载配置", command=self.handler.load_shot_config, width=70)
        cmds.setParent('..')

        cmds.separator(height=10)

        # JSON配置文件
        cmds.text(label="或使用JSON配置文件:", align="left", font="boldLabelFont")
        config_row = cmds.rowLayout(numberOfColumns=3, adjustableColumn=2, columnWidth3=(320, 60, 30))
        self.ui['config_path'] = cmds.textField(text="", changeCommand=self.handler.on_config_path_changed)
        cmds.button(label="浏览", command=self.handler.browse_config_file, width=60)
        self.ui['config_status'] = cmds.text(label="●", width=30, backgroundColor=[0.8, 0.3, 0.3])
        cmds.setParent('..')

        cmds.separator(height=10)

        # 资产选择
        cmds.text(label="选择资产:", align="left", font="boldLabelFont")
        asset_row = cmds.rowLayout(numberOfColumns=3, adjustableColumn=2, columnWidth3=(320, 80, 40))
        self.ui['asset_list'] = cmds.optionMenu(label="", changeCommand=self.handler.on_asset_changed)
        cmds.menuItem(label="请先选择场次镜头或加载配置文件")
        cmds.button(label="刷新资产", command=self.handler.refresh_assets, width=80)
        cmds.button(label="详情", command=self.handler.show_asset_details, width=40)
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

    def create_settings_section(self, section_collapse_states):
        """创建设置参数区域"""
        cmds.frameLayout(label="参数设置", collapsable=True, collapse=section_collapse_states['settings'],
                        marginWidth=10, marginHeight=10, width=480,
                        borderStyle='etchedIn', font='boldLabelFont',
                        backgroundColor=[0.35, 0.35, 0.38])

        # 命名空间设置
        cmds.rowLayout(numberOfColumns=2, adjustableColumn=2, columnWidth2=(120, 300))
        cmds.text(label="命名空间:", align="left")
        self.ui['namespace'] = cmds.textField(text="asset_lookdev", changeCommand=self.handler.on_namespace_changed)
        cmds.setParent('..')

        cmds.separator(height=10)

        # 相机文件设置
        cmds.text(label="相机文件设置:", align="left", font="boldLabelFont")
        camera_row = cmds.rowLayout(numberOfColumns=3, adjustableColumn=2, columnWidth3=(300, 60, 60))
        self.ui['camera_path'] = cmds.textField(text="", placeholderText="自动查找相机文件...", changeCommand=self.handler.on_camera_path_changed)
        cmds.button(label="浏览", command=self.handler.browse_camera_file, width=60)
        cmds.button(label="清除", command=self.handler.clear_camera_file, width=60)
        cmds.setParent('..')
        
        cmds.separator(height=10)

        cmds.setParent('..')  # frameLayout

    def create_execution_section(self, section_collapse_states):
        """创建执行操作区域"""
        cmds.frameLayout(label="执行操作", collapsable=True, collapse=section_collapse_states['execution'],
                        marginWidth=10, marginHeight=10, width=480,
                        borderStyle='etchedIn', font='boldLabelFont',
                        backgroundColor=[0.35, 0.35, 0.38])

        # 单步执行按钮
        cmds.text(label="分步执行:", align="left", font="boldLabelFont")

        step_col = cmds.columnLayout(adjustableColumn=True, rowSpacing=5)

        self.ui['step1_btn'] = cmds.button(label="步骤1: 导入Lookdev文件",
                                           command=self.handler.step1_import_lookdev,
                                           backgroundColor=[0.4, 0.6, 0.8], height=35)

        self.ui['step2_btn'] = cmds.button(label="步骤2: 导入动画ABC并连接",
                                           command=self.handler.step2_import_and_connect_animation_abc,
                                           backgroundColor=[0.4, 0.6, 0.8], height=35)

        self.ui['step3_btn'] = cmds.button(label="步骤3: 导入动画相机ABC",
                                           command=self.handler.step3_import_camera_abc,
                                           backgroundColor=[0.4, 0.6, 0.8], height=35)

        self.ui['step4_btn'] = cmds.button(label="步骤4: 设置毛发缓存路径",
                                           command=self.handler.step4_setup_hair_cache,
                                           backgroundColor=[0.4, 0.6, 0.8], height=35)

        self.ui['step5_btn'] = cmds.button(label="步骤5: 检查修复材质",
                                           command=self.handler.step5_fix_materials,
                                           backgroundColor=[0.4, 0.6, 0.8], height=35)

        self.ui['step6_btn'] = cmds.button(label="步骤6: 设置场景参数",
                                           command=self.handler.step6_setup_scene,
                                           backgroundColor=[0.4, 0.6, 0.8], height=35)

        cmds.setParent('..')  # step_col

        cmds.separator(height=10)

        # 一键执行
        cmds.text(label="一键执行:", align="left", font="boldLabelFont")

        execute_row = cmds.rowLayout(numberOfColumns=2, adjustableColumn=2, columnWidth2=(200, 200))

        self.ui['execute_all_btn'] = cmds.button(label="🚀 一键完成所有步骤",
                                                 command=self.handler.execute_all_steps,
                                                 backgroundColor=[0.2, 0.8, 0.4], height=45)

        self.ui['reset_btn'] = cmds.button(label="🔄 重置场景",
                                           command=self.handler.reset_scene,
                                           backgroundColor=[0.8, 0.4, 0.2], height=45)

        cmds.setParent('..')  # execute_row
        cmds.setParent('..')  # frameLayout

    def create_status_section(self, section_collapse_states):
        """创建状态显示区域"""
        cmds.frameLayout(label="状态信息", collapsable=True, collapse=section_collapse_states['status'],
                        marginWidth=10, marginHeight=10, width=480,
                        borderStyle='etchedIn', font='boldLabelFont',
                        backgroundColor=[0.35, 0.35, 0.38])

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
        cmds.button(label="清空日志", command=self.handler.clear_log, width=80)
        cmds.button(label="保存日志", command=self.handler.save_log, width=80)
        cmds.text(label="")  # 占位符
        cmds.setParent('..')

        cmds.setParent('..')  # frameLayout

    def create_tools_section(self, section_collapse_states):
        """创建工具按钮区域"""
        cmds.frameLayout(label="附加工具", collapsable=True, collapse=section_collapse_states['tools'],
                        marginWidth=10, marginHeight=10, width=480,
                        borderStyle='etchedIn', font='boldLabelFont',
                        backgroundColor=[0.35, 0.35, 0.38])

        # 第一行工具
        tools_row1 = cmds.rowLayout(numberOfColumns=4, adjustableColumn=4)
        cmds.button(label="播放动画", command=self.handler.play_animation, width=100)
        cmds.button(label="停止动画", command=self.handler.stop_animation, width=100)
        cmds.button(label="适配视图", command=self.handler.fit_view, width=100)
        cmds.text(label="")
        cmds.setParent('..')

        # 第二行工具
        tools_row2 = cmds.rowLayout(numberOfColumns=4, adjustableColumn=4)
        cmds.button(label="检查材质", command=self.handler.check_materials, width=100)
        cmds.button(label="检查纹理", command=self.handler.check_textures, width=100)
        cmds.button(label="处理特殊组", command=self.handler.handle_special_groups, width=100)
        cmds.button(label="修复布料驱动", command=self.handler.handle_cloth_blendshapes, width=100, backgroundColor=[0.8, 0.6, 0.4])
        cmds.setParent('..')

        # 第三行工具
        tools_row3 = cmds.rowLayout(numberOfColumns=4, adjustableColumn=4)
        cmds.button(label="检查XGen", command=self.handler.check_xgen, width=100)
        cmds.button(label="打开文件夹", command=self.handler.open_folder, width=100)
        cmds.button(label="场景信息", command=self.handler.show_scene_info, width=100)
        cmds.button(label="导出报告", command=self.handler.export_report, width=100)
        cmds.setParent('..')

        cmds.setParent('..')  # frameLayout

    def create_menu(self):
        """创建菜单栏"""
        # 文件菜单
        file_menu = cmds.menu(label="文件")
        cmds.menuItem(label="加载JSON配置", command=self.handler.load_json_config)
        cmds.menuItem(label="保存配置", command=self.handler.save_config)
        cmds.menuItem(divider=True)
        cmds.menuItem(label="退出", command=self.handler.close_window)

        # 工具菜单
        tools_menu = cmds.menu(label="工具")
        cmds.menuItem(label="刷新资产列表", command=lambda x: self.handler.update_asset_list())
        cmds.menuItem(label="验证配置", command=self.handler.validate_config)
        cmds.menuItem(label="清理场景", command=self.handler.clean_scene)
        cmds.menuItem(divider=True)
        cmds.menuItem(label="重载插件", command=self.handler.reload_plugins)

        # 帮助菜单
        help_menu = cmds.menu(label="帮助")
        cmds.menuItem(label="关于", command=self.handler.show_about)
        cmds.menuItem(label="使用说明", command=self.handler.show_help)