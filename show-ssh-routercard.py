#!/usr/bin/python3 
# -*- coding: utf-8 -*-
'''
Подключение к заданному устройству по ssh и выполнение на нём cisco-команд "sh run" и "sh ip int bri".
Обработка ответов cisco-команд с помощью шаблона textfsm.
Вывод собранной информации в виде карточки на маршрутизатор.
'''

import sys
sys.path.append('..')
import argparse
import cisco_utilites as cu
from tabulate import tabulate


def send_and_parse_1_command(ip, account, output_file):
    '''
    Подключается к заданному устройству по ssh и выполняет на нём cisco-команды "sh run" и "sh ip int bri".
    Обрабатывает ответ cisco-команд с помощью шаблонов textfsm.
    Выводит на экран или в файл собранную информацию в виде карточки на маршрутизатор.
    '''
    command = 'sh run'
    ip, show = cu.send_show_command_ip_user(ip, account, command)
    host = cu.get_hostname(show)
    command = 'sh ip int'
    ip, show = cu.send_show_command_ip_user(ip, account, command)
    interfaces = cu.parse_command_output(command, show, dic=True)
    header = 'Router info\n\nhostname: "{}"  IP: [{}]\n\nInterfaces brief:\n'.format(host, ip['ip'])
    result = [['Interface','IP','VRF']]
    for interface in interfaces:
        if interface['IPADDR']:
            result.append([interface['INTF'], interface['IPADDR'][0] + '/' + interface['MASK'][0], interface['VRF']])
    cu.print_to_file(header + tabulate(result, headers='firstrow'), output_file)


def show1(args):
    '''
    Принимает параметры командной строки.
    Запрашивает недостающие параметры и передает всё необходимое в send_and_parse_1_command.
    '''
    send_and_parse_1_command(cu.get_ip(args.ip), cu.get_username_password(args.username, args.password), args.output_file)


def create_parser():
    '''
    Парсер командной строки.
    '''
    nameprg = 'Скрипт подключается по ssh к маршрутизатору, выполняет cisco-команды "sh run " и "sh ip int", обрабатывает ответы с помощью шаблона textfsm и возвращает карточку маршрутизатора.'
    parser = argparse.ArgumentParser(prog = 'show-ssh-routercard',
                                        description = nameprg,
                                        add_help = False, 
                                        epilog = cu.r_copyright )
    pr_group = parser.add_argument_group (title=cu.r_params)
    pr_group.add_argument('-h', action=cu.r_help, help=cu.r_help1)
    pr_group.add_argument('-i',
                            dest='ip',
                            help='IP-адрес устройства')
    pr_group.add_argument('-u',
                           dest=cu.r_usr,
                           help=cu.r_usr_help)
    pr_group.add_argument('-p',
                           dest=cu.r_pwd,
                           help=cu.r_pwd_help)
    pr_group.add_argument('-o',
                          dest=cu.r_out_file,
                          default='',
                          help=cu.r_out_file_help)
    parser.set_defaults(func=show1)
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
