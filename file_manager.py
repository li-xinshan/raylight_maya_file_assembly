"""
文件管理模块
处理lookdev文件查找和版本管理
"""

import os
import re
import glob


class FileManager:
    """文件管理类"""
    
    def __init__(self):
        """初始化文件管理器"""
        self.supported_extensions = ['.ma', '.mb']
        self.version_pattern = re.compile(r'v(\d+)')
    
    def find_lookdev_files(self, lookdev_dir):
        """
        在lookdev目录中查找Maya文件
        
        Args:
            lookdev_dir (str): lookdev目录路径
            
        Returns:
            list: 找到的Maya文件列表，按版本排序
        """
        print(f"🔍 FileManager.find_lookdev_files: 搜索目录 {lookdev_dir}")
        
        if not os.path.exists(lookdev_dir):
            print(f"❌ Lookdev目录不存在: {lookdev_dir}")
            return []
        
        maya_files = []
        
        # 列出目录内容
        try:
            dir_contents = os.listdir(lookdev_dir)
            print(f"📁 目录内容: {dir_contents}")
        except Exception as e:
            print(f"❌ 无法列出目录内容: {e}")
            return []
        
        # 查找所有版本目录
        version_dirs = []
        for item in dir_contents:
            item_path = os.path.join(lookdev_dir, item)
            if os.path.isdir(item_path):
                print(f"📂 检查子目录: {item}")
                if self.version_pattern.match(item):
                    version_dirs.append(item_path)
                    print(f"✅ 版本目录: {item}")
                else:
                    print(f"⚠️  非版本目录: {item}")
        
        print(f"📂 找到 {len(version_dirs)} 个版本目录")
        
        # 按版本号排序
        version_dirs.sort(key=self._extract_version_number, reverse=True)
        
        # 在每个版本目录中查找Maya文件
        for version_dir in version_dirs:
            version_name = os.path.basename(version_dir)
            print(f"🔍 搜索版本目录: {version_name}")
            
            try:
                version_contents = os.listdir(version_dir)
                print(f"  📄 {version_name}/ 内容: {version_contents}")
            except Exception as e:
                print(f"  ❌ 无法读取版本目录: {e}")
                continue
            
            for ext in self.supported_extensions:
                pattern = os.path.join(version_dir, f"*{ext}")
                files = glob.glob(pattern)
                print(f"  🔍 搜索模式 {pattern}: 找到 {len(files)} 个文件")
                
                for file_path in files:
                    file_info = {
                        'path': file_path,
                        'filename': os.path.basename(file_path),
                        'version': self._extract_version_number(version_dir),
                        'extension': ext,
                        'size': os.path.getsize(file_path) if os.path.exists(file_path) else 0
                    }
                    maya_files.append(file_info)
                    print(f"  ✅ 找到文件: {file_info['filename']} (版本: {file_info['version']})")
        
        # 按版本号降序排序（最新版本在前）
        maya_files.sort(key=lambda x: x['version'], reverse=True)
        
        print(f"📊 总共找到 {len(maya_files)} 个Maya文件")
        
        return maya_files
    
    def get_latest_lookdev_file(self, lookdev_dir):
        """
        获取最新的lookdev文件
        
        Args:
            lookdev_dir (str): lookdev目录路径
            
        Returns:
            str: 最新的lookdev文件路径，如果没有找到返回None
        """
        print(f"🔍 FileManager.get_latest_lookdev_file: 搜索目录 {lookdev_dir}")
        maya_files = self.find_lookdev_files(lookdev_dir)
        
        print(f"📁 找到 {len(maya_files)} 个Maya文件")
        
        if maya_files:
            latest_file = maya_files[0]['path']
            print(f"✅ 最新文件: {latest_file}")
            return latest_file
        else:
            print("❌ 未找到Maya文件")
        
        return None
    
    def get_lookdev_file_by_version(self, lookdev_dir, version):
        """
        获取指定版本的lookdev文件
        
        Args:
            lookdev_dir (str): lookdev目录路径
            version (int): 版本号
            
        Returns:
            str: 指定版本的lookdev文件路径，如果没有找到返回None
        """
        maya_files = self.find_lookdev_files(lookdev_dir)
        
        for file_info in maya_files:
            if file_info['version'] == version:
                return file_info['path']
        
        return None
    
    def find_camera_files(self, base_dir, pattern="*cam*.abc"):
        """
        在指定目录中查找相机文件
        
        Args:
            base_dir (str): 基础目录
            pattern (str): 文件匹配模式
            
        Returns:
            list: 找到的相机文件列表，按版本排序
        """
        if not os.path.exists(base_dir):
            print(f"目录不存在: {base_dir}")
            return []
        
        camera_files = []
        
        # 搜索相机文件
        search_pattern = os.path.join(base_dir, pattern)
        files = glob.glob(search_pattern)
        
        for file_path in files:
            if os.path.isfile(file_path):
                version = self._extract_version_from_filename(os.path.basename(file_path))
                file_info = {
                    'path': file_path,
                    'filename': os.path.basename(file_path),
                    'version': version,
                    'size': os.path.getsize(file_path)
                }
                camera_files.append(file_info)
        
        # 按版本号降序排序
        camera_files.sort(key=lambda x: x['version'] or 0, reverse=True)
        
        return camera_files
    
    def get_latest_camera_file(self, base_dir):
        """
        获取最新的相机文件
        
        Args:
            base_dir (str): 基础目录
            
        Returns:
            str: 最新的相机文件路径，如果没有找到返回None
        """
        camera_files = self.find_camera_files(base_dir)
        
        if camera_files:
            return camera_files[0]['path']
        
        return None
    
    def validate_file_exists(self, file_path):
        """
        验证文件是否存在
        
        Args:
            file_path (str): 文件路径
            
        Returns:
            dict: 验证结果
        """
        result = {
            'exists': False,
            'readable': False,
            'size': 0,
            'error': None
        }
        
        try:
            if file_path and os.path.exists(file_path):
                result['exists'] = True
                result['readable'] = os.access(file_path, os.R_OK)
                result['size'] = os.path.getsize(file_path)
            else:
                result['error'] = "文件不存在"
                
        except Exception as e:
            result['error'] = str(e)
        
        return result
    
    def get_file_info(self, file_path):
        """
        获取文件详细信息
        
        Args:
            file_path (str): 文件路径
            
        Returns:
            dict: 文件信息
        """
        info = {
            'path': file_path,
            'filename': os.path.basename(file_path) if file_path else '',
            'directory': os.path.dirname(file_path) if file_path else '',
            'extension': os.path.splitext(file_path)[1] if file_path else '',
            'exists': False,
            'size': 0,
            'version': None
        }
        
        if file_path and os.path.exists(file_path):
            info['exists'] = True
            info['size'] = os.path.getsize(file_path)
            info['version'] = self._extract_version_from_filename(info['filename'])
        
        return info
    
    def list_directory_contents(self, directory, file_filter=None):
        """
        列出目录内容
        
        Args:
            directory (str): 目录路径
            file_filter (str): 文件过滤模式（可选）
            
        Returns:
            dict: 目录内容信息
        """
        result = {
            'exists': False,
            'files': [],
            'directories': [],
            'total_files': 0,
            'total_size': 0
        }
        
        if not os.path.exists(directory):
            return result
        
        result['exists'] = True
        
        try:
            items = os.listdir(directory)
            
            for item in items:
                item_path = os.path.join(directory, item)
                
                if os.path.isfile(item_path):
                    if not file_filter or self._match_filter(item, file_filter):
                        file_size = os.path.getsize(item_path)
                        file_info = {
                            'name': item,
                            'path': item_path,
                            'size': file_size,
                            'version': self._extract_version_from_filename(item)
                        }
                        result['files'].append(file_info)
                        result['total_size'] += file_size
                
                elif os.path.isdir(item_path):
                    dir_info = {
                        'name': item,
                        'path': item_path,
                        'version': self._extract_version_number(item_path)
                    }
                    result['directories'].append(dir_info)
            
            result['total_files'] = len(result['files'])
            
            # 按版本号排序
            result['files'].sort(key=lambda x: x['version'] or 0, reverse=True)
            result['directories'].sort(key=lambda x: x['version'] or 0, reverse=True)
            
        except Exception as e:
            print(f"列出目录内容失败: {str(e)}")
        
        return result
    
    def _extract_version_number(self, path):
        """
        从路径中提取版本号
        
        Args:
            path (str): 文件或目录路径
            
        Returns:
            int: 版本号，如果没有找到返回0
        """
        basename = os.path.basename(path)
        match = self.version_pattern.search(basename)
        
        if match:
            return int(match.group(1))
        
        return 0
    
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
        match = re.search(r'_v(\d+)', filename)
        if match:
            return int(match.group(1))
        
        return None
    
    def _match_filter(self, filename, file_filter):
        """
        检查文件名是否匹配过滤条件
        
        Args:
            filename (str): 文件名
            file_filter (str): 过滤模式
            
        Returns:
            bool: 是否匹配
        """
        if not file_filter:
            return True
        
        # 简单的通配符匹配
        import fnmatch
        return fnmatch.fnmatch(filename.lower(), file_filter.lower())
    
    def create_backup(self, file_path, backup_dir=None):
        """
        创建文件备份
        
        Args:
            file_path (str): 要备份的文件路径
            backup_dir (str): 备份目录（可选）
            
        Returns:
            str: 备份文件路径，如果失败返回None
        """
        if not os.path.exists(file_path):
            return None
        
        try:
            if not backup_dir:
                backup_dir = os.path.join(os.path.dirname(file_path), 'backup')
            
            if not os.path.exists(backup_dir):
                os.makedirs(backup_dir)
            
            import shutil
            import datetime
            
            filename = os.path.basename(file_path)
            name, ext = os.path.splitext(filename)
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"{name}_backup_{timestamp}{ext}"
            backup_path = os.path.join(backup_dir, backup_filename)
            
            shutil.copy2(file_path, backup_path)
            print(f"文件已备份到: {backup_path}")
            
            return backup_path
            
        except Exception as e:
            print(f"创建备份失败: {str(e)}")
            return None