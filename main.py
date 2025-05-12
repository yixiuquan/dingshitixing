import sys
import requests
import os
import json
from datetime import datetime, timedelta, time as dtime
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTableWidget, QTableWidgetItem, QDialog, QLabel, QComboBox,
    QCheckBox, QFormLayout, QLineEdit, QTimeEdit, QMessageBox, QMenuBar, QAction, QHeaderView, QSpinBox,
    QSystemTrayIcon, QMenu
)
from PyQt5.QtCore import Qt, QTime, QTimer, pyqtSignal, QObject, QEvent
from PyQt5.QtGui import QIcon
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
import logging

CYCLE_TYPES = [
    '法定工作日', '法定节假日', '周末', '每天', '自定义', '时间间隔'
]

# 设置日志文件名和格式
logging.basicConfig(
    filename='app.log',  # 日志文件名
    level=logging.INFO,   # 记录INFO及以上级别日志
    format='%(asctime)s %(levelname)s: %(message)s'
)

def debug_log(msg):
    print(f'[DEBUG] {datetime.now().strftime("%Y-%m-%d %H:%M:%S")} {msg}')

def get_now_hms():
    now = datetime.now()
    return now.hour, now.minute, now.second

class CycleSelector(QWidget):
    """
    周期选择控件，支持六种周期类型，自定义和时间间隔时显示不同控件
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout()
        # 周期类型选择
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel('周期类型：'))
        self.type_combo = QComboBox()
        self.type_combo.addItems(CYCLE_TYPES)
        type_layout.addWidget(self.type_combo)
        layout.addLayout(type_layout)
        # 自定义星期选择
        self.week_layout = QHBoxLayout()
        self.checks = []
        self.days = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
        for day in self.days:
            cb = QCheckBox(day)
            self.week_layout.addWidget(cb)
            self.checks.append(cb)
        layout.addLayout(self.week_layout)
        # 时间选择区（用三个SpinBox）
        time_layout = QHBoxLayout()
        self.time_label = QLabel('时间：')
        time_layout.addWidget(self.time_label)
        self.hour_spin = QSpinBox()
        self.hour_spin.setRange(0, 23)
        self.hour_spin.setSuffix(' 时')
        self.minute_spin = QSpinBox()
        self.minute_spin.setRange(0, 59)
        self.minute_spin.setSuffix(' 分')
        self.second_spin = QSpinBox()
        self.second_spin.setRange(0, 59)
        self.second_spin.setSuffix(' 秒')
        # 默认值为当前时间
        h, m, s = get_now_hms()
        self.hour_spin.setValue(h)
        self.minute_spin.setValue(m)
        self.second_spin.setValue(s)
        time_layout.addWidget(self.hour_spin)
        time_layout.addWidget(self.minute_spin)
        time_layout.addWidget(self.second_spin)
        layout.addLayout(time_layout)
        # 时间间隔区（用三个SpinBox）
        self.interval_layout = QHBoxLayout()
        self.interval_label = QLabel('每隔：')
        self.interval_layout.addWidget(self.interval_label)
        self.interval_hour_spin = QSpinBox()
        self.interval_hour_spin.setRange(0, 23)
        self.interval_hour_spin.setSuffix(' 小时')
        self.interval_minute_spin = QSpinBox()
        self.interval_minute_spin.setRange(0, 59)
        self.interval_minute_spin.setSuffix(' 分钟')
        self.interval_second_spin = QSpinBox()
        self.interval_second_spin.setRange(0, 59)
        self.interval_second_spin.setSuffix(' 秒')
        self.interval_layout.addWidget(self.interval_hour_spin)
        self.interval_layout.addWidget(self.interval_minute_spin)
        self.interval_layout.addWidget(self.interval_second_spin)
        layout.addLayout(self.interval_layout)
        self.setLayout(layout)
        self.type_combo.currentIndexChanged.connect(self.update_week_check_visible)
        self.update_week_check_visible()
    def update_week_check_visible(self):
        ctype = self.type_combo.currentText()
        week_visible = ctype == '自定义'
        for cb in self.checks:
            cb.setVisible(week_visible)
        # 时间点控件
        time_visible = ctype != '时间间隔'
        self.time_label.setVisible(time_visible)
        self.hour_spin.setVisible(time_visible)
        self.minute_spin.setVisible(time_visible)
        self.second_spin.setVisible(time_visible)
        # 间隔控件
        interval_visible = ctype == '时间间隔'
        self.interval_label.setVisible(interval_visible)
        self.interval_hour_spin.setVisible(interval_visible)
        self.interval_minute_spin.setVisible(interval_visible)
        self.interval_second_spin.setVisible(interval_visible)
    def get_cycle_type(self):
        return self.type_combo.currentText()
    def get_selected_days(self):
        if self.get_cycle_type() != '自定义':
            return []
        return [i for i, cb in enumerate(self.checks) if cb.isChecked()]
    def get_time(self):
        # 返回 (hour, minute, second)
        return self.hour_spin.value(), self.minute_spin.value(), self.second_spin.value()
    def get_interval(self):
        # 返回 (hour, minute, second)
        return self.interval_hour_spin.value(), self.interval_minute_spin.value(), self.interval_second_spin.value()
    def set_cycle(self, cycle_type, days=None, time_str=None, interval_str=None):
        idx = CYCLE_TYPES.index(cycle_type)
        self.type_combo.setCurrentIndex(idx)
        if days and cycle_type == '自定义':
            for i, cb in enumerate(self.checks):
                cb.setChecked(i in days)
        if time_str and cycle_type != '时间间隔':
            parts = time_str.split(':')
            h = int(parts[0]) if len(parts) > 0 else 0
            m = int(parts[1]) if len(parts) > 1 else 0
            s = int(parts[2]) if len(parts) > 2 else 0
            self.hour_spin.setValue(h)
            self.minute_spin.setValue(m)
            self.second_spin.setValue(s)
        if interval_str and cycle_type == '时间间隔':
            parts = interval_str.split(':')
            h = int(parts[0]) if len(parts) > 0 else 0
            m = int(parts[1]) if len(parts) > 1 else 0
            s = int(parts[2]) if len(parts) > 2 else 0
            self.interval_hour_spin.setValue(h)
            self.interval_minute_spin.setValue(m)
            self.interval_second_spin.setValue(s)

class TaskDialog(QDialog):
    def __init__(self, parent=None, task=None):
        super().__init__(parent)
        self.setWindowTitle('任务编辑')
        self.resize(400, 300)
        layout = QVBoxLayout()
        form_layout = QFormLayout()
        self.name_edit = QLineEdit()
        self.type_combo = QComboBox()
        self.type_combo.addItems(['提醒', '关机', '重启', '锁定'])
        self.content_edit = QLineEdit()
        self.cycle_selector = CycleSelector()
        # 新增提醒时间段
        self.remind_start_edit = QTimeEdit()
        self.remind_start_edit.setDisplayFormat('HH:mm')
        self.remind_start_edit.setTime(QTime(8, 0))
        self.remind_end_edit = QTimeEdit()
        self.remind_end_edit.setDisplayFormat('HH:mm')
        self.remind_end_edit.setTime(QTime(20, 0))
        form_layout.addRow('任务名称：', self.name_edit)
        form_layout.addRow('类型：', self.type_combo)
        form_layout.addRow('提醒内容：', self.content_edit)
        form_layout.addRow('周期选择：', self.cycle_selector)
        self.remind_start_row = form_layout.rowCount()
        form_layout.addRow('提醒开始时间：', self.remind_start_edit)
        self.remind_end_row = form_layout.rowCount()
        form_layout.addRow('提醒结束时间：', self.remind_end_edit)
        layout.addLayout(form_layout)
        btn_layout = QHBoxLayout()
        self.btn_ok = QPushButton('确定')
        self.btn_cancel = QPushButton('取消')
        btn_layout.addWidget(self.btn_ok)
        btn_layout.addWidget(self.btn_cancel)
        layout.addLayout(btn_layout)
        self.setLayout(layout)
        self.btn_ok.clicked.connect(self.accept)
        self.btn_cancel.clicked.connect(self.reject)
        # 类型切换时显示/隐藏提醒时间段
        self.type_combo.currentTextChanged.connect(self.update_remind_time_visible)
        self.update_remind_time_visible()
        if task:
            self.name_edit.setText(task['name'])
            self.type_combo.setCurrentText(task['type'])
            self.content_edit.setText(task.get('content', ''))
            self.cycle_selector.set_cycle(
                task['cycle_type'],
                task.get('days', []),
                task.get('time', '00:00:00'),
                task.get('interval', '00:00:00')
            )
            # 仅提醒类型才填充时间段
            if task.get('type', '提醒') == '提醒':
                start = task.get('remind_start', '08:00')
                end = task.get('remind_end', '20:00')
                sh, sm = map(int, start.split(':'))
                eh, em = map(int, end.split(':'))
                self.remind_start_edit.setTime(QTime(sh, sm))
                self.remind_end_edit.setTime(QTime(eh, em))
        else:
            # 新建任务时，时间默认当前
            h, m, s = get_now_hms()
            self.cycle_selector.hour_spin.setValue(h)
            self.cycle_selector.minute_spin.setValue(m)
            self.cycle_selector.second_spin.setValue(s)
            self.remind_start_edit.setTime(QTime(8, 0))
            self.remind_end_edit.setTime(QTime(20, 0))
    def update_remind_time_visible(self):
        is_remind = self.type_combo.currentText() == '提醒'
        self.remind_start_edit.setVisible(is_remind)
        self.remind_end_edit.setVisible(is_remind)
        # 还要隐藏label
        form_layout = self.layout().itemAt(0).layout()
        form_layout.labelForField(self.remind_start_edit).setVisible(is_remind)
        form_layout.labelForField(self.remind_end_edit).setVisible(is_remind)
    def get_task(self):
        name = self.name_edit.text().strip()
        ttype = self.type_combo.currentText()
        content = self.content_edit.text().strip()
        cycle_type = self.cycle_selector.get_cycle_type()
        days = self.cycle_selector.get_selected_days()
        h, m, s = self.cycle_selector.get_time()
        time_str = f'{h:02d}:{m:02d}:{s:02d}'
        interval_h, interval_m, interval_s = self.cycle_selector.get_interval()
        interval_str = f'{interval_h:02d}:{interval_m:02d}:{interval_s:02d}'
        task = {
            'name': name,
            'type': ttype,
            'content': content,
            'cycle_type': cycle_type,
            'days': days,
            'time': time_str,
            'interval': interval_str
        }
        if ttype == '提醒':
            remind_start = self.remind_start_edit.time().toString('HH:mm')
            remind_end = self.remind_end_edit.time().toString('HH:mm')
            task['remind_start'] = remind_start
            task['remind_end'] = remind_end
        return task

class ReminderSignal(QObject):
    remind = pyqtSignal(dict)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('智能定时提醒器')
        self.setFixedSize(1500, 800)
        self.tasks = []  # 任务列表，存储为dict
        self.scheduler = BackgroundScheduler()
        self.scheduler.start()
        self.reminder_signal = ReminderSignal()
        self.reminder_signal.remind.connect(self.show_reminder)
        # 托盘图标及菜单
        icon_path = os.path.join(os.path.dirname(__file__), 'output.ico')
        logging.info(f"托盘图标路径：{icon_path}")
        logging.info(f"文件是否存在：{os.path.exists(icon_path)}")
        icon = QIcon(icon_path)
        self.setWindowIcon(icon)
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(icon)
        self.tray_menu = QMenu(self)
        self.restore_action = QAction('还原窗口', self)
        self.quit_action = QAction('退出程序', self)
        self.tray_menu.addAction(self.restore_action)
        self.tray_menu.addAction(self.quit_action)
        self.tray_icon.setContextMenu(self.tray_menu)
        self.tray_icon.activated.connect(self.on_tray_activated)
        self.restore_action.triggered.connect(self.showNormal)
        self.quit_action.triggered.connect(self.exit_app)
        self.tray_icon.show()
        # 菜单栏
        menubar = QMenuBar(self)
        task_menu = menubar.addMenu('菜单')
        self.action_add = QAction('新增', self)
        task_menu.addAction(self.action_add)
        self.setMenuBar(menubar)
        self.action_add.triggered.connect(self.on_add_clicked)
        # 主体布局
        central = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(0,0,0,0)
        layout.setSpacing(0)
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(['任务名称', '类型', '周期', '时间', '状态', '操作', ''])
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.table)
        central.setLayout(layout)
        self.setCentralWidget(central)
        self.load_tasks()
        self.refresh_table()
        # 定时刷新法定日任务（每天0点重载）
        self.daily_timer = QTimer(self)
        self.daily_timer.timeout.connect(self.reload_schedules)
        self.daily_timer.start(60*60*1000)  # 每小时检查一次

    def on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self.showNormal()
            self.activateWindow()

    def closeEvent(self, event):
        event.ignore()
        self.hide()
        self.tray_icon.showMessage('智能定时提醒器', '程序已最小化到系统托盘，双击托盘图标可还原窗口。', QSystemTrayIcon.Information, 2000)

    def changeEvent(self, event):
        if event.type() == QEvent.WindowStateChange:
            if self.isMinimized():
                QTimer.singleShot(0, self.hide)
        super().changeEvent(event)

    def exit_app(self):
        self.tray_icon.hide()
        QApplication.quit()

    def save_tasks(self):
        try:
            with open('tasks.json', 'w', encoding='utf-8') as f:
                json.dump(self.tasks, f, ensure_ascii=False, indent=2)
        except Exception as e:
            debug_log(f'保存任务失败: {e}')
    def load_tasks(self):
        try:
            if os.path.exists('tasks.json'):
                with open('tasks.json', 'r', encoding='utf-8') as f:
                    self.tasks = json.load(f)
        except Exception as e:
            debug_log(f'加载任务失败: {e}')
            self.tasks = []
    def refresh_table(self):
        self.table.setRowCount(len(self.tasks))
        for row, task in enumerate(self.tasks):
            days_str = ''
            if task['cycle_type'] == '自定义':
                days_str = ','.join([CycleSelector().days[i] for i in task['days']])
            elif task['cycle_type'] == '时间间隔':
                # 显示为"每隔X小时Y分钟Z秒"
                interval = task.get('interval', '00:00:00')
                h, m, s = interval.split(':')
                parts = []
                if int(h) > 0:
                    parts.append(f'{int(h)}小时')
                if int(m) > 0:
                    parts.append(f'{int(m)}分钟')
                if int(s) > 0:
                    parts.append(f'{int(s)}秒')
                days_str = '每隔' + ''.join(parts) if parts else '每隔1秒'
            else:
                days_str = task['cycle_type']
            self.table.setItem(row, 0, QTableWidgetItem(task['name']))
            self.table.setItem(row, 1, QTableWidgetItem(task['type']))
            self.table.setItem(row, 2, QTableWidgetItem(days_str))
            self.table.setItem(row, 3, QTableWidgetItem(task['time']))
            self.table.setItem(row, 4, QTableWidgetItem(task.get('status', '启用')))
            op_widget = QWidget()
            op_layout = QHBoxLayout()
            btn_edit = QPushButton('编辑')
            btn_delete = QPushButton('删除')
            btn_toggle = QPushButton('禁用' if task.get('status', '启用') == '启用' else '启用')
            btn_edit.clicked.connect(lambda _, r=row: self.on_edit_clicked(r))
            btn_delete.clicked.connect(lambda _, r=row: self.on_delete_clicked(r))
            btn_toggle.clicked.connect(lambda _, r=row: self.on_toggle_clicked(r))
            op_layout.addWidget(btn_edit)
            op_layout.addWidget(btn_delete)
            op_layout.addWidget(btn_toggle)
            op_layout.setContentsMargins(0, 0, 0, 0)
            op_widget.setLayout(op_layout)
            self.table.setCellWidget(row, 5, op_widget)
            self.table.setItem(row, 6, QTableWidgetItem(''))
        self.table.resizeColumnsToContents()
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.reload_schedules()
        self.save_tasks()
    def on_add_clicked(self):
        dlg = TaskDialog(self)
        if dlg.exec_() == QDialog.Accepted:
            task = dlg.get_task()
            if not task['name']:
                QMessageBox.warning(self, '提示', '任务名称不能为空！')
                return
            task['status'] = '启用'
            self.tasks.append(task)
            self.refresh_table()
    def on_edit_clicked(self, row):
        task = self.tasks[row]
        dlg = TaskDialog(self, task)
        if dlg.exec_() == QDialog.Accepted:
            new_task = dlg.get_task()
            if not new_task['name']:
                QMessageBox.warning(self, '提示', '任务名称不能为空！')
                return
            new_task['status'] = task['status']
            self.tasks[row] = new_task
            self.refresh_table()
    def on_delete_clicked(self, row):
        ret = QMessageBox.question(self, '确认删除', '确定要删除该任务吗？')
        if ret == QMessageBox.Yes:
            del self.tasks[row]
            self.refresh_table()
    def on_toggle_clicked(self, row):
        task = self.tasks[row]
        if task.get('status', '启用') == '启用':
            task['status'] = '禁用'
        else:
            task['status'] = '启用'
        self.tasks[row] = task
        self.refresh_table()
    def reload_schedules(self):
        self.scheduler.remove_all_jobs()
        for idx, task in enumerate(self.tasks):
            if task.get('status', '启用') != '启用':
                continue
            h, m, s = task['time'].split(':')
            hour = int(h) if len(h) > 0 else 0
            minute = int(m) if len(m) > 0 else 0
            second = int(s) if len(s) > 0 else 0
            interval_h, interval_m, interval_s = 0, 0, 0
            if 'interval' in task:
                try:
                    ih, im, isec = task['interval'].split(':')
                    interval_h = int(ih) if len(ih) > 0 else 0
                    interval_m = int(im) if len(im) > 0 else 0
                    interval_s = int(isec) if len(isec) > 0 else 0
                except Exception:
                    pass
            if task['cycle_type'] == '每天':
                trigger = CronTrigger(hour=hour, minute=minute, second=second)
                self.scheduler.add_job(self.trigger_task, trigger, args=[task], id=f'task_{idx}', replace_existing=True)
            elif task['cycle_type'] == '周末':
                trigger = CronTrigger(day_of_week='6,0', hour=hour, minute=minute, second=second)
                self.scheduler.add_job(self.trigger_task, trigger, args=[task], id=f'task_{idx}', replace_existing=True)
            elif task['cycle_type'] == '自定义':
                if not task['days']:
                    continue
                days_str = ','.join(str((i+1)%7) for i in task['days'])
                trigger = CronTrigger(day_of_week=days_str, hour=hour, minute=minute, second=second)
                self.scheduler.add_job(self.trigger_task, trigger, args=[task], id=f'task_{idx}', replace_existing=True)
            elif task['cycle_type'] in ('法定工作日', '法定节假日'):
                trigger = CronTrigger(hour=hour, minute=minute, second=second)
                self.scheduler.add_job(self.trigger_task, trigger, args=[task], id=f'task_{idx}', replace_existing=True)
            elif task['cycle_type'] == '时间间隔':
                if interval_h == 0 and interval_m == 0 and interval_s == 0:
                    continue
                trigger = IntervalTrigger(hours=interval_h, minutes=interval_m, seconds=interval_s)
                self.scheduler.add_job(self.trigger_task, trigger, args=[task], id=f'task_{idx}', replace_existing=True)
    def trigger_task(self, task):
        debug_log(f'调度触发：{task}')
        # 判断提醒时间段
        now = datetime.now().time()
        remind_start = task.get('remind_start', '00:00')
        remind_end = task.get('remind_end', '23:59')
        try:
            start_h, start_m = map(int, remind_start.split(':'))
            end_h, end_m = map(int, remind_end.split(':'))
            start_time = dtime(start_h, start_m)
            end_time = dtime(end_h, end_m)
            if not (start_time <= now <= end_time):
                debug_log(f'当前时间{now}不在提醒时间段{remind_start}-{remind_end}内，跳过提醒')
                return
        except Exception as e:
            debug_log(f'提醒时间段解析异常：{e}')
            # 出错时默认不限制
        if task['cycle_type'] in ('法定工作日', '法定节假日'):
            try:
                today = datetime.now().strftime('%Y-%m-%d')
                resp = requests.get(f'https://date.appworlds.cn/work?date={today}', timeout=5, verify=False)
                data = resp.json()
                if data.get('code') == 200:
                    is_work = data['data']['work']
                    if task['cycle_type'] == '法定工作日' and not is_work:
                        debug_log('今日不是法定工作日，跳过提醒')
                        return
                    if task['cycle_type'] == '法定节假日' and is_work:
                        debug_log('今日不是法定节假日，跳过提醒')
                        return
                else:
                    debug_log('法定日接口返回异常')
                    return
            except Exception as e:
                debug_log(f'法定日接口异常：{e}')
                return
        if task['type'] == '提醒':
            self.reminder_signal.remind.emit(task)
        elif task['type'] == '关机':
            os.system('shutdown /s /t 0')
        elif task['type'] == '重启':
            os.system('shutdown /r /t 0')
        elif task['type'] == '锁定':
            os.system('rundll32.exe user32.dll,LockWorkStation')
    def show_reminder(self, task):
        logging.info(f"弹窗提醒：{task}")
        def popup():
            title = f"提醒：{task['name']}"
            content = task.get('content', '') or '时间到了！'
            QMessageBox.information(None, title, content)
        QTimer.singleShot(0, popup)

def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main() 
