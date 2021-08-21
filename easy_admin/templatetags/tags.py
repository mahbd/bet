from django import template

register = template.Library()


@register.inclusion_tag('easy_admin/easy_table.html')
def easy_table(table_data):
    return table_data


@register.inclusion_tag('easy_admin/link_buttons_group.html')
def link_buttons_group(buttons):
    return {'buttons': buttons}


@register.inclusion_tag('easy_admin/enable_field_button.html')
def enable_f_button(field_id):
    return {'field_id': field_id}


# @register.inclusion_tag('easy_admin/enable_field_button.html')
# def user_list_table_club(users):
#     table_header = (
#         ('', 'ID'),
#         ('', 'Joining Date'),
#         ('', 'Last Bet'),
#         ('', 'Name'),
#         ('', 'Username'),
#         ('', 'Total Bet'),
#         ('', 'Commission'),
#     )
#     table_body = [
#         (user.id, user.join_date, user.last_bet, user.get_full_name(),
#          user.username, user.total_bet, user.commission) for user in users]
#     table_data = {
#         'table_header': table_header,
#         'table_body': table_body,
#     }
#     return {'table_data': table_data}


@register.filter
def join_s(a, b):
    return str(a) + str(b)
