#!/usr/bin/python3 
# -*- coding: utf-8 -*-
'''
Нужно задать в командной строке IP-адрес или группу из файла AD.yml или файл с IP-адресами, файл с БД параметров и jinja2-шаблон конфигурации.
Выводит для всех заданных устройств конфигурационную cisco-команду, сгенерированную из шаблона. 
'''

import argparse
import cisco_utilites as cu


def create_conf(devices, database, input_file, input_add, input_level):
    '''
    Считывает файл БД со словарём параметров.
    Проходит по списку словарей устройств, выбирает из БД подходящий словарь параметров, передает его в конфигуратор и возвращает список конфигураций.
    Выводит для всех заданных устройств сгенерированную конфигурационную cisco-команду.
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

    configs = [cu.generate_config(input_file, {**device, **params[device['ip']]}) for device in devices]
    results = zip(devices, configs)
    for result in results:
        print('!','-'*80)
        ip = result[0]['ip']
        print('! "{}" [{}]\n'.format(params[ip].get('hostname'), ip))
        if cu.checkNotEmptyCommand(result[1]):
            print(result[1])
        else:
            print('...')
        print('\n\n')


def conf_run(args):
    '''
    Принимает параметры командной строки.
    Определяет, IP-адреса/группы заданы или файл.
    Передает всё необходимое в create_conf.
    '''
    devices = cu.parse_source_param(args.groups, args.include, args.exclude)
    if devices:
        create_conf(devices, args.database, args.template, args.adddict, args.level)


def create_parser():
    '''
    Парсер командной строки.
    '''
    desprg = 'Скрипт генерирует cisco-команду по шаблону.'
    parser = argparse.ArgumentParser(prog = 'conf-jinja-txt',
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
