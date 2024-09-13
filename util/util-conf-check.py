#!/usr/bin/python3 
# -*- coding: utf-8 -*-
'''
Анализ структуры конфигурационного файла.
Проверка объявления используемых объектов.
Проверка использования объявленных объектов.

'''
import sys
sys.path.append('..')
import re
import cisco_utilites as cu
import argparse


#DB =  {
#'interface' : {                                 # Название объекта
#    'declared' : [                              # список regexp-ов для поиска объявленных объектов
#        r'^interface (?P<name>\S+)$'            
#        ]
#    'declared_added' : ['default']              # Список объектов, которые нужно добавить к объявленным
#    'used' : [                                  # список regexp-ов для поиска использованных объектов
#        r'[ -]interface (?P<name>\S+)$'
#        ], 
#    'check_unused' : False,                     # флаг проверки объявленных, но не использованных объектов
#    'declared_used' : []                        # Список объектов, которые нужно добавить к использованным
#}


# Глобальные переменные
lines = []      # Список строк конфигурационного файла, начальные и конечные пробелы обязательно сохраняются
tree = {}       # Cловарь секций, где key - номер строки, а value - номер строки начала секции.
location = {}   # Cловарь, где key - объект, а value - номер строки, где он встретился


def load_conf_from_text(input_file):
    '''
    Загружает в список list конфигурацию из файла.
    Делает словарь секций tree, где key - номер строки, а value - номер строки начала секции.
    '''
    global lines
    global tree
   
    with open(input_file, 'r') as f:
        lines = [line.strip(('\n\r')) for line in f]

    parent = 0
    for num, line in enumerate(lines):
        if not line.startswith(' '):
            parent = num
        tree[num] = parent

    return None


def load_obj(regex, debug=False):
    '''
    Заполняет множество объявленных любых объектов из списка.
    Делает словарь location, где key - объект, а value - номер строки, где он встретился.
    '''
    global lines
    global location
    objs = set()
    for num, line in enumerate(lines):
        match = re.search(regex, line)
        if match:
            obj = match.group('name')
            if debug:
                print(obj)
            objs.add(obj)
            location[obj] = num
    return objs


def print_check_objs_err(num, name, objname):
    '''
    Выводит ошибку необъявленного объекта и текст, в котором она встретилась.
    '''
    global lines
    global tree
    if tree[num] == num:
        print('\n{0}\n   >>> не объявлен, но используется {2} \"{3}\" (строка {1}) <<<'.format(lines[num], num+1, objname, name))
    elif tree[num] == (num-1):
        print('\n{0}\n{1}\n   >>> не объявлен, но используется {3} \"{4}\" (строка {2}) <<<'.format(lines[tree[num]], lines[num], num+1, objname, name))
    else:
        print('\n{0}\n ...\n{1}\n   >>> не объявлен, но используется {3} \"{4}\" (строка {2}) <<<'.format(lines[tree[num]], lines[num], num+1, objname, name))
    return None


def print_check_objs_used_err(s, objname):
    '''
    Выводит ошибку объявленного, но неиспользованного объекта.
    '''
    global lines
    global location
    for obj in s:
        print('\n{0}\n   >>> объявлен, но не используется {2} \"{3}\" (строка {1}) <<<'.format(lines[location[obj]], location[obj]+1, objname, obj))
    return None


def check_objs(regex, objs, objname, debug=False):
    '''
    Проверяет строки c любыми объектами на наличие объекта.
    '''
    global lines
    objs_used = set()
    for num, line in enumerate(lines):
        match = re.search(regex, line)
        if match:
            obj = match.group('name')
            if debug:
                print(obj)
            objs_used.add(obj)
            if obj not in objs:
                print_check_objs_err(num, obj, objname)
    return objs_used


def check_objs_used(objs, objs_used, objname):
    '''
    Проверяет наличие объявленных, но не использованных объектов.
    '''
    s = objs - objs_used
    if (len(s) > 0):
        print_check_objs_used_err(s, objname)
    return None


def conf_run(args):
    if cu.exists_file(args.source):
        print('Проверка конфигурации из файла {}'.format(args.source))
        load_conf_from_text(args.source)

        DB = cu.load_from_file(args.database)

        for key in DB.keys():
            # Загрузка описаний объектов
            objects = set()
            for regex in DB[key].get('declared', []):
                objects = objects | load_obj(regex, DB[key].get('debug_load', False))
            for added in DB[key].get('declared_added', []):
                objects.add(added)

            # Проверка объявления использованных объектов
            objects_used = set()
            for regex in DB[key].get('used', []):
                objects_used = objects_used | check_objs(regex, objects, key, DB[key].get('debug_check', False))
            for added in DB[key].get('used_added', []):
                objects_used.add(added)

            # Проверка использования объявленых объектов
            if DB[key].get('check_unused', True):
                check_objs_used(objects, objects_used, key)
    else:
        print('\nФайл {} не найден'.format(args.source))

    return None


def create_parser():
    '''
    Парсер командной строки.
    '''
    desprg = 'Скрипт анализирует правильность объявления и использования объектов конфигурационного файла.'
    parser = argparse.ArgumentParser(prog = 'util-conf-check',
                                        description = desprg,
                                        add_help = False,
                                        epilog = cu.r_copyright )
    pr_group = parser.add_argument_group (title=cu.r_params)
    pr_group.add_argument('-h', action=cu.r_help, help=cu.r_help1)
    pr_group.add_argument('-d',
                          dest='database',
                          default='util-conf-check.yml',
                          help='база данных объектов конфигурации')
    pr_group.add_argument('-s',
                          dest='source',
                          required=True,
                          help='конфигурационный файл')
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
