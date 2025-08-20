"""
配置管理模块
处理JSON配置文件读取和路径生成
"""

import json
import os
import re
import glob
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed


class ConfigManager:
    """配置管理类"""
    
    def __init__(self, config_file=None):
        """
        初始化配置管理器
        
        Args:
            config_file (str): JSON配置文件路径
        """
        self.config_file = config_file
        self.assets_data = []
        self.base_paths = {
            'assets_root': 'P:\\LHSN\\assets',
            'publish_root': 'P:\\LHSN\\publish',
            'lookdev_template': '{assets_root}\\{asset_type}\\{asset_name}\\lookdev\\maya\\publish',
            'hair_cache_template': 'P:/LHSN/cache/dcc/shot/s310/c0990/cfx/alembic/hair/dwl_01/outcurve/cache_${DESC}.0001.abc'
        }
        
        # 项目扫描配置
        self.project_scan_config = {
            'scan_drives': ['P:', 'Q:', 'R:'],  # 要扫描的盘符
            'shot_pattern': r'shot[/\\](s\d+)[/\\](c\d+)',  # 场次和镜头匹配模式
            'animation_path_pattern': r'.*[/\\]element[/\\]ani[/\\]ani[/\\]cache[/\\](v\d+)[/\\].*\.(abc|ma)$',  # 动画文件路径模式
            'cfx_path_pattern': r'.*[/\\]cfx[/\\]alembic[/\\](hair|cloth)[/\\].*\.(abc|ma)$',  # CFX文件路径模式
            'max_workers': 4,  # 线程池大小
            'required_assets': ['chr', 'set', 'prp', 'env', 'prop'],  # 必需的资产类型（包含所有资产类型）
            'min_assets_per_shot': 1  # 每个镜头最少资产数量
        }
        
        if config_file and os.path.exists(config_file):
            self.load_config(config_file)
    
    def load_config(self, config_file):
        """
        加载JSON配置文件
        
        Args:
            config_file (str): JSON配置文件路径
            
        Returns:
            bool: 是否加载成功
        """
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                self.assets_data = json.load(f)
            
            print(f"成功加载配置文件: {config_file}")
            print(f"包含 {len(self.assets_data)} 个资产配置")
            
            return True
            
        except Exception as e:
            print(f"加载配置文件失败: {str(e)}")
            return False
    
    def get_assets_data(self):
        """
        获取所有资产数据
        
        Returns:
            list: 资产数据列表
        """
        return self.assets_data
    
    def generate_lookdev_path(self, asset_name, asset_type, asset_type_group_name=None):
        """
        生成lookdev文件路径
        
        Args:
            asset_name (str): 资产名称，如 'dwl'
            asset_type (str): 资产类型，如 'chr'
            asset_type_group_name (str): 资产类型组名称（可选）
            
        Returns:
            str: lookdev目录路径
        """
        lookdev_dir = self.base_paths['lookdev_template'].format(
            assets_root=self.base_paths['assets_root'],
            asset_type=asset_type,
            asset_name=asset_name
        )
        
        return lookdev_dir
    
    def extract_camera_path_from_animation(self, animation_abc_path):
        """
        从动画ABC路径推导相机ABC路径
        
        Args:
            animation_abc_path (str): 动画ABC文件路径
            
        Returns:
            str: 相机ABC文件路径，如果推导失败返回None
        """
        try:
            # 解析路径结构
            # 输入: P:\LHSN\publish\shot\s310\c0990\element\ani\ani\cache\v002\LHSN_s310_c0990_ani_ani_v002-chr_dwl_01.abc
            # 输出: P:\LHSN\publish\shot\s310\c0990\element\ani\ani\LHSN_s310_c0990_ani_cam_v002.abc
            
            # 标准化路径分隔符
            normalized_path = animation_abc_path.replace('\\', '/')
            
            # 获取目录路径，去掉最后的 cache/vXXX 部分
            # 找到cache目录的位置
            path_parts = normalized_path.split('/')
            cache_index = -1
            for i, part in enumerate(path_parts):
                if part == 'cache':
                    cache_index = i
                    break
            
            if cache_index > 0:
                # 重构基础目录路径（到cache之前）
                base_parts = path_parts[:cache_index]
                dir_path = '/'.join(base_parts)
            else:
                # 如果没有找到cache，使用父父目录
                dir_path = os.path.dirname(os.path.dirname(normalized_path)).replace('\\', '/')
            
            # 获取文件名并解析
            filename = os.path.basename(animation_abc_path)
            
            # 解析版本信息
            # LHSN_s310_c0990_ani_ani_v002-chr_dwl_01.abc
            # 提取基础名称和版本
            if '_v' in filename:
                base_part = filename.split('_v')[0]  # LHSN_s310_c0990_ani_ani
                version_part = filename.split('_v')[1].split('-')[0]  # 002
                
                # 构造相机文件名：将最后一个 ani 替换为 cam
                base_parts = base_part.split('_')
                if base_parts and base_parts[-1] == 'ani':
                    base_parts[-1] = 'cam'
                    camera_base = '_'.join(base_parts)
                    camera_filename = f"{camera_base}_v{version_part}.abc"
                else:
                    # 如果最后不是ani，直接添加cam
                    camera_filename = f"{base_part}_cam_v{version_part}.abc"
                
                camera_path = f"{dir_path}/{camera_filename}"
                
                # 转回Windows格式（如果需要）
                return camera_path.replace('/', '\\')
            
            return None
            
        except Exception as e:
            print(f"推导相机路径失败: {str(e)}")
            return None
    
    def get_asset_config(self, asset_name):
        """
        获取指定资产的配置
        
        Args:
            asset_name (str): 资产名称
            
        Returns:
            dict: 资产配置，如果不存在返回None
        """
        for asset in self.assets_data:
            if asset.get('asset_name') == asset_name:
                return asset
        return None
    
    def get_all_animation_files(self):
        """
        获取所有动画文件路径（包含ABC和Maya文件）
        
        Returns:
            list: 动画文件路径列表
        """
        animation_files = []
        for asset in self.assets_data:
            outputs = asset.get('outputs', [])
            for output_path in outputs:
                if output_path.endswith(('.abc', '.ma')):
                    animation_files.append(output_path)
        
        return animation_files
    
    def get_hair_cache_template(self):
        """
        获取毛发缓存模板路径
        
        Returns:
            str: 毛发缓存模板路径
        """
        return self.base_paths['hair_cache_template']
    
    def set_hair_cache_template(self, template):
        """
        设置毛发缓存模板路径
        
        Args:
            template (str): 毛发缓存模板路径
        """
        self.base_paths['hair_cache_template'] = template
    
    def validate_config(self):
        """
        验证配置数据的完整性
        
        Returns:
            dict: 验证结果
        """
        result = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        if not self.assets_data:
            result['valid'] = False
            result['errors'].append("配置数据为空")
            return result
        
        required_fields = ['asset_name', 'asset_type', 'outputs']
        
        for i, asset in enumerate(self.assets_data):
            asset_name = asset.get('asset_name', f'Asset_{i}')
            
            # 检查必需字段
            for field in required_fields:
                if field not in asset:
                    result['errors'].append(f"资产 {asset_name} 缺少必需字段: {field}")
                    result['valid'] = False
            
            # 检查outputs字段
            outputs = asset.get('outputs', [])
            if not outputs:
                result['warnings'].append(f"资产 {asset_name} 没有输出文件")
            else:
                for j, output_path in enumerate(outputs):
                    if not isinstance(output_path, str):
                        result['errors'].append(f"资产 {asset_name} 的输出路径 {j} 不是字符串")
                        result['valid'] = False
        
        return result
    
    def export_config(self, output_file):
        """
        导出配置到JSON文件
        
        Args:
            output_file (str): 输出文件路径
            
        Returns:
            bool: 是否导出成功
        """
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(self.assets_data, f, indent=4, ensure_ascii=False)
            
            print(f"配置文件已导出到: {output_file}")
            return True
            
        except Exception as e:
            print(f"导出配置文件失败: {str(e)}")
            return False
    
    def scan_project_animation_files(self, progress_callback=None):
        """
        扫描项目路径下的动画文件，按场次和镜头组织（多线程版本）
        
        Args:
            progress_callback (function): 进度回调函数，接收 (current, total, message) 参数
        
        Returns:
            dict: 按场次和镜头组织的动画文件信息
        """
        print("🔍 开始多线程扫描项目动画文件...")
        start_time = time.time()
        
        # 获取可用盘符
        available_drives = self._get_available_drives()
        if not available_drives:
            print("❌ 没有找到可用的扫描盘符")
            return {}
        
        print(f"🎯 发现可用盘符: {available_drives}")
        
        # 使用线程池扫描
        max_workers = self.project_scan_config['max_workers']
        all_shot_data = {}
        total_files = 0
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交扫描任务
            future_to_drive = {
                executor.submit(self._scan_single_drive, drive, progress_callback): drive 
                for drive in available_drives
            }
            
            completed = 0
            for future in as_completed(future_to_drive):
                drive = future_to_drive[future]
                completed += 1
                
                try:
                    drive_result = future.result()
                    if drive_result:
                        drive_shot_data, drive_files_count = drive_result
                        
                        # 合并结果
                        for shot_key, shot_data in drive_shot_data.items():
                            if shot_key not in all_shot_data:
                                all_shot_data[shot_key] = shot_data
                            else:
                                # 合并同一镜头的数据
                                all_shot_data[shot_key] = self._merge_shot_data(all_shot_data[shot_key], shot_data)
                        
                        total_files += drive_files_count
                        print(f"  ✅ 完成盘符 {drive}: {drive_files_count} 个文件")
                    else:
                        print(f"  ❌ 盘符 {drive} 扫描失败")
                        
                except Exception as e:
                    print(f"  ❌ 盘符 {drive} 扫描异常: {str(e)}")
                
                # 更新进度
                if progress_callback:
                    progress_callback(completed, len(available_drives), f"已完成 {completed}/{len(available_drives)} 个盘符扫描")
        
        # 后处理：版本过滤和资产完整性验证
        print("🔧 开始后处理...")
        processed_shot_data = self._post_process_shot_data(all_shot_data, total_files)
        
        # 只保留有完整资产的镜头
        complete_shots = self._filter_complete_shots(processed_shot_data)
        
        elapsed_time = time.time() - start_time
        print(f"⏱️  扫描完成，耗时 {elapsed_time:.2f} 秒")
        
        return complete_shots
    
    def get_shot_animation_files(self, sequence, shot, shot_data=None):
        """
        获取指定场次和镜头的动画文件
        
        Args:
            sequence (str): 场次，如 's310'
            shot (str): 镜头，如 'c0990'
            shot_data (dict): 已扫描的场次数据（可选，避免重复扫描）
            
        Returns:
            list: 动画文件信息列表
        """
        shot_key = f"{sequence}_{shot}"
        
        # 如果没有提供数据，则重新扫描
        if shot_data is None:
            shot_data = self.scan_project_animation_files()
        
        if shot_key in shot_data:
            return shot_data[shot_key]['animation_files']
        
        return []
    
    def create_config_from_shot_data(self, sequence, shot, selected_assets=None, shot_data=None):
        """
        从场次镜头数据创建配置
        
        Args:
            sequence (str): 场次
            shot (str): 镜头
            selected_assets (list): 选中的资产列表（可选）
            shot_data (dict): 已扫描的场次数据（可选，避免重复扫描）
            
        Returns:
            bool: 是否创建成功
        """
        try:
            animation_files = self.get_shot_animation_files(sequence, shot, shot_data)
            
            if not animation_files:
                print(f"未找到 {sequence}_{shot} 的动画文件")
                return False
            
            # 按资产组织文件
            assets_dict = {}
            for file_info in animation_files:
                asset_key = f"{file_info['asset_type']}_{file_info['asset_name']}"
                
                # 如果指定了选中资产，只处理选中的
                if selected_assets and asset_key not in selected_assets:
                    continue
                
                if asset_key not in assets_dict:
                    assets_dict[asset_key] = {
                        'asset_name': file_info['asset_name'],
                        'asset_type': file_info['asset_type'],
                        'asset_type_group_name': file_info['asset_type'],
                        'outputs': []
                    }
                
                assets_dict[asset_key]['outputs'].append(file_info['path'])
            
            # 转换为配置格式
            self.assets_data = list(assets_dict.values())
            
            # 按资产名称排序
            self.assets_data.sort(key=lambda x: x['asset_name'])
            
            print(f"✅ 已创建 {sequence}_{shot} 的配置，包含 {len(self.assets_data)} 个资产")
            
            return True
            
        except Exception as e:
            print(f"❌ 创建配置失败: {str(e)}")
            return False
    
    def _filter_latest_version_files(self, shot_data):
        """
        过滤出最新版本的动画文件
        
        Args:
            shot_data (dict): 场次镜头数据
            
        Returns:
            dict: 过滤后的场次镜头数据（只包含最新版本）
        """
        try:
            # 找到最新版本
            versions = shot_data.get('versions', set())
            if not versions:
                return shot_data
            
            # 解析版本号并排序
            version_numbers = []
            for version in versions:
                if version.startswith('v') and version[1:].isdigit():
                    version_numbers.append(int(version[1:]))
            
            if not version_numbers:
                return shot_data
            
            # 获取最新版本号
            latest_version_num = max(version_numbers)
            latest_version = f"v{latest_version_num:03d}"  # 格式化为v001, v002等
            
            print(f"    🔍 场次 {shot_data['display_name']}: 发现版本 {sorted(versions)}, 选择最新版本 {latest_version}")
            
            # 过滤出最新版本的文件
            latest_files = []
            for file_info in shot_data.get('animation_files', []):
                if file_info.get('version') == latest_version:
                    latest_files.append(file_info)
            
            # 更新数据
            filtered_shot_data = shot_data.copy()
            filtered_shot_data['animation_files'] = latest_files
            filtered_shot_data['versions'] = {latest_version}  # 只保留最新版本
            
            # 重新统计资产（基于最新版本的文件）
            assets = set()
            for file_info in latest_files:
                asset_type = file_info.get('asset_type', 'unknown')
                asset_name = file_info.get('asset_name', 'unknown')
                assets.add(f"{asset_type}_{asset_name}")
            
            filtered_shot_data['assets'] = assets
            
            print(f"    ✅ 过滤完成: {len(shot_data['animation_files'])} → {len(latest_files)} 个文件")
            
            return filtered_shot_data
            
        except Exception as e:
            print(f"    ❌ 过滤版本失败: {str(e)}")
            return shot_data
    
    def _get_available_drives(self):
        """获取可用的扫描盘符"""
        available_drives = []
        for drive in self.project_scan_config['scan_drives']:
            if os.path.exists(drive + '\\'):
                available_drives.append(drive)
        return available_drives
    
    def _scan_single_drive(self, drive, progress_callback=None):
        """扫描单个盘符"""
        try:
            print(f"  🔍 开始扫描盘符: {drive}")
            
            shot_data = {}
            files_count = 0
            
            # 编译正则表达式
            shot_pattern = re.compile(self.project_scan_config['shot_pattern'])
            animation_pattern = re.compile(self.project_scan_config['animation_path_pattern'])
            cfx_pattern = re.compile(self.project_scan_config['cfx_path_pattern'])
            
            # 扫描publish目录结构 - 动画文件
            publish_pattern = os.path.join(drive, '*', 'publish', 'shot', '*', '*', 'element', 'ani', 'ani', 'cache', '*', '*.abc')
            abc_files = glob.glob(publish_pattern)
            
            # 扫描cache目录结构 - CFX文件
            cfx_pattern_path = os.path.join(drive, '*', 'cache', 'dcc', 'shot', '*', '*', 'cfx', 'alembic', '*', '*', '*.abc')
            cfx_files = glob.glob(cfx_pattern_path)
            
            # 合并所有文件
            all_files = abc_files + cfx_files
            
            for file_path in all_files:
                # 标准化路径
                normalized_path = file_path.replace('\\', '/')
                
                # 匹配场次和镜头
                shot_match = shot_pattern.search(normalized_path)
                if not shot_match:
                    continue
                
                # 判断文件类型 - 动画文件或CFX文件
                is_animation = animation_pattern.match(file_path)
                is_cfx = cfx_pattern.match(file_path)
                
                if not is_animation and not is_cfx:
                    continue
                
                sequence = shot_match.group(1)  # s310
                shot = shot_match.group(2)      # c0990
                shot_key = f"{sequence}_{shot}"
                
                # 提取版本信息
                if is_animation:
                    version_match = re.search(r'[/\\](v\d+)[/\\]', normalized_path)
                    version = version_match.group(1) if version_match else 'unknown'
                else:  # CFX文件可能没有版本号，使用默认
                    version = 'v001'
                
                # 提取资产信息
                filename = os.path.basename(file_path)
                
                if is_animation:
                    # 动画文件: LHSN_s310_c0990_ani_ani_v002-chr_dwl_01.abc
                    asset_match = re.search(r'-(chr|prop|env|set|prp)_(\w+)_(\d+)\.(abc|ma)$', filename)
                    asset_type = asset_match.group(1) if asset_match else 'unknown'
                    asset_name = asset_match.group(2) if asset_match else 'unknown'  
                    asset_index = asset_match.group(3) if asset_match else '01'
                elif is_cfx:
                    # CFX文件: cache_dwl_01.abc 或类似格式
                    # 从路径中提取资产信息: /cfx/alembic/hair/dwl_01/
                    cfx_type_match = re.search(r'[/\\]cfx[/\\]alembic[/\\](hair|cloth)[/\\]', normalized_path)
                    cfx_asset_match = re.search(r'[/\\](chr_|)(\w+)_(\d+)[/\\]', normalized_path)
                    
                    if cfx_type_match and cfx_asset_match:
                        cfx_type = cfx_type_match.group(1)  # hair or cloth
                        asset_type = 'chr'  # CFX通常用于角色
                        asset_name = cfx_asset_match.group(2)  # dwl
                        asset_index = cfx_asset_match.group(3)  # 01
                    else:
                        asset_type = 'cfx'
                        asset_name = 'unknown'
                        asset_index = '01'
                
                # 组织数据
                if shot_key not in shot_data:
                    shot_data[shot_key] = {
                        'sequence': sequence,
                        'shot': shot,
                        'display_name': shot_key,
                        'animation_files': [],
                        'assets': set(),
                        'versions': set()
                    }
                
                # 添加文件信息
                file_info = {
                    'path': file_path,
                    'filename': filename,
                    'asset_type': asset_type,
                    'asset_name': asset_name,
                    'asset_index': asset_index,
                    'version': version,
                    'file_type': 'cfx' if is_cfx else 'animation',
                    'size': os.path.getsize(file_path) if os.path.exists(file_path) else 0
                }
                
                # 为CFX文件添加额外信息
                if is_cfx and 'cfx_type' in locals():
                    file_info['cfx_type'] = cfx_type  # hair 或 cloth
                
                shot_data[shot_key]['animation_files'].append(file_info)
                shot_data[shot_key]['assets'].add(f"{asset_type}_{asset_name}")
                shot_data[shot_key]['versions'].add(version)
                files_count += 1
            
            return shot_data, files_count
            
        except Exception as e:
            print(f"    ❌ 扫描盘符 {drive} 失败: {str(e)}")
            return None
    
    def _merge_shot_data(self, data1, data2):
        """合并两个镜头数据"""
        try:
            merged = data1.copy()
            merged['animation_files'].extend(data2['animation_files'])
            merged['assets'].update(data2['assets'])
            merged['versions'].update(data2['versions'])
            return merged
        except Exception as e:
            print(f"    ❌ 合并镜头数据失败: {str(e)}")
            return data1
    
    def _post_process_shot_data(self, shot_data, total_files):
        """后处理镜头数据"""
        print("  📋 版本过滤和数据整理...")
        
        # 处理每个场次镜头的数据
        for shot_key in shot_data:
            # 只保留最新版本的动画文件
            shot_data[shot_key] = self._filter_latest_version_files(shot_data[shot_key])
            
            # 转换set为sorted list
            shot_data[shot_key]['assets'] = sorted(list(shot_data[shot_key]['assets']))
            shot_data[shot_key]['versions'] = sorted(list(shot_data[shot_key]['versions']))
            
            # 按文件名排序
            shot_data[shot_key]['animation_files'].sort(key=lambda x: x['filename'])
        
        # 重新计算过滤后的文件总数
        filtered_total_files = sum(len(data['animation_files']) for data in shot_data.values())
        
        print(f"  📊 版本过滤: {total_files} → {filtered_total_files} 个动画文件（只保留最新版本）")
        
        return shot_data
    
    def _filter_complete_shots(self, shot_data):
        """过滤出有完整资产的镜头"""
        print("  🎯 过滤完整资产镜头...")
        
        complete_shots = {}
        required_assets = self.project_scan_config['required_assets']
        min_assets = self.project_scan_config['min_assets_per_shot']
        
        for shot_key, data in shot_data.items():
            assets = data.get('assets', [])
            
            # 检查是否有必需的资产类型
            has_required_assets = False
            for asset in assets:
                asset_type = asset.split('_')[0]  # chr_dwl → chr
                if asset_type in required_assets:
                    has_required_assets = True
                    break
            
            # 检查资产数量
            has_enough_assets = len(assets) >= min_assets
            
            if has_required_assets and has_enough_assets:
                complete_shots[shot_key] = data
                print(f"    ✅ {shot_key}: {len(assets)}个资产 {assets}")
            else:
                print(f"    ❌ {shot_key}: 资产不完整 ({len(assets)}个资产, 需要{required_assets}类型)")
        
        print(f"  🎯 完整镜头过滤: {len(shot_data)} → {len(complete_shots)} 个镜头")
        
        # 显示最终统计信息
        if complete_shots:
            print("📊 完整镜头统计:")
            for shot_key, data in sorted(complete_shots.items())[:10]:  # 显示前10个
                asset_count = len(data['assets'])
                file_count = len(data['animation_files'])
                versions = ', '.join(data['versions'])
                print(f"  {shot_key}: {file_count}文件, {asset_count}资产, 版本[{versions}]")
            
            if len(complete_shots) > 10:
                print(f"  ... 还有 {len(complete_shots) - 10} 个完整镜头")
        
        return complete_shots


def create_example_config():
    """
    创建示例配置数据
    
    Returns:
        list: 示例配置数据
    """
    example_data = [
        {
            "asset_name": "dwl",
            "asset_type": "chr",
            "asset_type_group_name": "character",
            "outputs": [
                "P:\\LHSN\\publish\\shot\\s310\\c0990\\element\\ani\\ani\\cache\\v002\\LHSN_s310_c0990_ani_ani_v002-chr_dwl_01.abc",
                "P:\\LHSN\\publish\\shot\\s310\\c0990\\element\\ani\\ani\\cache\\v002\\LHSN_s310_c0990_ani_ani_v002-chr_dwl_02.abc"
            ]
        },
        {
            "asset_name": "prop01",
            "asset_type": "prop",
            "asset_type_group_name": "props",
            "outputs": [
                "P:\\LHSN\\publish\\shot\\s310\\c0990\\element\\ani\\ani\\cache\\v002\\LHSN_s310_c0990_ani_ani_v002-prop_prop01_01.abc"
            ]
        }
    ]
    
    return example_data