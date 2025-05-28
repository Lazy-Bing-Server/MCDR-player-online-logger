PLUGIN_METADATA = {
    "id": "cute_log",
    "version": "1.1.0",
    "name": "Cute Log && Parser",
    "author": "xinbing",
    "dependencies": {}
}


from mcdreforged.api.all import *
import os
import re
import time
from datetime import datetime

# 可修改变量开始
DEBUG = False
PREFIX = "!!log"
LIST_PREFIX = "list"
# 可修改变量结束
'''
Command-Tree
!!log <command>
        |-- list : 列出所有可操作玩家列表
        |-- <player_name>  <fliter(可选)> : 解析玩家数据 | 不使用过滤器时解析数据总览
                            |-- <fliter> : 过滤器, 限整数类型
                                |-- <fliter>  value <=100 : 列出最后 <fliter> 条登录记录
                                |-- <fliter>  value  >100 : 以YYYYMMDD(如20250401)格式解析, 只统计该日期后的数据总览
'''


# Cute Logger Start
# 存储每个玩家的登录时间
active_sessions = {}
def write_cute_log(player_name: str, join_time: float, leave_time: float):
    duration = leave_time - join_time
    # 格式化时间
    join_time_str = datetime.fromtimestamp(join_time).strftime('%Y-%m-%d %H:%M:%S')
    leave_time_str = datetime.fromtimestamp(leave_time).strftime('%Y-%m-%d %H:%M:%S')
    time_now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    hours = int(duration // 3600)
    minutes = int((duration % 3600) // 60)
    seconds = int(duration % 60)
    duration_str = f"{hours}h {minutes}m {seconds}s"

    # 写入日志
    log_line = f"[{time_now}] | 登录时间: {join_time_str}, 登出时间: {leave_time_str}, 在线时长: {duration_str}\n"

    file_path = os.path.join(LOG_FILE_PATH, f"{player_name}.log")
    print(f"Cute_Log | DEBUG | Writing log to {file_path} | {log_line}") if DEBUG else None
    try:
        with open(file_path, "a+", encoding="utf-8") as f:
            f.write(log_line)
    except:
        pass


@new_thread('session_logger')
def on_player_joined(server: PluginServerInterface, player: str, info: Info):
    # 记录玩家登录时刻
    active_sessions[player] = time.time()
    print(f'Cute_Log | INFO | {player} joined at {active_sessions[player]}') if DEBUG else None


@new_thread('session_logger')
def on_player_left(server: PluginServerInterface, player: str):
    leave_time = time.time()
    print(f'Cute_Log | INFO | {player} left at {leave_time}') if DEBUG else None

    join_time = active_sessions.pop(player, None)
    if join_time:
        write_cute_log(player, join_time, leave_time)
# Cute Logger End

# Cute Log Parser Start
# 正则在线时长到秒
def parse_duration(duration_str):
    hours = minutes = seconds = 0
    h_match = re.search(r'(\d+)h', duration_str)
    m_match = re.search(r'(\d+)m', duration_str)
    s_match = re.search(r'(\d+)s', duration_str)
    if h_match:
        hours = int(h_match.group(1))
    if m_match:
        minutes = int(m_match.group(1))
    if s_match:
        seconds = int(s_match.group(1))
    return hours * 3600 + minutes * 60 + seconds


# 格式化在线时长
def format_duration(seconds):
    hours = seconds // 3600
    seconds %= 3600
    minutes = seconds // 60
    seconds %= 60
    return f"{hours}h {minutes}m {seconds}s"


# 统计数据
def process_login_file(file_path, date_filter=None):
    file_name = os.path.splitext(os.path.basename(file_path))[0]
    
    total_duration = 0
    login_count = 0
    earliest_login = None
    latest_login = None
    
    # 解析 date_filter
    filter_date = None
    if date_filter:
        try:
            filter_date = datetime.strptime(str(date_filter), '%Y%m%d').replace(hour=0, minute=0, second=0, microsecond=0)
        except ValueError:
            return f"§c错误§r: §c无效的日期格式 {date_filter}§r, 应为 §eYYYYMMDD§r"
    
    with open(file_path, 'r', encoding='utf-8') as file:
        for line in file:
            # 提取登录时间和在线时长
            login_match = re.search(r'登录时间: (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', line)
            duration_match = re.search(r'在线时长: (\d+h \d+m \d+s)', line)
            
            if login_match and duration_match:
                login_time = datetime.strptime(login_match.group(1), '%Y-%m-%d %H:%M:%S')
                
                # 筛选满足日期过滤器
                if filter_date and login_time.date() < filter_date.date():
                    continue
                
                # 更新统计数据
                duration = parse_duration(duration_match.group(1))
                total_duration += duration
                login_count += 1
                
                # 更新最早和最晚登录时间
                if earliest_login is None or login_time < earliest_login:
                    earliest_login = login_time
                if latest_login is None or login_time > latest_login:
                    latest_login = login_time
    
    # 获取当前日期
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_str = today.strftime('%Y年%m月%d日')

    # 如果没有符合条件的数据
    if login_count == 0:
        return [
            f"----- 玩家 §a{file_name}§r 的统计数据 -----\n", 
            f"数据范围: §b{filter_date.strftime('%Y年%m月%d日') if filter_date else '文件开始'}§r ~ §b{today_str}§r\n", 
            f"无符合条件的登录记录"]

    # 使用 filter_date 作为最早日期（如有）, 否则使用文件中的最早登录时间
    earliest_date_str = filter_date.strftime('%Y年%m月%d日') if filter_date else earliest_login.strftime('%Y年%m月%d日')
    latest_login_str = latest_login.strftime('%Y年%m月%d日 %H:%M:%S') if latest_login else '无记录'
    total_duration_str = format_duration(total_duration)

    output = [
        f"----- 玩家 §a{file_name}§r 的统计数据 -----\n", 
        f"数据范围: §b{earliest_date_str}§r ~ §b{today_str}§r\n", 
        f"总登录次数: §b{login_count}§r   总在线时间: §b{total_duration_str}§r\n", 
        f"最后一次登录: §e{latest_login_str}§r"]
    
    return output


# 查询最后 <fliter> 次登录记录
def list_last_logins(file_path, filter_count):
    player_name = os.path.splitext(os.path.basename(file_path))[0]

    # 获取玩家日志数据
    login_records = []
    with open(file_path, 'r', encoding='utf-8') as file:
        for line in file:
            login_match = re.search(r'登录时间: (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', line)
            duration_match = re.search(r'在线时长: (\d+h \d+m \d+s)', line)

            if login_match and duration_match:
                login_time = datetime.strptime(login_match.group(1), '%Y-%m-%d %H:%M:%S')
                login_records.append((login_time, duration_match.group(1)))

    # 数据排序, 取最后 <fliter> 次记录
    login_records.sort(key=lambda x: x[0], reverse=True)
    last_logins = login_records[:filter_count]

    # 计算数据总览
    total_duration = sum(parse_duration(record[1]) for record in login_records)
    last_duration = sum(parse_duration(record[1]) for record in last_logins)

    # 格式化输出 | 无数据
    if not login_records:
        return [
            f"-----   §c悲报§r   -----", 
            f"  玩家 §a{player_name}§r 找不到任何记录, 无法与您互动"]

    #有数据
    output = [f"----- 玩家 §a{player_name}§r 的最后 §b{len(last_logins)}§r 次登录记录 -----"]
    for i, (login_time, duration) in enumerate(last_logins, 1):
        if len(str(i)) < len(str(len(last_logins))):
            i = (len(str(len(last_logins))) - len(str(i)))*'0' + str(i)

        output.append(f"  §e{i}§r - {login_time.strftime('%Y年 §b%m月 %d日§r §e%H§r:§e%M§r:%S')}, 在线时长: §b{duration}§r")
    output.append(f"最近 §e{len(last_logins)}§r 次登录, 在线时间和:  §e{format_duration(last_duration)}§r")
    output.append(f"总登录次数: §b{len(login_records)}§r,  总在线时间: §b{format_duration(total_duration)}§r")

    return output


# 查询可操作目标与最后更新时间
def get_file_info():
    # 写入表头
    file_info_list, temp_info_list = [], []
    file_info_list.append("-----  可查询玩家列表  -----")
    file_info_list.append("-- §a玩家名称§r --- §b日志§r更新§e时间§r --")

    # 遍历路径下的所有文件
    for entry in os.listdir(LOG_FILE_PATH):
        full_path = os.path.join(LOG_FILE_PATH, entry)

        if os.path.isfile(full_path):
            # 排除空文件
            if os.path.getsize(full_path) > 0:

                file_name = os.path.splitext(entry)[0]
                mtime = os.path.getmtime(full_path)
                last_modified = datetime.fromtimestamp(mtime).strftime('%Y年 §b%m月 %d日§r §e%H:%M§r:%S')

                temp_info_list.append(f'{file_name} - {last_modified}')

    # 以最长玩家名为基准, 计算空格数量
    max_length = 3+ max(len(item.split(' - ')[0]) for item in temp_info_list) if temp_info_list else 0

    # 格式化输出,按照最后修改时间排序
    for item in sorted(temp_info_list):
        file_name, last_modified = item.split(' - ')
        space_count = max_length - len(file_name)
        space = ' ' * space_count

        file_info_list.append(f"  §a{file_name}§r{space}{last_modified}")

    return file_info_list


# 帮助信息
def show_help_msg():
    return [
        "可爱日志解析器使用说明: \n", 
        "0. 输入 §6!!log list§r 来列出所有可查询玩家\n", 
        "", 
        "1. 输入 §6!!log§r §a<player_name>§r 查询一名玩家的日志数据\n", 
        "   例: §6!!log§r §axinbing§r : 输出玩家 §axinbing§r 的数据总览\n", 
        "", 
        "2. (可选) 命令后可添加过滤器 §e<filter>§r, 过滤器只能输入整数", 
        "   例: §6!!log§r §a<player_name>§r §e<filter>§r", 
        "   过滤器有两种用法, 详情如下: \n", 
        "", 
        "3. 当 §e<filter>§r 值§b<=100§r 时, 将输出玩家最后 §exx§r 次登录记录\n", 
        "   例: §6!!log§r §axinbing§r §e10§r : 输出玩家 §axinbing§r 最后 §e10§r 次登录记录\n", 
        "", 
        "4. 当 §e<filter>§r 值 §b>100§r 时, 将被解析为§e日期§r", 
        "   解析格式为YYYYMMDD(如20250401), 将作为数据总览的§e统计起始日期§r\n", 
        "   例: §6!!log§r §axinbing§r §e20250401§r : 查询玩家 §axinbing§r 从 §e2025年4月1日§r 开始的数据总览\n"]


def reply(return_msg):
    if type(return_msg) == str:
        for line in return_msg.split('\n'):
            print(f"Cute_Log | DEBUG | {line}") if DEBUG else None
            g_server.say(line) if not DEBUG else None

    # 去除\n控制符, 按行回复
    elif type(return_msg) == list:
        for line in return_msg:
            line = line.replace('\n', '')
            print(f"Cute_Log | DEBUG | {line}") if DEBUG else None
            g_server.say(line) if not DEBUG else None



# Main
@new_thread("cute_log_parser")
def parser(source: CommandSource, message: str):
    # 手解命令树
    if len(message.split(' ')) == 0: # 无参数时
        reply('错误: 命令格式错误 => 请至少输入玩家名称\n')
        reply('输入 §6!!log help§r 获取帮助信息\n')

    # 只存在参数 <player_name> 时
    elif len(message.split(' ')) == 1:
        # 特判指令
        if message.split(' ')[0] == 'list':
            reply(get_file_info())

        elif message.split(' ')[0] == 'help':
            reply(show_help_msg())

        # 按 <player_name> 解析
        else:
            player_name = message.split(' ')[0]
            file_path = os.path.join(LOG_FILE_PATH, f"{player_name}.log")

            if not os.path.exists(file_path):
                reply(f"§c错误§r: 玩家 §c{player_name}§r 的日志§c文件不存在§r  使用 §6!!log list§r 查询可操作玩家列表")
                return

            else:
                reply(process_login_file(file_path, None))

    if len(message.split(' ')) == 2:  # 存在参数 <player_name> 和 <filter> 时
        player_name, filter_value = message.split(' ')
        file_path = os.path.join(LOG_FILE_PATH, f"{player_name}.log")

        if not os.path.exists(file_path):
            reply(f"§c错误§r: 玩家 §c{player_name}§r 的日志§c文件不存在§r, 使用 §6!!log list§r 查询可操作玩家列表")
            return
        
        # 检查过滤器是否为整数
        try:
            filter_value = int(filter_value)
        except ValueError:
            reply(f"§c错误§r: 命令 §6!!log <player>§r §c<fliter>§r 中, §c<fliter>§r 的值必须是整数 | 当前值:  {filter_value} ")
            return
        
        # 过滤器<100  ==> 列出最后 filter_value 次登录记录
        if filter_value <= 100:
            reply(list_last_logins(file_path, filter_value))

        # 过滤器>=100 ==> 解析为统计开始日期
        else:
            reply(process_login_file(file_path, filter_value))

    if len(message.split(' ')) > 2:  # 存在多余参数时
        reply('§c错误§r: 命令格式错误 => 输入的参数数量§c超出最大值§r: §c2§r\n')
        reply('输入 §6!!log help§r 获取帮助信息\n')


def on_load(server: PluginServerInterface, old_module):
    global g_server, LOG_FILE_PATH
    g_server = server
    LOG_FILE_PATH = server.get_data_folder()
    MESSAGE = 'message'
    builder = SimpleCommandBuilder()
    builder.command(PREFIX, lambda src, ctx: reply('输入 §6!!log help§r 获取详细说明\n'))
    builder.command(f"{PREFIX} <{MESSAGE}>", lambda src, ctx: parser(src, ctx[MESSAGE]))
    builder.arg(MESSAGE, GreedyText)
    builder.register(server)
    server.register_help_message(PREFIX, '§f可爱日志解析器 | 输入 §6!!log help§r 获取详细说明\n')
