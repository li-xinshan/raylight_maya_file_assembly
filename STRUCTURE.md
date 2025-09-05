# 项目结构说明

## 目录结构

```
raylight_maya_file_assembly/
│
├── main.py                 # 主入口文件
├── maya_startup.py         # Maya启动脚本
├── test_import.py          # 导入测试脚本
│
├── ui/                     # UI界面模块
│   ├── __init__.py
│   ├── maya_assembler.py   # 主UI类
│   ├── ui_components.py    # UI组件创建
│   ├── ui_event_handlers.py # 事件处理
│   └── ui_utils.py         # UI工具函数
│
├── core/                   # 核心逻辑模块
│   ├── __init__.py
│   ├── core_assembler.py   # 核心组装器
│   └── assembly_coordinator.py # 组装协调器
│
├── managers/               # 功能管理器模块
│   ├── __init__.py
│   ├── lookdev_manager.py  # Lookdev管理
│   ├── animation_manager.py # 动画管理
│   ├── abc_importer.py     # ABC导入
│   ├── blendshape_manager.py # BlendShape管理
│   ├── scene_manager.py    # 场景管理
│   ├── material_manager.py # 材质管理
│   └── xgen_manager.py     # XGen管理
│
├── utils/                  # 工具模块
│   ├── __init__.py
│   ├── file_manager.py     # 文件管理
│   └── path_utils.py       # 路径工具
│
└── config/                 # 配置模块
    ├── __init__.py
    ├── config_manager.py   # 配置管理
    ├── example_config.json # 示例配置
    └── link_asset.json     # 资产配置

```

## 模块职责

### UI模块 (`ui/`)
- **maya_assembler.py**: 主UI窗口和界面逻辑
- **ui_components.py**: UI组件创建（按钮、输入框等）
- **ui_event_handlers.py**: 用户交互事件处理
- **ui_utils.py**: UI辅助工具（更新显示、对话框等）

### 核心模块 (`core/`)
- **core_assembler.py**: 核心调度逻辑，协调各个管理器
- **assembly_coordinator.py**: 组装流程协调，执行六个步骤

### 管理器模块 (`managers/`)
每个管理器负责特定功能：
- **lookdev_manager.py**: Lookdev文件导入和验证
- **animation_manager.py**: 动画、毛发、布料处理
- **abc_importer.py**: ABC文件导入和连接
- **blendshape_manager.py**: BlendShape创建和管理
- **scene_manager.py**: 场景设置和优化
- **material_manager.py**: 材质检查和修复
- **xgen_manager.py**: XGen毛发缓存管理

### 工具模块 (`utils/`)
- **file_manager.py**: 文件查找、版本管理
- **path_utils.py**: 路径推导、验证

### 配置模块 (`config/`)
- **config_manager.py**: JSON配置加载和管理
- 配置文件存储

## 使用方式

### 在Maya中启动

1. **方式1: 使用maya_startup.py**
```python
# 在Maya Script Editor中运行
execfile("/path/to/raylight_maya_file_assembly/maya_startup.py")
launch_tool()
```

2. **方式2: 使用main.py**
```python
import sys
sys.path.append("/path/to/raylight_maya_file_assembly")
from main import main
main()
```

3. **方式3: 直接导入UI**
```python
import sys
sys.path.append("/path/to/raylight_maya_file_assembly")
from ui.maya_assembler import show_lookdev_animation_setup_ui
show_lookdev_animation_setup_ui()
```

## 工作流程

1. **初始化**: 创建UI和核心组装器
2. **配置加载**: 从JSON文件加载资产配置
3. **资产选择**: 用户选择要处理的资产
4. **文件查找**: 自动查找相关文件
5. **执行组装**: 按六个步骤执行
   - 导入Lookdev
   - 导入动画ABC
   - 导入相机
   - 设置毛发缓存
   - 修复材质
   - 设置场景参数

## 优势

- **模块化设计**: 职责分离，易于维护
- **代码复用**: 通用功能抽取到工具模块
- **可扩展性**: 容易添加新功能
- **清晰结构**: 目录结构反映功能划分
- **独立测试**: 每个模块可独立测试