# Windows-Linux File Bridge

一个面向 Windows 和 WSL Linux 之间高频文件传输场景的桌面小工具。

它不是通用文件管理器，而是把最常见的跨系统资料传输、整理和简单管理做得更顺手、更安全。

## 功能

- Windows 和 Linux 双栏目录浏览
- 双向手动传输，支持文件和文件夹
- 同名冲突自动重命名，保留两份
- 搜索、排序、文件类型筛选
- 右键菜单：重命名、打开所在位置、查看属性、新建文件夹、删除
- 删除前二次确认
- 历史记录与失败重试
- 无控制台窗口启动

## 默认过滤规则

- `.lnk`、`.url` 快捷方式默认不显示，也不会参与传输
- `~$` 开头的 Office 临时文件默认隐藏
- `desktop.ini` 默认隐藏
- `文件夹` 筛选只显示目录
- `媒体文件`、`数据文件` 等具体类型筛选只显示匹配文件，不混入文件夹

## 界面细节

- 文件夹、压缩包、文档、图片、媒体、代码、安装文件有不同图标前缀
- 顶部可切换 WSL 发行版名称
- Linux 路径通过 `\\wsl$\发行版` 访问
- 默认发行版是 `Ubuntu-24.04`

## 运行方式

### 直接运行

双击 `start_gui.vbs`

### 命令行运行

```powershell
python wsl_file_bridge_gui.py
```

## 打包 EXE

仓库已提供 `PyInstaller` 打包脚本：

```powershell
build_exe.bat
```

当前常用打包产物有两种：

- 单文件版：`dist_pyinstaller_onefile\WindowsLinuxFileBridge-OneFile.exe`
- 目录版：`dist_pyinstaller\WindowsLinuxFileBridge\WindowsLinuxFileBridge.exe`

推荐优先使用单文件版，分发和测试更方便。

## 图标资源

- `assets/app_icon.ico`
- `assets/app_icon_preview.png`

## 项目文件

- `wsl_file_bridge_gui.py`：主程序
- `start_gui.vbs`：无黑窗启动器
- `build_exe.bat`：PyInstaller 打包脚本
- `DESIGN_PLAN.md`：设计规划

## 已知限制

- 拖拽功能依赖 `tkinterdnd2`，未安装时会自动降级
- 当前仍是 Tkinter 版本，界面偏轻量，不是完整资源管理器

## License

当前仓库还没有单独的许可证文件；如果需要开源发布，建议下一步补一个 `MIT` License。
