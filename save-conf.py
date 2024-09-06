#!/usr/bin/python3 
# -*- coding: utf-8 -*-
'''
Нужно задать в командной строке IP-адрес или группу из файла AD.yml или файл с IP-адресами, логин и пароль.
Многопоточно подключается по ssh ко всем заданным устройствам и выполняет на всех заданных устройствах cisco-команду "sh run".
Cохраняет полученную конфигурацию в файл вида HOSTNAME-confg
'''

import argparse
import subprocess
import os
import re
import logging
from itertools import repeat
from concurrent.futures import ThreadPoolExecutor
import cisco_utilites as cu


def send_and_parse_sh_run_parallel(devices, account, folder, conftype='no', keysremove='no', limit=16):
    '''
    Многопоточно подключается по ssh ко всем заданным устройствам и выполняет на всех заданных устройствах cisco-команду "sh run, sh run all или sh start".
    Находит в выводе hostname имя файла.
    Выводит в файл собранную со всех устройств конфигурацию.
    '''
    if conftype == 'start':
        command = 'sh startup-config'
    elif conftype == 'all':
        command = 'sh running-config all'
    else:
        command = 'sh running-config'
    with ThreadPoolExecutor(max_workers=limit) as executor:
        result = executor.map(cu.send_show_command_ip_user, devices, repeat(account), repeat(command))
    for ip, show in result:
        host = cu.get_hostname(show)
        if host:
            if conftype == 'start':
                output_file = folder + host + '-confg-start'
            elif conftype == 'all':
                output_file = folder + host + '-confg-all'
            else:
                output_file = folder + host + '-confg'
            i = show.find('!')
            show = show[i:]
            if keysremove == 'yes':
                show = cu.obfus_cisco(show)
            with open(output_file, 'w') as f:
                print('\n' + show, file=f)
            logging.info('Конфигурация устройства [' + ip['ip'] + '] cохранена в файл ' + output_file)


def show_run(args):
    '''
    Принимает параметры командной строки.
    Определяет, IP-адреса/группы заданы или файл.
    Запрашивает недостающие параметры и передает всё необходимое в send_and_parse_sh_run_parallel.
    '''
    devices = cu.parse_source_param(args.groups, args.include, args.exclude)
    if devices:
        if args.output_folder:
            if not os.path.exists(args.output_folder):
                print('\nКаталог ' + args.output_folder + ' не найден')
                return None   
            if not (args.output_folder[-1] == '/'):
                args.output_folder = args.output_folder + '/'
        send_and_parse_sh_run_parallel(devices, cu.get_username_password(args.username, args.password), args.output_folder, args.config_type, args.keys_remove)


def create_parser():
    '''
    Парсер командной строки
    '''
    desprg = 'Скрипт подключается по ssh к устройству (устройствам), выполняет cisco-команду "show running-config" и сохраняет результат в файл вида HOSTNAME-confg или "show running-config all" и сохраняет результат в файл вида HOSTNAME-confg-all'
    parser = argparse.ArgumentParser(prog = 'save-conf',
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
    pr_group.add_argument('-o',
                          dest=cu.r_out_folder,
                          default='',
                          help=cu.r_out_folder_help)
    pr_group.add_argument('-k',
                          dest=cu.r_keys_remove,
                          choices=['yes','no'],
                          default='no',
                          help=cu.r_keys_remove_help)
    pr_group.add_argument('-c',
                          dest=cu.r_config_type,
                          choices=['run','all','start'],
                          default='run',
                          help=cu.r_config_type_help)

    pr_group.set_defaults(func=show_run)
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
