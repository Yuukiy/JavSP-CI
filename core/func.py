"""业务逻辑所需的或有一定通用性的函数"""
# 为了降低耦合度，也避免功能复杂后可能出现的循环导入的问题，这里尽量不导入项目内部的模块
# 如果需要获得配置信息，也应当由外部模块将配置项的值以参数的形式传入
import os
import re
import sys
import time
import logging
from datetime import datetime
from packaging import version
from tkinter import filedialog, Tk
from colorama import Fore, Style

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from web.base import *
from core.datatype import mei_path


__all__ = ['select_folder', 'get_scan_dir', 'remove_trail_actor_in_title',
           'shutdown', 'CLEAR_LINE', 'check_update']


CLEAR_LINE = '\r\x1b[K'
logger = logging.getLogger(__name__)


def select_folder(default_dir=''):
    """使用文件对话框提示用户选择一个文件夹"""
    window = Tk()
    window.withdraw()
    window.iconbitmap(mei_path('image/JavSP.ico'))
    path = filedialog.askdirectory(initialdir=default_dir)
    if path != '':
        return os.path.normpath(path)


def get_scan_dir(cfg_scan_dir):
    """综合命令参数、配置文件等信息，返回要扫描影片的文件夹"""
    # 目前config模块负责处理来自命令行和来自文件的配置，cfg_scan_dir已经是综合了这两处后得到的结果
    if cfg_scan_dir:
        if os.path.isdir(cfg_scan_dir):
            return cfg_scan_dir
        else:
            logger.error(f"配置的待整理文件夹无效：'{cfg_scan_dir}'")
    else:
        print('请选择要整理的文件夹：', end='')
        root = select_folder()
        print(root)
        return root


def remove_trail_actor_in_title(title:str, actors:list) -> str:
    """寻找并移除标题尾部的女优名"""
    # 目前使用分隔符白名单来做检测（担心按Unicode范围匹配误伤太多），考虑尽可能多的分隔符
    delimiters = '-xX &·,;　＆・，；'
    pattern = f"^(.*?)([{delimiters}]{{1,3}}({'|'.join(actors)}))+$"
    # 使用match而不是sub是为了将替换掉的部分写入日志
    match = re.match(pattern, title)
    if match:
        logger.debug(f"移除标题尾部的女优名: '{match.group(1)}'[{match.group(2)}]")
        return match.group(1)
    else:
        return title


def shutdown(timeout=120):
    """关闭计算机"""
    try:
        for i in reversed(range(timeout)):
            print(CLEAR_LINE + f"JavSP整理完成，将在 {i} 秒后关机。按'Ctrl+C'取消", end='')
            time.sleep(1)
        logger.info('整理完成，自动关机')
        #TODO: 当前仅支持Windows平台
        os.system('shutdown -s')
    except KeyboardInterrupt:
        return


def utc2local(utc_str):
    """将UTC时间转换为本地时间"""
    # python不支持 ISO-8601 中的Z后缀
    now = time.time()
    offset = datetime.fromtimestamp(now) - datetime.utcfromtimestamp(now)
    utc_str = utc_str.replace('Z', '+00:00')
    utc_time = datetime.fromisoformat(utc_str)
    local_time = utc_time + offset
    return local_time


def get_actual_width(mix_str: str) -> int:
    """给定一个中英混合的字符串，返回实际的显示宽度"""
    width = len(mix_str)
    for c in mix_str:
        if u'\u4e00' <= c <= u'\u9fa5':
            width += 1
    return width


def align_center(mix_str: str, total_width: int) -> str:
    """给定一个中英混合的字符串，根据其实际显示宽度中心对齐"""
    actual_width = get_actual_width(mix_str)
    add_space = int((total_width - actual_width) / 2)
    aligned_str = ' ' * add_space + mix_str
    return aligned_str


def check_update(allow_check=True):
    """检查版本更新"""

    def print_header(title, info=[]):
        title_width = max([get_actual_width(i) for i in title])
        if info:
            info_width = max([get_actual_width(i) for i in info])
        else:
            info_width = 0
        display_width = max(title_width, info_width) + 6
        print('=' * display_width)
        for line in title:
            print(align_center(line, display_width))
        if info:
            print('-' * display_width)
            for line in info:
                print(line)
        print('=' * display_width)
        print('')

    # 使用pyinstaller打包exe时生成hook，运行时由该hook将版本信息注入到sys中
    local_version = getattr(sys, 'javsp_version', None)
    if not local_version:
        return
    # 检查更新
    if allow_check:
        api_url = 'https://api.github.com/repos/Yuukiy/JavSP/releases/latest'
        release_url = 'https://github.com/Yuukiy/JavSP/releases/latest'
        print('正在检查更新...', end='')
        try:
            data = request_get(api_url, timeout=3).json()
            latest_version = data['tag_name']
            release_time = utc2local(data['published_at'])
            release_date = release_time.isoformat().split('T')[0]
            if version.parse(local_version) < version.parse(latest_version):
                update_status = 'new_version'
            else:
                update_status = 'already_latest'
        except Exception as e:
            logger.debug('检查版本更新时出错: ' + repr(e))
            update_status = 'fail_to_check'
    else:
        update_status = 'disallow'
    # 根据检查更新的情况输出软件版本信息和更新信息
    print(CLEAR_LINE, end='')
    if update_status == 'disallow':
        title = f'Jav Scraper Package: {local_version}'
        print_header([title])
    elif update_status == 'already_latest':
        title = f'Jav Scraper Package: {local_version} (已是最新版)'
        print_header([title])
    elif update_status == 'fail_to_check':
        titles = [f'Jav Scraper Package: {local_version}']
        info = ['检查更新失败，请前往以下地址查看最新版本:', '  '+release_url]
        print_header(titles, info)
    elif update_status == 'new_version':
        titles = [f'Jav Scraper Package: {local_version}']
        titles.append(f'↓ 有新版本可下载: {latest_version} ↓')
        titles.append(release_url)
        # 提取changelog消息
        try:
            lines = data['body'].split('\r\n')
            changelog = [f'更新时间: {release_date}']
            for line in lines:
                if line.startswith('## '):
                    changelog.append(Style.BRIGHT + line[3:] + Style.RESET_ALL)
                elif line.startswith('- '):
                    changelog.append(line)
            print_header(titles, changelog)
        except:
            print_header(titles)


if __name__ == "__main__":
    setattr(sys, 'javsp_version', 'v0')
    check_update()
