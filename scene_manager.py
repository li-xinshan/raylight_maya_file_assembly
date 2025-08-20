"""
场景管理模块
负责处理Maya场景设置、优化和管理功能
"""

import maya.cmds as cmds
import maya.mel as mel


class SceneManager:
    """场景管理器"""
    
    def __init__(self):
        self.default_units = {
            'linear': 'cm',
            'time': 'film'
        }
    
    def setup_scene_settings(self, start_frame=1001, end_frame=1100):
        """
        设置场景参数
        
        Args:
            start_frame (int): 开始帧
            end_frame (int): 结束帧
        """
        print(f"\n设置场景参数...")
        
        # 设置时间范围
        cmds.playbackOptions(min=start_frame, max=end_frame)
        cmds.currentTime(start_frame)
        print(f"时间范围: {start_frame} - {end_frame}")
        
        # 设置单位
        cmds.currentUnit(linear=self.default_units['linear'], time=self.default_units['time'])
        print(f"单位设置: {self.default_units['linear']} / {self.default_units['time']}")
        
        # 设置视口显示
        self._setup_viewport()
        
        return True
    
    def _setup_viewport(self):
        """设置视口显示"""
        panel = cmds.getPanel(withFocus=True)
        if panel and cmds.modelPanel(panel, query=True, exists=True):
            cmds.modelEditor(panel, edit=True, displayTextures=True, displayLights="all")
            print("视口显示已更新")
    
    def optimize_scene(self, lookdev_namespace=None):
        """
        场景优化
        
        Args:
            lookdev_namespace (str): Lookdev命名空间
        """
        print("开始场景优化...")
        
        # 选择lookdev根节点（如果存在）
        if lookdev_namespace and cmds.objExists(f"{lookdev_namespace}:Master"):
            cmds.select(f"{lookdev_namespace}:Master", replace=True)
            print(f"已选择lookdev根节点: {lookdev_namespace}:Master")
        
        # 刷新视图
        cmds.refresh(currentView=True)
        print("场景优化完成")
        
        return True
    
    def reset_scene(self):
        """重置场景，删除所有引用和ABC节点"""
        print("开始重置场景...")
        
        try:
            # 删除所有引用
            refs = cmds.ls(type="reference")
            removed_refs = 0
            for ref in refs:
                if ref != "sharedReferenceNode":
                    try:
                        cmds.file(removeReference=True, referenceNode=ref)
                        removed_refs += 1
                    except:
                        pass
            
            print(f"已删除 {removed_refs} 个引用")
            
            # 删除所有ABC节点
            abc_nodes = cmds.ls(type="AlembicNode")
            removed_abc = 0
            for node in abc_nodes:
                try:
                    cmds.delete(node)
                    removed_abc += 1
                except:
                    pass
            
            print(f"已删除 {removed_abc} 个ABC节点")
            print("场景重置完成")
            
            return True
            
        except Exception as e:
            print(f"场景重置失败: {str(e)}")
            return False
    
    def clean_scene(self):
        """清理场景未使用的节点"""
        try:
            mel.eval("MLdeleteUnused")
            print("场景清理完成")
            return True
        except Exception as e:
            print(f"场景清理失败: {str(e)}")
            return False
    
    def get_scene_info(self):
        """
        获取场景信息统计
        
        Returns:
            dict: 场景信息字典
        """
        info = {}
        
        try:
            # 几何体统计
            all_meshes = cmds.ls(type="mesh", noIntermediate=True)
            info['mesh_count'] = len(all_meshes)
            
            # ABC节点统计
            abc_nodes = cmds.ls(type="AlembicNode")
            info['abc_nodes_count'] = len(abc_nodes)
            
            # 材质组统计
            shading_groups = cmds.ls(type="shadingEngine")
            info['shading_groups_count'] = len(shading_groups)
            
            # 时间范围
            info['time_range'] = {
                'min': cmds.playbackOptions(query=True, min=True),
                'max': cmds.playbackOptions(query=True, max=True),
                'current': cmds.currentTime(query=True)
            }
            
            # 相机统计
            cameras = cmds.ls(type="camera")
            default_cameras = ["perspShape", "topShape", "frontShape", "sideShape"]
            animation_cameras = [cam for cam in cameras if cam not in default_cameras]
            info['animation_cameras_count'] = len(animation_cameras)
            
            # 可见几何体统计
            visible_meshes = []
            for mesh in all_meshes:
                transform = cmds.listRelatives(mesh, parent=True, type="transform")
                if transform and cmds.getAttr(f"{transform[0]}.visibility"):
                    visible_meshes.append(transform[0])
            info['visible_meshes_count'] = len(visible_meshes)
            
            return info
            
        except Exception as e:
            print(f"获取场景信息失败: {str(e)}")
            return {}
    
    def print_scene_info(self):
        """打印场景信息"""
        print("\n=== 场景信息 ===")
        info = self.get_scene_info()
        
        if info:
            print(f"几何体数量: {info.get('mesh_count', 0)}")
            print(f"ABC节点数量: {info.get('abc_nodes_count', 0)}")
            print(f"材质组数量: {info.get('shading_groups_count', 0)}")
            print(f"动画相机数量: {info.get('animation_cameras_count', 0)}")
            print(f"可见几何体数量: {info.get('visible_meshes_count', 0)}")
            
            time_range = info.get('time_range', {})
            if time_range:
                print(f"时间范围: {time_range.get('min', 0)} - {time_range.get('max', 0)} (当前: {time_range.get('current', 0)})")
    
    def set_time_range_from_abc_node(self, abc_node):
        """
        从ABC节点设置时间范围
        
        Args:
            abc_node (str): ABC节点名称
            
        Returns:
            tuple: (success, start_frame, end_frame)
        """
        try:
            if not cmds.objExists(abc_node):
                return False, None, None
            
            start_frame = cmds.getAttr(f"{abc_node}.startFrame")
            end_frame = cmds.getAttr(f"{abc_node}.endFrame")
            
            cmds.playbackOptions(min=start_frame, max=end_frame)
            cmds.currentTime(start_frame)
            
            print(f"从ABC节点设置时间范围: {start_frame} - {end_frame}")
            return True, start_frame, end_frame
            
        except Exception as e:
            print(f"从ABC节点设置时间范围失败: {str(e)}")
            return False, None, None