# GitHub Release 模板

这是一份可直接整理后发布到 GitHub Release 页面中的说明模板，内容已按当前版本更新。

## 建议版本标题

`v1.1.0 - Desktop Workflow Polish`

## 建议上传附件

- `WindowsLinuxFileBridge-OneFile.exe`
- `WindowsLinuxFileBridge.zip`

## 发布说明

Windows-Linux File Bridge 是一个面向 Windows 与 WSL Linux 文件交换场景的轻量桌面工具，提供双栏浏览、双向传输与常用文件管理能力，适合日常文档、资料、代码与项目文件在两个系统之间快速流转。

### 本版更新

- 全面升级主界面布局，增强桌面工具感
- 新增顶部状态卡，显示当前发行版、面板状态与最近结果
- 文件列表升级为列式视图，信息更清晰
- 增强右键菜单，支持重命名、打开所在位置、查看属性、新建文件夹、删除
- 修复右键新建文件夹在当前界面中的可用性问题
- 将历史记录改为独立“操作记录”二级窗口展示
- 支持失败记录直接重试
- 优化滚动条交互体验
- 优化二级弹窗打开位置，默认相对主窗口居中

### 当前包含能力

- Windows / Linux 双栏目录浏览
- 文件与文件夹双向传输
- 同名冲突自动重命名
- 搜索、排序、文件类型筛选
- 新建文件夹、删除、重命名、属性查看
- 历史记录与失败重试
- 直接运行的 Windows EXE 打包版本

### 推荐下载

日常使用优先推荐：

- `WindowsLinuxFileBridge-OneFile.exe`

### 说明

- 当前版本主要面向 Windows + WSL 使用场景
- 拖拽能力在安装 `tkinterdnd2` 后体验更完整
- 当前界面目标是轻量、直接、实用
