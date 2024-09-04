{#-
    Шаблон Include (в формате jinja2) настройки инкапсуляции саб-интерфейса
    параметры:
        IF.INTF - название саб-интерфейса, из которого определяется номер инкапсулированного vlan-а
-#}
{%- if IF and IF.INTF and (IF.INTF is trunk) %}
 encapsulation dot1Q {{ IF.INTF|intf_to_encapsulation}}
{%- endif -%}