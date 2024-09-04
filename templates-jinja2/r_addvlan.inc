{#-
    Шаблон Include (в формате jinja2) объявление vlan на маршрутизаторе
    параметры:
        namevlan - имя vlan-а
        IF.INTF  - название интерфейса
-#}
{%- if namevlan and IF and IF.INTF and IF.INTF.startswith('Vl') -%}
vlan {{ IF.INTF|intf_to_vlan }}
 name {{ namevlan }}
exit
{%- endif -%}
