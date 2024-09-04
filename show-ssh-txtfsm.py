#!/usr/bin/python3 
# -*- coding: utf-8 -*-
'''
Нужно задать в командной строке IP-адрес или группу из файла AD.yml или файл с IP-адресами, логин, пароль и команду из перечня, формат вывода и файл вывода.
Многопоточно подключается по ssh ко всем заданным устройствам и выполняет на всех заданных устройствах выбранную параметрами командной строки cisco-команду или huawei-команду.
Обрабатывает ответы команды со всех устройств с помощью шаблона textfsm.
Сводит в единое собранную информацию и выводит результат в табличном виде или в словарь значений.
'''

import argparse
import subprocess
from concurrent.futures import ThreadPoolExecutor
import cisco_utilites as cu
from itertools import repeat


def send_and_parse_command_parallel(devices, account, vendor, command, add_source_ip, output_format, output_file, limit=16):
    '''
    Многопоточно подключается по ssh ко всем заданным устройствам и выполняет на всех заданных устройствах переданную команду.
    Обрабатывает ответы команды со всех устройств с помощью шаблона textfsm.
    Сводит результаты обработки в один список.
    Выводит на экран или в файл собранную со всех устройств информацию в табличном виде (в нескольких форматах по выбору).
    '''
    with ThreadPoolExecutor(max_workers=limit) as executor:
        result = executor.map(cu.send_show_command_ip_user, devices, repeat(account), repeat(command), repeat(vendor))
    biglist = []
    for ip, show in result:
        if add_source_ip == 'yes':
            biglist.extend(cu.parse_command_output(command, show, dic=True, source_ip=ip, vendor=vendor))
        else:
            biglist.extend(cu.parse_command_output(command, show, dic=True, vendor=vendor))
    cu.print_table(biglist, output_format, output_file)


def show_grp(args):
    '''
    Принимает параметры командной строки.
    Определяет, IP-адреса/группы заданы или файл.
    Запрашивает недостающие параметры, формирует команду и передает всё необходимое в send_and_parse_command_parallel.
    '''
    devices = cu.parse_source_param(args.groups, args.include, args.exclude)
    if not devices:
        print('В списке нет устройств')
        return None
    if not cu.isFsmCommand(args.command):
        print('Неизвестная команда:', args.command)
        return None
    if   args.command.startswith('sh'):
        vendor = 'cisco_ios'
    elif args.command.startswith('dis'):
        vendor = 'huawei'
    else:
        print('Неизвестный вендор')
        return None

    send_and_parse_command_parallel(devices, cu.get_username_password(args.username, args.password), vendor, args.command, args.add_source_ip, args.format, args.output_file)


def create_parser():
    '''
    Парсер командной строки.
    '''
    choices= [cu.convertCommandFsmToMax(command) for command in cu.readTemplateFsmCommands()]
    cmdHelp = 'выполняемая команда из перечня: '
    for cmd in choices:
        cmdHelp += '"' + cmd + '", '
    cmdHelp = cmdHelp[:-2]
    desprg = 'Скрипт подключается по ssh к устройству (устройствам), выполняет выбранную cisco-команду или huawei-команду, обрабатывает ответ с помощью шаблона textfsm и возвращает результат в табличном виде, в виде списка или словаря.'
    parser = argparse.ArgumentParser(prog = 'show-ssh-txtfsm',
                                        description = desprg,
                                        add_help = False,
                                        epilog = cu.r_copyright )
    pr_group = parser.add_argument_group (title=cu.r_params)
    pr_group.add_argument('-h', action=cu.r_help, help=cu.r_help1)
    pr_group.add_argument('-i',
                          dest=cu.r_include,
                          nargs='+',
                          required=True,
                          help=cu.r_include_help)
    pr_group.add_argument('-e',
                          dest=cu.r_exclude,
                          nargs='*',
                          help=cu.r_exclude_help)
    pr_group.add_argument('-g',
                          dest=cu.r_ad,
                          default=cu.r_ad_default,
                          help=cu.r_ad_help)
    pr_group.add_argument('-u',
                          dest=cu.r_usr,
                          help=cu.r_usr_help)
    pr_group.add_argument('-p',
                          dest=cu.r_pwd,
                          help=cu.r_pwd_help)
    pr_group.add_argument('-c',
                          dest='command',
                          required=True,
                          help=cmdHelp)
    pr_group.add_argument('-a',
                          dest='add_source_ip',
                          choices=['yes','no'],
                          default='yes',
                          help='добавить столбец с ip устройства в выводимый результат (по умолчанию - yes)')
    pr_group.add_argument('-f',
                          dest='format',
                          choices=['table', 'list', 'dict'],
                          default='table',
                          help='формат вывода (таблица, список, словарь) (по умолчанию - table)')
    pr_group.add_argument('-o',
                          dest=cu.r_out_file,
                          default='',
                          help=cu.r_out_file_help)
    pr_group.set_defaults(func=show_grp)
    return parser


if __name__ == '__main__':
    cu.setup_logging()
    cu.print_full_name()
    parser = create_parser()
    args = parser.parse_args()
    if not vars(args):
        parser.print_usage()
    else:
        args.func(args)
