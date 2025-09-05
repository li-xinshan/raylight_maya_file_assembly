"""
UI事件处理模块
负责处理所有UI事件和用户交互
"""

import maya.cmds as cmds
import maya.mel as mel
import os
import subprocess


class UIEventHandlers:
    """UI事件处理器"""
    
    def __init__(self, main_ui):
        self.main_ui = main_ui
        self.ui = main_ui.ui
        self.core = main_ui.core
    
    # ===== 配置相关事件 =====
    
    def on_config_path_changed(self, *args):
        """配置文件路径改变时的回调"""
        config_path = cmds.textField(self.ui['config_path'], query=True, text=True)
        if config_path and os.path.exists(config_path):
            success = self.core.load_config(config_path)
            if success:
                self.main_ui.update_asset_list()
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
        """资产选择改变时的回调 - 旧版本兼容"""
        # 这个函数保留用于兼容，但现在使用on_assets_selected
        pass
    
    def on_assets_selected(self, *args):
        """资产多选改变时的回调"""
        selected_items = cmds.textScrollList(self.ui['asset_list'], query=True, selectItem=True) or []
        
        if not selected_items:
            return
        
        # 过滤掉提示信息
        valid_assets = [item for item in selected_items 
                       if item not in ["请先加载配置文件", "请先选择场次镜头或加载配置文件"]]
        
        if not valid_assets:
            return
        
        # 如果只选择了一个资产，设置为当前资产
        if len(valid_assets) == 1:
            asset_name = self._parse_asset_name(valid_assets[0])
            success = self.core.set_current_asset(asset_name)
            if success:
                self.main_ui.update_asset_info()
                self.main_ui.update_namespace()
        else:
            # 多选时显示统计信息
            self._show_batch_info(valid_assets)
    
    def _parse_asset_name(self, display_name):
        """解析资产显示名称获取实际资产名"""
        if " (" in display_name and display_name.endswith(")"):
            return display_name.split(" (")[0]
        return display_name
    
    def _show_batch_info(self, selected_assets):
        """显示批量选择信息"""
        # 统计选中的资产类型
        asset_types = {}
        for asset in selected_assets:
            asset_name = self._parse_asset_name(asset)
            asset_config = self.core.config_manager.get_asset_config(asset_name)
            if asset_config:
                asset_type = asset_config.get('asset_type', 'unknown')
                if asset_type not in asset_types:
                    asset_types[asset_type] = []
                asset_types[asset_type].append(asset_name)
        
        # 更新信息显示
        info_text = f"已选择 {len(selected_assets)} 个资产:\n\n"
        for asset_type, assets in asset_types.items():
            info_text += f"{asset_type}: {len(assets)} 个\n"
            for asset in assets[:3]:  # 只显示前3个
                info_text += f"  • {asset}\n"
            if len(assets) > 3:
                info_text += f"  ... 还有 {len(assets)-3} 个\n"
        
        cmds.scrollField(self.ui['asset_info'], edit=True, text=info_text)

    def refresh_assets(self, *args):
        """刷新资产列表"""
        self.main_ui.update_asset_list()
    
    # ===== 批量选择功能 =====
    
    def select_all_assets(self, *args):
        """全选所有资产"""
        all_items = cmds.textScrollList(self.ui['asset_list'], query=True, allItems=True) or []
        valid_items = [item for item in all_items 
                      if item not in ["请先加载配置文件", "请先选择场次镜头或加载配置文件"]]
        if valid_items:
            cmds.textScrollList(self.ui['asset_list'], edit=True, deselectAll=True)
            cmds.textScrollList(self.ui['asset_list'], edit=True, selectItem=valid_items)
            self.on_assets_selected()
    
    def deselect_all_assets(self, *args):
        """取消所有选择"""
        cmds.textScrollList(self.ui['asset_list'], edit=True, deselectAll=True)
        cmds.scrollField(self.ui['asset_info'], edit=True, text="未选择资产")
    
    def select_character_assets(self, *args):
        """选择所有角色资产"""
        self._select_by_type("character")
    
    def select_prop_assets(self, *args):
        """选择所有道具资产"""
        self._select_by_type("prop")
    
    def _select_by_type(self, asset_type):
        """按类型选择资产"""
        all_items = cmds.textScrollList(self.ui['asset_list'], query=True, allItems=True) or []
        
        # 获取指定类型的资产
        type_assets = []
        for item in all_items:
            if item in ["请先加载配置文件", "请先选择场次镜头或加载配置文件"]:
                continue
            asset_name = self._parse_asset_name(item)
            asset_config = self.core.config_manager.get_asset_config(asset_name)
            if asset_config and asset_config.get('asset_type') == asset_type:
                type_assets.append(item)
        
        if type_assets:
            cmds.textScrollList(self.ui['asset_list'], edit=True, deselectAll=True)
            cmds.textScrollList(self.ui['asset_list'], edit=True, selectItem=type_assets)
            self.on_assets_selected()
        else:
            self.main_ui.log_message(f"没有找到类型为 {asset_type} 的资产")
    
    def batch_import_selected(self, *args):
        """批量导入选中的资产"""
        selected_items = cmds.textScrollList(self.ui['asset_list'], query=True, selectItem=True) or []
        
        # 过滤有效资产
        valid_assets = [item for item in selected_items 
                       if item not in ["请先加载配置文件", "请先选择场次镜头或加载配置文件"]]
        
        if not valid_assets:
            self.main_ui.log_message("❌ 请先选择要导入的资产")
            return
        
        # 确认对话框
        result = cmds.confirmDialog(
            title="批量导入确认",
            message=f"即将批量导入 {len(valid_assets)} 个资产\n\n是否继续？",
            button=["执行", "取消"],
            defaultButton="执行",
            cancelButton="取消",
            dismissString="取消"
        )
        
        if result != "执行":
            return
        
        # 执行批量导入
        self._execute_batch_import(valid_assets)
    
    def _execute_batch_import(self, asset_list):
        """执行批量导入"""
        self.main_ui.log_message(f"\n{'='*50}")
        self.main_ui.log_message(f"开始批量导入 {len(asset_list)} 个资产")
        self.main_ui.log_message(f"{'='*50}\n")
        
        success_count = 0
        failed_assets = []
        
        # 逐个导入资产
        for i, asset_item in enumerate(asset_list):
            asset_name = self._parse_asset_name(asset_item)
            
            self.main_ui.log_message(f"\n[{i+1}/{len(asset_list)}] 正在导入: {asset_name}")
            self.main_ui.log_message("-" * 40)
            
            # 设置当前资产
            success = self.core.set_current_asset(asset_name)
            if not success:
                self.main_ui.log_message(f"❌ 设置资产 {asset_name} 失败")
                failed_assets.append(asset_name)
                continue
            
            # 执行所有步骤
            try:
                result = self.core.execute_all_steps()
                if result:
                    success_count += 1
                    self.main_ui.log_message(f"✅ 资产 {asset_name} 导入成功")
                else:
                    failed_assets.append(asset_name)
                    self.main_ui.log_message(f"❌ 资产 {asset_name} 导入失败")
            except Exception as e:
                failed_assets.append(asset_name)
                self.main_ui.log_message(f"❌ 资产 {asset_name} 导入异常: {str(e)}")
            
            # 更新进度
            progress = int((i + 1) / len(asset_list) * 100)
            self.main_ui.update_progress(progress)
        
        # 显示总结
        self.main_ui.log_message(f"\n{'='*50}")
        self.main_ui.log_message(f"批量导入完成")
        self.main_ui.log_message(f"成功: {success_count} 个")
        self.main_ui.log_message(f"失败: {len(failed_assets)} 个")
        if failed_assets:
            self.main_ui.log_message(f"失败资产: {', '.join(failed_assets)}")
        self.main_ui.log_message(f"{'='*50}\n")

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

    # ===== 参数设置事件 =====
    
    def on_namespace_changed(self, *args):
        """命名空间改变时的回调"""
        namespace = cmds.textField(self.ui['namespace'], query=True, text=True)
        if hasattr(self.core, 'lookdev_namespace'):
            self.core.lookdev_namespace = namespace

    def on_camera_path_changed(self, *args):
        """相机文件路径改变时的回调"""
        camera_path = cmds.textField(self.ui['camera_path'], query=True, text=True)
        if camera_path:
            success = self.core.set_manual_camera_file(camera_path)
            if success:
                self.main_ui.log_message(f"✅ 手动设置相机文件: {os.path.basename(camera_path)}")
            else:
                self.main_ui.log_message(f"❌ 相机文件无效或不存在")
    
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
        self.main_ui.log_message("已清除手动指定的相机文件，将使用自动查找")
        # 重新查找相机文件
        self.core._find_camera_file()
        if self.core.current_camera_file:
            self.main_ui.log_message(f"自动找到相机文件: {os.path.basename(self.core.current_camera_file)}")
        else:
            self.main_ui.log_message("未能自动找到相机文件")

    # ===== 执行步骤事件 =====

    def step1_import_lookdev(self, *args):
        """步骤1: 导入Lookdev文件"""
        self.main_ui.log_message("\n=== 步骤1: 导入Lookdev文件 ===")
        self.main_ui.update_progress(1)

        try:
            success = self.core.step1_import_lookdev()
            
            if success:
                self.main_ui.log_message("✅ Lookdev文件导入成功")
                self.main_ui.update_button_state('step1_btn', True)
            else:
                self.main_ui.log_message("❌ Lookdev文件导入失败")
                self.main_ui.update_button_state('step1_btn', False)
        except Exception as e:
            self.main_ui.log_message(f"❌ 步骤1执行出错: {str(e)}")
            self.main_ui.update_button_state('step1_btn', False)

    def step2_import_and_connect_animation_abc(self, *args):
        """步骤2: 导入动画ABC并连接"""
        self.main_ui.log_message("\n=== 步骤2: 导入动画ABC并连接 ===")
        self.main_ui.update_progress(2)

        try:
            success = self.core.step2_import_and_connect_animation_abc()
            
            if success:
                self.main_ui.log_message("✅ 动画ABC缓存导入并连接成功")
                self.main_ui.update_button_state('step2_btn', True)
            else:
                self.main_ui.log_message("❌ 动画ABC缓存导入失败")
                self.main_ui.update_button_state('step2_btn', False)
        except Exception as e:
            self.main_ui.log_message(f"❌ 步骤2执行出错: {str(e)}")
            self.main_ui.update_button_state('step2_btn', False)

    def step3_import_camera_abc(self, *args):
        """步骤3: 导入动画相机ABC"""
        self.main_ui.log_message("\n=== 步骤3: 导入动画相机ABC ===")
        self.main_ui.update_progress(3)

        try:
            success = self.core.step3_import_camera_abc()
            
            if success:
                self.main_ui.log_message("✅ 动画相机ABC导入成功")
                self.main_ui.update_button_state('step3_btn', True)
            else:
                self.main_ui.log_message("❌ 动画相机ABC导入失败")
                self.main_ui.update_button_state('step3_btn', False)
        except Exception as e:
            self.main_ui.log_message(f"❌ 步骤3执行出错: {str(e)}")
            self.main_ui.update_button_state('step3_btn', False)

    def step4_setup_hair_cache(self, *args):
        """步骤4: 设置毛发缓存路径"""
        self.main_ui.log_message("\n=== 步骤4: 设置毛发缓存路径 ===")
        self.main_ui.update_progress(4)

        try:
            success = self.core.step4_setup_hair_cache()
            
            if success:
                self.main_ui.log_message("✅ 毛发缓存路径设置成功")
                self.main_ui.update_button_state('step4_btn', True)
            else:
                self.main_ui.log_message("❌ 毛发缓存路径设置失败")
                self.main_ui.update_button_state('step4_btn', False)
        except Exception as e:
            self.main_ui.log_message(f"❌ 步骤4执行出错: {str(e)}")
            self.main_ui.update_button_state('step4_btn', False)

    def step5_fix_materials(self, *args):
        """步骤5: 检查修复材质"""
        self.main_ui.log_message("\n=== 步骤5: 检查修复材质 ===")
        self.main_ui.update_progress(5)

        try:
            success = self.core.step5_fix_materials()
                
            if success:
                self.main_ui.log_message("✅ 材质检查修复完成")
                self.main_ui.update_button_state('step5_btn', True)
            else:
                self.main_ui.update_button_state('step5_btn', False)
        except Exception as e:
            self.main_ui.log_message(f"❌ 步骤5执行出错: {str(e)}")
            self.main_ui.update_button_state('step5_btn', False)

    def step6_setup_scene(self, *args):
        """步骤6: 设置场景参数"""
        self.main_ui.log_message("\n=== 步骤6: 设置场景参数 ===")
        self.main_ui.update_progress(6)

        try:
            success = self.core.step6_setup_scene()
                
            if success:
                self.main_ui.log_message("✅ 场景参数设置完成")
                self.main_ui.update_button_state('step6_btn', True)
            else:
                self.main_ui.update_button_state('step6_btn', False)
        except Exception as e:
            self.main_ui.log_message(f"❌ 步骤6执行出错: {str(e)}")
            self.main_ui.update_button_state('step6_btn', False)

    def execute_all_steps(self, *args):
        """一键执行所有步骤"""
        self.main_ui.log_message("\n" + "=" * 50)
        self.main_ui.log_message("开始一键执行所有步骤")
        self.main_ui.log_message("=" * 50)

        # 重置进度
        self.main_ui.update_progress(0)
        self.main_ui.reset_button_states()

        try:
            # 检查是否选择了资产
            if not self.core.current_asset:
                self.main_ui.log_message("❌ 请先选择资产")
                return
            
            success = self.core.execute_all_steps()
            if success:
                self.main_ui.log_message("\n🎉 所有步骤执行完成！")
                self.main_ui.update_progress(6)
                # 更新所有按钮状态为成功
                for btn in ['step1_btn', 'step2_btn', 'step3_btn', 'step4_btn', 'step5_btn', 'step6_btn']:
                    self.main_ui.update_button_state(btn, True)
            else:
                self.main_ui.log_message("\n⚠️  执行过程中遇到问题")
                    
        except Exception as e:
            self.main_ui.log_message(f"❌ 执行过程出错: {str(e)}")

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
            self.main_ui.log_message("\n=== 重置场景 ===")
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
                self.main_ui.update_progress(0)
                self.main_ui.reset_button_states()
                self.main_ui.log_message("✅ 场景重置完成")

                # 重置组装状态
                self.core.reset_assembly_status()

            except Exception as e:
                self.main_ui.log_message(f"❌ 场景重置失败: {str(e)}")

    # ===== 工具函数事件 =====

    def play_animation(self, *args):
        """播放动画"""
        cmds.play(forward=True)
        self.main_ui.log_message("开始播放动画")

    def stop_animation(self, *args):
        """停止动画"""
        cmds.play(state=False)
        self.main_ui.log_message("停止播放动画")

    def fit_view(self, *args):
        """适配视图"""
        cmds.select(all=True)
        cmds.viewFit()
        cmds.select(clear=True)
        self.main_ui.log_message("视图已适配")

    def check_materials(self, *args):
        """检查材质"""
        self.main_ui.log_message("\n=== 材质检查 ===")
        try:
            # 调用材质管理器检查
            results = self.core.coordinator.material_manager.check_and_fix_materials()
            self.main_ui.log_message(f"✅ 材质检查完成: {results['total_materials']} 个材质")
        except Exception as e:
            self.main_ui.log_message(f"材质检查失败: {str(e)}")

    def check_textures(self, *args):
        """检查纹理"""
        self.main_ui.log_message("\n=== 纹理检查 ===")
        try:
            # 调用材质管理器检查纹理
            results = self.core.coordinator.material_manager.check_and_fix_materials()
            self.main_ui.log_message(f"✅ 纹理检查完成: {results['missing_textures']} 个缺失纹理")
        except Exception as e:
            self.main_ui.log_message(f"纹理检查失败: {str(e)}")

    def handle_special_groups(self, *args):
        """处理特殊组的blendShape连接"""
        self.main_ui.log_message("\n=== 手动处理特殊组 ===")
        try:
            if not self.core.current_asset:
                self.main_ui.log_message("❌ 请先选择资产")
                return
            
            success = self.core.coordinator.animation_manager.handle_special_groups_blendshape(
                self.core.lookdev_namespace
            )
            if success:
                self.main_ui.log_message("✅ 特殊组处理完成")
            else:
                self.main_ui.log_message("⚠️  特殊组处理未完成或无需处理")
        except Exception as e:
            self.main_ui.log_message(f"❌ 特殊组处理失败: {str(e)}")

    def handle_cloth_blendshapes(self, *args):
        """手动处理布料blendShape连接"""
        self.main_ui.log_message("\n=== 手动处理布料BlendShape ===")
        try:
            if not self.core.current_asset:
                self.main_ui.log_message("❌ 请先选择资产")
                return
            
            # 调用动画管理器处理布料BlendShape
            success = self.core.coordinator.animation_manager._handle_cloth_blendshapes()
            
            if success:
                self.main_ui.log_message("✅ 布料BlendShape处理完成")
            else:
                self.main_ui.log_message("❌ 布料BlendShape处理失败")
                
        except Exception as e:
            self.main_ui.log_message(f"❌ 布料BlendShape处理失败: {str(e)}")

    def check_xgen(self, *args):
        """检查XGen状态"""
        self.main_ui.log_message("\n=== XGen检查 ===")
        try:
            stats = self.core.coordinator.xgen_manager.get_xgen_statistics()
            self.main_ui.log_message(f"XGen调色板: {stats['palette_count']} 个")
            self.main_ui.log_message(f"XGen描述: {stats['description_count']} 个")
        except Exception as e:
            self.main_ui.log_message(f"XGen检查失败: {str(e)}")

    def open_folder(self, *args):
        """打开文件夹"""
        if self.core.current_lookdev_file:
            folder_path = os.path.dirname(self.core.current_lookdev_file)
        else:
            self.main_ui.log_message("没有可打开的文件夹")
            return
            
        if os.path.exists(folder_path):
            if os.name == 'nt':  # Windows
                subprocess.Popen(['explorer', folder_path])
            else:  # macOS/Linux
                subprocess.Popen(['open', folder_path])
            self.main_ui.log_message(f"已打开文件夹: {folder_path}")
        else:
            self.main_ui.log_message("文件夹不存在")

    def show_scene_info(self, *args):
        """显示场景信息"""
        self.main_ui.log_message("\n=== 场景信息 ===")
        try:
            # 统计信息
            all_meshes = cmds.ls(type="mesh", noIntermediate=True)
            abc_nodes = cmds.ls(type="AlembicNode")
            shading_groups = cmds.ls(type="shadingEngine")

            self.main_ui.log_message(f"几何体数量: {len(all_meshes)}")
            self.main_ui.log_message(f"ABC节点数量: {len(abc_nodes)}")
            self.main_ui.log_message(f"材质组数量: {len(shading_groups)}")

            # 时间范围
            min_time = cmds.playbackOptions(query=True, min=True)
            max_time = cmds.playbackOptions(query=True, max=True)
            current_time = cmds.currentTime(query=True)
            self.main_ui.log_message(f"时间范围: {min_time} - {max_time} (当前: {current_time})")

        except Exception as e:
            self.main_ui.log_message(f"获取场景信息失败: {str(e)}")

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

                self.main_ui.log_message(f"报告已保存: {report_file[0]}")
            except Exception as e:
                self.main_ui.log_message(f"保存报告失败: {str(e)}")

    # ===== 日志和状态事件 =====

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
                self.main_ui.log_message(f"日志已保存: {log_file[0]}")
            except Exception as e:
                self.main_ui.log_message(f"保存日志失败: {str(e)}")

    # ===== 菜单事件 =====

    def load_json_config(self, *args):
        """加载JSON配置菜单命令"""
        self.browse_config_file()

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
                self.main_ui.log_message(f"配置已保存: {config_file[0]}")
            else:
                self.main_ui.log_message("保存配置失败")

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
                self.main_ui.log_message("场景清理完成")
            except Exception as e:
                self.main_ui.log_message(f"场景清理失败: {str(e)}")

    def reload_plugins(self, *args):
        """重新加载插件"""
        plugins = ['AbcImport', 'AbcExport', 'xgenToolkit']
        for plugin in plugins:
            try:
                if cmds.pluginInfo(plugin, query=True, loaded=True):
                    cmds.unloadPlugin(plugin)
                cmds.loadPlugin(plugin)
                self.main_ui.log_message(f"插件 {plugin} 重新加载成功")
            except Exception as e:
                self.main_ui.log_message(f"插件 {plugin} 重新加载失败: {str(e)}")

    def close_window(self, *args):
        """关闭窗口"""
        if cmds.window(self.main_ui.window_name, exists=True):
            cmds.deleteUI(self.main_ui.window_name, window=True)

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

    # ===== 项目扫描事件 =====

    def scan_project_shots(self, *args):
        """扫描项目场次镜头"""
        try:
            self.main_ui.log_message("开始多线程扫描项目动画文件...")
            
            # 定义进度回调函数
            def progress_callback(current, total, message):
                progress = int((current / total) * 100) if total > 0 else 0
                self.main_ui.log_message(f"📊 扫描进度 {progress}%: {message}")
            
            # 获取扫描数据（支持进度回调）
            self.main_ui.project_shots = self.core.config_manager.scan_project_animation_files(progress_callback)
            
            # 更新combobox
            self.main_ui.update_shot_list()
            
            if self.main_ui.project_shots:
                self.main_ui.log_message(f"✅ 扫描完成，找到 {len(self.main_ui.project_shots)} 个完整场次/镜头")
            else:
                self.main_ui.log_message("❌ 未找到任何完整的场次/镜头")
                
        except Exception as e:
            self.main_ui.log_message(f"❌ 扫描项目失败: {str(e)}")

    def on_shot_changed(self, *args):
        """场次镜头选择变化回调 - 直接加载配置"""
        try:
            selected_item = cmds.optionMenu(self.ui['shot_list'], query=True, value=True)
            
            if selected_item and "未找到" not in selected_item and "扫描中" not in selected_item:
                # 提取场次镜头key（格式：s310_c0990 (5文件, 3资产)）
                shot_key = selected_item.split(' ')[0]  # 取第一部分 s310_c0990
                
                if shot_key in self.main_ui.project_shots:
                    self.main_ui.current_shot_key = shot_key
                    shot_data = self.main_ui.project_shots[shot_key]
                    
                    self.main_ui.log_message(f"选择场次镜头: {shot_key}")
                    
                    # 直接加载配置
                    self.main_ui._load_shot_config_internal(shot_key, shot_data)
                    
        except Exception as e:
            self.main_ui.log_message(f"❌ 场次镜头选择失败: {str(e)}")

    def load_shot_config(self, *args):
        """加载选中场次镜头的配置"""
        try:
            if not self.main_ui.current_shot_key:
                self.main_ui.log_message("❌ 请先选择场次镜头")
                return
            
            if self.main_ui.current_shot_key not in self.main_ui.project_shots:
                self.main_ui.log_message("❌ 场次镜头数据无效")
                return
            
            shot_data = self.main_ui.project_shots[self.main_ui.current_shot_key]
            self.main_ui.log_message(f"手动加载 {self.main_ui.current_shot_key} 的配置...")
            
            # 调用内部方法
            self.main_ui._load_shot_config_internal(self.main_ui.current_shot_key, shot_data)
                
        except Exception as e:
            self.main_ui.log_message(f"❌ 加载场次镜头配置失败: {str(e)}")