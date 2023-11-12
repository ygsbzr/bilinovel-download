# coding:utf-8
from PyQt5.QtCore import Qt, pyqtSignal, QObject, QThread, QRegExp
from PyQt5.QtGui import QIcon, QFont, QTextCursor, QPixmap, QColor,QRegExpValidator
from PyQt5.QtWidgets import QApplication, QFrame, QGridLayout, QFileDialog
from qfluentwidgets import (setTheme, Theme, PushSettingCard, SettingCardGroup, ExpandLayout, TextEdit, ImageLabel, LineEdit, PushButton, Theme,
                            ProgressRing, setTheme, Theme, OptionsSettingCard, OptionsConfigItem, OptionsValidator, FluentWindow, SubtitleLabel, NavigationItemPosition, setThemeColor, qconfig)
from qfluentwidgets import FluentIcon as FIF
import sys
import base64
import shutil
from resource.logo import logo_base64
from resource.book import book_base64
from bilinovel import *

font_label = QFont('微软雅黑', 18)
font_msg = QFont('微软雅黑', 11)

class MainThread(QThread):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        
    def run(self):
        try:
            self.parent.clear_signal.emit('')
            print('正在获取书籍信息....')
            volume = self.parent.editer.get_index_url()
            print(self.parent.editer.title + '-' + volume['name'], self.parent.editer.author)
            print('****************************')
            if not self.parent.editer.is_buffer():
                print('正在下载文本....')
                volume = self.parent.editer.check_volume(volume, is_gui=True, signal=self.parent.hang_signal, editline=self.parent.editline_hang)
                self.parent.editer.get_text(volume)
                self.parent.editer.buffer(volume)
            else:
                print('检测到文本文件，直接下载插图')
                volume = self.parent.editer.buffer(volume)
            
            print('正在下载插图....')
            self.parent.editer.get_image(is_gui=True, signal=self.parent.progressring_signal)

            print('正在编辑元数据....')
            self.parent.editer.get_cover(is_gui=True, signal = self.parent.cover_signal)
            self.parent.editer.get_toc(volume)
            self.parent.editer.get_content(volume)
            self.parent.editer.get_epub_head()

            print('正在生成电子书....')
            epub_file = self.parent.editer.get_epub(volume)
            self.parent.clear_signal.emit('')
            print('生成成功！')
            print(f'电子书路径【{epub_file}】')

            self.parent.end_signal.emit('')
        except Exception as e:
            self.parent.end_signal.emit('')
            print('错误，请检查网络情况或确认输入是否正确')
            print('错误信息：')
            print(e)

class EmittingStr(QObject):
    textWritten = pyqtSignal(str)  # 定义一个发送str的信号
    def write(self, text):
        self.textWritten.emit(str(text))
    def flush(self):
        pass
    def isatty(self):
        pass

class SettingWidget(QFrame):
    def __init__(self, text: str, parent=None):
        super().__init__(parent=parent)

        self.parent = parent
        self.expandLayout = ExpandLayout(self)
        self.setObjectName(text.replace(' ', '-'))
        self.setting_group = SettingCardGroup(self.tr("下载设置"), self)
        
        self.download_path_card = PushSettingCard(
            self.tr('选择文件夹'),
            FIF.DOWNLOAD,
            self.tr("下载目录"),
            self.parent.out_path,
            self.setting_group
        )
        self.themeMode = OptionsConfigItem(
        None, "ThemeMode", Theme.DARK, OptionsValidator(Theme), None)

        self.theme_card = OptionsSettingCard(
            self.themeMode,
            FIF.BRUSH,
            self.tr('应用主题'),
            self.tr("更改外观"),
            texts=[
                self.tr('亮'), self.tr('暗'),
                self.tr('跟随系统设置')
            ],
            parent=self.parent
        )

        self.setting_group.addSettingCard(self.download_path_card)
        self.setting_group.addSettingCard(self.theme_card)
        self.expandLayout.setSpacing(28)
        self.expandLayout.setContentsMargins(20, 10, 20, 0)
        self.expandLayout.addWidget(self.setting_group)

        self.download_path_card.clicked.connect(self.download_path_changed)
        self.theme_card.optionChanged.connect(self.theme_changed)

    def download_path_changed(self):
        """ download folder card clicked slot """
        self.parent.out_path = QFileDialog.getExistingDirectory(
            self, self.tr("Choose folder"), self.parent.out_path)
        self.download_path_card.contentLabel.setText(self.parent.out_path)
    
    def theme_changed(self):
        theme_name = self.theme_card.choiceLabel.text()
        self.parent.set_theme(theme_name)


            

class HomeWidget(QFrame):

    progressring_signal = pyqtSignal(object) 
    end_signal = pyqtSignal(object) 
    hang_signal = pyqtSignal(object)
    clear_signal = pyqtSignal(object)
    cover_signal = pyqtSignal(object)

    def __init__(self, text: str, parent=None):
        super().__init__(parent=parent)
        self.setObjectName(text)
        self.parent = parent
        self.label_book = SubtitleLabel('书号：', self)
        self.label_volumn = SubtitleLabel('卷号：', self)
        self.editline_book = LineEdit(self) 
        self.editline_volumn = LineEdit(self) 
        validator = QRegExpValidator(QRegExp("\\d+"))  # 正则表达式匹配阿拉伯数字
        self.editline_book.setValidator(validator)
        self.editline_volumn.setValidator(validator)

        self.editline_book.setMaxLength(4)
        self.editline_volumn.setMaxLength(2)
        
        # self.editline_book.setText('2059')
        # self.editline_volumn.setText('3')
        
        self.book_icon = QPixmap()
        self.book_icon.loadFromData(base64.b64decode(book_base64))
        self.cover_w, self.cover_h = 110, 160

        self.label_cover = ImageLabel(self.book_icon, self)
        self.label_cover.setFixedSize(self.cover_w, self.cover_h)

        self.text_screen = TextEdit()
        self.text_screen.setReadOnly(True)
        self.text_screen.setFixedHeight(self.cover_h)

        self.progressRing = ProgressRing(self)
        self.progressRing.setValue(0)
        self.progressRing.setTextVisible(True)
        self.progressRing.setFixedSize(60, 60)
        
        self.btn_run = PushButton('开始下载', self)
        self.btn_run.setShortcut(Qt.Key_Return)
        self.btn_stop = PushButton('取消', self)
        self.btn_hang = PushButton('确定', self)
        
        self.editline_hang = LineEdit(self)
        self.gridLayout = QGridLayout(self)
        self.screen_layout = QGridLayout()
        self.btn_layout = QGridLayout()
        self.hang_layout = QGridLayout()
        
        self.label_book.setFont(font_label)
        self.label_volumn.setFont(font_label)
        self.editline_book.setFont(font_label)
        self.editline_volumn.setFont(font_label)
        self.text_screen.setFont(font_msg)
        self.editline_hang.setFont(font_msg)

        self.gridLayout.addWidget(self.editline_book, 0, 1)
        self.gridLayout.addWidget(self.editline_volumn, 1, 1)
        self.gridLayout.addWidget(self.label_book, 0, 0)
        self.gridLayout.addWidget(self.label_volumn, 1, 0)

        self.gridLayout.addLayout(self.btn_layout, 2, 1, 1, 1)
        self.btn_layout.addWidget(self.btn_run, 2, 1)
        self.btn_layout.addWidget(self.btn_stop, 2, 2)

        self.gridLayout.addLayout(self.screen_layout, 3, 0, 2, 2)

        self.screen_layout.addWidget(self.text_screen, 0, 0)
        self.screen_layout.addWidget(self.label_cover, 0, 1)
        self.screen_layout.addWidget(self.progressRing, 0, 2)

        self.gridLayout.addLayout(self.hang_layout, 5, 0, 1, 2)
        self.hang_layout.addWidget(self.editline_hang, 0, 0)
        self.hang_layout.addWidget(self.btn_hang, 0, 1)

        self.screen_layout.setContentsMargins(0,0,0,0)
        self.btn_layout.setContentsMargins(0,0,0,0)
        self.gridLayout.setContentsMargins(20, 10, 20, 10)

        self.btn_run.clicked.connect(self.process_start)
        self.btn_stop.clicked.connect(self.process_stop)
        self.btn_hang.clicked.connect(self.process_continue)

        self.progressring_signal.connect(self.progressring_msg)
        self.end_signal.connect(self.process_end)
        self.hang_signal.connect(self.process_hang)
        self.clear_signal.connect(self.clear_screen)
        self.cover_signal.connect(self.display_cover)

        self.progressRing.hide()
        self.btn_hang.hide()
        self.editline_hang.hide()
        self.btn_stop.setEnabled(False)
        
        sys.stdout = EmittingStr(textWritten=self.outputWritten)
        sys.stderr = EmittingStr(textWritten=self.outputWritten)
        self.text_screen.setText(self.parent.welcome_text) 
        if os.path.exists('./config'):
            shutil.rmtree('./config')
    
    def process_start(self):
        self.label_cover.setImage(self.book_icon)
        self.label_cover.setFixedSize(self.cover_w, self.cover_h)
        self.btn_run.setEnabled(False)
        self.btn_run.setText('正在下载')
        self.btn_stop.setEnabled(True)
        self.clear_signal.emit('')
        book_no = self.editline_book.text()
        volumn_no = self.editline_volumn.text()
        if len(book_no)==0 or len(volumn_no)==0 or int(volumn_no)<1:
            print('请检查输入是否完整正确！')
            self.end_signal.emit('')
            return
        try:
            self.editer = Editer(root_path=self.parent.out_path, head=self.parent.head, book_no=book_no, volume_no=int(volumn_no))
        except Exception as e:
            print(e)
            self.end_signal.emit('')
            return
        self.main_thread = MainThread(self)
        self.main_thread.start()
        
    def process_end(self, input=None):
        self.btn_run.setEnabled(True)
        self.btn_run.setText('开始下载')
        self.btn_run.setShortcut(Qt.Key_Return)
        self.btn_stop.setEnabled(False)
        self.progressRing.hide()
        self.btn_hang.hide()
        self.editline_hang.clear()
        self.editline_hang.hide()
        if input=='refresh':
            self.label_cover.setImage(self.book_icon)
            self.label_cover.setFixedSize(self.cover_w, self.cover_h)
            self.clear_signal.emit('')
            self.text_screen.setText(self.parent.welcome_text) 
        
    def outputWritten(self, text):
        cursor = self.text_screen.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertText(text)
        self.text_screen.setTextCursor(cursor)
        self.text_screen.ensureCursorVisible()
    
    def clear_screen(self):
        self.text_screen.clear()
    
    def display_cover(self, filepath):
        self.label_cover.setImage(filepath)
        self.label_cover.setFixedSize(self.cover_w, self.cover_h)
        
    def progressring_msg(self, input):
        if input == 'start':
            self.progressRing.setValue(0)
            self.progressRing.show()
        elif input == 'end':
            self.progressRing.hide()
        else:
            self.progressRing.setValue(input)
    
    def process_hang(self, input=None):
        self.btn_hang.setEnabled(True)
        self.btn_hang.setShortcut(Qt.Key_Return)
        self.btn_hang.show()
        self.editline_hang.show()
    
    def process_continue(self, input=None):
        self.editer.hang_flag=False
        self.btn_hang.hide()
        self.btn_hang.setEnabled(False)
        self.editline_hang.hide()
    
    def process_stop(self):
        self.main_thread.terminate()
        self.end_signal.emit('refresh')
        
        
    

class Window(FluentWindow):
    def __init__(self):
        super().__init__()

        self.out_path = os.path.join(os.path.expanduser('~'), 'Downloads')
        self.head = 'https://www.bilinovel.com'
        self.welcome_text = f'    搜索小说请登录哔哩轻小说手机版{self.head}，查询后请根据书籍网址输入书号，并根据需要输入下载的卷号（卷号是按照网页的顺序，非实际出版顺序）。\n    例如小说网址是{self.head}/novel/2704.html，要下载第二卷，则书号输入2704，卷号输入2。\n    书号最多输入4位阿拉伯数字，卷号最多输入2位阿拉伯数字。'
        self.homeInterface = HomeWidget('Home Interface', self)
        self.settingInterface = SettingWidget('Setting Interface', self)
        self.initNavigation()
        self.initWindow()
        
    def initNavigation(self):
        self.addSubInterface(self.homeInterface, FIF.HOME, '主界面')
        self.addSubInterface(self.settingInterface, FIF.SETTING, '设置', NavigationItemPosition.BOTTOM)

    def initWindow(self):
        self.resize(600, 355)
        pixmap = QPixmap()
        pixmap.loadFromData(base64.b64decode(logo_base64))
        self.setWindowIcon(QIcon(pixmap))
        self.setWindowTitle('哔哩轻小说EPUB下载器')
        self.setFont(font_label)

        desktop = QApplication.desktop().availableGeometry()
        w, h = desktop.width(), desktop.height()
        self.move(w//2 - self.width()//2, h//2 - self.height()//2)
    
    def set_theme(self, mode=None):
        if mode=='亮':
            setTheme(Theme.LIGHT)
        elif mode=='暗':
            setTheme(Theme.DARK)
        elif mode=='跟随系统设置':
            setTheme(Theme.AUTO)
        theme = qconfig.theme
        if theme == Theme.DARK:
            self.homeInterface.label_book.setTextColor(QColor(255,255,255))
            self.homeInterface.label_volumn.setTextColor(QColor(255,255,255))
        elif theme == Theme.LIGHT:
            self.homeInterface.label_book.setTextColor(QColor(0,0,0))
            self.homeInterface.label_volumn.setTextColor(QColor(0,0,0))


    
if __name__ == '__main__':
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)

    setTheme(Theme.DARK)
    setThemeColor('#FF7233')
    app = QApplication(sys.argv)
    w = Window()
    w.show()
    app.exec_()
