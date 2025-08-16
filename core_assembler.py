"""
核心组装器模块
重构后的主要功能类，集成配置管理、文件管理和路径工具
"""

import os
import maya.cmds as cmds
import maya.mel as mel
import xgenm

from config_manager import ConfigManager
from file_manager import FileManager
from path_utils import PathUtils


class CoreAssembler:
    """核心组装器类 - 重构后的主要功能类"""
    
    def __init__(self, config_file=None):
        """
        初始化核心组装器
        
        Args:
            config_file (str): JSON配置文件路径（可选）
        """
        # 初始化管理器
        self.config_manager = ConfigManager(config_file)
        self.file_manager = FileManager()
        self.path_utils = PathUtils()
        
        # 当前工作配置
        self.current_asset = None
        self.current_lookdev_file = None
        self.current_animation_files = []
        self.current_camera_file = None
        self.manual_camera_file = None  # 手动指定的相机文件
        
        # 命名空间配置
        self.lookdev_namespace = "asset_lookdev"
        self.animation_namespace = "asset_animation"
        self.fur_namespace = "asset_fur"
        self.cloth_namespace = "asset_cloth"
        
        # 时间范围设置
        self.start_frame = 1001
        self.end_frame = 1100
        
        # 状态跟踪
        self.assembly_status = {
            'lookdev_imported': False,
            'animation_connected': False,
            'camera_imported': False,
            'hair_configured': False,
            'materials_fixed': False,
            'scene_configured': False
        }
    
    def load_config(self, config_file):
        """
        加载新的配置文件
        
        Args:
            config_file (str): JSON配置文件路径
            
        Returns:
            bool: 是否加载成功
        """
        success = self.config_manager.load_config(config_file)
        
        if success:
            # 重置状态
            self.reset_assembly_status()
            print("配置加载完成，已重置组装状态")
        
        return success
    
    def set_current_asset(self, asset_name):
        """
        设置当前工作的资产
        
        Args:
            asset_name (str): 资产名称
            
        Returns:
            bool: 是否设置成功
        """
        asset_config = self.config_manager.get_asset_config(asset_name)
        
        if not asset_config:
            print(f"未找到资产配置: {asset_name}")
            return False
        
        self.current_asset = asset_config
        
        # 更新所有命名空间
        self.lookdev_namespace = f"{asset_name}_lookdev"
        self.animation_namespace = f"{asset_name}_animation"
        self.fur_namespace = f"{asset_name}_fur"
        self.cloth_namespace = f"{asset_name}_cloth"
        
        # 查找lookdev文件
        self._find_lookdev_file()
        
        # 设置动画文件
        self._set_animation_files()
        
        # 查找相机文件
        self._find_camera_file()
        
        print(f"当前资产设置为: {asset_name}")
        self._print_current_files()
        
        return True
    
    def _find_lookdev_file(self):
        """查找当前资产的lookdev文件"""
        if not self.current_asset:
            print("❌ _find_lookdev_file: 当前没有设置资产")
            return
        
        asset_name = self.current_asset['asset_name']
        asset_type = self.current_asset['asset_type']
        
        print(f"🔍 查找lookdev文件 - 资产: {asset_name}, 类型: {asset_type}")
        
        # 生成lookdev目录路径
        lookdev_dir = self.config_manager.generate_lookdev_path(asset_name, asset_type)
        print(f"🔍 生成的lookdev目录路径: {lookdev_dir}")
        
        # 检查目录是否存在
        if not os.path.exists(lookdev_dir):
            print(f"❌ lookdev目录不存在: {lookdev_dir}")
            self.current_lookdev_file = None
            return
        
        # 查找最新的lookdev文件
        print("🔍 正在查找最新的lookdev文件...")
        latest_file = self.file_manager.get_latest_lookdev_file(lookdev_dir)
        
        if latest_file:
            self.current_lookdev_file = latest_file
            print(f"✅ 找到lookdev文件: {latest_file}")
        else:
            print(f"❌ 未在目录中找到lookdev文件: {lookdev_dir}")
            self.current_lookdev_file = None
    
    def _set_animation_files(self):
        """设置动画文件列表（包含ABC和Maya文件）"""
        if not self.current_asset:
            return
        
        outputs = self.current_asset.get('outputs', [])
        self.current_animation_files = [path for path in outputs if path.endswith(('.abc', '.ma'))]
        
        print(f"找到 {len(self.current_animation_files)} 个动画文件")
        for i, file_path in enumerate(self.current_animation_files, 1):
            file_type = "Maya场景" if file_path.endswith('.ma') else "Alembic缓存"
            print(f"  {i}. {os.path.basename(file_path)} ({file_type})")
    
    def _find_camera_file(self):
        """查找相机文件"""
        print("\n🎥 查找相机文件...")
        
        # 如果有手动指定的相机文件，优先使用
        if self.manual_camera_file and os.path.exists(self.manual_camera_file):
            print(f"   使用手动指定的相机文件: {self.manual_camera_file}")
            self.current_camera_file = self.manual_camera_file
            return
        
        if not self.current_animation_files:
            print("   ❌ 没有动画文件，无法查找相机")
            self.current_camera_file = None
            return
        
        print(f"   动画文件数量: {len(self.current_animation_files)}")
        
        # 使用第一个动画文件推导相机路径
        first_animation = self.current_animation_files[0]
        print(f"   使用第一个动画文件: {first_animation}")
        
        camera_path = self.path_utils.get_best_camera_file(first_animation)
        
        self.current_camera_file = camera_path
        
        if camera_path:
            print(f"   ✅ 找到相机文件: {camera_path}")
        else:
            print("   ❌ 未找到匹配的相机文件")
            
            # 尝试其他动画文件
            if len(self.current_animation_files) > 1:
                print("   尝试其他动画文件...")
                for i, animation_file in enumerate(self.current_animation_files[1:], 2):
                    print(f"   尝试第{i}个动画文件: {animation_file}")
                    camera_path = self.path_utils.get_best_camera_file(animation_file)
                    if camera_path:
                        self.current_camera_file = camera_path
                        print(f"   ✅ 通过第{i}个动画文件找到相机: {camera_path}")
                        break
    
    def set_manual_camera_file(self, camera_file):
        """手动设置相机文件路径"""
        if camera_file and os.path.exists(camera_file):
            self.manual_camera_file = camera_file
            self.current_camera_file = camera_file
            print(f"✅ 手动设置相机文件: {camera_file}")
            return True
        else:
            print(f"❌ 相机文件不存在: {camera_file}")
            return False
    
    def _print_current_files(self):
        """打印当前文件状态"""
        print("\n=== 当前文件配置 ===")
        print(f"Lookdev文件: {self.current_lookdev_file or '未找到'}")
        print(f"动画文件数量: {len(self.current_animation_files)}")
        for i, anim_file in enumerate(self.current_animation_files, 1):
            print(f"  {i}. {anim_file}")
        print(f"相机文件: {self.current_camera_file or '未找到'}")
        print(f"Lookdev命名空间: {self.lookdev_namespace}")
        print(f"动画命名空间: {self.animation_namespace}")
        print(f"毛发命名空间: {self.fur_namespace}")
        print(f"布料命名空间: {self.cloth_namespace}")
        print("==================\n")
    
    def step1_import_lookdev(self):
        """步骤1: 导入lookdev文件"""
        print("\n=== 步骤1: 导入Lookdev文件 ===")
        
        if not self.current_lookdev_file:
            print("❌ 没有可用的lookdev文件")
            # 显示详细的调试信息
            if self.current_asset:
                asset_name = self.current_asset['asset_name']
                asset_type = self.current_asset['asset_type']
                lookdev_dir = self.config_manager.generate_lookdev_path(asset_name, asset_type)
                print(f"🔍 查找的lookdev目录: {lookdev_dir}")
                
                # 检查目录是否存在
                if os.path.exists(lookdev_dir):
                    print("✅ lookdev目录存在")
                    # 列出目录内容
                    try:
                        contents = os.listdir(lookdev_dir)
                        print(f"📁 目录内容: {contents}")
                        
                        # 查找所有子目录
                        subdirs = [d for d in contents if os.path.isdir(os.path.join(lookdev_dir, d))]
                        print(f"📂 子目录: {subdirs}")
                        
                        # 查找各版本目录中的文件
                        for subdir in subdirs:
                            subdir_path = os.path.join(lookdev_dir, subdir)
                            try:
                                subdir_files = os.listdir(subdir_path)
                                print(f"📄 {subdir}/ 目录文件: {subdir_files}")
                            except Exception as e:
                                print(f"❌ 无法读取目录 {subdir}: {e}")
                    except Exception as e:
                        print(f"❌ 无法读取lookdev目录: {e}")
                else:
                    print("❌ lookdev目录不存在")
            else:
                print("❌ 当前没有设置资产")
            return False
        
        if not os.path.exists(self.current_lookdev_file):
            print(f"❌ Lookdev文件不存在: {self.current_lookdev_file}")
            return False
        
        try:
            # 导入文件
            cmds.file(
                self.current_lookdev_file,
                i=True,
                type="mayaAscii" if self.current_lookdev_file.endswith('.ma') else "mayaBinary",
                ignoreVersion=True,
                ra=True,
                mergeNamespacesOnClash=False,
                namespace=self.lookdev_namespace,
                pr=True
            )
            
            print(f"✅ 已导入Lookdev文件: {os.path.basename(self.current_lookdev_file)}")
            print(f"命名空间: {self.lookdev_namespace}")
            
            # 列出导入的主要节点
            imported_nodes = cmds.ls(f"{self.lookdev_namespace}:*", type="transform")
            print(f"导入节点数量: {len(imported_nodes)}")
            
            self.assembly_status['lookdev_imported'] = True
            return True
            
        except Exception as e:
            print(f"❌ 导入Lookdev文件失败: {str(e)}")
            return False
    
    def step2_import_and_connect_animation_abc(self):
        """步骤2: 导入动画ABC并连接"""
        print("\n=== 步骤2: 导入动画文件并连接 ===")
        
        if not self.current_animation_files:
            print("❌ 没有可用的动画文件")
            return False
        
        if not self.assembly_status['lookdev_imported']:
            print("❌ 请先导入Lookdev文件")
            return False
        
        success_count = 0
        
        for i, animation_file in enumerate(self.current_animation_files, 1):
            print(f"\n处理动画文件 {i}/{len(self.current_animation_files)}: {os.path.basename(animation_file)}")
            
            if self._import_single_animation_abc(animation_file):
                success_count += 1
            else:
                print(f"❌ 动画文件 {i} 处理失败")
        
        if success_count > 0:
            print(f"✅ 成功处理 {success_count}/{len(self.current_animation_files)} 个动画文件")
            self.assembly_status['animation_connected'] = True
            return True
        else:
            print("❌ 所有动画文件处理失败")
            return False
    
    def _import_single_animation_abc(self, animation_file):
        """导入单个动画文件（ABC或Maya场景）"""
        try:
            if not os.path.exists(animation_file):
                print(f"❌ 动画文件不存在: {animation_file}")
                return False
            
            # 根据文件扩展名确定导入类型
            file_ext = os.path.splitext(animation_file)[1].lower()
            if file_ext == '.abc':
                import_type = "Alembic"
                # 确保ABC插件已加载
                if not cmds.pluginInfo('AbcImport', query=True, loaded=True):
                    cmds.loadPlugin('AbcImport')
            elif file_ext == '.ma':
                import_type = "mayaAscii"
            elif file_ext == '.mb':
                import_type = "mayaBinary"
            else:
                print(f"❌ 不支持的文件类型: {file_ext}")
                return False
            
            print(f"导入类型: {import_type}")
            
            # 记录导入前状态
            transforms_before = set(cmds.ls(type='transform'))
            if import_type == "Alembic":
                abc_nodes_before = set(cmds.ls(type="AlembicNode"))
            
            # 使用Maya file -import命令导入文件（支持namespace）
            try:
                # 确保命名空间存在
                if not cmds.namespace(exists=self.animation_namespace):
                    cmds.namespace(add=self.animation_namespace)
                
                # 记录导入前的命名空间
                namespaces_before = set(cmds.namespaceInfo(listOnlyNamespaces=True))
                
                # 准备导入参数
                import_kwargs = {
                    'i': True,  # import
                    'type': import_type,
                    'ignoreVersion': True,
                    'mergeNamespacesOnClash': False,
                    'namespace': self.animation_namespace,
                    'returnNewNodes': True  # 返回新创建的节点
                }
                
                # 对于ABC文件添加特定参数
                if import_type == "Alembic":
                    import_kwargs['importTimeRange'] = "combine"
                
                # 使用file -import命令导入文件
                import_result = cmds.file(animation_file, **import_kwargs)
                
                # 检查实际使用的命名空间
                namespaces_after = set(cmds.namespaceInfo(listOnlyNamespaces=True))
                new_namespaces = namespaces_after - namespaces_before
                
                # 如果Maya自动添加了数字后缀，更新命名空间变量
                actual_namespace = self.animation_namespace
                for ns in new_namespaces:
                    if ns.startswith(self.animation_namespace):
                        actual_namespace = ns
                        print(f"⚠️  Maya使用了命名空间: {actual_namespace}")
                        break
                
                # 更新命名空间变量以便后续使用
                self.actual_animation_namespace = actual_namespace
                
                print(f"✅ 已导入动画ABC到命名空间: {actual_namespace}")
                
            except Exception as e:
                print(f"❌ 导入ABC文件失败: {str(e)}")
                return False
            
            # 查找新创建的ABC节点
            abc_nodes_after = set(cmds.ls(type="AlembicNode"))
            new_abc_nodes = abc_nodes_after - abc_nodes_before
            
            if not new_abc_nodes:
                print("❌ 没有找到新的ABC节点")
                return False
            
            abc_node = list(new_abc_nodes)[-1]
            
            # 设置时间范围
            self._update_time_range_from_abc(abc_node)
            
            # 查找新创建的transform
            transforms_after = set(cmds.ls(type='transform'))
            new_transforms = transforms_after - transforms_before
            
            # 隐藏新导入的顶层transform（避免重复显示模型）
            print(f"隐藏导入的动画ABC几何体...")
            for transform in new_transforms:
                # 只隐藏顶层transform（没有父节点的）
                parent = cmds.listRelatives(transform, parent=True)
                if not parent:
                    try:
                        cmds.setAttr(transform + '.visibility', 0)
                        print(f"  已隐藏: {transform}")
                    except Exception as e:
                        print(f"  无法隐藏 {transform}: {str(e)}")
            
            # 暂存ABC信息，延迟到step4后再连接
            if not hasattr(self, 'pending_animation_connections'):
                self.pending_animation_connections = []
            
            self.pending_animation_connections.append({
                'transforms': new_transforms,
                'abc_node': abc_node,
                'file': animation_file
            })
            
            print(f"✅ 动画ABC已导入并隐藏，连接将在解算文件处理后进行")
            
            # 在导入ABC后自动调用动态blendShape匹配
            self._auto_match_simulation_blendshapes(new_transforms, actual_namespace)
            
            print(f"✅ 动画ABC处理完成: {os.path.basename(animation_file)}")
            return True
            
        except Exception as e:
            print(f"❌ 导入动画ABC失败: {str(e)}")
            return False
    
    def _update_time_range_from_abc(self, abc_node):
        """从ABC节点更新时间范围"""
        try:
            start_frame = cmds.getAttr(f"{abc_node}.startFrame")
            end_frame = cmds.getAttr(f"{abc_node}.endFrame")
            
            self.start_frame = int(start_frame)
            self.end_frame = int(end_frame)
            
            cmds.playbackOptions(min=start_frame, max=end_frame)
            cmds.currentTime(start_frame)
            
            print(f"时间范围已更新: {self.start_frame} - {self.end_frame}")
            
        except Exception as e:
            print(f"更新时间范围失败: {str(e)}")
    
    def _connect_abc_to_lookdev(self, new_transforms, abc_node):
        """连接ABC到lookdev几何体"""
        try:
            # 查找ABC几何体
            abc_meshes = self._find_abc_meshes(new_transforms, abc_node)
            print(f"找到 {len(abc_meshes)} 个ABC几何体")
            
            # 查找lookdev几何体
            lookdev_meshes = self._find_lookdev_meshes()
            print(f"找到 {len(lookdev_meshes)} 个lookdev几何体")
            
            if not abc_meshes or not lookdev_meshes:
                print("❌ 未找到足够的几何体进行连接")
                return
            
            # 执行连接
            self._connect_meshes(abc_meshes, lookdev_meshes)
            
            # 处理特殊组的blendShape连接
            self._handle_special_groups_blendshape()
            
            # 隐藏ABC几何体
            self._hide_abc_meshes(abc_meshes)
            
        except Exception as e:
            print(f"连接ABC到lookdev失败: {str(e)}")
    
    def _find_abc_meshes(self, new_transforms, abc_node):
        """查找ABC几何体"""
        abc_meshes = {}
        
        print(f"   查找ABC几何体，新transform数量: {len(new_transforms)}")
        print(f"   ABC节点: {abc_node}")
        
        # 通过ABC节点连接查找
        abc_connections = cmds.listConnections(abc_node, type='transform') or []
        print(f"   通过ABC节点找到的连接: {len(abc_connections)}")
        
        for transform in abc_connections:
            if cmds.objExists(transform):
                shapes = cmds.listRelatives(transform, shapes=True, type='mesh') or []
                if shapes:
                    shape = shapes[0]
                    input_connections = cmds.listConnections(shape + '.inMesh', source=True, plugs=True)
                    if input_connections:
                        base_name = transform.split('|')[-1].lower()
                        abc_meshes[base_name] = {
                            'transform': transform,
                            'shape': shape,
                            'abc_connection': input_connections[0]
                        }
                        print(f"   ✅ 通过ABC连接找到: {base_name} -> {transform}")
        
        # 如果通过连接找不到，遍历所有新导入的transform
        if not abc_meshes:
            print("   通过ABC节点连接未找到几何体，尝试遍历新transform...")
            
            for transform in new_transforms:
                if not cmds.objExists(transform):
                    continue
                
                print(f"   检查transform: {transform}")
                
                # 获取实际使用的命名空间
                actual_namespace = getattr(self, 'actual_animation_namespace', self.animation_namespace)
                
                # 检查是否在动画命名空间中
                if f'{actual_namespace}:' in transform or f'{self.animation_namespace}:' in transform:
                    shapes = cmds.listRelatives(transform, shapes=True, type='mesh') or []
                    print(f"     找到mesh数量: {len(shapes)}")
                    
                    if shapes:
                        for shape in shapes:
                            print(f"     检查shape: {shape}")
                            
                            # 检查shape的input连接
                            input_connections = cmds.listConnections(shape + '.inMesh', source=True, plugs=True)
                            if input_connections:
                                print(f"     找到input连接: {input_connections}")
                                source_node = input_connections[0].split('.')[0]
                                node_type = cmds.nodeType(source_node)
                                print(f"     源节点类型: {node_type}")
                                
                                # 检查是否来自ABC相关节点
                                if node_type in ['AlembicNode', 'mesh', 'polyUnite', 'groupParts']:
                                    # 去掉命名空间获取基础名称
                                    base_name = transform.split('|')[-1]
                                    if ':' in base_name:
                                        base_name = base_name.split(':')[-1]
                                    base_name = base_name.lower()
                                    
                                    abc_meshes[base_name] = {
                                        'transform': transform,
                                        'shape': shape,
                                        'abc_connection': input_connections[0]
                                    }
                                    print(f"   ✅ 通过transform遍历找到: {base_name} -> {transform}")
                            else:
                                print(f"     shape {shape} 没有input连接")
                else:
                    print(f"     跳过非动画命名空间的transform: {transform}")
        
        # 如果还是找不到，直接查找动画命名空间下的所有mesh
        if not abc_meshes:
            print("   尝试直接查找动画命名空间下的所有mesh...")
            actual_namespace = getattr(self, 'actual_animation_namespace', self.animation_namespace)
            
            # 尝试两种命名空间模式
            namespace_transforms = cmds.ls(f'{actual_namespace}:*', type='transform') or []
            if not namespace_transforms:
                namespace_transforms = cmds.ls(f'{self.animation_namespace}*:*', type='transform') or []
            
            print(f"   动画命名空间下的transform数量: {len(namespace_transforms)}")
            
            for transform in namespace_transforms:
                if cmds.objExists(transform):
                    shapes = cmds.listRelatives(transform, shapes=True, type='mesh') or []
                    if shapes:
                        shape = shapes[0]
                        # 获取基础名称
                        base_name = transform.split('|')[-1]
                        if ':' in base_name:
                            base_name = base_name.split(':')[-1]
                        base_name = base_name.lower()
                        
                        abc_meshes[base_name] = {
                            'transform': transform,
                            'shape': shape,
                            'abc_connection': None  # 可能没有直接连接
                        }
                        print(f"   ✅ 直接从命名空间找到: {base_name} -> {transform}")
        
        print(f"   最终找到 {len(abc_meshes)} 个ABC几何体")
        return abc_meshes
    
    def _find_lookdev_meshes(self):
        """查找lookdev几何体"""
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
    
    def _connect_meshes(self, abc_meshes, lookdev_meshes):
        """连接ABC和lookdev几何体"""
        connected = 0
        
        for abc_name, abc_data in abc_meshes.items():
            # 寻找最佳匹配
            best_match = self._find_best_mesh_match(abc_name, lookdev_meshes.keys())
            
            if best_match:
                lookdev_data = lookdev_meshes[best_match]
                
                try:
                    abc_output = abc_data['abc_connection']
                    abc_shape = abc_data['shape']
                    lookdev_shape = lookdev_data['shape']
                    
                    # 如果abc_connection为None，尝试直接从shape获取输出
                    if abc_output is None:
                        abc_output = f"{abc_shape}.outMesh"
                        print(f"  使用shape输出: {abc_output}")
                    
                    # 检查lookdev几何体是否有blendShape节点
                    blendshape_node = self._find_blendshape_for_mesh(lookdev_shape)
                    
                    if blendshape_node:
                        # 如果有blendShape，使用安全的blendShape目标添加方法
                        print(f"  发现blendShape节点: {blendshape_node}")
                        
                        # 使用安全的方法添加blendShape目标
                        success = self._add_abc_as_blendshape_target(blendshape_node, abc_shape, lookdev_shape, abc_name)
                        if success:
                            print(f"  连接到blendShape成功: {abc_name} -> {best_match}")
                        else:
                            print(f"  ⚠️  添加blendShape目标失败，跳过连接")
                            continue
                    else:
                        # 如果没有blendShape，直接连接到inMesh
                        existing_connections = cmds.listConnections(lookdev_shape + '.inMesh', source=True, plugs=True)
                        if existing_connections:
                            cmds.disconnectAttr(existing_connections[0], lookdev_shape + '.inMesh')
                        
                        cmds.connectAttr(abc_output, lookdev_shape + '.inMesh', force=True)
                        print(f"  直接连接成功: {abc_name} -> {best_match}")
                    
                    connected += 1
                    
                except Exception as e:
                    print(f"  连接失败 {abc_name} -> {best_match}: {e}")
            else:
                print(f"  未找到匹配: {abc_name}")
        
        print(f"总共连接了 {connected} 个几何体")
    
    def _find_best_mesh_match(self, abc_name, lookdev_names):
        """查找最佳几何体匹配，使用多层匹配策略"""
        abc_clean = self._clean_mesh_name(abc_name)
        abc_keywords = self._extract_mesh_keywords(abc_clean)
        
        candidates = []
        
        for lookdev_name in lookdev_names:
            lookdev_clean = self._clean_mesh_name(lookdev_name)
            lookdev_keywords = self._extract_mesh_keywords(lookdev_clean)
            
            score = 0
            match_type = []
            
            # 1. 完全匹配（最高优先级）
            if abc_clean == lookdev_clean:
                score += 100
                match_type.append("exact")
            
            # 2. 包含匹配
            elif abc_clean in lookdev_clean:
                score += 80
                match_type.append("abc_in_lookdev")
            elif lookdev_clean in abc_clean:
                score += 70
                match_type.append("lookdev_in_abc")
            
            # 3. 关键词匹配
            common_keywords = abc_keywords & lookdev_keywords
            if common_keywords:
                score += len(common_keywords) * 10
                match_type.append(f"keywords({len(common_keywords)})")
            
            # 4. 相似度匹配（Levenshtein距离）
            similarity = self._calculate_string_similarity(abc_clean, lookdev_clean)
            if similarity > 0.6:  # 60%以上相似度
                score += int(similarity * 20)
                match_type.append(f"similarity({similarity:.2f})")
            
            # 5. 特殊名称处理（如eye相关的特殊匹配）
            if self._is_special_mesh_pair(abc_clean, lookdev_clean):
                score += 50
                match_type.append("special")
            
            if score > 0:
                candidates.append({
                    'name': lookdev_name,
                    'score': score,
                    'match_types': match_type
                })
        
        if candidates:
            # 按分数排序，返回最高分
            candidates.sort(key=lambda x: x['score'], reverse=True)
            best = candidates[0]
            
            print(f"    匹配结果: {abc_name} -> {best['name']} (分数:{best['score']}, 类型:{','.join(best['match_types'])})")
            
            # 如果最高分低于阈值，返回None
            if best['score'] < 20:
                print(f"    ⚠️  匹配分数过低，跳过匹配")
                return None
                
            return best['name']
        
        return None
    
    def _calculate_string_similarity(self, str1, str2):
        """计算两个字符串的相似度（简化版Levenshtein距离）"""
        if not str1 or not str2:
            return 0.0
        
        # 转换为小写进行比较
        s1, s2 = str1.lower(), str2.lower()
        
        if s1 == s2:
            return 1.0
        
        # 计算相同字符的比例
        common_chars = 0
        for char in set(s1):
            common_chars += min(s1.count(char), s2.count(char))
        
        max_len = max(len(s1), len(s2))
        if max_len == 0:
            return 0.0
        
        return common_chars / max_len
    
    def _is_special_mesh_pair(self, abc_name, lookdev_name):
        """检查是否是特殊的mesh配对（如eyeball相关）"""
        special_pairs = [
            ('eye', 'vitreous'),
            ('eyeball', 'vitreous'),
            ('hair', 'fur'),
            ('cloth', 'skirt'),
            ('lowteeth', 'teeth'),
            ('upteeth', 'teeth')
        ]
        
        for pair in special_pairs:
            if (pair[0] in abc_name and pair[1] in lookdev_name) or \
               (pair[1] in abc_name and pair[0] in lookdev_name):
                return True
        
        return False
    
    def _clean_mesh_name(self, name):
        """清理mesh名称"""
        import re
        name = name.lower()
        name = name.replace('dwl_', '').replace('chr_', '').replace('_grp', '')
        name = name.replace('dwl', '').replace('chr', '').replace('grp', '')
        name = re.sub(r'_?\d+$', '', name)
        name = re.sub(r'\d+$', '', name)
        return name
    
    def _extract_mesh_keywords(self, name):
        """提取mesh关键词"""
        keywords = set()
        
        body_parts = ['body', 'head', 'eye', 'eyel', 'eyer', 'eyebrow', 'eyelash',
                      'hair', 'face', 'hand', 'leg', 'arm', 'foot', 'teeth', 'lowteeth',
                      'upteeth', 'tongue', 'tail', 'fur']
        
        clothing = ['skirt', 'gauntlets', 'necklace', 'rope', 'belt', 'beltrope']
        
        others = ['vitreous', 'ball', 'grow', 'blend']
        
        all_keywords = body_parts + clothing + others
        
        for keyword in all_keywords:
            if keyword in name:
                keywords.add(keyword)
        
        if 'vitreous' in name or ('ball' in name and 'eye' in name):
            keywords.add('eye')
        
        return keywords
    
    def _find_blendshape_for_mesh(self, mesh_shape):
        """查找mesh是否有blendShape节点"""
        try:
            # 检查inMesh的连接
            connections = cmds.listConnections(mesh_shape + '.inMesh', source=True, type='blendShape')
            if connections:
                return connections[0]
            return None
        except:
            return None
    
    def _find_available_blendshape_input(self, blendshape_node):
        """查找blendShape节点的可用输入槽"""
        try:
            # 获取当前使用的权重索引
            weight_attrs = cmds.listAttr(blendshape_node + '.weight', multi=True) or []
            used_indices = []
            
            for attr in weight_attrs:
                # 提取索引号 weight[0] -> 0
                if '[' in attr and ']' in attr:
                    index_str = attr.split('[')[1].split(']')[0]
                    try:
                        used_indices.append(int(index_str))
                    except:
                        continue
            
            # 找到第一个未使用的索引（从1开始，0通常保留给base）
            for i in range(1, 100):  # 限制在100以内
                if i not in used_indices:
                    return i
            
            return None
        except Exception as e:
            print(f"查找blendShape输入槽失败: {str(e)}")
            return None
    
    def _add_abc_as_blendshape_target(self, blendshape_node, abc_shape, lookdev_shape, abc_name):
        """安全地将ABC添加为blendShape目标，避免循环依赖"""
        try:
            # 检查是否已经有来自这个ABC的连接
            existing_inputs = cmds.listConnections(f"{blendshape_node}.inputTarget", source=True, plugs=True) or []
            for input_plug in existing_inputs:
                if abc_shape in input_plug:
                    print(f"    ABC {abc_name} 已经连接到此blendShape，跳过")
                    return True
            
            # 找到可用的输入槽
            input_index = self._find_available_blendshape_input(blendshape_node)
            if input_index is None:
                print(f"    blendShape节点没有可用输入槽")
                return False
            
            # 创建临时复制以避免循环依赖
            temp_duplicate = cmds.duplicate(abc_shape, name=f"temp_{abc_name}")[0]
            
            try:
                # 将临时复制添加为blendShape目标
                cmds.blendShape(blendshape_node, edit=True, target=(lookdev_shape, input_index, temp_duplicate, 1.0))
                
                # 设置权重为1
                cmds.setAttr(f"{blendshape_node}.weight[{input_index}]", 1.0)
                
                # 现在安全地连接ABC到blendShape目标
                target_attr = f"{blendshape_node}.inputTarget[0].inputTargetGroup[{input_index}].inputTargetItem[6000].inputGeomTarget"
                abc_output = f"{abc_shape}.outMesh"
                
                # 断开临时连接
                temp_connections = cmds.listConnections(target_attr, source=True, plugs=True)
                if temp_connections:
                    cmds.disconnectAttr(temp_connections[0], target_attr)
                
                # 连接ABC输出
                cmds.connectAttr(abc_output, target_attr, force=True)
                
                print(f"    成功添加ABC目标到blendShape (槽{input_index})")
                return True
                
            finally:
                # 清理临时对象
                if cmds.objExists(temp_duplicate):
                    cmds.delete(temp_duplicate)
                    
        except Exception as e:
            print(f"    添加ABC blendShape目标失败: {str(e)}")
            return False
    
    def _identify_cfx_and_ani_groups(self, group1, group2):
        """智能识别哪个是CFX组，哪个是ANI组"""
        try:
            group1_name = group1.split('|')[-1].lower()
            group2_name = group2.split('|')[-1].lower()
            
            # 通过命名空间识别
            if 'cfx' in group1_name or self.cloth_namespace in group1:
                return group1, group2
            elif 'cfx' in group2_name or self.cloth_namespace in group2:
                return group2, group1
            
            # 通过子mesh数量识别（通常CFX组mesh更少）
            try:
                group1_meshes = cmds.listRelatives(group1, allDescendents=True, type='mesh') or []
                group2_meshes = cmds.listRelatives(group2, allDescendents=True, type='mesh') or []
                
                if len(group1_meshes) < len(group2_meshes):
                    return group1, group2
                else:
                    return group2, group1
            except:
                pass
            
            # 默认返回原顺序
            return group1, group2
            
        except Exception as e:
            print(f"    识别CFX和ANI组失败: {str(e)}")
            return None, None
    
    def _add_mesh_to_existing_blendshape(self, blendshape_node, source_mesh, target_mesh):
        """将mesh添加到现有的blendShape节点"""
        try:
            # 找到可用的输入槽
            input_index = self._find_available_blendshape_input(blendshape_node)
            if input_index is None:
                print(f"      blendShape节点没有可用输入槽")
                return False
            
            # 添加新的blendShape target
            cmds.blendShape(blendshape_node, edit=True, target=(target_mesh, input_index, source_mesh, 1.0))
            # 设置权重为1
            cmds.setAttr(f"{blendshape_node}.weight[{input_index}]", 1.0)
            
            return True
            
        except Exception as e:
            print(f"      添加到现有blendShape失败: {str(e)}")
            return False
    
    def _create_safe_blendshape(self, source_mesh, target_mesh):
        """安全创建blendShape，避免循环依赖和重复连接"""
        try:
            # 获取target mesh的shape节点
            if cmds.nodeType(target_mesh) == 'transform':
                target_shapes = cmds.listRelatives(target_mesh, shapes=True, type='mesh')
                if not target_shapes:
                    print(f"    目标mesh没有shape节点: {target_mesh}")
                    return None
                target_shape = target_shapes[0]
            else:
                target_shape = target_mesh
            
            # 获取source mesh的shape节点
            if cmds.nodeType(source_mesh) == 'transform':
                source_shapes = cmds.listRelatives(source_mesh, shapes=True, type='mesh')
                if not source_shapes:
                    print(f"    源mesh没有shape节点: {source_mesh}")
                    return None
                source_shape = source_shapes[0]
            else:
                source_shape = source_mesh
            
            # 检查是否会创建循环依赖
            if self._would_create_cycle(source_shape, target_shape):
                print(f"    ⚠️  检测到潜在循环依赖，跳过创建blendShape")
                return None
            
            # 检查是否已有blendShape
            existing_blendshape = self._find_blendshape_for_mesh(target_shape)
            
            if existing_blendshape:
                print(f"    发现现有blendShape: {existing_blendshape}")
                # 检查source是否已经是此blendShape的目标
                if self._is_already_blendshape_target(existing_blendshape, source_shape):
                    print(f"    源mesh已经是此blendShape的目标，跳过")
                    return existing_blendshape
                
                # 添加新的target到现有blendShape
                return self._add_mesh_to_existing_blendshape(existing_blendshape, source_mesh, target_mesh)
            else:
                # 如果没有blendShape，创建新的（使用duplicated source避免循环）
                try:
                    # 创建源mesh的副本以避免循环依赖
                    temp_source = cmds.duplicate(source_mesh, name=f"temp_blend_source")[0]
                    
                    # 创建blendShape
                    blend_node = cmds.blendShape(temp_source, target_mesh)[0]
                    cmds.setAttr(f"{blend_node}.weight[0]", 1.0)
                    
                    # 现在安全地连接原始source到blendShape
                    target_attr = f"{blend_node}.inputTarget[0].inputTargetGroup[0].inputTargetItem[6000].inputGeomTarget"
                    source_output = f"{source_shape}.outMesh"
                    
                    # 断开临时连接
                    temp_connections = cmds.listConnections(target_attr, source=True, plugs=True)
                    if temp_connections:
                        cmds.disconnectAttr(temp_connections[0], target_attr)
                    
                    # 连接原始source
                    cmds.connectAttr(source_output, target_attr, force=True)
                    
                    # 删除临时对象
                    cmds.delete(temp_source)
                    
                    print(f"    创建新blendShape: {blend_node}")
                    return blend_node
                    
                except Exception as e:
                    print(f"    ❌ 创建新blendShape失败: {str(e)}")
                    return None
                    
        except Exception as e:
            print(f"    ❌ 安全创建blendShape失败: {str(e)}")
            return None
    
    def _would_create_cycle(self, source_shape, target_shape):
        """检查连接是否会创建循环依赖"""
        try:
            # 检查target是否已经依赖于source
            if self._is_mesh_dependent_on(target_shape, source_shape):
                return True
            
            # 检查source是否已经依赖于target
            if self._is_mesh_dependent_on(source_shape, target_shape):
                return True
            
            return False
        except:
            return False
    
    def _is_mesh_dependent_on(self, mesh1, mesh2):
        """检查mesh1是否依赖于mesh2"""
        try:
            # 获取mesh1的所有上游连接
            connections = cmds.listHistory(mesh1, pruneDagObjects=True) or []
            return mesh2 in connections
        except:
            return False
    
    def _is_already_blendshape_target(self, blendshape_node, source_shape):
        """检查source是否已经是blendShape的目标"""
        try:
            # 获取blendShape的所有输入连接
            input_connections = cmds.listConnections(f"{blendshape_node}.inputTarget", source=True) or []
            return source_shape in input_connections
        except:
            return False
    
    def _hide_abc_meshes(self, abc_meshes):
        """隐藏ABC几何体"""
        for name, data in abc_meshes.items():
            transform = data['transform']
            try:
                if cmds.objExists(transform):
                    cmds.setAttr(transform + '.visibility', 0)
            except Exception as e:
                print(f"隐藏失败 {transform}: {e}")
    
    def create_dynamic_blendshapes(self, source_objects, target_objects, conflict_check=True):
        """
        动态创建blendShape连接
        
        Args:
            source_objects (list): 源对象列表（组或mesh）
            target_objects (list): 目标对象列表（组或mesh）
            conflict_check (bool): 是否检查与动画blendShape的冲突
            
        Returns:
            dict: 创建结果统计
        """
        print("\n=== 动态blendShape匹配系统 ===")
        
        # 获取所有源mesh
        source_meshes = self._extract_meshes_from_objects(source_objects, "源")
        
        # 获取所有目标mesh
        target_meshes = self._extract_meshes_from_objects(target_objects, "目标")
        
        if not source_meshes or not target_meshes:
            print("❌ 没有找到有效的mesh")
            return {'success': 0, 'failed': 0, 'skipped': 0}
        
        # 执行智能匹配
        return self._perform_smart_blendshape_matching(source_meshes, target_meshes, conflict_check)
    
    def _extract_meshes_from_objects(self, objects, label):
        """从对象列表中提取所有mesh信息"""
        mesh_info = {}
        
        print(f"分析{label}对象:")
        for obj in objects:
            if not cmds.objExists(obj):
                print(f"  ⚠️  对象不存在: {obj}")
                continue
            
            # 检查对象类型
            if cmds.nodeType(obj) == 'transform':
                # 检查是否有mesh子节点
                mesh_shapes = cmds.listRelatives(obj, shapes=True, type='mesh')
                if mesh_shapes:
                    # 单个mesh transform
                    mesh_shape = mesh_shapes[0]
                    face_count = cmds.polyEvaluate(mesh_shape, face=True)
                    clean_name = self._clean_mesh_name(obj.split('|')[-1])
                    
                    mesh_info[obj] = {
                        'shape': mesh_shape,
                        'face_count': face_count,
                        'clean_name': clean_name,
                        'original_name': obj.split('|')[-1]
                    }
                    print(f"  📦 Mesh: {obj.split('|')[-1]} - {face_count} 面 ({clean_name})")
                else:
                    # 组 - 获取所有子mesh
                    child_meshes = cmds.listRelatives(obj, allDescendents=True, type='mesh', fullPath=True) or []
                    print(f"  📁 组: {obj.split('|')[-1]} - 找到 {len(child_meshes)} 个子mesh")
                    
                    for mesh_shape in child_meshes:
                        # 获取mesh的transform
                        mesh_transform = cmds.listRelatives(mesh_shape, parent=True, fullPath=True)[0]
                        try:
                            face_count = cmds.polyEvaluate(mesh_shape, face=True)
                            clean_name = self._clean_mesh_name(mesh_transform.split('|')[-1])
                            
                            mesh_info[mesh_transform] = {
                                'shape': mesh_shape,
                                'face_count': face_count,
                                'clean_name': clean_name,
                                'original_name': mesh_transform.split('|')[-1]
                            }
                            print(f"    - {mesh_transform.split('|')[-1]} - {face_count} 面 ({clean_name})")
                        except:
                            print(f"    ❌ 无法分析mesh: {mesh_shape}")
                            continue
            elif cmds.nodeType(obj) == 'mesh':
                # 直接是mesh shape
                mesh_transform = cmds.listRelatives(obj, parent=True, fullPath=True)[0]
                try:
                    face_count = cmds.polyEvaluate(obj, face=True)
                    clean_name = self._clean_mesh_name(mesh_transform.split('|')[-1])
                    
                    mesh_info[mesh_transform] = {
                        'shape': obj,
                        'face_count': face_count,
                        'clean_name': clean_name,
                        'original_name': mesh_transform.split('|')[-1]
                    }
                    print(f"  📦 Mesh Shape: {mesh_transform.split('|')[-1]} - {face_count} 面 ({clean_name})")
                except:
                    print(f"  ❌ 无法分析mesh shape: {obj}")
                    continue
        
        return mesh_info
    
    def _perform_smart_blendshape_matching(self, source_meshes, target_meshes, conflict_check):
        """执行智能blendShape匹配"""
        results = {'success': 0, 'failed': 0, 'skipped': 0}
        matched_pairs = []
        
        print(f"\n开始智能匹配 ({len(source_meshes)} 源 -> {len(target_meshes)} 目标)")
        
        # 为每个源mesh找到最佳目标mesh
        for source_transform, source_info in source_meshes.items():
            best_match = None
            best_score = 0
            
            for target_transform, target_info in target_meshes.items():
                # 如果目标已经被匹配过，跳过
                if any(pair[1] == target_transform for pair in matched_pairs):
                    continue
                
                # 计算匹配分数
                score = self._calculate_mesh_match_score(source_info, target_info)
                
                if score > best_score:
                    best_score = score
                    best_match = target_transform
            
            if best_match and best_score >= 10:  # 至少面数要匹配(10分)
                matched_pairs.append((source_transform, best_match))
                target_info = target_meshes[best_match]
                
                print(f"✅ 匹配: {source_info['original_name']} -> {target_info['original_name']} (分数:{best_score})")
                
                # 检查冲突
                if conflict_check and self._has_animation_blendshape_conflict(target_info['shape']):
                    print(f"  ⚠️  跳过 - 目标mesh已有动画blendShape连接")
                    results['skipped'] += 1
                    continue
                
                # 创建blendShape
                if self._create_single_blendshape_connection(source_info, target_info):
                    results['success'] += 1
                else:
                    results['failed'] += 1
            else:
                print(f"❌ 未匹配: {source_info['original_name']} (最高分数:{best_score})")
        
        # 报告未匹配的mesh
        unmatched_sources = [info['original_name'] for transform, info in source_meshes.items() 
                           if not any(pair[0] == transform for pair in matched_pairs)]
        unmatched_targets = [info['original_name'] for transform, info in target_meshes.items() 
                           if not any(pair[1] == transform for pair in matched_pairs)]
        
        if unmatched_sources:
            print(f"\n⚠️  未匹配的源mesh: {', '.join(unmatched_sources)}")
        if unmatched_targets:
            print(f"⚠️  未匹配的目标mesh: {', '.join(unmatched_targets)}")
        
        print(f"\n📊 匹配结果: 成功{results['success']}, 失败{results['failed']}, 跳过{results['skipped']}")
        return results
    
    def _calculate_mesh_match_score(self, source_info, target_info):
        """计算mesh匹配分数"""
        score = 0
        
        # 1. 面数匹配 (必须条件)
        if source_info['face_count'] == target_info['face_count']:
            score += 10
        else:
            return 0  # 面数不匹配直接返回0
        
        # 2. 名称匹配
        source_clean = source_info['clean_name']
        target_clean = target_info['clean_name']
        
        if source_clean == target_clean:
            score += 20  # 完全匹配
        elif source_clean in target_clean or target_clean in source_clean:
            score += 15  # 包含匹配
        
        # 3. 相似度匹配
        similarity = self._calculate_string_similarity(source_clean, target_clean)
        if similarity > 0.6:
            score += int(similarity * 10)
        
        # 4. 特殊配对
        if self._is_special_mesh_pair(source_clean, target_clean):
            score += 5
        
        return score
    
    def _has_animation_blendshape_conflict(self, target_shape):
        """检查目标mesh是否已有动画blendShape连接"""
        try:
            # 检查inMesh的连接
            connections = cmds.listConnections(target_shape + '.inMesh', source=True, type='blendShape')
            if connections:
                # 检查blendShape是否来自动画命名空间
                for blend_node in connections:
                    if self.animation_namespace in blend_node:
                        return True
            return False
        except:
            return False
    
    def _create_single_blendshape_connection(self, source_info, target_info):
        """创建单个blendShape连接"""
        try:
            source_shape = source_info['shape']
            target_shape = target_info['shape']
            
            # 检查是否会创建循环依赖
            if self._would_create_cycle(source_shape, target_shape):
                print(f"    ⚠️  检测到循环依赖，跳过")
                return False
            
            # 检查目标是否已有blendShape
            existing_blendshape = self._find_blendshape_for_mesh(target_shape)
            
            if existing_blendshape:
                # 添加到现有blendShape
                success = self._add_mesh_to_existing_blendshape(existing_blendshape, source_shape, target_shape)
                if success:
                    print(f"    ✅ 添加到现有blendShape: {existing_blendshape}")
                return success
            else:
                # 创建新blendShape
                blend_node = self._create_safe_blendshape(source_shape, target_shape)
                if blend_node:
                    print(f"    ✅ 创建新blendShape: {blend_node}")
                    return True
                return False
                
        except Exception as e:
            print(f"    ❌ 创建blendShape失败: {str(e)}")
            return False
    
    def _auto_match_simulation_blendshapes(self, abc_transforms, abc_namespace):
        """导入解算ABC后自动匹配blendShape"""
        print("\n🔄 自动匹配解算blendShape...")
        
        # 去掉命名空间的解算mesh名称，用于匹配lookdev中的对应mesh
        abc_objects_clean = []
        for transform in abc_transforms:
            # 去掉命名空间前缀
            clean_name = transform.split(':')[-1] if ':' in transform else transform
            # 查找在lookdev命名空间中的对应对象
            lookdev_equivalent = f"{self.lookdev_namespace}:{clean_name}"
            
            if cmds.objExists(lookdev_equivalent):
                abc_objects_clean.append(transform)
                print(f"  找到匹配对象: {clean_name}")
            else:
                print(f"  ⚠️  在lookdev中未找到对应对象: {clean_name}")
        
        if abc_objects_clean:
            # 获取lookdev中的对应对象
            lookdev_objects = []
            for abc_transform in abc_objects_clean:
                clean_name = abc_transform.split(':')[-1] if ':' in abc_transform else abc_transform
                lookdev_equivalent = f"{self.lookdev_namespace}:{clean_name}"
                lookdev_objects.append(lookdev_equivalent)
            
            print(f"找到 {len(abc_objects_clean)} 个解算对象需要匹配")
            
            # 调用动态blendShape匹配系统
            # 源对象：解算ABC的mesh，目标对象：lookdev的mesh
            # 启用冲突检查以避免与动画blendShape冲突
            results = self.create_dynamic_blendshapes(
                source_objects=abc_objects_clean,
                target_objects=lookdev_objects,
                conflict_check=True
            )
            
            print(f"🎯 解算blendShape自动匹配完成: {results}")
        else:
            print("⚠️  没有找到需要匹配的解算对象")
    
    def _connect_pending_animation_abc(self):
        """连接所有暂存的动画ABC"""
        if not hasattr(self, 'pending_animation_connections'):
            print("没有暂存的动画ABC连接")
            return
        
        print(f"\n=== 连接暂存的动画ABC ({len(self.pending_animation_connections)}个) ===")
        
        for i, connection_data in enumerate(self.pending_animation_connections, 1):
            print(f"\n处理第{i}个动画ABC...")
            try:
                new_transforms = connection_data['transforms']
                abc_node = connection_data['abc_node']
                file_path = connection_data['file']
                
                print(f"文件: {os.path.basename(file_path)}")
                
                # 连接ABC到lookdev
                self._connect_abc_to_lookdev(new_transforms, abc_node)
                
            except Exception as e:
                print(f"❌ 连接第{i}个动画ABC失败: {str(e)}")
        
        # 清空暂存列表
        self.pending_animation_connections = []
        print("✅ 所有动画ABC连接完成")
    
    def step3_import_camera_abc(self):
        """步骤3: 导入相机ABC"""
        print("\n=== 步骤3: 导入动画相机ABC ===")
        
        if not self.current_camera_file:
            print("❌ 没有可用的相机文件")
            return False
        
        if not os.path.exists(self.current_camera_file):
            print(f"❌ 相机ABC文件不存在: {self.current_camera_file}")
            return False
        
        try:
            # 使用Maya file -import命令导入相机ABC文件（支持namespace）
            try:
                # 获取实际使用的动画命名空间（可能有数字后缀）
                actual_namespace = getattr(self, 'actual_animation_namespace', self.animation_namespace)
                
                # 确保命名空间存在
                if not cmds.namespace(exists=actual_namespace):
                    if not cmds.namespace(exists=self.animation_namespace):
                        cmds.namespace(add=self.animation_namespace)
                    actual_namespace = self.animation_namespace
                
                # 记录导入前的命名空间
                namespaces_before = set(cmds.namespaceInfo(listOnlyNamespaces=True))
                
                # 使用file -import命令导入相机ABC文件
                cmds.file(
                    self.current_camera_file,
                    i=True,  # import
                    type="Alembic",
                    ignoreVersion=True,
                    ra=True,  # reference assembly 
                    mergeNamespacesOnClash=False,
                    namespace=actual_namespace,
                    pr=True,  # preserve references
                    importTimeRange="combine"
                )
                
                # 检查实际使用的命名空间
                namespaces_after = set(cmds.namespaceInfo(listOnlyNamespaces=True))
                new_namespaces = namespaces_after - namespaces_before
                
                # 检查是否有新的命名空间
                for ns in new_namespaces:
                    if ns.startswith(self.animation_namespace):
                        if ns != actual_namespace:
                            print(f"⚠️  相机导入使用了新命名空间: {ns}")
                        break
                
                print(f"✅ 已导入相机ABC到命名空间: {actual_namespace}")
                
            except Exception as e:
                print(f"❌ 导入相机ABC文件失败: {str(e)}")
                return False
            
            # 检查导入的相机
            cameras = cmds.ls(type="camera")
            animation_cameras = [cam for cam in cameras if
                               "persp" not in cam and "top" not in cam and 
                               "front" not in cam and "side" not in cam]
            
            if animation_cameras:
                print(f"找到{len(animation_cameras)}个动画相机")
                
                # 设置活动相机
                cam_transform = cmds.listRelatives(animation_cameras[0], parent=True, type="transform")
                if cam_transform:
                    panel = cmds.getPanel(withFocus=True)
                    if panel and cmds.modelPanel(panel, query=True, exists=True):
                        cmds.modelEditor(panel, edit=True, camera=cam_transform[0])
                        print(f"已设置活动相机: {cam_transform[0]}")
            
            # 从相机获取时间范围
            self._get_time_range_from_imported_camera()
            
            self.assembly_status['camera_imported'] = True
            return True
            
        except Exception as e:
            print(f"❌ 导入相机ABC失败: {str(e)}")
            return False
    
    def _get_time_range_from_imported_camera(self):
        """从已导入的相机获取时间范围"""
        try:
            abc_nodes = cmds.ls(type="AlembicNode")
            if abc_nodes:
                abc_node = abc_nodes[-1]
                start_frame = cmds.getAttr(f"{abc_node}.startFrame")
                end_frame = cmds.getAttr(f"{abc_node}.endFrame")
                
                self.start_frame = int(start_frame)
                self.end_frame = int(end_frame)
                
                cmds.playbackOptions(min=start_frame, max=end_frame)
                cmds.currentTime(start_frame)
                
                print(f"从相机更新时间范围: {self.start_frame} - {self.end_frame}")
                
        except Exception as e:
            print(f"从相机获取时间范围失败: {str(e)}")
    
    def step4_setup_hair_cache(self):
        """步骤4: 设置毛发缓存和解算文件"""
        print("\n=== 步骤4: 设置毛发缓存和解算文件 ===")
        
        try:
            # 先处理毛发解算文件（fur文件）
            self._import_and_connect_fur_cache()
            
            # 处理布料解算文件（cloth文件）
            self._import_and_connect_cloth_cache()
            
            # 确保XGen插件已加载
            if not cmds.pluginInfo('xgenToolkit', query=True, loaded=True):
                cmds.loadPlugin('xgenToolkit')
            
            # 获取毛发缓存模板
            hair_template = self.config_manager.get_hair_cache_template()
            
            # 获取所有XGen调色板
            palettes = xgenm.palettes()
            if not palettes:
                print("场景中没有找到XGen调色板")
                return True
            
            print(f"找到 {len(palettes)} 个XGen调色板")
            
            total_descriptions = 0
            updated_descriptions = 0
            
            for palette in palettes:
                descriptions = xgenm.descriptions(palette)
                
                for desc in descriptions:
                    total_descriptions += 1
                    desc_name = desc.split(':')[-1]
                    
                    # 替换模板中的${DESC}
                    cache_path = hair_template.replace('${DESC}', desc_name)
                    
                    # 检查缓存路径是否存在
                    if not os.path.exists(cache_path):
                        print(f"  描述 '{desc_name}' 缓存文件不存在: {cache_path}")
                        print(f"    跳过设置，保持原有配置")
                        continue
                    
                    try:
                        obj = 'SplinePrimitive'
                        xgenm.setAttr('useCache', 'true', palette, desc, obj)
                        xgenm.setAttr('liveMode', 'false', palette, desc, obj)
                        xgenm.setAttr('cacheFileName', cache_path, palette, desc, obj)
                        
                        print(f"  描述 '{desc_name}' 缓存路径已设置: {os.path.basename(cache_path)}")
                        updated_descriptions += 1
                        
                    except Exception as e:
                        print(f"  描述 '{desc_name}' 设置失败: {str(e)}")
            
            # 统计结果
            skipped_descriptions = total_descriptions - updated_descriptions
            
            print(f"\n=== 毛发缓存设置结果 ===")
            print(f"总描述数量: {total_descriptions}")
            print(f"成功设置: {updated_descriptions}")
            print(f"跳过设置: {skipped_descriptions}")
            
            # 处理完解算文件后，连接所有暂存的动画ABC
            self._connect_pending_animation_abc()
            
            if updated_descriptions > 0:
                self.assembly_status['hair_configured'] = True
                print("✅ 毛发缓存设置完成")
                return True
            elif skipped_descriptions > 0:
                print("⚠️  所有描述的缓存文件都不存在，跳过设置")
                return True  # 认为是成功的，只是没有可用的缓存文件
            else:
                print("❌ 毛发缓存设置失败")
                return False
                
        except Exception as e:
            print(f"❌ 设置毛发缓存失败: {str(e)}")
            return False
    
    def step5_fix_materials(self):
        """步骤5: 修复材质"""
        print("\n=== 步骤5: 检查修复材质 ===")
        
        try:
            self._fix_missing_textures()
            self._check_unmaterialized_objects()
            
            self.assembly_status['materials_fixed'] = True
            print("✅ 材质检查修复完成")
            return True
            
        except Exception as e:
            print(f"❌ 材质修复失败: {str(e)}")
            return False
    
    def _fix_missing_textures(self):
        """修复缺失的纹理"""
        file_nodes = cmds.ls(type="file")
        missing_count = 0
        fixed_count = 0
        
        for node in file_nodes:
            texture_path = cmds.getAttr(f"{node}.fileTextureName")
            if texture_path and not os.path.exists(texture_path):
                missing_count += 1
                print(f"缺失纹理: {os.path.basename(texture_path)}")
                
                # 尝试修复路径
                possible_paths = [
                    texture_path.replace("P:/LTT", "//192.168.50.250/public/LTT"),
                    os.path.join(cmds.workspace(query=True, rootDirectory=True), "sourceimages",
                               os.path.basename(texture_path))
                ]
                
                for new_path in possible_paths:
                    if os.path.exists(new_path):
                        cmds.setAttr(f"{node}.fileTextureName", new_path, type="string")
                        print(f"  ✅ 已修复: {os.path.basename(new_path)}")
                        fixed_count += 1
                        break
        
        if missing_count > 0:
            print(f"纹理状态: {missing_count}个缺失, {fixed_count}个已修复")
    
    def _check_unmaterialized_objects(self):
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
            print(f"警告: {len(no_material)}个对象没有材质")
            for obj in no_material[:5]:
                print(f"  - {obj}")
            if len(no_material) > 5:
                print(f"  ... 还有{len(no_material) - 5}个")
    
    def step6_setup_scene(self):
        """步骤6: 设置场景参数"""
        print("\n=== 步骤6: 设置场景参数 ===")
        
        try:
            # 设置时间范围
            cmds.playbackOptions(min=self.start_frame, max=self.end_frame)
            cmds.currentTime(self.start_frame)
            print(f"时间范围: {self.start_frame} - {self.end_frame}")
            
            # 设置单位
            cmds.currentUnit(linear="cm", time="film")
            
            # 设置视口显示
            panel = cmds.getPanel(withFocus=True)
            if panel and cmds.modelPanel(panel, query=True, exists=True):
                cmds.modelEditor(panel, edit=True, displayTextures=True, displayLights="all")
                print("视口显示已更新")
            
            # 优化选择
            if cmds.objExists(f"{self.lookdev_namespace}:Master"):
                cmds.select(f"{self.lookdev_namespace}:Master", replace=True)
                print("已选择lookdev根节点")
            
            self.assembly_status['scene_configured'] = True
            print("✅ 场景参数设置完成")
            return True
            
        except Exception as e:
            print(f"❌ 场景设置失败: {str(e)}")
            return False
    
    def execute_all_steps(self):
        """执行所有步骤"""
        print("\n" + "=" * 50)
        print("开始执行所有组装步骤")
        print("=" * 50)
        
        if not self.current_asset:
            print("❌ 请先设置当前工作的资产")
            return False
        
        steps = [
            (self.step1_import_lookdev, "导入Lookdev"),
            (self.step2_import_and_connect_animation_abc, "导入动画ABC"),
            (self.step3_import_camera_abc, "导入相机ABC"),
            (self.step4_setup_hair_cache, "设置毛发缓存"),
            (self.step5_fix_materials, "修复材质"),
            (self.step6_setup_scene, "设置场景")
        ]
        
        success_count = 0
        for step_func, step_name in steps:
            try:
                if step_func():
                    success_count += 1
                    print(f"✅ {step_name} 完成")
                else:
                    print(f"❌ {step_name} 失败")
                    break
            except Exception as e:
                print(f"❌ {step_name} 执行出错: {str(e)}")
                break
        
        if success_count == len(steps):
            print("\n🎉 所有步骤执行完成！")
            self._final_check()
            return True
        else:
            print(f"\n⚠️  执行中断，完成了{success_count}/{len(steps)}个步骤")
            return False
    
    def _final_check(self):
        """最终检查"""
        print("\n=== 最终检查 ===")
        
        # 统计信息
        abc_nodes = cmds.ls(type="AlembicNode")
        visible_meshes = []
        all_meshes = cmds.ls(type="mesh", noIntermediate=True)
        
        for mesh in all_meshes:
            transform = cmds.listRelatives(mesh, parent=True, type="transform")
            if transform and cmds.getAttr(f"{transform[0]}.visibility"):
                visible_meshes.append(transform[0])
        
        print(f"ABC节点数量: {len(abc_nodes)}")
        print(f"可见几何体数量: {len(visible_meshes)}")
        print(f"时间范围: {self.start_frame} - {self.end_frame}")
        
        # 检查命名空间中的几何体
        print("\n=== 命名空间几何体检查 ===")
        
        # 获取实际使用的命名空间
        actual_animation_namespace = getattr(self, 'actual_animation_namespace', self.animation_namespace)
        
        # 尝试多种模式查找动画mesh
        animation_meshes = cmds.ls(f'{actual_animation_namespace}:*', type='mesh') or []
        if not animation_meshes:
            # 尝试通配符模式
            animation_meshes = cmds.ls(f'{self.animation_namespace}*:*', type='mesh') or []
        
        lookdev_meshes = cmds.ls(f'{self.lookdev_namespace}:*', type='mesh') or []
        
        print(f"动画命名空间中的mesh数量: {len(animation_meshes)}")
        print(f"Lookdev命名空间中的mesh数量: {len(lookdev_meshes)}")
        
        if animation_meshes:
            print("动画mesh列表:")
            for i, mesh in enumerate(animation_meshes[:5]):  # 只显示前5个
                transform = cmds.listRelatives(mesh, parent=True, type="transform")
                if transform:
                    print(f"  {i+1}. {transform[0]} -> {mesh}")
            if len(animation_meshes) > 5:
                print(f"  ... 还有 {len(animation_meshes) - 5} 个")
        
        # 检查XGen状态
        try:
            palettes = xgenm.palettes()
            if palettes:
                print(f"\n=== XGen检查 ===")
                print(f"XGen调色板数量: {len(palettes)}")
                total_descriptions = 0
                for palette in palettes:
                    descriptions = xgenm.descriptions(palette)
                    total_descriptions += len(descriptions)
                    print(f"调色板 '{palette}': {len(descriptions)} 个描述")
                print(f"XGen描述总数: {total_descriptions}")
            else:
                print("\n=== XGen检查 ===")
                print("场景中没有找到XGen调色板")
        except Exception as e:
            print(f"\n=== XGen检查 ===")
            print(f"XGen检查失败: {str(e)}")
        
        print("\n✅ 组装完成！可以播放动画查看效果。")
    
    def check_xgen_status(self):
        """检查XGen状态"""
        print("\n=== XGen状态详细检查 ===")
        try:
            # 确保XGen插件已加载
            if not cmds.pluginInfo('xgenToolkit', query=True, loaded=True):
                print("XGen插件未加载，尝试加载...")
                cmds.loadPlugin('xgenToolkit')
                print("✅ XGen插件已加载")
            
            palettes = xgenm.palettes()
            if not palettes:
                print("❌ 场景中没有找到XGen调色板")
                return
            
            print(f"✅ 找到 {len(palettes)} 个XGen调色板")
            
            for palette in palettes:
                print(f"\n调色板: {palette}")
                descriptions = xgenm.descriptions(palette)
                print(f"  描述数量: {len(descriptions)}")
                
                for desc in descriptions:
                    print(f"  描述: {desc}")
                    try:
                        # 检查基础属性
                        use_cache = xgenm.getAttr('useCache', palette, desc, 'SplinePrimitive')
                        live_mode = xgenm.getAttr('liveMode', palette, desc, 'SplinePrimitive')
                        cache_file = xgenm.getAttr('cacheFileName', palette, desc, 'SplinePrimitive')
                        
                        print(f"    useCache: {use_cache}")
                        print(f"    liveMode: {live_mode}")
                        print(f"    cacheFile: {cache_file}")
                        
                        # 检查绑定表面
                        bound_geos = xgenm.boundGeometry(palette, desc)
                        if bound_geos:
                            print(f"    绑定表面: {bound_geos}")
                            for geo in bound_geos:
                                # 检查表面是否存在且可见
                                if cmds.objExists(geo):
                                    visible = cmds.getAttr(f"{geo}.visibility")
                                    print(f"      {geo}: 存在={True}, 可见={visible}")
                                else:
                                    print(f"      {geo}: 存在=False")
                        else:
                            print(f"    ⚠️  没有绑定表面")
                            
                    except Exception as e:
                        print(f"    ❌ 检查描述 {desc} 失败: {str(e)}")
                        
        except Exception as e:
            print(f"❌ XGen状态检查失败: {str(e)}")
    
    def get_assembly_status(self):
        """获取组装状态"""
        return self.assembly_status.copy()
    
    def reset_assembly_status(self):
        """重置组装状态"""
        for key in self.assembly_status:
            self.assembly_status[key] = False
        print("组装状态已重置")
    
    def get_current_config_summary(self):
        """获取当前配置摘要"""
        summary = {
            'asset': self.current_asset.get('asset_name', 'None') if self.current_asset else 'None',
            'lookdev_file': os.path.basename(self.current_lookdev_file) if self.current_lookdev_file else 'None',
            'animation_files_count': len(self.current_animation_files),
            'camera_file': os.path.basename(self.current_camera_file) if self.current_camera_file else 'None',
            'namespace': self.lookdev_namespace,
            'time_range': f"{self.start_frame}-{self.end_frame}",
            'status': self.assembly_status.copy()
        }
        return summary
    
    def _handle_special_groups_blendshape(self):
        """处理特殊组的blendShape连接 - Clothes_grp和chr_dwl_growthmesh_grp"""
        print("\n=== 处理特殊组blendShape连接 ===")
        
        try:
            # 查找特殊组
            special_groups = self._find_special_groups()
            
            if not special_groups:
                print("未找到需要处理的特殊组")
                return False
            
            total_blendshapes = 0
            
            for group_type, groups in special_groups.items():
                if len(groups) >= 2:
                    print(f"\n处理 {group_type} 组:")
                    cfx_group = groups[0]  # CFX组（源）
                    ani_group = groups[1]  # 动画组（目标）
                    
                    blendshapes_created = self._create_blendshapes_for_groups(cfx_group, ani_group)
                    total_blendshapes += blendshapes_created
                    
                    print(f"  {group_type} 组创建了 {blendshapes_created} 个blendShape")
                else:
                    print(f"⚠️  {group_type} 组数量不足 (找到 {len(groups)} 个，需要至少2个)")
            
            print(f"\n✅ 特殊组处理完成，总共创建了 {total_blendshapes} 个blendShape")
            return total_blendshapes > 0
            
        except Exception as e:
            print(f"❌ 特殊组处理失败: {str(e)}")
            return False
    
    def _find_special_groups(self):
        """查找特殊组"""
        special_groups = {
            'Clothes': [],
            'Growth': []
        }
        
        # 在lookdev命名空间下查找所有transform
        lookdev_transforms = cmds.ls(f"{self.lookdev_namespace}:*", type='transform', long=True) or []
        
        # 查找Clothes组
        clothes_groups = [t for t in lookdev_transforms if 'clothes' in t.lower() and 'grp' in t.lower()]
        special_groups['Clothes'] = clothes_groups
        
        # 查找Growth组
        growth_groups = [t for t in lookdev_transforms if 'growth' in t.lower() and ('mesh' in t.lower() or 'grp' in t.lower())]
        special_groups['Growth'] = growth_groups
        
        # 打印找到的组
        for group_type, groups in special_groups.items():
            if groups:
                print(f"找到 {group_type} 组 ({len(groups)} 个):")
                for group in groups:
                    print(f"  - {group}")
            else:
                print(f"未找到 {group_type} 组")
        
        return {k: v for k, v in special_groups.items() if v}
    
    def _create_blendshapes_for_groups(self, group1, group2):
        """为两个组创建blendShape连接，智能识别CFX和ANI组"""
        try:
            # 智能识别哪个是CFX组，哪个是ANI组
            cfx_group, ani_group = self._identify_cfx_and_ani_groups(group1, group2)
            
            if not cfx_group or not ani_group:
                print(f"    无法识别CFX和ANI组，跳过处理")
                return 0
            
            # 存储面数信息的字典
            cfx_mesh_info = {}
            ani_mesh_info = {}
            created_blendshapes = []
            
            print(f"  分析CFX组: {cfx_group.split('|')[-1]}")
            # 获取CFX组下所有mesh并统计面数
            cfx_meshes = cmds.listRelatives(cfx_group, allDescendents=True, children=True, fullPath=True, type='mesh') or []
            for cfx_mesh in cfx_meshes:
                try:
                    face_count = cmds.polyEvaluate(cfx_mesh, face=True)
                    mesh_name = self._clean_mesh_name(cfx_mesh.split('|')[-1])
                    cfx_mesh_info[cfx_mesh] = {
                        'face_count': face_count,
                        'clean_name': mesh_name
                    }
                    print(f"    CFX: {cfx_mesh.split('|')[-1]} - {face_count} 面 ({mesh_name})")
                except:
                    continue
            
            print(f"  分析ANI组: {ani_group.split('|')[-1]}")
            # 获取ANI组下所有mesh并统计面数
            ani_meshes = cmds.listRelatives(ani_group, allDescendents=True, children=True, fullPath=True, type='mesh') or []
            for ani_mesh in ani_meshes:
                try:
                    face_count = cmds.polyEvaluate(ani_mesh, face=True)
                    mesh_name = self._clean_mesh_name(ani_mesh.split('|')[-1])
                    ani_mesh_info[ani_mesh] = {
                        'face_count': face_count,
                        'clean_name': mesh_name
                    }
                    print(f"    ANI: {ani_mesh.split('|')[-1]} - {face_count} 面 ({mesh_name})")
                except:
                    continue
            
            print(f"  智能匹配mesh并创建blendShape...")
            # 通过面数和名称匹配mesh并创建blendShape
            matched_pairs = {}
            for cfx_mesh, cfx_info in cfx_mesh_info.items():
                best_match = None
                best_score = 0
                
                for ani_mesh, ani_info in ani_mesh_info.items():
                    if ani_mesh in matched_pairs.values():
                        continue  # 已经被匹配过
                    
                    score = 0
                    # 面数必须完全匹配
                    if cfx_info['face_count'] == ani_info['face_count']:
                        score += 10
                        
                        # 名称相似度加分
                        if cfx_info['clean_name'] == ani_info['clean_name']:
                            score += 5
                        elif cfx_info['clean_name'] in ani_info['clean_name'] or ani_info['clean_name'] in cfx_info['clean_name']:
                            score += 3
                        
                        if score > best_score:
                            best_score = score
                            best_match = ani_mesh
                
                if best_match and best_score >= 10:  # 至少面数要匹配
                    matched_pairs[cfx_mesh] = best_match
                    
                    try:
                        # 检查ANI mesh是否已经有blendShape连接，避免重复
                        ani_shape = best_match
                        existing_blendshape = self._find_blendshape_for_mesh(ani_shape)
                        
                        if existing_blendshape:
                            # 使用现有blendShape，添加新目标
                            success = self._add_mesh_to_existing_blendshape(existing_blendshape, cfx_mesh, ani_shape)
                            if success:
                                created_blendshapes.append(existing_blendshape)
                                cfx_name = cfx_mesh.split('|')[-1]
                                ani_name = best_match.split('|')[-1]
                                print(f"    ✅ 添加到现有blendShape: {cfx_name} -> {ani_name} ({cfx_info['face_count']} 面)")
                        else:
                            # 创建新的blendShape
                            blend_node = self._create_safe_blendshape(cfx_mesh, best_match)
                            if blend_node:
                                created_blendshapes.append(blend_node)
                                cfx_name = cfx_mesh.split('|')[-1]
                                ani_name = best_match.split('|')[-1]
                                print(f"    ✅ 创建新blendShape: {cfx_name} -> {ani_name} ({cfx_info['face_count']} 面)")
                            else:
                                print(f"    ❌ 创建blendShape失败: {cfx_mesh.split('|')[-1]} -> {best_match.split('|')[-1]}")
                        
                    except Exception as e:
                        print(f"    ❌ 创建blendShape失败: {cfx_mesh.split('|')[-1]} -> {best_match.split('|')[-1]}, 错误: {str(e)}")
            
            # 检查未匹配的mesh
            unmatched_cfx = []
            unmatched_ani = []
            
            for cfx_mesh in cfx_mesh_info.keys():
                if cfx_mesh not in matched_pairs:
                    unmatched_cfx.append(f"{cfx_mesh.split('|')[-1]} ({cfx_mesh_info[cfx_mesh]['face_count']} 面)")
            
            for ani_mesh in ani_mesh_info.keys():
                if ani_mesh not in matched_pairs.values():
                    unmatched_ani.append(f"{ani_mesh.split('|')[-1]} ({ani_mesh_info[ani_mesh]['face_count']} 面)")
            
            if unmatched_cfx:
                print(f"    ⚠️  CFX组中未匹配的mesh:")
                for mesh in unmatched_cfx:
                    print(f"      - {mesh}")
            
            if unmatched_ani:
                print(f"    ⚠️  ANI组中未匹配的mesh:")
                for mesh in unmatched_ani:
                    print(f"      - {mesh}")
            
            return len(created_blendshapes)
            
        except Exception as e:
            print(f"    ❌ 为组创建blendShape失败: {str(e)}")
            return 0
    
    def _import_and_connect_fur_cache(self):
        """导入并连接毛发解算文件（fur文件）"""
        print("\n=== 处理毛发解算文件（fur文件）===")
        
        try:
            # 查找毛发解算文件
            fur_file = self._find_fur_cache_file()
            
            if not fur_file:
                print("未找到毛发解算文件")
                return False
            
            print(f"找到毛发解算文件: {fur_file}")
            
            # 确保ABC插件已加载
            if not cmds.pluginInfo('AbcImport', query=True, loaded=True):
                cmds.loadPlugin('AbcImport')
            
            # 记录导入前的transform
            transforms_before = set(cmds.ls(type='transform'))
            
            # 使用Maya file -import命令导入毛发解算文件（支持namespace）
            print(f"导入毛发解算文件: {os.path.basename(fur_file)}")
            try:
                # 构建简化的命名空间
                # 从文件名提取资产信息创建简化命名空间：dwl_fur_cfx
                fur_filename = os.path.basename(fur_file)
                if self.current_asset:
                    asset_name = self.current_asset.get('asset_name', 'fur')
                    simplified_namespace = f"{asset_name}_fur_cfx"
                else:
                    simplified_namespace = self.fur_namespace
                
                print(f"使用简化命名空间: {simplified_namespace}")
                
                # 确保命名空间存在
                if not cmds.namespace(exists=simplified_namespace):
                    cmds.namespace(add=simplified_namespace)
                
                # 记录导入前的命名空间
                namespaces_before = set(cmds.namespaceInfo(listOnlyNamespaces=True))
                
                # 使用file -import命令导入毛发ABC文件
                # 注意：-gr 标志会创建组，但不会创建引用（移除了-ra和-pr）
                cmds.file(
                    fur_file,
                    i=True,  # import
                    type="Alembic",
                    gr=True,  # groupReference - 创建组但不引用
                    ignoreVersion=True,
                    mergeNamespacesOnClash=False,
                    namespace=simplified_namespace,
                    importTimeRange="combine"
                )
                
                # 检查实际使用的命名空间
                namespaces_after = set(cmds.namespaceInfo(listOnlyNamespaces=True))
                new_namespaces = namespaces_after - namespaces_before
                
                # 如果Maya自动添加了数字后缀，更新命名空间变量
                actual_fur_namespace = simplified_namespace
                for ns in new_namespaces:
                    if ns.startswith(simplified_namespace):
                        actual_fur_namespace = ns
                        if actual_fur_namespace != simplified_namespace:
                            print(f"⚠️  Maya使用了毛发命名空间: {actual_fur_namespace}")
                        break
                
                # 更新命名空间变量以便后续使用
                self.actual_fur_namespace = actual_fur_namespace
                
                print(f"✅ 已导入毛发解算ABC到命名空间: {actual_fur_namespace}")
                
            except Exception as e:
                print(f"❌ 导入毛发解算ABC文件失败: {str(e)}")
                return False
            
            # 找到新导入的transform
            transforms_after = set(cmds.ls(type='transform'))
            new_transforms = transforms_after - transforms_before
            
            if not new_transforms:
                print("❌ 没有导入新的transform")
                return False
            
            print(f"导入了 {len(new_transforms)} 个新transform")
            
            # 查找fur组（新导入的顶层组）
            fur_group = None
            for transform in new_transforms:
                # 查找没有父节点的transform（顶层组）
                parent = cmds.listRelatives(transform, parent=True)
                if not parent:
                    fur_group = transform
                    break
            
            if not fur_group:
                print("❌ 未找到fur顶层组")
                return False
            
            print(f"原始Fur组: {fur_group}")
            
            # 保存原始fur组的引用
            original_fur_group = fur_group
            
            # 创建fur管理组并将fur组放入其中
            fur_container_group = self._create_fur_container_group(fur_group)
            if fur_container_group:
                print(f"Fur容器组: {fur_container_group}")
                # 注意：这里不能替换fur_group，因为blendShape需要使用原始的fur组
            else:
                print("使用原始fur组继续处理")
                fur_container_group = None
            
            # 查找lookdev中的growthmesh组
            growthmesh_group = self._find_growthmesh_group()
            
            if not growthmesh_group:
                print("❌ 未找到growthmesh组")
                return False
            
            print(f"Growthmesh组: {growthmesh_group}")
            
            # 创建blendShape连接（使用原始fur组，因为实际的mesh在原始组中）
            success = self._create_fur_blendshapes(original_fur_group, growthmesh_group)
            
            if success:
                print("✅ 毛发解算文件处理完成")
                
                # 隐藏fur组（如果是容器组则隐藏整个容器组）
                try:
                    if fur_container_group:
                        # 隐藏容器组
                        cmds.setAttr(fur_container_group + '.visibility', 0)
                        print(f"已隐藏fur容器组: {fur_container_group}")
                    else:
                        # 隐藏原始组
                        cmds.setAttr(fur_group + '.visibility', 0)
                        print(f"已隐藏fur组: {fur_group}")
                except Exception as e:
                    print(f"⚠️  隐藏fur组失败: {str(e)}")
                
                return True
            else:
                print("❌ 毛发解算文件处理失败")
                return False
                
        except Exception as e:
            print(f"❌ 处理毛发解算文件失败: {str(e)}")
            return False
    
    def _find_fur_cache_file(self):
        """查找毛发解算文件"""
        try:
            # 从毛发缓存路径推导解算文件路径
            hair_template = self.config_manager.get_hair_cache_template()
            
            # 解析路径获取hair目录
            # 从 P:/LHSN/cache/dcc/shot/s310/c0990/cfx/alembic/hair/dwl_01/outcurve/cache_${DESC}.0001.abc
            # 获取 P:/LHSN/cache/dcc/shot/s310/c0990/cfx/alembic/hair/
            
            path_parts = hair_template.replace('\\', '/').split('/')
            hair_index = -1
            for i, part in enumerate(path_parts):
                if part == 'hair':
                    hair_index = i
                    break
            
            if hair_index < 0:
                print("无法从模板路径找到hair目录")
                return None
            
            # 构建hair目录路径
            hair_dir = '/'.join(path_parts[:hair_index + 1])
            hair_dir = hair_dir.replace('/', '\\')
            
            print(f"搜索毛发解算文件目录: {hair_dir}")
            
            if not os.path.exists(hair_dir):
                print(f"目录不存在: {hair_dir}")
                return None
            
            # 查找fur文件
            # 文件名模式可能是:
            # LHSN_chr_dwl_01_fur_fur_v006__LHSN_chr_dwl_fur_fur_v006__dwl_fur_col.abc
            # LHSN_chr_tna_01_fur_fur_v007__tna_fur_col.abc
            
            fur_files = []
            try:
                for file in os.listdir(hair_dir):
                    if file.endswith('.abc') and 'fur' in file.lower():
                        full_path = os.path.join(hair_dir, file)
                        if os.path.isfile(full_path):
                            fur_files.append(full_path)
                            print(f"  找到fur文件: {file}")
            except Exception as e:
                print(f"搜索fur文件失败: {str(e)}")
                return None
            
            if not fur_files:
                print("未找到fur文件")
                return None
            
            # 如果当前资产名称可用，优先选择匹配的文件
            if self.current_asset:
                asset_name = self.current_asset.get('asset_name', '')
                for fur_file in fur_files:
                    if asset_name in os.path.basename(fur_file):
                        print(f"选择匹配资产的fur文件: {os.path.basename(fur_file)}")
                        return fur_file
            
            # 返回第一个找到的fur文件
            print(f"选择第一个fur文件: {os.path.basename(fur_files[0])}")
            return fur_files[0]
            
        except Exception as e:
            print(f"查找毛发解算文件失败: {str(e)}")
            return None
    
    def _find_growthmesh_group(self):
        """查找lookdev中的growthmesh组"""
        try:
            # 查找路径: Master/GEO/CFX/chr_dwl_growthmesh_grp
            search_patterns = [
                f"{self.lookdev_namespace}:Master|{self.lookdev_namespace}:GEO|{self.lookdev_namespace}:CFX|*growthmesh*",
                f"{self.lookdev_namespace}:Master|{self.lookdev_namespace}:GEO|{self.lookdev_namespace}:CFX|*growth*",
                f"{self.lookdev_namespace}:*growthmesh*",
                f"{self.lookdev_namespace}:*growth*"
            ]
            
            for pattern in search_patterns:
                transforms = cmds.ls(pattern, type='transform', long=True) or []
                for transform in transforms:
                    if 'growth' in transform.lower():
                        print(f"找到growthmesh组: {transform}")
                        return transform
            
            # 如果没有找到，尝试更广泛的搜索
            all_transforms = cmds.ls(f"{self.lookdev_namespace}:*", type='transform', long=True) or []
            for transform in all_transforms:
                if 'growth' in transform.lower() and ('mesh' in transform.lower() or 'grp' in transform.lower()):
                    if 'CFX' in transform or 'cfx' in transform:
                        print(f"找到growthmesh组: {transform}")
                        return transform
            
            return None
            
        except Exception as e:
            print(f"查找growthmesh组失败: {str(e)}")
            return None
    
    def _create_fur_blendshapes(self, fur_group, growthmesh_group):
        """为fur和growthmesh创建blendShape连接"""
        try:
            print("\n创建fur到growthmesh的blendShape连接...")
            
            # 获取fur组下所有mesh
            fur_meshes = cmds.listRelatives(fur_group, allDescendents=True, type='mesh', fullPath=True) or []
            print(f"Fur组中找到 {len(fur_meshes)} 个mesh")
            
            # 获取growthmesh组下所有mesh
            growth_meshes = cmds.listRelatives(growthmesh_group, allDescendents=True, type='mesh', fullPath=True) or []
            print(f"Growthmesh组中找到 {len(growth_meshes)} 个mesh")
            
            if not fur_meshes or not growth_meshes:
                print("❌ 没有找到足够的mesh进行连接")
                return False
            
            # 创建mesh名称映射（去掉命名空间后的名称）
            fur_mesh_dict = {}
            for fur_mesh in fur_meshes:
                # 获取不带命名空间的名称
                mesh_name = fur_mesh.split('|')[-1]
                if ':' in mesh_name:
                    mesh_name = mesh_name.split(':')[-1]
                fur_mesh_dict[mesh_name.lower()] = fur_mesh
                print(f"  Fur mesh: {mesh_name}")
            
            growth_mesh_dict = {}
            for growth_mesh in growth_meshes:
                # 获取不带命名空间的名称
                mesh_name = growth_mesh.split('|')[-1]
                if ':' in mesh_name:
                    mesh_name = mesh_name.split(':')[-1]
                growth_mesh_dict[mesh_name.lower()] = growth_mesh
                print(f"  Growth mesh: {mesh_name}")
            
            # 匹配并创建blendShape
            created_count = 0
            for mesh_name, fur_mesh in fur_mesh_dict.items():
                if mesh_name in growth_mesh_dict:
                    growth_mesh = growth_mesh_dict[mesh_name]
                    
                    try:
                        # 安全创建blendShape（fur驱动growth）
                        blend_node = self._create_safe_blendshape(fur_mesh, growth_mesh)
                        if blend_node:
                            print(f"  ✅ 创建blendShape: {mesh_name}")
                            created_count += 1
                        else:
                            print(f"  ❌ 创建blendShape失败 {mesh_name}")
                        
                    except Exception as e:
                        print(f"  ❌ 创建blendShape失败 {mesh_name}: {str(e)}")
                else:
                    print(f"  ⚠️  未找到匹配的growth mesh: {mesh_name}")
            
            if created_count > 0:
                print(f"\n✅ 成功创建 {created_count} 个fur blendShape")
                return True
            else:
                print("❌ 没有创建任何fur blendShape")
                return False
                
        except Exception as e:
            print(f"创建fur blendShape失败: {str(e)}")
            return False
    
    def _import_and_connect_cloth_cache(self):
        """导入并连接布料解算文件（cloth文件）"""
        print("\n=== 处理布料解算文件（cloth文件）===")
        
        try:
            # 查找布料解算文件
            cloth_file = self._find_cloth_cache_file()
            
            if not cloth_file:
                print("未找到布料解算文件")
                return False
            
            print(f"找到布料解算文件: {cloth_file}")
            
            # 确保ABC插件已加载
            if not cmds.pluginInfo('AbcImport', query=True, loaded=True):
                cmds.loadPlugin('AbcImport')
            
            # 记录导入前的transform
            transforms_before = set(cmds.ls(type='transform'))
            
            # 使用Maya file -import命令导入布料解算文件（支持namespace）
            print(f"导入布料解算文件: {os.path.basename(cloth_file)}")
            try:
                # 构建简化的命名空间
                # 创建简化命名空间：dwl_cloth_cfx
                if self.current_asset:
                    asset_name = self.current_asset.get('asset_name', 'cloth')
                    simplified_namespace = f"{asset_name}_cloth_cfx"
                else:
                    simplified_namespace = self.cloth_namespace
                
                print(f"使用简化命名空间: {simplified_namespace}")
                
                # 确保命名空间存在
                if not cmds.namespace(exists=simplified_namespace):
                    cmds.namespace(add=simplified_namespace)
                
                # 记录导入前的命名空间
                namespaces_before = set(cmds.namespaceInfo(listOnlyNamespaces=True))
                
                # 使用file -import命令导入布料ABC文件
                # 注意：-gr 标志会创建组，但不会创建引用（移除了-ra和-pr）
                cmds.file(
                    cloth_file,
                    i=True,  # import
                    type="Alembic",
                    gr=True,  # groupReference - 创建组但不引用
                    ignoreVersion=True,
                    mergeNamespacesOnClash=False,
                    namespace=simplified_namespace,
                    importTimeRange="combine"
                )
                
                # 检查实际使用的命名空间
                namespaces_after = set(cmds.namespaceInfo(listOnlyNamespaces=True))
                new_namespaces = namespaces_after - namespaces_before
                
                # 如果Maya自动添加了数字后缀，更新命名空间变量
                actual_cloth_namespace = simplified_namespace
                for ns in new_namespaces:
                    if ns.startswith(simplified_namespace):
                        actual_cloth_namespace = ns
                        if actual_cloth_namespace != simplified_namespace:
                            print(f"⚠️  Maya使用了布料命名空间: {actual_cloth_namespace}")
                        break
                
                # 更新命名空间变量以便后续使用
                self.actual_cloth_namespace = actual_cloth_namespace
                
                print(f"✅ 已导入布料解算ABC到命名空间: {actual_cloth_namespace}")
                
            except Exception as e:
                print(f"❌ 导入布料解算ABC文件失败: {str(e)}")
                return False
            
            # 找到新导入的transform
            transforms_after = set(cmds.ls(type='transform'))
            new_transforms = transforms_after - transforms_before
            
            if not new_transforms:
                print("❌ 没有导入新的transform")
                return False
            
            print(f"导入了 {len(new_transforms)} 个新transform")
            
            # 查找cloth组（新导入的顶层组）
            cloth_group = None
            for transform in new_transforms:
                # 查找没有父节点的transform（顶层组）
                parent = cmds.listRelatives(transform, parent=True)
                if not parent:
                    cloth_group = transform
                    break
            
            if not cloth_group:
                print("❌ 未找到cloth顶层组")
                return False
            
            print(f"Cloth组: {cloth_group}")
            
            # 查找lookdev中的clothes组
            clothes_group = self._find_clothes_group()
            
            if not clothes_group:
                print("❌ 未找到clothes组")
                return False
            
            print(f"Clothes组: {clothes_group}")
            
            # 创建blendShape连接
            success = self._create_cloth_blendshapes(cloth_group, clothes_group)
            
            if success:
                print("✅ 布料解算文件处理完成")
                
                # 隐藏cloth组
                try:
                    cmds.setAttr(cloth_group + '.visibility', 0)
                    print(f"已隐藏cloth组: {cloth_group}")
                except:
                    pass
                
                return True
            else:
                print("❌ 布料解算文件处理失败")
                return False
                
        except Exception as e:
            print(f"❌ 处理布料解算文件失败: {str(e)}")
            return False
    
    def _find_cloth_cache_file(self):
        """查找布料解算文件"""
        try:
            # 从毛发缓存路径推导布料解算文件路径
            hair_template = self.config_manager.get_hair_cache_template()
            
            # 解析路径获取基础cfx目录
            # 从 P:/LHSN/cache/dcc/shot/s310/c0990/cfx/alembic/hair/dwl_01/outcurve/cache_${DESC}.0001.abc
            # 获取 P:/LHSN/cache/dcc/shot/s310/c0990/cfx/alembic/cloth/
            
            path_parts = hair_template.replace('\\', '/').split('/')
            alembic_index = -1
            for i, part in enumerate(path_parts):
                if part == 'alembic':
                    alembic_index = i
                    break
            
            if alembic_index < 0:
                print("无法从模板路径找到alembic目录")
                return None
            
            # 构建cloth目录路径
            cloth_dir = '/'.join(path_parts[:alembic_index + 1]) + '/cloth'
            cloth_dir = cloth_dir.replace('/', '\\')
            
            print(f"搜索布料解算文件目录: {cloth_dir}")
            
            if not os.path.exists(cloth_dir):
                print(f"目录不存在: {cloth_dir}")
                return None
            
            # 查找资产对应的子目录
            asset_cloth_dir = None
            if self.current_asset:
                asset_name = self.current_asset.get('asset_name', '')
                
                # 查找包含资产名称的子目录
                try:
                    for item in os.listdir(cloth_dir):
                        item_path = os.path.join(cloth_dir, item)
                        if os.path.isdir(item_path) and asset_name in item:
                            asset_cloth_dir = item_path
                            print(f"找到资产布料目录: {item}")
                            break
                except Exception as e:
                    print(f"搜索资产布料目录失败: {str(e)}")
                    return None
            
            if not asset_cloth_dir:
                print("未找到资产对应的布料目录")
                return None
            
            # 查找cloth ABC文件，按编号取最新的
            # 文件名模式: dwl_01.0001.abc, dwl_01.0002.abc 等
            print(f"搜索布料文件在目录: {asset_cloth_dir}")
            
            # 列出目录内容进行调试
            try:
                dir_contents = os.listdir(asset_cloth_dir)
                print(f"目录内容: {dir_contents}")
            except Exception as e:
                print(f"无法列出目录内容: {str(e)}")
                return None
            
            cloth_files = []
            try:
                for file in dir_contents:
                    print(f"检查文件: {file}")
                    if file.endswith('.abc'):
                        # 提取编号
                        try:
                            # dwl_01.0002.abc -> 0002
                            parts = file.split('.')
                            print(f"  文件分段: {parts}")
                            if len(parts) >= 3:
                                number = int(parts[-2])  # 倒数第二个部分是编号
                                full_path = os.path.join(asset_cloth_dir, file)
                                cloth_files.append((number, full_path, file))
                                print(f"  ✅ 找到cloth文件: {file} (编号: {number})")
                            else:
                                print(f"  ⚠️  文件名格式不符合预期: {file}")
                        except ValueError as ve:
                            print(f"  ⚠️  无法提取编号: {file}, 错误: {ve}")
                            continue
                    else:
                        print(f"  跳过非ABC文件: {file}")
            except Exception as e:
                print(f"搜索cloth文件失败: {str(e)}")
                return None
            
            if not cloth_files:
                print("未找到cloth文件")
                return None
            
            # 按编号排序，取最新的（编号最大的）
            cloth_files.sort(key=lambda x: x[0], reverse=True)
            latest_cloth = cloth_files[0]
            
            print(f"选择最新的cloth文件: {latest_cloth[2]} (编号: {latest_cloth[0]})")
            return latest_cloth[1]
            
        except Exception as e:
            print(f"查找布料解算文件失败: {str(e)}")
            return None
    
    def _find_clothes_group(self, asset_name=None):
        """查找lookdev中的clothes组"""
        try:
            # 使用传入的asset_name或当前资产名称
            if not asset_name and self.current_asset:
                asset_name = self.current_asset.get('asset_name', 'dwl')
            elif not asset_name:
                asset_name = 'dwl'
            
            print(f"查找clothes组，lookdev命名空间: {self.lookdev_namespace}, 资产名称: {asset_name}")
            
            # 方法1: 直接构建预期路径
            expected_paths = [
                # 使用动态资产名称构建路径
                f"|{self.lookdev_namespace}:Master|{self.lookdev_namespace}:GEO|{self.lookdev_namespace}:HIG|{self.lookdev_namespace}:chr_{asset_name}_hig_grp|{self.lookdev_namespace}:Clothes_grp|{self.lookdev_namespace}:{asset_name}_cloth_group",
                f"|{self.lookdev_namespace}:Master|{self.lookdev_namespace}:GEO|{self.lookdev_namespace}:HIG|{self.lookdev_namespace}:chr_{asset_name}_hig_grp|{self.lookdev_namespace}:Clothes_grp",
                # 保留原始dwl作为备选
                f"|{self.lookdev_namespace}:Master|{self.lookdev_namespace}:GEO|{self.lookdev_namespace}:HIG|{self.lookdev_namespace}:chr_dwl_hig_grp|{self.lookdev_namespace}:Clothes_grp|{self.lookdev_namespace}:dwl_cloth_group",
                f"|{self.lookdev_namespace}:Master|{self.lookdev_namespace}:GEO|{self.lookdev_namespace}:HIG|{self.lookdev_namespace}:chr_dwl_hig_grp|{self.lookdev_namespace}:Clothes_grp"
            ]
            
            for path in expected_paths:
                print(f"检查路径: {path}")
                if cmds.objExists(path):
                    # 检查这个路径下是否有mesh
                    try:
                        meshes = cmds.listRelatives(path, allDescendents=True, type='mesh', fullPath=True, noIntermediate=True) or []
                        if meshes:
                            print(f"✅ 找到clothes组: {path} (包含 {len(meshes)} 个mesh)")
                            return path
                        else:
                            print(f"⚠️  路径存在但没有mesh: {path}")
                    except:
                        print(f"⚠️  无法检查mesh: {path}")
                else:
                    print(f"路径不存在: {path}")
            
            # 方法2: 在Clothes_grp下搜索所有子组
            clothes_grp_path = f"|{self.lookdev_namespace}:Master|{self.lookdev_namespace}:GEO|{self.lookdev_namespace}:HIG|{self.lookdev_namespace}:chr_dwl_hig_grp|{self.lookdev_namespace}:Clothes_grp"
            print(f"在Clothes_grp下搜索: {clothes_grp_path}")
            
            if cmds.objExists(clothes_grp_path):
                try:
                    children = cmds.listRelatives(clothes_grp_path, children=True, fullPath=True) or []
                    print(f"Clothes_grp下有 {len(children)} 个子节点")
                    
                    for child in children:
                        child_name = child.split('|')[-1]
                        print(f"  检查子节点: {child_name}")
                        
                        # 检查是否包含mesh
                        try:
                            meshes = cmds.listRelatives(child, allDescendents=True, type='mesh', fullPath=True, noIntermediate=True) or []
                            if meshes:
                                print(f"✅ 找到包含mesh的子组: {child} (包含 {len(meshes)} 个mesh)")
                                return child
                        except:
                            continue
                except Exception as e:
                    print(f"搜索Clothes_grp子节点失败: {str(e)}")
            
            # 方法3: 模糊搜索包含cloth的组
            print("执行模糊搜索...")
            all_transforms = cmds.ls(f"{self.lookdev_namespace}:*", type='transform', long=True) or []
            
            candidates = []
            for transform in all_transforms:
                if ('cloth' in transform.lower() or 'clothes' in transform.lower()) and 'HIG' in transform:
                    try:
                        meshes = cmds.listRelatives(transform, allDescendents=True, type='mesh', fullPath=True, noIntermediate=True) or []
                        if meshes:
                            candidates.append((transform, len(meshes)))
                            print(f"候选: {transform} (包含 {len(meshes)} 个mesh)")
                    except:
                        continue
            
            if candidates:
                # 选择包含最多mesh的候选
                best_candidate = max(candidates, key=lambda x: x[1])
                print(f"✅ 选择最佳候选: {best_candidate[0]}")
                return best_candidate[0]
            
            print("❌ 未找到clothes组")
            return None
            
        except Exception as e:
            print(f"查找clothes组失败: {str(e)}")
            return None
    
    def _create_cloth_blendshapes(self, cloth_group, clothes_group):
        """为cloth和clothes创建blendShape连接"""
        try:
            print("\n创建cloth到clothes的blendShape连接...")
            
            # 获取cloth组下所有mesh（排除中间形状）
            print(f"检查cloth组结构: {cloth_group}")
            cloth_meshes = cmds.listRelatives(cloth_group, allDescendents=True, type='mesh', fullPath=True, noIntermediate=True) or []
            print(f"Cloth组中找到 {len(cloth_meshes)} 个mesh")
            
            # 显示前5个cloth mesh作为调试
            for i, mesh in enumerate(cloth_meshes[:5]):
                mesh_name = mesh.split('|')[-1]
                print(f"  Cloth mesh {i+1}: {mesh_name}")
            if len(cloth_meshes) > 5:
                print(f"  ... 还有 {len(cloth_meshes) - 5} 个cloth mesh")
            
            # 获取clothes组下所有mesh（排除中间形状）
            print(f"检查clothes组结构: {clothes_group}")
            
            # 先检查clothes组下的所有子节点
            try:
                all_children = cmds.listRelatives(clothes_group, allDescendents=True, fullPath=True) or []
                print(f"Clothes组下所有子节点数量: {len(all_children)}")
                
                # 显示前10个子节点作为调试
                for i, child in enumerate(all_children[:10]):
                    node_type = cmds.nodeType(child)
                    print(f"  子节点 {i+1}: {child.split('|')[-1]} (类型: {node_type})")
                if len(all_children) > 10:
                    print(f"  ... 还有 {len(all_children) - 10} 个子节点")
                    
            except Exception as e:
                print(f"获取clothes组子节点失败: {str(e)}")
            
            # 获取mesh节点
            clothes_meshes = cmds.listRelatives(clothes_group, allDescendents=True, type='mesh', fullPath=True, noIntermediate=True) or []
            print(f"Clothes组中找到 {len(clothes_meshes)} 个mesh")
            
            # 如果没有找到mesh，尝试包含中间形状
            if not clothes_meshes:
                print("未找到非中间形状的mesh，尝试包含中间形状...")
                clothes_meshes_with_intermediate = cmds.listRelatives(clothes_group, allDescendents=True, type='mesh', fullPath=True) or []
                print(f"包含中间形状的mesh数量: {len(clothes_meshes_with_intermediate)}")
                
                # 显示所有mesh的详细信息
                for mesh in clothes_meshes_with_intermediate:
                    try:
                        is_intermediate = cmds.getAttr(mesh + '.intermediateObject')
                        print(f"  Mesh: {mesh.split('|')[-1]} (中间形状: {is_intermediate})")
                    except:
                        print(f"  Mesh: {mesh.split('|')[-1]} (无法检查中间形状属性)")
                
                # 使用非中间形状的mesh
                clothes_meshes = [mesh for mesh in clothes_meshes_with_intermediate 
                                if not cmds.getAttr(mesh + '.intermediateObject', silent=True)]
                print(f"过滤后的Clothes组mesh数量: {len(clothes_meshes)}")
            
            if not cloth_meshes or not clothes_meshes:
                print("❌ 没有找到足够的mesh进行连接")
                return False
            
            # 创建mesh信息字典，包含名称和面数
            cloth_mesh_info = {}
            for cloth_mesh in cloth_meshes:
                # 获取transform节点
                transform = cmds.listRelatives(cloth_mesh, parent=True, fullPath=True)[0]
                # 获取不带命名空间的名称
                mesh_name = transform.split('|')[-1]
                if ':' in mesh_name:
                    mesh_name = mesh_name.split(':')[-1]
                
                # 获取面数
                try:
                    face_count = cmds.polyEvaluate(cloth_mesh, face=True)
                except:
                    face_count = 0
                
                cloth_mesh_info[mesh_name.lower()] = {
                    'mesh': cloth_mesh,
                    'transform': transform,
                    'face_count': face_count,
                    'original_name': mesh_name
                }
                print(f"  Cloth mesh: {mesh_name} (面数: {face_count})")
            
            clothes_mesh_info = {}
            for clothes_mesh in clothes_meshes:
                # 获取transform节点
                transform = cmds.listRelatives(clothes_mesh, parent=True, fullPath=True)[0]
                # 获取不带命名空间的名称
                mesh_name = transform.split('|')[-1]
                if ':' in mesh_name:
                    mesh_name = mesh_name.split(':')[-1]
                
                # 获取面数
                try:
                    face_count = cmds.polyEvaluate(clothes_mesh, face=True)
                except:
                    face_count = 0
                    
                clothes_mesh_info[mesh_name.lower()] = {
                    'mesh': clothes_mesh,
                    'transform': transform,
                    'face_count': face_count,
                    'original_name': mesh_name
                }
                print(f"  Clothes mesh: {mesh_name} (面数: {face_count})")
            
            # 智能匹配：首先按名称匹配，然后按面数匹配
            created_count = 0
            matched_clothes = set()
            
            # 第一轮：精确名称匹配
            print("\n第一轮：精确名称匹配...")
            for mesh_name, cloth_info in cloth_mesh_info.items():
                if mesh_name in clothes_mesh_info and mesh_name not in matched_clothes:
                    clothes_info = clothes_mesh_info[mesh_name]
                    
                    # 检查面数是否匹配
                    if cloth_info['face_count'] != clothes_info['face_count']:
                        print(f"  ⚠️  {cloth_info['original_name']}: 面数不匹配 (cloth: {cloth_info['face_count']}, clothes: {clothes_info['face_count']})")
                        continue
                    
                    try:
                        # 使用transform节点创建blendShape（cloth驱动clothes）
                        blend_node = self._create_safe_blendshape(cloth_info['transform'], clothes_info['transform'])
                        if blend_node:
                            print(f"  ✅ 创建blendShape: {cloth_info['original_name']} -> {clothes_info['original_name']}")
                            created_count += 1
                            matched_clothes.add(mesh_name)
                        else:
                            print(f"  ❌ 创建blendShape失败: {cloth_info['original_name']}")
                        
                    except Exception as e:
                        print(f"  ❌ 创建blendShape失败 {cloth_info['original_name']}: {str(e)}")
            
            # 第二轮：基于面数的模糊匹配（用于未匹配的mesh）
            print("\n第二轮：基于面数的模糊匹配...")
            unmatched_cloth = [info for name, info in cloth_mesh_info.items() if name not in matched_clothes]
            unmatched_clothes = [info for name, info in clothes_mesh_info.items() if name not in matched_clothes]
            
            for cloth_info in unmatched_cloth:
                best_match = None
                best_score = 0
                
                for clothes_info in unmatched_clothes:
                    # 计算匹配分数
                    score = 0
                    
                    # 面数必须完全匹配
                    if cloth_info['face_count'] == clothes_info['face_count'] and cloth_info['face_count'] > 0:
                        score += 100
                        
                        # 名称相似度加分
                        cloth_name = cloth_info['original_name'].lower()
                        clothes_name = clothes_info['original_name'].lower()
                        
                        # 计算共同字符
                        common_chars = sum(1 for c in cloth_name if c in clothes_name)
                        score += common_chars * 5
                        
                        if score > best_score:
                            best_score = score
                            best_match = clothes_info
                
                if best_match and best_score >= 100:  # 至少面数要匹配
                    try:
                        blend_node = self._create_safe_blendshape(cloth_info['transform'], best_match['transform'])
                        if blend_node:
                            print(f"  ✅ 模糊匹配创建blendShape: {cloth_info['original_name']} -> {best_match['original_name']} (分数: {best_score})")
                            created_count += 1
                            # 标记为已匹配
                            for name, info in clothes_mesh_info.items():
                                if info == best_match:
                                    matched_clothes.add(name)
                                    break
                        else:
                            print(f"  ❌ 创建blendShape失败: {cloth_info['original_name']}")
                    except Exception as e:
                        print(f"  ❌ 创建blendShape失败 {cloth_info['original_name']}: {str(e)}")
                else:
                    print(f"  ⚠️  未找到匹配的clothes mesh: {cloth_info['original_name']} (面数: {cloth_info['face_count']})")
            
            # 报告未匹配的clothes mesh
            for name, info in clothes_mesh_info.items():
                if name not in matched_clothes:
                    print(f"  ⚠️  Clothes mesh未被驱动: {info['original_name']} (面数: {info['face_count']})")
            
            if created_count > 0:
                print(f"\n✅ 成功创建 {created_count} 个cloth blendShape")
                return True
            else:
                print("❌ 没有创建任何cloth blendShape")
                return False
                
        except Exception as e:
            print(f"创建cloth blendShape失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def _create_fur_container_group(self, original_fur_group):
        """为fur组创建管理容器组"""
        try:
            # 获取资产名称用于命名
            asset_name = "fur"
            if self.current_asset:
                asset_name = self.current_asset.get('asset_name', 'fur')
            
            # 创建容器组名称（不使用命名空间，在根级别创建）
            container_name = f"{asset_name}_fur_cache_grp"
            
            # 检查是否已存在同名组
            if cmds.objExists(container_name):
                # 如果存在，生成唯一名称
                counter = 1
                while cmds.objExists(f"{container_name}_{counter}"):
                    counter += 1
                container_name = f"{container_name}_{counter}"
            
            # 创建空组
            container_group = cmds.group(empty=True, name=container_name)
            print(f"创建fur容器组: {container_group}")
            
            # 将原始fur组作为子组放入容器组
            try:
                cmds.parent(original_fur_group, container_group)
                print(f"将 {original_fur_group} 放入容器组")
            except Exception as e:
                print(f"⚠️  无法将fur组放入容器组: {str(e)}")
                # 如果parenting失败，删除容器组并返回None
                cmds.delete(container_group)
                return None
            
            # 设置容器组的属性
            try:
                # 添加自定义属性标识这是fur缓存组
                cmds.addAttr(container_group, longName="fur_cache_group", dataType="string")
                cmds.setAttr(f"{container_group}.fur_cache_group", "fur_simulation_cache", type="string")
                
                # 设置组的显示颜色为白色
                cmds.setAttr(f"{container_group}.useOutlinerColor", 1)
                cmds.setAttr(f"{container_group}.outlinerColor", 1.0, 1.0, 1.0)  # 白色
                
                print(f"设置fur容器组属性完成")
            except Exception as e:
                print(f"⚠️  设置容器组属性失败: {str(e)}")
            
            return container_group
            
        except Exception as e:
            print(f"❌ 创建fur容器组失败: {str(e)}")
            return None