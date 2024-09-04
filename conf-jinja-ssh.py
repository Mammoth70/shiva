#!/usr/bin/python3 
# -*- coding: utf-8 -*-
'''
Нужно задать в командной строке IP-адрес или группу из файла AD.yml или файл с IP-адресами, логин и пароль, файл с БД параметров и jinja2-шаблон конфигурации.
Многопоточно подключается по ssh ко всем заданным устройствам и выполняет на всех заданных устройствах конфигурационную cisco-команду, сгенерированную из шаблона.
'''

import argparse
import subprocess
from concurrent.futures import ThreadPoolExecutor
from itertools import repeat
import cisco_utilites as cu



def create_send_and_parse_conf_parallel(devices, account, database, input_file, input_add, input_level, disable_echo, limit=16):
    '''
    Считывает файл БД со словарём параметров.
    Проходит по списку словарей устройств, выбирает из БД подходящий словарь параметров, передает его в конфигуратор и возвращает список конфигураций.
    Многопоточно подключается по ssh ко всем заданным устройствам и выполняет на всех заданных устройствах переданную конфигурационную cisco-команду.
    '''
    if not cu.exists_file(database):
        print('\nфайл ' + database + ' - не найден')
        return None  
    params = cu.load_from_file(database)

    if not cu.get_template_file(input_file):
        print('\nфайл ' + input_file + ' - не найден')
        return None

    if input_add: 
        if not cu.exists_file(input_add):
            print('\nфайл ' + input_add + ' - не найден')
            return None  
        paramadd = cu.load_from_file(input_add)
        if input_level == 'yes':
            # Добавляем уровень ADD дополнительному словарю
            paramadd = {'ADD' : paramadd}
        if not type(paramadd) is dict:
            print('\nФайл ' + input_add + ' - не словарь')
            return None  
        firstkey = list(paramadd.keys())[0]
        if not cu.true_ip(firstkey):
            # Добавляем дополнительный словарь полностью к параметрам каждого устройства
            for param in params.values():
                param.update(paramadd)
        elif cu.is_private_ip(firstkey):
            # Добавляем совпадающие по устройствам значения дополнительного словаря к параметрам соответствующего устройства
            for key, param in params.items():
                if paramadd.get(key):
                    param.update(paramadd[key])
        else:
            print('\nСловарь ' + input_add + ' - не подключён')
            return None  

    configs = [cu.generate_config(input_file, {**device, **params[device['ip']]}).split('\n') for device in devices]
    vendors = cu.get_vendors_DB(devices, params)

    with ThreadPoolExecutor(max_workers=limit) as executor:
        result = executor.map(cu.send_config_commands_ip_user, devices, repeat(account), configs, vendors)
    print('\n\n')
    for ip, res in result:
        if disable_echo == 'no':
            print('!','-'*80)
            print('! "{}" [{}]\n'.format(params[ip['ip']].get('hostname'), ip['ip']))
            print(res)
            print('\n\n')
        elif cu.is_bad_command(res):
            print('!','-'*80)
            print('! "{}" [{}]\n'.format(params[ip['ip']].get('hostname'), ip['ip']))
            print(res)
            print('\n\n')


def conf_run(args):
    '''
    Принимает параметры командной строки.
    Определяет, IP-адреса/группы заданы или файл.
    Запрашивает недостающие параметры и передает всё необходимое в create_send_and_parse_conf_parallel.
    '''
    devices = cu.parse_source_param(args.groups, args.include, args.exclude)
    if devices:
        create_send_and_parse_conf_parallel(devices, cu.get_username_password(args.username, args.password), args.database, args.template, args.adddict, args.level, args.disable_echo)


def create_parser():
    '''
    Парсер командной строки.
    '''
    desprg = 'Скрипт подключается по ssh к устройству (устройствам) и выполняет cisco-команду по шаблону.'
    parser = argparse.ArgumentParser(prog = 'conf-jinja-ssh',
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
    pr_group.add_argument('-d',
                          dest=cu.r_db,
                          default=cu.r_db_default,
                          help=cu.r_db_help)
    pr_group.add_argument('-g',
                          dest=cu.r_ad,
                          default=cu.r_ad_default,
                          help=cu.r_ad_help)
    pr_group.add_argument('-j',
                          dest=cu.r_jinja,
                          required=True,
                          help=cu.r_jinja_help)
    pr_group.add_argument('-a',
                          dest=cu.r_add_d,
                          default='',
                          help=cu.r_add_d_help)
    pr_group.add_argument('-u',
                          dest=cu.r_usr,
                          help=cu.r_usr_help)
    pr_group.add_argument('-p',
                          dest=cu.r_pwd,
                          help=cu.r_pwd_help)
    pr_group.add_argument('-n',
                          dest=cu.r_echo,
                          choices=['yes','no'],
                          default='no',
                          help=cu.r_echo_help)
    pr_group.add_argument('-l',
                          dest=cu.r_level,
                          choices=['yes','no'],
                          default='no',
                          help=cu.r_level_help)
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
