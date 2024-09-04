# -*- coding: utf-8 -*-
'''
Общие функции для обработки cisco-команд и huawei-команд

'''

import sys
import os
import ipaddress
import getpass
import yaml
import logging
import re
from tabulate import tabulate
from pprint import pprint
from netmiko import ConnectHandler
from textfsm import clitable
from jinja2 import Environment, FileSystemLoader


AD = {}  # Словарь с БД групп и объектов (IP-адресов) вида {группа : [список групп/объектов]}

# Текстовые строки для вывода информации о программе и помощи по командным строкам.
# А также строки с именами некоторых папок и файлов по умолчанию.
r_name = 'Shiva'
r_fullname = '\n' + r_name + ' - система автоматизации администрирования телекоммуникационного оборудования\n'
# r_version = 'ver. 1.0.2077  - 10.12.2020'
r_version = 'ver. 1.3.4  - 26.02.2024'
r_copyright = 'Автор: Андрей Яковлев (andrey-yakovlev@yandex.ru) ' + r_version
r_params = 'параметры командной строки'
r_help = 'help'
r_help1 = 'вывод подсказки'

r_include = 'include'
r_include_help = 'IP-адреса и/или группы, введенные через пробел; или файл со строками из IP-адресов'

r_exclude = 'exclude'
r_exclude_help = 'исключаемые IP-адреса и/или группы, введенные через пробел'

r_db ='database'
r_db_default = 'DB/paramsDB.yml'         # Файл с БД конфигурационных параметров
r_db_help = 'yaml файл с БД конфигурационных параметров (по умолчанию ' + r_db_default + ')'

r_ad = 'groups'
r_ad_default='DB/AD.yml'                 # Файл с БД групп и объектов
r_ad_help='yaml файл с БД групп и объектов (по умолчанию ' + r_ad_default + ')'

jinja2_folder  = 'templates-jinja2'      # Каталог с шаблонами jinja2
textfsm_folder = 'templates-textfsm'     # Каталог с шаблонами textfsm

r_usr = 'username'
r_usr_help='имя пользователя'

r_pwd = 'password'
r_pwd_help='пароль пользователя'

r_jinja = 'template'
r_jinja_help = 'файл c jinja2 шаблоном команды'

r_add_d = 'adddict'
r_add_d_help = 'yaml файл с дополнительным словарем конфигурационных параметров'

r_level= 'level'
r_level_help = 'добавить уровень вложенности {ADD:{доп. словарь}} дополнительному словарю конфигурационных параметров (по умолчанию - no)'

r_echo='disable_echo'
r_echo_help='подавить вывод ответов устройств (по умолчанию - no)'

r_keys_remove='keys_remove'
r_keys_remove_help='удалить из конфигурации секреты (по умолчанию - no)'

r_config_type='config_type'
r_config_type_help='сохранить обычную (run), полную (all) или стартовую (start) конфигурацию (по умолчанию - run)'

r_out_file = 'output_file'
r_out_file_help = 'файл вывода (по умолчанию - вывод на экран)'

r_out_folder = 'output_folder'
r_out_folder_help = 'папка для сохранения конфигурации'

def setup_logging():
    '''
    Настраивает форматы и уровни логирования.
    '''
    logging.basicConfig(
        format = 'Шива говорит --  %(levelname)s:  %(message)s',
        level=logging.INFO)
    logging.getLogger('paramiko').setLevel(logging.WARNING)


def print_full_name():
    '''
    Выводит название системы.
    '''
    print(r_fullname, file=sys.stderr)


def print_to_file(txt, output_file=None):
    '''
    Выводит текст на экран или в файл.
    '''
    if not output_file:
        print('\n\n')
        print(txt)
    else:
        with open(output_file, 'w') as f:
            print(txt, file=f)
        logging.info('Результат записан в файл ' +  output_file)


def save_to_file(struct, output_file=None):
    '''
    Выводит структуру на экран с помощью pprint или в yaml файл.
    '''
    if not output_file:
        print('\n\n')
        pprint(struct)
    else:
        with open(output_file, 'w') as f:
            yaml.dump(struct, f, default_flow_style=False)
        logging.info('Словарь записан в файл ' + output_file)


def save_set_to_text(struct, output_file, header=None, footer=None):
    '''
    Сортирует и сохраняет множество со строками IP-адресов вида {"192.168.1.2" ,"192.168.1.1"...} 
    в текстовый файл со строками IP-адресов.
    Опционально можно добавить строки хидера и футера.
    '''
    with open(output_file, 'w') as f:
        if header:
            print(header, file=f)
        for device in sorted([obj for obj in struct], key=split_ip):
            print(device, file=f)
        if footer:
            print(footer, file=f)


def exists_file(file_name):
    '''
    Проверяет, есть ли такой файл.
    '''
    return os.path.isfile(file_name)

def get_files(directory):
    '''
    Возвращает список всех файлов в каталоге с подкаталогами.
    '''
    folder = []
    for fn in os.walk(directory):
        folder.append(fn)
    result = []
    for address, dirs, files in folder:
        for fn in files:
            result.append(address + '/' + fn)
    return result

def find_file(word, directory):
    '''
    Возвращает первое найденное полное имя файла из каталога с подкаталогами, содержащего в названии слово word.
    '''
    for fn in get_files(directory):
        if word in fn:
            return fn
    return None


def load_from_file(input_file):
    '''
    Загружает структуру из yaml файла и возвращает её.
    '''
    if not exists_file(input_file):
        logging.error('Файл ' + input_file + ' не найден')
        return None
    with open(input_file, 'r') as f:
        result = yaml.safe_load(f)
    return result


def load_devices_from_text(input_file):
    '''
    Загружает текст со строками IP-адресов и преобразует его в список со словарями IP-адресов вида [{"ip": "192.168.1.1"}, {"ip": "192.168.1.2"}...]
    '''
    if not exists_file(input_file):
        logging.error('Файл ' + input_file + ' не найден')
        return None
    with open(input_file, 'r') as f:
        result = [{'ip': line.strip()} for line in f if true_ip(line.strip())]
    return result


def get_devices_from_set(devices):
    '''
    Получает из множества со строками IP-адресов вида {"192.168.1.2" ,"192.168.1.1"...}
    сортированный список со словарями IP-адресов вида [{"ip": "192.168.1.1"}, {"ip": "192.168.1.2"}...]
    '''
    return [{'ip': ip} for ip in sorted([ip for ip in devices], key=split_ip) if true_ip(ip)]


def load_config_from_text(input_file):
    '''
    Загружает текст с конфигурационными командами и преобразует его в список команд.
    '''
    if not exists_file(input_file):
        logging.error('Файл ' + input_file + ' не найден')
        return None
    with open(input_file, 'r') as f:
        result = [line.rstrip() for line in f]
    return result


def zip_devices_DB(devices, params):
    '''
    Проходит по списку словарей устройства вида [{"ip": "192.168.1.1", "device_type": "cisco_ios", "username": "cisco", "password": "cisco"}, {"ip": "192.168.1.2"...}...]
    выбирает из БД подходящие словари с словарём параметров и составляет список объединённых словарей устройства и его параметров.
    '''
    result = [{**device, **params[device['ip']]} for device in devices]
    return result


def get_vendors_DB(devices, params):
    '''
    Проходит по списку словарей устройства вида [{"ip": "192.168.1.1"}, {"ip": "192.168.1.2"...}...]
    выбирает из БД подходящие словари с словарём параметров и возвращает список вендоров ["cisco_ios",...].
    '''
    result = []
    for device in devices:
        if params[device['ip']].get('device_type'):
            result.append(params[device['ip']]['device_type'])
        else:
            result.append('cisco_ios')
    return result


def make_device(ip, account, vendor):
    '''
    Делает полный словарь устройства вида {"ip": "192.168.1.1", "device_type": "cisco_ios", "username": "cisco", "password": "cisco"},
    составленный из словарей с IP-адресом и с логином и паролем, а также с именем вендора
    Возвращает объединеннный словарь.
    '''
    device = {'device_type' : vendor}
    device.update(ip)
    device.update(account)
    return device


def send_show_command(device, command):
    '''
    Подключается по ssh к заданному устройству и выполняет на нём заданную команду.
    Возвращает вывод с устройства.
    '''
    result = ''
    logging.info('SSH соединение с: ' + device['ip'])
    try:
        with ConnectHandler(**device) as ssh:
            result = ssh.send_command(command)
    except Exception as err:
        logging.warning('[' + device['ip'] + '] ')
        logging.warning(err)
    return result


def send_show_command_ip_user(ip, account, command, vendor='cisco_ios'):
    '''
    Получает словарь с IP-адресом, словарь с логином и паролем, название вендора и команду.
    Запускает выполнение send_show_command.
    Возвращает словарь c IP-адресом и результат выполнения команды.
    '''
    result = ''
    result = send_show_command(make_device(ip, account, vendor), command)
    return ip, result


def send_config_commands(device, config_commands):
    '''
    Подключается по ssh к заданному устройству и выполняет на нём заданный список конфигурационных команд.
    Возвращает вывод с устройства.
    '''
    result = ''
    config_commands = clearCommands(config_commands)
    try:
        with ConnectHandler(**device) as ssh:
            #ssh.enable()
            result = ssh.send_config_set(config_commands, cmd_verify = False)
            logging.info('Конфигурационная команда для устройства [' + device['ip'] + '] выполнена')
    except Exception as err:
        logging.error('[' + device['ip'] + ']')
        logging.error(err)
    return result


def send_config_commands_ip_user(ip, account, config_commands, vendor='cisco_ios'):
    '''
    Получает словарь с IP-адресом, словарь с логином и паролем, название вендора и список конфигурационных команд.
    Запускает выполнение send_config_commands, если config_commands не пустая
    Возвращает словарь c IP-адресом и результат выполнения конфигурационных команд.
    '''
    result = ''
    if checkNotEmptyCommands(config_commands):
        result = send_config_commands(make_device(ip, account, vendor), config_commands)
    else:
        result = '...'
    return ip, result


def send_config_commands_from_file(device, config_file):
    '''
    Подключается по ssh к заданному устройству и выполняет на нём конфигурационные команды из заданного файла.
    Возвращает вывод с устройства.
    '''
    result = ''
    try:
        with ConnectHandler(**device) as ssh:
            #ssh.enable()
            result = ssh.send_config_set_from_file(config_file, cmd_verify = False)
            logging.info('Конфигурационная команда для устройства [' + device['ip'] + '] выполнена')
    except Exception as err:
        logging.error('[' + device['ip'] + ']')
        logging.error(err)
    return result


def send_config_commands_from_file_ip_user(ip, account, config_file, vendor='cisco_ios'):
    '''
    Получает словарь с IP-адресом, словарь с логином и паролем, название вендора и имя файла с конфигурационными командами.
    Запускает выполнение send_config_commands_from_file.
    Возвращает словарь c IP-адресом и результат выполнения конфигурационных команд.
    '''
    result = ''
    result = send_config_commands_from_file(make_device(ip, account, vendor), config_file)
    return ip, result


def get_ip(ip=None):
    '''
    Если это не строка с IP-адресом - запрашивает IP-адрес, пока не введут правильный.
    Возвращает словарь вида {"ip": "192.168.1.1"}
    '''
    while not true_ip(ip):
        ip = input('Введите IP: ')
    return {'ip' : ip}


def true_ip(ip_address):
    '''
    Проверяет, правильный ли IP-адрес.
    Используется, как тест для jinja
    '''
    try:
        ipaddress.ip_network(ip_address)
        return True
    except ValueError:
        return False


def true_ip_my(ip_address):
    '''
    По другому проверяет, правильная ли строка с IP-адресом.
    '''
    if (not(type(ip_address) is str)) or (not ip_address):
        return False
    octets = ip_address.split('.')
    if len(octets) != 4:
        return False
    for octet in octets:
        if (not octet.isdigit()) or (int(octet) < 0) or (int(octet) > 255):
            return False
    return True


def is_private_ip(ip_address):
    '''
    Проверяет, приватный ли IP-адрес (RFC1918).
    Используется, как тест для jinja
    '''
    private = ['10.', '192.168.', '172.16.', '172.17.', '172.18.', '172.19.', '172.20.', '172.21.', '172.22.', '172.23.', 
               '172.24.', '172.25.', '172.26.', '172.27.', '172.28.', '172.29.', '172.30.', '172.31.']
    return any(ip_address.startswith(word) for word in private)


def is_public_ip(ip_address):
    '''
    Проверяет, публичный ли IP-адрес (RFC1918, RFC5735, RFC6598, RFC6890).   
    Используется, как тест для jinja
    '''
    private = ['10.', '192.168.', '172.16.', '172.17.', '172.18.', '172.19.', '172.20.', '172.21.', '172.22.', '172.23.', 
               '172.24.', '172.25.', '172.26.', '172.27.', '172.28.', '172.29.', '172.30.', '172.31.',
               '0.', '192.0.0.', '192.0.2.', '169.254.', '127.', '192.88.99.', '192.18.', '192.19.', '198.51.100.', '203.0.113.', 
               '224.', '225.', '226.', '227.', '228.', '229.', '230.', '231.', '232.', '233.', '234.', '235.', '236.', '237.', '238.', '239.',
               '240.', '241.', '242.', '243.', '244.', '245.', '246.', '247.', '248.', '249.', '250.', '251.', '252.', '253.', '254.', '255.',
               '100.64.', '100.65.', '100.66.', '100.67.', '100.68.', '100.69.', '100.70.', '100.71.', '100.72.', '100.73.',
               '100.74.', '100.75.', '100.76.', '100.77.', '100.78.', '100.79.', '100.80.', '100.81.', '100.82.', '100.83.',
               '100.84.', '100.85.', '100.86.', '100.87.', '100.88.', '100.89.', '100.90.', '100.91.', '100.92.', '100.93.',
               '100.94.', '100.95.', '100.96.', '100.97.', '100.98.', '100.99.', '100.100.', '100.101.', '100.102.', '100.103.',
               '100.104.', '100.105.', '100.106.', '100.107.', '100.108.', '100.109.', '100.110.', '100.111.', '100.112.', '100.113.',
               '100.114.', '100.115.', '100.116.', '100.117.', '100.118.', '100.119.', '100.120.', '100.121.', '100.122.', '100.123.',
               '100.124.', '100.125.', '100.126.', '100.127.' ]
    return not (any(ip_address.startswith(word) for word in private))


def split_ip(ip):
    '''
    Разбивает строку с IP-адресом на кортеж из четырех целых чисел.
    Функция используется, как ключ для правильной сортировки IP-адресов.
    '''
    return tuple(int(part) for part in ip.split('.'))


def capitalize1(interface):
    '''
    Принимает строку, а возвращает строку с капитализированной первой буквой.
    '''
    return interface[0].upper() + interface[1::]


def abbr_interface(interface):
    '''
    Сокращает строку с названием интерфейса.
    '''
    abbr = {#'NeuroInterface'      : 'Ne'
            'FastEthernet'         : 'Fa', 
            'GigabitEthernet'      : 'Gi',
            'Ethernet'             : 'Eth',
            'TenGigabitEthernet'   : 'Te', 
            'TwentyFiveGigE'       : 'Twe', 
            'FortyGigabitEthernet' : 'Fo', 
            'HundredGigE'          : 'Hu', 
            'Vlan'                 : 'Vl', 
            'Port-channel'         : 'Po', 
            'Dialer'               : 'Di', 
            'Loopback'             : 'Lo', 
            'Tunnel'               : 'Tu'}
    interface = capitalize1(interface)
    for key in abbr.keys():
        interface = interface.replace(key, abbr[key])
    return interface


def full_interface(interface):
    '''
    Восстанавливает сокращенную строку с названием интерфейса.
    '''
    abbr = {#'Ne'   : 'NeuroInterface'
            'Fa'    : 'FastEthernet', 
            'Gi'    : 'GigabitEthernet', 
            'Eth'   : 'Ethernet', 
            'Te'    : 'TenGigabitEthernet', 
            'Twe'   : 'TwentyFiveGigE', 
            'Fo'    : 'FortyGigabitEthernet', 
            'Hu'    : 'HundredGigE', 
            'Vl'    : 'Vlan', 
            'Po'    : 'Port-channel', 
            'Di'    : 'Dialer', 
            'Lo'    : 'Loopback', 
            'Tu'    : 'Tunnel'}
    interface = interface.capitalize()
    for key in abbr.keys():
        interface = interface.replace(key, abbr[key])
    return interface


def word_in_str(line, words):
    '''
    Проверяет, есть ли в строке "line" слово из списка "words".
    '''
    return any(word in line for word in words)


def word_is_str(line, words):
    '''
    Проверяет, совпадает строка "line" со любым словом из списка "words".
    '''
    return any((word == line) for word in words)


def word_start_str(line, words):
    '''
    Проверяет, начинается ли строка "line" со слова из списка "words".
    '''
    return any(line.startswith(word) for word in words)


def is_bad_command(res):
    '''
    Проверяет, есть ли в строке "res" ошибки выполнения конфигурационных команд cisco.
    '''
    errors = ['% Incomplete command', '% Invalid input detected', '% Ambiguous command']
    return word_in_str(res, errors)


def is_bad_command_h(res):
    '''
    Проверяет, есть ли в строке "res" ошибки выполнения конфигурационных команд huawei.
    '''
    errors = ['Error', 'Warning']
    return word_in_str(res, errors)


def get_username_password(username=None, password=None):
    '''
    Если нет логина - запрашивает его, пока не введут.
    Если нет пароля - запрашивает его, пока не введут.
    Пароль на экране не показывает.
    Возвращает словарь из логина и пароля.
    '''
    while not username:
        print('Введите имя пользователя: ', end='', file=sys.stderr)
        username = input()
    while not password:
        password = getpass.getpass('Введите пароль: ')
    return {'username' : username, 'password' : password}


def get_template_file(input_file, ret3=False):
    '''
    Возвращает имя файла jinja2-шаблона.
    '''
    global jinja2_folder
    regex = (r'^(?P<folder>.+)/(?P<filename>.+?)$')
    match = re.search(regex, input_file)
    if match:
        folder = match.group('folder')
        filename = match.group('filename')
        fullname = input_file
    else:
        folder = jinja2_folder
        filename = input_file
        fullname = folder + '/' + input_file
    if not exists_file(fullname):
        return None
    else:
        if ret3:
            return filename, folder
        else:
            return fullname


def generate_config(input_file, data_dict):
    '''
    Генерирует конфигурацию по jinja2-шаблону из словаря с конфигурационными параметрами.
    '''
    config = ''
    filename, folder = get_template_file(input_file, True)
    if not filename:
        logging.error('Файл ' + fullname + ' не найден')
        return ''
    env = Environment(loader=FileSystemLoader(folder))
    env.tests['ipaddr'] = true_ip
    env.tests['ipaddrprivate'] = is_private_ip
    env.tests['ipaddrpublic']  = is_public_ip
    env.tests['trunk']  = is_trunk
    env.filters['netmask_to_hostmask'] = netmask_to_hostmask
    env.filters['iphost_to_ipnetwork'] = iphost_to_ipnetwork
    env.filters['interface_to_ip'] = interface_to_ip
    env.filters['interface_to_ip_by_num'] = interface_to_ip_by_num
    env.filters['interface_to_ipnetwork'] = interface_to_ipnetwork
    env.filters['interface_to_netmask'] = interface_to_netmask
    env.filters['interface_to_hostmask'] = interface_to_hostmask
    env.filters['interface_to_prefixlen'] = interface_to_prefixlen
    env.filters['intf_to_encapsulation'] = intf_to_encapsulation
    env.filters['intf_to_vlan'] = intf_to_vlan
    try:
        templ = env.get_template(filename)
        config = templ.render(data_dict)
    except Exception as err:
        logging.error('Ошибка в синтаксисе jinja шаблона')
        logging.error(err)
    return config


def is_obj(obj):
    '''
    Объектом считает строку с IP-адресом, группой - всё остальное
    '''
    return true_ip(obj)


def dynamic_header(include, exclude=None):
    '''
    Делает заголовок из списков включенных групп/объектов и исключенных групп/объектов.
    '''
    result = '# include: '
    for inc in include:
        result = result + inc + ', '
    result = result[0:-2] + '\n'
    if exclude:
        result = result + '# exclude: '
        for exc in exclude:
            result = result + exc + ', '
        result = result[0:-2] + '\n'
    result = result + '#'
    print(result)
    return result


def get_objects(group):
    '''
    Рекурсивно составляет множество объектов из группы.
    В любую группу могут входить, как объекты, так и другие группы.
    '''

    global AD

    # Если задействано ключевое слово "all", то возвращаем множество всех объектов из словаря AD.
    if (group == ['all']):
        return get_all()

    # Если это объект, то возвращаем множество, состоящее из этого объекта.
    if is_obj(group):
        return {group}

    objects = set()
    # Проходим по списку всех членов в группе, взяв его из словаря AD.
    try:
        for obj in AD[group]:
            if is_obj(obj):
                # Если это объект - добавляем его в множество.
                objects.add(obj)
            else:
                # Если это группа - рекурсивно вызываем функцию и добавляем её результат в множество.
                objects = objects | get_objects(obj)
    except KeyError as err:
        logging.warning('Группа ' + str(err) + ' не найдена')
    except RecursionError as err:
        logging.error('Превышена вложенность объектов или обнаружена ссылка группы на саму себя')
        objects = set()

    # Возвращаем множество объектов.
    return objects


def dynamic_grop(include, exclude=None):
    '''
    Cобирает список объектов по спискам включенных групп/объектов и исключенных групп/объектов.
    '''
    inc_objects = set()

    # Проходим по списку включенных групп/объектов.
    for inc in include:
        # Добавляем всех членов группы/объекта в включаемое множество.
        inc_objects = inc_objects | get_objects(inc)

    # Если есть исключения
    if exclude:
        exc_objects = set()
        # проходим по списку исключенных групп/объектов,
        for exc in exclude:
            # добавляем всех членов группы/объекта в исключаемое множество;
            exc_objects = exc_objects | get_objects(exc)
        # проходим по членам исключаемого множества
        for obj in exc_objects:
            # и выкидываем их включаемого множества.
            inc_objects.discard(obj)

    # Возвращаем множество включенных объектов за минусом исключенных.
    return inc_objects


def get_all(exclude=None):
    '''
    Рекурсивно собирает множество объектов из всех групп за минусом списка исключенных.
    '''
    global AD

    all_objects = set()
    # Проходим по словарю групп/объектов.
    for inc in AD.keys():
        # Добавляем всех членов группы/объекта в включаемое множество.
        all_objects = all_objects | get_objects(inc)

    # Если есть исключения
    if exclude:
        exc_objects = set()
        # проходим по списку исключенных групп/объектов,
        for exc in exclude:
            # добавляем всех членов группы/объекта в исключаемое множество;
            exc_objects = exc_objects | get_objects(exc)
        # проходим по членам исключаемого множества
        for obj in exc_objects:
            # и выкидываем их включаемого множества.
            all_objects.discard(obj)
    # Возвращаем множество всех объектов за минусом исключенных.
    return all_objects



def parse_source_param(groupfile, include, exclude = None):
    '''
    Определяет, что введено: список с именем файла, или список с корректными IP-адресами и группами из словаря AD.
    Возвращает сортированный список словарей IP-адресов вида [{"ip": "192.168.1.1"}, {"ip": "192.168.1.2"}...]
    '''
    global AD
    devices = []

    if exists_file(groupfile):
        AD = load_from_file(groupfile)   # Загружаем словарь AD, если такой файл есть.
    else:
        print('\nфайл словаря групп ' + groupfile + ' - не найден\nРабота с группами и исключениями отключена')

    if (len(include)==1) & (exists_file(include[0])):                       # это одна запись в списке и есть такой файл?
        devices = load_devices_from_text(include[0])                           # тогда загружаем устройства из файла
        print('\nСписок устройств загружен из файла ' + include[0] + '\nИсключения проигнорированы')
    elif AD:                                                                # или если словарь AD загружен?
        if (include == ['all']):                                                # это встроенная группа "all"?
            devices = get_devices_from_set(get_all(exclude))                    # тогда работаем по группе "all"
        else:                                                                   # или это список групп?
            devices = get_devices_from_set(dynamic_grop(include, exclude))      # работаем по списку групп
    elif all( true_ip(ip) for ip in include):                               # или в списке только правильные IP-адреса?
        devices = get_devices_from_set(include)                             # работаем по списку IP-адресов
    else:
        # Всё плохо. Ничего не нашли. Вернём пустой список.
        if AD:
            print('\nПараметр' , include , 'не список IP-адресов/групп и не существующий файл')
        else:
            print('\nПараметр' , include , 'не список IP-адресов и не существующий файл')
    return devices


def get_hostname(show):
    '''
    Возвращает имя устройства из ответа на cisco-команду "sh run".
    '''
    res = re.findall(r'hostname (\S+)', show)
    if res:
        return (res[0])
    else:
        return None


def get_sysname(show):
    '''
    Возвращает имя устройства из ответа на huawei-команду "dis conf".
    '''
    res = re.findall(r'sysname (\S+)', show)
    if res:
        return (res[0])
    else:
        return None


def readTemplateFsmCommands():
    '''
    Читает из индексного файла шаблонов textfsm команды описания команд в формате "sh[[ow]] cdp n[[eighbors]]"
    Возвращает список описаний команд
    '''
    input_file = textfsm_folder + '/index'
    with open(input_file, 'r') as f:
        templates = [line.strip().split(',') for line in f if line.strip()]
    return [line[-1].strip() for line in templates if line[-1].strip() != 'Command']


def isFsmCommand(command):
    '''
    Проверяет, есть ли такая команда в шаблоне textfsm.
    Учитываются все возможные варианты написания команды (сокращенные, промежуточные и полные).
    '''
    return compareCommandAndReg(command, [convertCommandFsmToReg(line) for line in readTemplateFsmCommands()])


def getFsmCommand(command):
    '''
    Если команда не найдена в шаблоне textfsm - запрашивает её, пока не введут.
    Учитываются все возможные варианты написания команды (сокращенные, промежуточные и полные).
    Возвращает опознанную команду.
    '''
    regexps = [convertCommandFsmToReg(line) for line in readTemplateFsmCommands()]
    while not compareCommandAndReg(command, regexps):
        command = input('Введите поддерживаемую команду устройства: ')
    return command


def getIdxFsmTemplate(command):
    '''
    Возвращает по введенной команде номер шаблона textfsm.
    Если шаблон не найден - возвращается 0.
    '''
    global textfsm_folder
    attributes = {'Command': command}
    cli_table = clitable.CliTable('index', textfsm_folder)
    return cli_table.index.GetRowMatch(attributes)


def getFsmTemplate(command):
    '''
    Возвращает по введенной команде название шаблона textfsm.
    '''
    global textfsm_folder
    attributes = {'Command': command}
    cli_table = clitable.CliTable('index', textfsm_folder)
    idx = cli_table.index.GetRowMatch(attributes)
    if idx:
        return cli_table.index.index[idx]['Template']
    else:
        return None


def parse_command_output(command, command_output, dic=True, source_ip=None, vendor='cisco_ios'):
    '''
    Обрабатывает ответ от команды с помощью шаблона textfsm.
    Выводит полученную табличную информацию в виде списка словарей значений (по умолчанию) или списка списков значений.
    Добавляет в таблицу IP-адрес источника, если он передан.
    '''
    global textfsm_folder
    attributes = {'Platform': vendor}
    attributes['Command'] = command
    cli_table = clitable.CliTable('index', textfsm_folder)
    cli_table.ParseCmd(command_output, attributes)
    header1 = list(cli_table.header)
    if source_ip:
        ip1 = {'SOURCE_IP' : source_ip['ip']}
        ip2 = [source_ip['ip']]
        header2 = ['SOURCE_IP'] + header1
    else:
        ip1 = {}
        ip2 = []
        header2 = header1
    if dic:
        result = [{**ip1, **dict(zip(header1, list(row)))} for row in cli_table]
    else:
        result = [header2] + [ip2 + list(row) for row in cli_table]
    return result


def print_table(biglist, output_format, output_file):
    '''
    Выводит на экран или в файл полученный список значений в табличном виде (в трёх форматах по выбору).
    '''
    if   output_format == 'table':
        print_to_file(tabulate(biglist, headers='keys'), output_file)
    elif output_format == 'list':
        print_to_file(tabulate(biglist, tablefmt='plain'), output_file)
    elif output_format == 'dict':
        save_to_file(biglist, output_file)


reg1 = r'\[\[(\S)+\]\]' # Регулярное выражение для поиска переменной части "[[...]]" в описаниях команд из шаблонов textfsm


def convertSubCommandFsm(line):
    '''
    Конвертирует переменную часть команды вида "[[eighbors]]"
    в часть регулярного выражения вида "(e(i(g(h(b(o(r(s)?)?)?)?)?)?)?)?"
    и возвращает его.
    '''
    line = line[2:-2]
    result = ''
    for ch in line:
        result += '(' + ch
    result += ')?' * len(line)
    return result


def convertCommandFsmToReg(command):
    '''
    Конвертирует описание команды в формате "sh[[ow]] cdp n[[eighbors]]"
    в регулярное выражение вида "^sh(o(w)?)? cdp n(e(i(g(h(b(o(r(s)?)?)?)?)?)?)?)?$"
    и возвращает его.
    '''
    global reg1
    for m in re.finditer(reg1, command):
        command = command.replace(m[0], convertSubCommandFsm(m[0]))
    command = re.sub(r'\s+', '\s+', command)
    return '^' + command + '$'


def convertCommandFsmToMin(command):
    '''
    Преобразовывает описание команды из шаблонов textfsm в сокращенный вариант команды
    '''
    global reg1
    return re.sub(reg1, '', command)


def convertCommandFsmToMax(command):
    '''
    Преобразовывает описание команды из шаблонов textfsm в полный вариант команды
    '''
    for m in re.finditer(reg1, command):
        command = command.replace(m[0], m[0][2:-2])
    return command


def compareCommandAndReg(command, regexps):
    '''
    Сравнивает введенную команду со списком шаблонов
    '''
    return any(re.fullmatch(reg, command.strip()) for reg in regexps)


def checkDictOfLists(struct):
    '''
    Делает предварительную проверку структуры на соответствие словарю списков.
    '''
    if not struct:
        logging.error('Проверяемая структура пустая')
        return False
    if not (type(struct) is dict):
        logging.error('Проверяемая структура - не словарь')
        return False
    for obj in struct.keys():
        if not (type(struct[obj]) is list):
            logging.error('Одно из значений по ключу в проверяемом словаре - не список')
            return False
    return True


def checkListOfDicts(struct):
    '''
    Делает предварительную проверку структуры на соответствие списку словарей.
    '''
    if not struct:
        logging.error('Проверяемая структура пустая')
        return False
    if not (type(struct) is list):
        logging.error('Проверяемая структура - не список')
        return False
    for obj in struct():
        if not (type(struct[obj]) is dict):
            logging.error('Одна из строк проверяемого списка - не словарь')
            return False
    return True


def checkNotEmptyCommand(command):
    '''
    Проверяет не пустая команда, или нет.
    '''
    if not command:
        return False
    if (command.strip()):
        return True
    else:
        return False


def checkNotEmptyCommands(commands):
    '''
    Проверяет не пустой ли список команд, или нет.
    '''
    if not commands:
        return False
    for command in commands:
        if (command.strip()):
            return True
    return False


def clearCommands(commands):
    '''
    Удаляет пустые строки из списка команд.
    '''
    result = []
    for command in commands:
        if command.strip():
            result.append(command.strip())
    return result


def clear_mac(mac):
    '''
    Возвращает MAC-адрес, очищенный от двоеточий, точек и тире в нижнем регистре.
    '''
    symbols = [':','-','.']
    for ch in symbols:
        mac = mac.replace(ch, '')
    return mac.lower()


def format_mac(mac):
    '''
    Возвращает отформатированный MAC-адрес, двоеточие через четыре символа
    '''
    mac = clear_mac(mac)
    return ':'.join(re.findall(r'.{4}', mac))


def get_mac_from_client(client):
    '''
    Возвращает MAC-адрес, из поля client словаря "sh ip dhcp binding".
    '''
    client = clear_mac(client)
    return client[-12:]


def true_mac(mac):
    '''
    Проверяет, правильный ли MAC-адрес.
    '''
    if (not(type(mac) is str)) or (not mac):
        return False
    if len(mac) != 12:
        return False
    regex = (r'^(?P<MAC>([0-9a-f]{12}))$')
    match = re.search(regex, mac)
    if match:
        return True
    else:
        return False


def split_arp(obj):
    '''
    Разбивает IP-адрес в кортеже с IP-адресом и MAC-адресом на кортеж из пяти целых чисел.
    Функция используется, как ключ для правильной сортировки.
    '''
    return tuple(int(part) for part in obj[0].split('.') ), obj[1]


def get_dict_type(struct):
    '''
    На вход подаётся структура.
    Структура должна быть списком словарей или словарём.
    Функция возвращает номер вида структуры, если распознает.
    '''
    if not struct:
        return None
    if (type(struct) is list) and (type(struct[0]) is dict):
        dct = struct[0]
        if   dct.get('IP_ADDRESS') and dct.get('MAC'):
            # определён, как список словарей "sh arp"
            return 1
        elif dct.get('ip') and dct.get('client'):
            # определён, как список словарей "sh ip dhcp binding"
            return 2
        elif dct.get('ip') and dct.get('mac'):
            # определён, как список словарей "sр ip dhcp snooping binding"
            return 3
    elif (type(struct) is dict):
        key = list(struct.keys())[0]
        if  true_ip(key) and true_mac(struct[key]):
            # определён, как словарь "IP:MAC"
            return 4
        elif true_mac(key) and true_ip(struct[key]):
            # определён, как словарь "MAC:IP"
            return 5
    # структура не распознана
    return None


def get_gates(flist):
    '''
    Анализирует конфигурационные файлы и
    возвращает множество IP адресов L3-интерфейсов.
    '''
    regex1 = ' ip address (?P<IP>(\d{1,3}\.){3}\d{1,3}) (\d{1,3}\.){3}\d{1,3}'
    regex2 = ' vrrp vrid \d+ virtual-ip (?P<IP>(\d{1,3}\.){3}\d{1,3})'
    regex3 = ' standby \d+ ip (?P<IP>(\d{1,3}\.){3}\d{1,3})'
    result = set()
    for fn in flist:
        logging.info(fn)
        with open(fn) as f:
            match_iter = re.finditer(regex1, f.read())
            for match in match_iter:
                result.add(match.group('IP'))
        with open(fn) as f:
            match_iter = re.finditer(regex2, f.read())
            for match in match_iter:
                result.add(match.group('IP'))
        with open(fn) as f:
            match_iter = re.finditer(regex3, f.read())
            for match in match_iter:
                result.add(match.group('IP'))
    return result


def mac_to_eui64(mac, prefix=None):
    '''
    Конвертирует MAC address в EUI64 адрес
    или, если задан префикс, в полный IPv6 адрес
    см. http://tools.ietf.org/html/rfc4291#section-2.5.1
    '''
    eui64 = clear_mac(mac)
    eui64 = eui64[0:6] + 'fffe' + eui64[6:]
    eui64 = hex(int(eui64[0:2], 16) ^ 2)[2:].zfill(2) + eui64[2:]

    if prefix is None:
        return ':'.join(re.findall(r'.{4}', eui64))
    else:
        try:
            net = ipaddress.ip_network(prefix, strict=False)
            euil = int('0x{0}'.format(eui64), 16)
            return str(net[euil])
        except:  # pylint: disable=bare-except
            return


def eui64_to_mac(eui64):
    '''
    Конвертирует EUI64 адрес в MAC адрес
    '''
    mac = clear_mac(eui64)
    if mac[6:10] == 'fffe':
        mac = mac[0:6] + mac[10:]
        mac = hex(int(mac[0:2], 16) ^ 2)[2:].zfill(2) + mac[2:]
        return mac
    else:
        return '000000000000'


def obfus_cisco(conf):
    '''
    Принимает текст с конфигурацией cisco.
    Возвращает текст без паролей и ключей.
    '''
    obf = 'XXXXXXXXXXXX'
    result = ''

#   Регулярные выражения с секретами
    regexs1 = [
    #'username (?P<key>\S+) ',
    'secret \d+ (?P<key>\S+)$',
    'password \d+ (?P<key>\S+)$',
    'pre-shared-key (local|remote) (?P<key>\S+)$',
    'pre-shared-key (local|remote) \d+ (?P<key>\S+)$',
    'pre-shared-key address \S+ key (?P<key>\S+)$',
    'pre-shared-key address \S+ key \d+ (?P<key>\S+)$',
    'pre-shared-key \d+ (?P<key>\S+)$',
    'crypto isakmp key (?P<key>\S+)',
    'tunnel key (?P<key>\d+)$',
    'ip nhrp authentication (?P<key>\S+)$',
    'digest-key \d+ md5 \d+ (?P<key>\S+)$',
    'authentication-key \d+ md5 (?P<key>\S+)',
    'key-string \d+ (?P<key>\S+)$',
    '^ key \d+ (?P<key>\S+)$',
    'port \d+ key \d+ (?P<key>\S+)$',
    'snmp-server (group|community) (?P<key>\S+)',
    'snmp-server host \S+ (informs|inform) version \S+ priv (?P<key>\S+)',
    'snmp-server host \S+ traps version \S+ (?P<key>\S+)',
    'snmp-server host \S+ version \S+ (?P<key>\S+)']
    regexs2 = [
    'snmp-server user (?P<key>\S+) (?P<key1>\S+)']

    for line in conf.split('\n'):
        for regex in regexs1:
            match = re.search(regex, line)
            if match:
                line = line.replace(match.group('key'), obf)
        for regex in regexs2:
            match = re.search(regex, line)
            if match:
                line = line.replace(match.group('key'), obf)
                line = line.replace(match.group('key1'), obf)
        result = result + line + '\n'
    return result


def cidr_to_netmask(cidr):
    '''
    Конвертирует битовую маску ip адреса в стандартную маску
    Возможен ввод в формате "192.168.1.1/24" или "24"
    Возвращает, соответственно, "192.168.1.1 255.255.255.0" или "255.255.255.0"
    '''
    if (type(cidr) is str) and ('/' in cidr):
        ip = cidr.split('/')
        network = ip[0]
        mask = int(ip[1])
    elif (type(cidr) is str) and (cidr.isdigit()):
        network = ''
        mask = int(cidr)
    elif (type(cidr) is int):
        network = ''
        mask = cidr
    else:
        return None
    bitmask = ('1' * mask) + ('0' * (32-mask))
    return '{0} {1}.{2}.{3}.{4}'.format(network, int(bitmask[0:8],2), int(bitmask[8:16],2), int(bitmask[16:24],2), int(bitmask[24:32],2)).strip()


def netmask_to_hostmask(mask):
    '''
    Принимает прямую маску, а возвращает обратную.
    Используется, как фильтр для jinja
    '''
    try:
        return str(ipaddress.ip_network('0.0.0.0/' + mask).hostmask)
    except ValueError:
        return ''


def iphost_to_ipnetwork(ip, mask):
    '''
    Принимает ip и маску хоста, а возвращает ip адрес сети.
    Используется, как фильтр для jinja
    '''
    try:
        return str(ipaddress.ip_interface(ip + '/' + mask).network.network_address)
    except ValueError:
        return ''


def interface_to_ip(interface):
    '''
    Принимает ip и маску хоста через дробь, а возвращает ip адрес.
    Используется, как фильтр для jinja
    '''
    try:
        return str(ipaddress.ip_interface(interface).ip)
    except ValueError:
        return ''


def interface_to_netmask(interface):
    '''
    Принимает ip и маску хоста через дробь, а возвращает маску.
    Используется, как фильтр для jinja
    '''
    try:
        return str(ipaddress.ip_interface(interface).netmask)
    except ValueError:
        return ''


def interface_to_hostmask(interface):
    '''
    Принимает ip и маску хоста через дробь, а возвращает обратную маску.
    Используется, как фильтр для jinja
    '''
    try:
        return str(ipaddress.ip_interface(interface).hostmask)
    except ValueError:
        return ''


def interface_to_prefixlen(interface):
    '''
    Принимает ip и маску хоста через дробь, а возвращает сокращенную маску.
    Используется, как фильтр для jinja
    '''
    try:
        return str(ipaddress.ip_interface(interface).network.prefixlen)
    except ValueError:
        return ''


def interface_to_ipnetwork(interface):
    '''
    Принимает ip и маску хоста через дробь, а возвращает ip адрес сети.
    Используется, как фильтр для jinja
    '''
    try:
        return str(ipaddress.ip_interface(interface).network.network_address)
    except ValueError:
        return ''


def interface_to_ip_by_num(interface, num=1):
    '''
    Принимает ip и маску хоста через дробь, а возвращает ip адрес по номеру.
    num == 0 - сеть;  num == 1 - первый ip в сети и т.д.
    Используется, как фильтр для jinja
    '''
    try:
        return str(ipaddress.ip_interface(interface).network[num])
    except ValueError:
        return ''


def is_trunk(interface):
    '''
    Проверяет, транковый ли интерфейс.   
    Используется, как тест для jinja
    '''
    return (interface.count('.') == 1)


def intf_to_encapsulation(interface):
    '''
    Принимает имя интерфейса Port-Ch а возвращает encapsulation номер.
    Используется, как фильтр для jinja
    '''
    if is_trunk(interface):
        return interface[interface.find('.')+1::]
    else:
        return ''


def intf_to_vlan(interface):
    '''
    Принимает имя интерфейса, а возвращает номер инкапсулированного на интерфейс Vlan-а.
    Используется, как фильтр для jinja
    '''
    interface = abbr_interface(interface)
    if is_trunk(interface):
        return interface[interface.find('.')+1::]
    elif interface.startswith('Vl'):
        return interface[2::]
    else:
        return ''

