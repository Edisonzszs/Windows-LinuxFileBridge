# Windows-Linux File Bridge

一个面向 Windows 和 WSL Linux 高频文件传输场景的轻量桌面工具。
它不是通用文件管理器，而是把跨系统资料传输、整理和常用管理动作做得更直接、更安全。

## 功能

- Windows / Linux 双栏目录浏览
- 手动双向传输，支持文件和文件夹
- 同名冲突自动重命名，保留两份
- 搜索、排序、文件类型筛选
- 右键菜单：重命名、打开所在位置、查看属性、新建文件夹、删除
- 删除前二次确认
- 传输历史记录与失败重试
- 无控制台窗口启动

## 默认过滤规则

- `.lnk`、`.url` 快捷方式默认隐藏，也不会参与传输
- `~$` 开头的 Office 临时文件默认隐藏
- `desktop.ini` 默认隐藏
- `文件夹` 筛选仅显示目录
- `媒体文件`、`数据文件` 等具体类型筛选仅显示匹配文件，不混入文件夹

## 界面特点

- 文件夹、压缩包、文档、图片、媒体、代码、安装文件等带有不同图标前缀
- 顶部可切换 WSL 发行版名称
- Linux 路径通过 `\\wsl$\发行版名` 访问
- 默认发行版为 `Ubuntu-24.04`

## 运行方式

直接双击：

- `start_gui.vbs`

或在命令行运行：

```powershell
python wsl_file_bridge_gui.py
```

## 打包 EXE

仓库已提供 `PyInstaller` 打包脚本：

```powershell
build_exe.bat
```

当前常用打包产物：

- 单文件版：`dist_pyinstaller_onefile\WindowsLinuxFileBridge-OneFile.exe`
- 目录版：`dist_pyinstaller\WindowsLinuxFileBridge\WindowsLinuxFileBridge.exe`

推荐优先分发单文件版，测试和使用都更省事。

## 图标资源

- `assets/app_icon.ico`
- `assets/app_icon_preview.png`

## 项目结构

- `wsl_file_bridge_gui.py`：主程序
- `start_gui.vbs`：无黑窗启动器
- `build_exe.bat`：PyInstaller 打包脚本
- `DESIGN_PLAN.md`：设计规划
- `RELEASE_NOTES.md`：GitHub Release 说明模板

## 已知限制

- 拖拽能力依赖 `tkinterdnd2`，未安装时会自动降级
- 当前仍是 Tkinter 版本，界面偏轻量，不是完整资源管理器
- 主要面向 Windows + WSL 文件交换场景

## License

本项目采用 [MIT License](LICENSE)。
