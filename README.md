# 智能定时提醒器

## 简介

**智能定时提醒器** 是一款基于 Python 和 PyQt5 开发的桌面定时任务管理软件。  
支持多种周期类型的定时提醒、关机、重启、锁定等操作，支持最小化到系统托盘，适合日常工作和生活中的定时任务自动化管理。

法定工作日、节假日调用接口：https://date.appworlds.cn/work?date=日期 不传日期默认为今天
参考地址：https://appworlds.cn/holiday/
---

## 主要功能

- 支持多种任务类型：提醒、关机、重启、锁定
- 支持多种周期：法定工作日、法定节假日、周末、每天、自定义、时间间隔
- 任务可启用/禁用、编辑、删除
- 最小化到系统托盘，后台静默运行
- 托盘菜单可还原窗口或退出程序
- 所有操作日志自动写入 `app.log` 文件，便于排查问题
- 支持设置提醒时间段：用户可以在任务中配置提醒的开始和结束时间，例如仅在每天的 8:00 到 20:00 之间提醒。

### 设置提醒时间段

在任务编辑对话框中，选择任务类型为"提醒"后，可以设置提醒的开始时间和结束时间。默认情况下，提醒时间段为每天的 8:00 到 20:00。用户可以根据需要调整这些时间。

## 自动重启功能

本程序支持在锁屏状态下自动重启计算机。为实现此功能，请确保已创建一个计划任务，具体步骤如下：

1. 打开“任务计划程序”。
2. 选择“创建任务”。
3. 在“常规”选项卡中：
   - 输入任务名称，例如“定时软件调用重启”。
   - 勾选“使用最高权限运行”。
   - 选择“无论用户是否登录都要运行”。
4. 在“触发器”选项卡中，可以不设置（因为程序会通过命令触发）。
5. 在“操作”选项卡中：
   - 新建操作，程序或脚本：`shutdown`
   - 添加参数：`/r /f /t 0`
   - 起始于：留空或 `C:\Windows\System32`
6. 在“条件”和“设置”选项卡中，确保没有限制任务运行的选项。

完成以上步骤后，程序将能够在锁屏状态下通过调用计划任务实现重启。
![image](https://github.com/user-attachments/assets/1b558d4f-5a41-4dd4-9811-3a4097302e7c)

![image](https://github.com/user-attachments/assets/04b71eb6-9d1a-4bf6-ae32-891397ade392)

---

## 环境要求

- Python 3.7 及以上
- Windows 10/11
- 依赖库见 requirements.txt

---

## 安装依赖

```bash
pip install -r requirements.txt
```

---

## 运行方式

```bash
python main.py
```

---

## 打包为 EXE（推荐 PyInstaller）

1. 确保 `output.ico`（或 long.png）图标文件与 main.py 同级目录
2. 打包命令（无命令行窗口）：

```bash
pyinstaller -F main.py --add-data "output.ico;." --noconsole
```

3. 打包后在 `dist` 目录下找到 `main.exe`，双击即可运行

---

## 使用说明

- 启动后，主界面可添加、编辑、删除定时任务
- 任务类型支持提醒、关机、重启、锁定
- 支持多种周期设置
- 关闭或最小化窗口时，程序会驻留在系统托盘
- 托盘图标右键菜单可还原窗口或退出程序
- 所有日志信息写入 `app.log` 文件
![image](https://github.com/user-attachments/assets/33843a11-bce1-47f5-919b-d9cbcff12848)
![image](https://github.com/user-attachments/assets/c591e35c-cd70-4970-82bb-85d98e65c7f2)
![image](https://github.com/user-attachments/assets/8daea369-bb5a-432b-8582-4d10bcce98ab)
![image](https://github.com/user-attachments/assets/7d3e3074-a504-40a8-89ff-027fe35b171b)

---

## 常见问题

- **托盘图标不显示**：请确保 output.ico 或 long.png 文件存在且为标准 32x32 像素图标
- **打包后无图标**：请参考上方打包命令，务必加上 `--add-data` 参数
- **程序无响应或报错**：请查看 `app.log` 日志文件，获取详细错误信息

---

## 许可

本项目仅供学习与交流，禁止用于商业用途。

---

如需进一步定制 README 或添加截图、FAQ 等内容，请告知！
