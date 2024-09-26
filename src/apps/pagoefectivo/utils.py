from user_agents import parse


def get_device(ua_string):
    try:
        user_agent = parse(ua_string)
        if user_agent.is_mobile:
            text_user_agent = '1'
        elif user_agent.is_tablet:  # returns False
            text_user_agent = '3'
        elif user_agent.is_pc:  # returns False
            text_user_agent = '2'
        else:
            text_user_agent = '4'

        return text_user_agent
    except Exception as e:
        print(e)
        return '4'


def get_user_agent_pretty(ua_string):
    try:
        return str(parse(ua_string))
    except Exception as e:
        return ''


def get_browser_version(ua_string):
    try:
        user_agent = parse(ua_string)
        ua_family = user_agent.browser.family
        ua_version_string = user_agent.browser.version_string

        return '{ua_family} - {ua_version_string}'.format(ua_family=ua_family, ua_version_string=ua_version_string)
    except Exception as e:
        return ''


def get_os_version(ua_string):
    try:
        user_agent = parse(ua_string)
        ua_os_family = user_agent.os.family
        ua_os_version_string = user_agent.os.version_string
        if ua_os_version_string and ua_os_family:
            return '{ua_os_family} {ua_os_version_string}'.format(
                ua_os_family=ua_os_family,
                ua_os_version_string=ua_os_version_string)
        elif ua_os_family:
            return ua_os_family
        elif ua_os_version_string:
            return ua_os_version_string
        else:
            return ''
    except Exception as e:
        return ''


def get_device_user_agent(ua_string):
    try:
        user_agent = parse(ua_string)
        ua_family = user_agent.device.family
        ua_brand = user_agent.device.brand
        ua_model = user_agent.device.model

        return '{ua_family} - {ua_brand} - {ua_model}'.format(
            ua_family=ua_family,
            ua_brand=ua_brand,
            ua_model=ua_model
        )
    except Exception as e:
        return ''
