#!/usr/bin/python3 
# -*- coding: utf-8 -*-
'''
Нужно задать в командной строке IP-адрес или группу из файла AD.yml или файл с IP-адресами, логин и пароль.
Многопоточно подключается по ssh ко всем заданным устройствам и выполняет на всех заданных устройствах конфигурационную cisco-команду из файла.
'''

import argparse
import subprocess
from concurrent.futures import ThreadPoolExecutor
from itertools import repeat
import cisco_utilites as cu


def send_and_parse_conf_parallel(devices, account, config_file, disable_echo, limit=16):
    '''
    Загружает cisco-команду из файла.
    Многопоточно подключается по ssh ко всем заданным устройствам и выполняет на всех заданных устройствах загруженную cisco-команду.
    '''
    config = cu.load_config_from_text(config_file)

    with ThreadPoolExecutor(max_workers=limit) as executor:
        result = executor.map(cu.send_config_commands_ip_user, devices, repeat(account), repeat(config))
    for ip, res in result:
        if disable_echo == 'no':
            print('!','-'*80)
            print('! [{}]\n'.format(ip['ip']))
            print(res)
            print('\n\n')
        elif cu.is_bad_command(res):
            print('!','-'*80)
            print('! [{}]\n'.format(ip['ip']))
            print(res)
            print('\n\n')


def conf_run(args):
    '''
    Принимает параметры командной строки.
    Определяет, IP-адреса/группы заданы или файл.
    Запрашивает недостающие параметры и передает всё необходимое в send_and_parse_conf_parallel.
    '''
    devices = cu.parse_source_param(args.groups, args.include, args.exclude)
    if devices:
        send_and_parse_conf_parallel(devices, cu.get_username_password(args.username, args.password), args.config, args.disable_echo)


def create_parser():
    '''
    Парсер командной строки.
    '''
    desprg = 'Скрипт подключается по ssh к устройству (устройствам) и выполняет конфигурационные cisco-команды из файла.'
    parser = argparse.ArgumentParser(prog = 'conf-text-ssh',
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
                          dest='config',
                          required=True,
                          help='файл с конфигурационными cisco-командами (без заголовка "conf t" и без окончания "end")')
    pr_group.add_argument('-n',
                          dest=cu.r_echo,
                          choices=['yes','no'],
                          default='no',
                          help=cu.r_echo_help)
    pr_group.set_defaults(func=conf_run)
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
