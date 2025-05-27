# Shiva

[![Python][1]][2] [![GitHub license][5]][6] [![GitHub code size in bytes][7]]()

[1]: https://img.shields.io/badge/python-3.6+-blue.svg?logo=python&logoColor=white
[2]: https://www.python.org/downloads/
[3]: https://img.shields.io/pypi/v/PyYAML.svg?logo=pypi&logoColor=white
[4]: https://pypi.python.org/pypi/
[5]: https://img.shields.io/github/license/Mammoth70/shiva.svg
[6]: LICENSE
[7]: https://img.shields.io/github/languages/code-size/Mammoth70/shiva.svg?color=teal

система автоматизации администрирования телекоммуникационного оборудования.

Утилиты предназначены:
- для автоматизации работы с оборудованием Cisco (проверялось на IOS 12, 15, XE).
- для автоматизации работы с оборудованием Cisco ASA.
- для автоматизации работы с оборудованием Cisco NEXUS.

ВНИМАНИЕ !
Все утилиты поставляются как есть (AS IS). Используйте их на свой страх и риск.
Никакой ответственности за использование утилит автор не несёт.
Будьте осторожны, внимательны и осмотрительны!
Некорректное использование утилит способно в считанные секунды уничтожить всю сеть!

## Требования
* [Python 3.6+](https://www.python.org/downloads/)
* [PyYAML](https://pypi.python.org/pypi/PyYAML)
* [Jinja2](https://pypi.python.org/pypi/Jinja2)
* [tabulate](https://pypi.python.org/pypi/tabulate)
* [textfsm](https://pypi.python.org/pypi/textfsm)
* [netmiko](https://pypi.python.org/pypi/netmiko)
* [paramiko](https://pypi.python.org/pypi/paramiko)

## Установка
Склонировать репозиторий:
```bash
git clone https://github.com/Mammoth70/shiva.git
cd shiva
```
Установить пакеты:
```bash
pip install -r requirements.txt
```

## Лицензирование
This project is licensed under the **GNU General Public License v3.0 (GPLv3)**  
See the [LICENSE](LICENSE) file for details.  
Copyright 2025 Andrey Yakovlev <andrey-yakovlev@yandex.ru>
