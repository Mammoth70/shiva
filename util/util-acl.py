#!/usr/bin/python3
# -*- coding: utf-8 -*-
'''
Анализ файла с ACL в формате Huawei.
Преобразование ACL в формат Cisco и запись его в файл

'''

import sys
sys.path.append('..')
import argparse
import logging
import cisco_utilites as cu
import re



def change_ports(port):
    '''
    Подменяет названия протоколов, несовместимые с cisco.
    '''
    abbr = {'dns'    : 'domain'} 
    for key in abbr.keys():
        port = port.replace(key, abbr[key])
    return port



def format_acl_line(rule, protocol, so, so_mask, so_exp, so_ports, de, de_mask, de_exp, de_ports, log):
    '''
    Принимает части ACL.
    Возвращает форматированную ACL-Cisco строку.
    '''
    result = rule + ' ' + protocol + ' ' + so 
    if so_mask:
        result = result + ' ' + so_mask
    if so_exp:
        result = result + ' ' + so_exp + ' ' + so_ports
    result = result + ' ' + de
    if de_mask:
        result = result + ' ' + de_mask
    if de_exp:
        result = result + ' ' + de_exp + ' ' + de_ports
    if log:
        result = result + ' ' + log
    return result


def parse_line(line):
    '''
    Принимает и разбирает строку.   
    Если строка в формате ACL-Huawei, то возвращает форматированную ACL-Cisco строку.
    Иначе - возвращает None
    '''
    result = None
    match = re.search('rule\s+(?P<rule>(deny)|(permit))\s+(?P<protocol>\S+)', line)
    if match:
        # rule
        rule = match.group('rule')
        protocol = match.group('protocol')
        # source
        so = 'any'                                            
        so_mask = ''
        match = re.search('source\s+(?P<so>\S+)\s+(?P<so_mask>\S+)', line)
        if match:
            so = match.group('so')
            so_mask = match.group('so_mask')
            if (so_mask is '0'):
                so = 'h ' + so
                so_mask = ''
        # source-port
        so_exp = ''
        so_ports = ''
        match = re.search('source-port\s+(?P<so_exp>(eq)|(gt)|(ge))\s+(?P<so_ports>\S+)', line)
        if match:
            so_exp = match.group('so_exp')
            so_ports = change_ports(match.group('so_ports'))
        match = re.search('source-port\s+(?P<so_exp>range)\s+(?P<so_ports>\S+\s+\S+)', line)
        if match:
            so_exp = match.group('so_exp')
            so_ports = change_ports(match.group('so_ports'))
        # destination
        de = 'any'                                            
        de_mask = ''
        match = re.search('destination\s+(?P<de>\S+)\s+(?P<de_mask>\S+)', line)
        if match:
            de = match.group('de')
            de_mask = match.group('de_mask')
            if (de_mask is '0'):
                de = 'h ' + de
                de_mask = ''
        # destination-port
        de_exp = ''
        de_ports = ''
        match = re.search('destination-port\s+(?P<de_exp>(eq)|(gt)|(ge))\s+(?P<de_ports>\S+)', line)
        if match:
            de_exp = match.group('de_exp')
            de_ports = change_ports(match.group('de_ports'))
        match = re.search('destination-port\s+(?P<de_exp>range)\s+(?P<de_ports>\S+\s+\S+)', line)
        if match:
            de_exp = match.group('de_exp')
            de_ports = change_ports(match.group('de_ports'))
        # log
        log = ''
        match = re.search('\s+(?P<log>log)\s*$', line)
        if match:
            log = match.group('log')
        result = format_acl_line(rule, protocol, so, so_mask, so_exp, so_ports, de, de_mask, de_exp, de_ports, log)
    return result


def parse_acl(args):
    '''
    Принимает параметры командной строки.
    Считывает и преобразовывает файл ввода c ACL-Huawei,
    а затем записывает ACL-Cisco в файл вывода.
    '''
    txt = ''
    input_file = args.source_file
    output_file = args.output_file
    if not cu.exists_file(input_file):
        logging.error('Файл ' + input_file + ' не найден')
        return None
    with open(input_file, 'r') as f:
        for line in f:
            result = parse_line(line)
            if result:
                txt = txt + result + '\n'
    cu.print_to_file(txt, output_file)                

def create_parser():
    '''
    Парсер командной строки.
    '''
    nameprg = 'Скрипт преобразовывает ACL из формата Huawei в формат Cisco.'
    parser = argparse.ArgumentParser(prog = 'util-acl', description = nameprg, add_help = False, epilog = cu.r_copyright)
    pr_group = parser.add_argument_group (title=cu.r_params)
    pr_group.add_argument('-h', action=cu.r_help, help=cu.r_help1)
    pr_group.add_argument('-s',
                          dest='source_file',
                          required=True,
                          help='файл с ACL в формате Huawei')
    pr_group.add_argument('-o',
                          dest=cu.r_out_file,
                          default=None,
                          help='файл вывода ACL в формате Cisco (по умолчанию - на экран)')
    pr_group.set_defaults(func=parse_acl)
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
