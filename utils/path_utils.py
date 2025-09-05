"""
路径工具模块
处理相机路径推导和文件匹配
"""

import os
import re
import glob


class PathUtils:
    """路径工具类"""
    
    def __init__(self):
        """初始化路径工具"""
        # 常用的路径模式
        self.path_patterns = {
            'shot_animation': r'.*[/\\]shot[/\\](\w+)[/\\](\w+)[/\\]element[/\\]ani[/\\]ani[/\\]cache[/\\](v\d+)[/\\].*\.abc$',
            'camera_pattern': r'.*_cam_v(\d+)\.abc$',
            'version_pattern': r'v(\d+)',
            'asset_pattern': r'.*-(\w+)_(\w+)_(\d+)\.abc$'
        }
        
        self.compiled_patterns = {
            name: re.compile(pattern, re.IGNORECASE) 
            for name, pattern in self.path_patterns.items()
        }
    
    def extract_shot_info_from_animation_path(self, animation_path):
        """
        从动画路径中提取镜头信息
        
        Args:
            animation_path (str): 动画ABC文件路径
            
        Returns:
            dict: 镜头信息 {shot: str, sequence: str, version: str, base_dir: str}
        """
        result = {
            'shot': None,
            'sequence': None, 
            'version': None,
            'base_dir': None,
            'valid': False
        }
        
        try:
            # 标准化路径分隔符
            normalized_path = animation_path.replace('\\', '/')
            
            # 匹配镜头动画路径模式
            match = self.compiled_patterns['shot_animation'].match(normalized_path)
            
            if match:
                result['sequence'] = match.group(1)  # s310
                result['shot'] = match.group(2)      # c0990
                result['version'] = match.group(3)   # v002
                result['valid'] = True
                
                # 构建基础目录路径（去掉cache/vXXX部分）
                # 从 .../element/ani/ani/cache/v002/... 变成 .../element/ani/ani/
                parts = normalized_path.split('/')
                cache_index = -1
                for i, part in enumerate(parts):
                    if part == 'cache':
                        cache_index = i
                        break
                
                if cache_index > 0:
                    result['base_dir'] = '/'.join(parts[:cache_index])
                    
        except Exception as e:
            print(f"提取镜头信息失败: {str(e)}")
        
        return result
    
    def derive_camera_path_from_animation(self, animation_path):
        """
        从动画路径推导相机路径
        
        Args:
            animation_path (str): 动画ABC文件路径
            
        Returns:
            str: 相机ABC文件路径，如果推导失败返回None
        """
        try:
            print(f"\n   📐 推导相机路径...")
            shot_info = self.extract_shot_info_from_animation_path(animation_path)
            
            if not shot_info['valid']:
                print(f"      ❌ 无法从动画路径提取镜头信息")
                return None
            
            # 显示完整的路径结构
            print(f"      动画完整路径: {animation_path}")
            print(f"      基础目录(去掉cache/vXXX): {shot_info['base_dir']}")
            
            # 构建相机文件名模式
            # 从动画: .../element/ani/ani/cache/v002/LHSN_s310_c0990_ani_ani_v002-chr_dwl_01.abc
            # 到相机: .../element/ani/ani/LHSN_s310_c0990_ani_cam_v002.abc
            
            animation_filename = os.path.basename(animation_path)
            print(f"      动画文件名: {animation_filename}")
            
            # 解析动画文件名
            if '_v' in animation_filename:
                base_name_part = animation_filename.split('_v')[0]  # LHSN_s310_c0990_ani_ani
                version_with_suffix = animation_filename.split('_v')[1]  # 002-chr_dwl_01.abc
                
                # 提取版本号（处理可能有或没有后缀的情况）
                if '-' in version_with_suffix:
                    version_part = version_with_suffix.split('-')[0]  # 002
                else:
                    version_part = version_with_suffix.split('.')[0]  # 002 (从002.abc中提取)
                
                print(f"      基础名称部分: {base_name_part}")
                print(f"      版本部分: {version_part}")
                
                # 替换 ani 为 cam
                base_parts = base_name_part.split('_')
                print(f"      名称段: {base_parts}")
                
                if len(base_parts) >= 5 and base_parts[-1] == 'ani':
                    base_parts[-1] = 'cam'
                    camera_base_name = '_'.join(base_parts)
                    camera_filename = f"{camera_base_name}_v{version_part}.abc"
                    
                    print(f"      相机文件名: {camera_filename}")
                    
                    # 构建完整的相机路径 - 相机在动画文件的上两层目录
                    # 动画文件路径: .../element/ani/ani/cache/v002/LHSN_xxx_ani_ani_v002-chr_dwl_01.abc
                    # 相机文件路径: .../element/ani/ani/LHSN_xxx_ani_cam_v002.abc
                    # shot_info['base_dir'] 已经是 .../element/ani/ani/ 
                    # 所以相机路径就是 base_dir + camera_filename
                    camera_path = os.path.join(shot_info['base_dir'], camera_filename)
                    
                    # 标准化路径分隔符（转回Windows格式）
                    camera_path = camera_path.replace('/', '\\')
                    
                    print(f"      推导的完整路径: {camera_path}")
                    return camera_path
                else:
                    print(f"      ❌ 文件名格式不符合预期 (需要以'ani'结尾)")
            else:
                print(f"      ❌ 文件名中没有版本号标记 '_v'")
            
            return None
            
        except Exception as e:
            print(f"      ❌ 推导相机路径失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return None
    
    def find_camera_files_in_directory(self, directory, shot_info=None):
        """
        在目录中查找相机文件
        
        Args:
            directory (str): 搜索目录
            shot_info (dict): 镜头信息（可选，用于更精确的匹配）
            
        Returns:
            list: 找到的相机文件列表
        """
        if not os.path.exists(directory):
            return []
        
        camera_files = []
        
        # 搜索模式
        patterns = ['*cam*.abc', '*camera*.abc', '*CAM*.abc']
        
        for pattern in patterns:
            search_pattern = os.path.join(directory, pattern)
            files = glob.glob(search_pattern)
            
            for file_path in files:
                if os.path.isfile(file_path):
                    file_info = self._analyze_camera_file(file_path, shot_info)
                    if file_info:
                        camera_files.append(file_info)
        
        # 按版本号和匹配度排序
        camera_files.sort(key=lambda x: (x.get('match_score', 0), x.get('version', 0)), reverse=True)
        
        return camera_files
    
    def get_best_camera_file(self, animation_path):
        """
        根据动画路径找到最匹配的相机文件
        
        Args:
            animation_path (str): 动画ABC文件路径
            
        Returns:
            str: 最佳匹配的相机文件路径，如果没有找到返回None
        """
        print(f"\n🔍 开始查找相机文件")
        print(f"   动画路径: {animation_path}")
        
        # 首先尝试标准推导
        derived_camera_path = self.derive_camera_path_from_animation(animation_path)
        
        if derived_camera_path:
            print(f"   推导的相机路径: {derived_camera_path}")
            if os.path.exists(derived_camera_path):
                print(f"   ✅ 找到推导的相机文件: {derived_camera_path}")
                return derived_camera_path
            else:
                print(f"   ❌ 推导的相机文件不存在")
        else:
            print(f"   ❌ 无法从动画路径推导相机路径")
        
        # 如果推导的路径不存在，在目录中搜索
        shot_info = self.extract_shot_info_from_animation_path(animation_path)
        print(f"   镜头信息: sequence={shot_info.get('sequence')}, shot={shot_info.get('shot')}, version={shot_info.get('version')}")
        
        if shot_info['valid'] and shot_info['base_dir']:
            search_dir = shot_info['base_dir'].replace('/', '\\')
            print(f"   搜索目录: {search_dir}")
            
            if os.path.exists(search_dir):
                print(f"   ✅ 搜索目录存在")
                
                # 列出目录内容
                try:
                    dir_contents = os.listdir(search_dir)
                    abc_files = [f for f in dir_contents if f.endswith('.abc')]
                    print(f"   目录中的ABC文件: {abc_files}")
                except Exception as e:
                    print(f"   ❌ 无法列出目录内容: {e}")
                
                camera_files = self.find_camera_files_in_directory(search_dir, shot_info)
                
                if camera_files:
                    best_camera = camera_files[0]
                    print(f"   ✅ 找到最匹配的相机文件: {best_camera['path']}")
                    print(f"      匹配分数: {best_camera.get('match_score', 0)}")
                    return best_camera['path']
                else:
                    print(f"   ❌ 在搜索目录中未找到相机文件")
            else:
                print(f"   ❌ 搜索目录不存在: {search_dir}")
        else:
            print(f"   ❌ 镜头信息无效或基础目录为空")
        
        print(f"   ❌ 未找到与动画文件匹配的相机文件")
        return None
    
    def _analyze_camera_file(self, file_path, shot_info=None):
        """
        分析相机文件信息
        
        Args:
            file_path (str): 相机文件路径
            shot_info (dict): 镜头信息（可选）
            
        Returns:
            dict: 相机文件信息
        """
        filename = os.path.basename(file_path)
        
        file_info = {
            'path': file_path,
            'filename': filename,
            'version': self._extract_version_from_filename(filename),
            'match_score': 0,
            'size': os.path.getsize(file_path) if os.path.exists(file_path) else 0
        }
        
        # 计算匹配度
        if shot_info:
            score = 0
            
            # 检查镜头和序列信息
            if shot_info.get('sequence') and shot_info['sequence'] in filename:
                score += 10
            
            if shot_info.get('shot') and shot_info['shot'] in filename:
                score += 10
            
            if shot_info.get('version'):
                file_version = file_info['version']
                target_version = int(shot_info['version'][1:])  # 去掉 'v' 前缀
                
                if file_version == target_version:
                    score += 20  # 版本完全匹配
                elif file_version and abs(file_version - target_version) <= 1:
                    score += 10  # 版本接近
            
            # 检查是否包含cam关键字
            if 'cam' in filename.lower():
                score += 5
            
            file_info['match_score'] = score
        
        return file_info
    
    def _extract_version_from_filename(self, filename):
        """
        从文件名中提取版本号
        
        Args:
            filename (str): 文件名
            
        Returns:
            int: 版本号，如果没有找到返回None
        """
        if not filename:
            return None
        
        # 匹配 v001, v002 等模式
        match = re.search(r'_v(\d+)', filename, re.IGNORECASE)
        if match:
            return int(match.group(1))
        
        return None
    
    def validate_file_structure(self, animation_path, expected_camera_path=None):
        """
        验证文件结构的完整性
        
        Args:
            animation_path (str): 动画文件路径
            expected_camera_path (str): 期望的相机文件路径（可选）
            
        Returns:
            dict: 验证结果
        """
        result = {
            'valid': False,
            'animation_exists': False,
            'camera_exists': False,
            'camera_path': None,
            'errors': [],
            'warnings': []
        }
        
        # 检查动画文件
        if animation_path and os.path.exists(animation_path):
            result['animation_exists'] = True
        else:
            result['errors'].append(f"动画文件不存在: {animation_path}")
        
        # 检查或查找相机文件
        camera_path = expected_camera_path
        if not camera_path:
            camera_path = self.get_best_camera_file(animation_path)
        
        if camera_path:
            result['camera_path'] = camera_path
            if os.path.exists(camera_path):
                result['camera_exists'] = True
            else:
                result['errors'].append(f"相机文件不存在: {camera_path}")
        else:
            result['warnings'].append("未找到匹配的相机文件")
        
        # 提取镜头信息
        shot_info = self.extract_shot_info_from_animation_path(animation_path)
        if not shot_info['valid']:
            result['errors'].append("无法从动画路径提取镜头信息")
        
        result['valid'] = (result['animation_exists'] and 
                          result['camera_exists'] and 
                          len(result['errors']) == 0)
        
        return result
