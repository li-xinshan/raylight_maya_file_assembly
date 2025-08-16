# Lookdev动画组装工具 v2.0

## 概述

这是一个Maya插件，用于自动化Lookdev和动画数据的组装过程。v2.0版本采用了全新的模块化架构，支持JSON配置文件，具备智能文件查找和路径推导功能。

## 主要特性

### v2.0 新功能
- **JSON配置系统**: 支持从JSON文件读取资产配置
- **智能文件查找**: 自动查找最新版本的Lookdev文件
- **相机路径推导**: 从动画文件路径智能推导相机文件路径
- **模块化架构**: 分离关注点，便于维护和扩展
- **版本管理**: 自动处理文件版本选择

### 核心功能
1. 自动导入Lookdev文件
2. 导入动画ABC缓存并连接到Lookdev几何体
3. 导入动画相机ABC并自动获取时间范围
4. 设置XGen毛发缓存路径
5. 材质检查和修复
6. 场景参数自动设置

## 文件结构

```
raylight_maya_file_assembly/
├── maya_assembler_v2.py        # 主插件文件（v2.0）
├── maya_assembler.py           # 原始插件文件
├── maya_assembler_v1_backup.py # v1.1备份
├── core_assembler.py           # 核心组装器
├── config_manager.py           # 配置管理模块
├── file_manager.py             # 文件管理模块
├── path_utils.py              # 路径工具模块
├── example_config.json        # 示例配置文件
├── test_new_system.py         # 测试脚本
└── README.md                  # 本文档
```

## 安装和使用

### 1. 安装插件

将所有Python文件复制到Maya的scripts目录或插件目录：

```python
# 在Maya Script Editor中运行
import sys
sys.path.append("path/to/raylight_maya_file_assembly")

# 导入并运行
from maya_assembler_v2 import show_lookdev_animation_setup_ui
show_lookdev_animation_setup_ui()
```

### 2. 配置文件格式

创建JSON配置文件，格式如下：

```json
[
    {
        "asset_name": "dwl",
        "asset_type": "chr",
        "asset_type_group_name": "character",
        "description": "角色：动物狼",
        "outputs": [
            "P:\\LHSN\\publish\\shot\\s310\\c0990\\element\\ani\\ani\\cache\\v002\\LHSN_s310_c0990_ani_ani_v002-chr_dwl_01.abc",
            "P:\\LHSN\\publish\\shot\\s310\\c0990\\element\\ani\\ani\\cache\\v002\\LHSN_s310_c0990_ani_ani_v002-chr_dwl_02.abc"
        ]
    }
]
```

### 3. 目录结构规范

#### Lookdev文件结构
```
P:\LHSN\assets\{asset_type}\{asset_name}\lookdev\maya\publish\
├── v001\
│   └── {asset_name}_lookdev_v001.ma
├── v002\
│   └── {asset_name}_lookdev_v002.ma
└── v003\
    └── {asset_name}_lookdev_v003.ma
```

#### 动画文件结构
```
P:\LHSN\publish\shot\{sequence}\{shot}\element\ani\ani\
├── cache\
│   └── v002\
│       ├── LHSN_{sequence}_{shot}_ani_ani_v002-{asset_type}_{asset_name}_01.abc
│       └── LHSN_{sequence}_{shot}_ani_ani_v002-{asset_type}_{asset_name}_02.abc
└── LHSN_{sequence}_{shot}_ani_cam_v002.abc
```

## 使用流程

### 方式一：使用JSON配置（推荐）

1. **准备配置文件**
   - 创建或使用现有的JSON配置文件
   - 确保文件路径和资产信息正确

2. **启动插件**
   ```python
   from maya_assembler_v2 import show_lookdev_animation_setup_ui
   show_lookdev_animation_setup_ui("path/to/config.json")
   ```

3. **选择资产**
   - 从资产下拉列表中选择要处理的资产
   - 系统会自动查找对应的文件

4. **执行组装**
   - 可以分步执行各个步骤
   - 或者点击"一键完成所有步骤"

### 方式二：传统模式

如果模块化组件不可用，系统会自动回退到传统模式：

1. **手动设置文件路径**
   - Lookdev文件路径
   - 动画ABC文件路径
   - 相机ABC文件路径

2. **执行组装步骤**

## 路径推导规则

### 相机路径推导

从动画文件路径：
```
P:\LHSN\publish\shot\s310\c0990\element\ani\ani\cache\v002\LHSN_s310_c0990_ani_ani_v002-chr_dwl_01.abc
```

推导出相机路径：
```
P:\LHSN\publish\shot\s310\c0990\element\ani\ani\LHSN_s310_c0990_ani_cam_v002.abc
```

规则：
1. 去掉 `cache/vXXX/` 部分
2. 将文件名中的 `ani_ani` 替换为 `ani_cam`
3. 去掉资产特定的后缀部分

### Lookdev路径生成

根据资产信息：
```
asset_name: "dwl"
asset_type: "chr"
```

生成路径：
```
P:\LHSN\assets\chr\dwl\lookdev\maya\publish\
```

## API 参考

### 核心类

#### `CoreAssembler`
主要的组装器类，集成了所有功能模块。

```python
from core_assembler import CoreAssembler

# 初始化
assembler = CoreAssembler("config.json")

# 设置当前资产
assembler.set_current_asset("dwl")

# 执行步骤
assembler.step1_import_lookdev()
assembler.step2_import_and_connect_animation_abc()
# ... 其他步骤

# 一键执行
assembler.execute_all_steps()
```

#### `ConfigManager`
配置文件管理类。

```python
from config_manager import ConfigManager

config = ConfigManager("config.json")
assets = config.get_assets_data()
lookdev_path = config.generate_lookdev_path("dwl", "chr")
```

#### `FileManager`
文件查找和版本管理类。

```python
from file_manager import FileManager

file_mgr = FileManager()
latest_file = file_mgr.get_latest_lookdev_file("/path/to/lookdev/dir")
```

#### `PathUtils`
路径工具类，处理路径推导和验证。

```python
from path_utils import PathUtils

path_utils = PathUtils()
camera_path = path_utils.derive_camera_path_from_animation(animation_file)
```

## 测试

运行测试脚本验证系统功能：

```bash
python test_new_system.py
```

## 故障排除

### 常见问题

1. **模块导入失败**
   - 检查文件路径是否正确
   - 确保所有模块文件都在Python路径中

2. **配置文件加载失败**
   - 检查JSON格式是否正确
   - 验证文件编码为UTF-8

3. **文件路径不匹配**
   - 检查目录结构是否符合规范
   - 验证文件命名约定

4. **相机路径推导错误**
   - 检查动画文件路径格式
   - 验证命名约定是否正确

### 日志和调试

- 插件会在Maya Script Editor中输出详细日志
- UI中的状态区域显示执行过程
- 可以导出执行报告用于分析

## 更新记录

### v2.0
- 全新模块化架构
- JSON配置系统
- 智能文件查找
- 相机路径推导
- 改进的UI和用户体验

### v1.1
- 基础的Lookdev动画组装功能
- 手动文件路径设置
- XGen毛发缓存支持

## 贡献

如需报告问题或提出改进建议，请联系开发团队。

## 许可

版权所有 © Maya Pipeline Team