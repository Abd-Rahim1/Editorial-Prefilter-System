"""
Configuration for editorial rules.
Dynamically retrieved from PostgreSQL via ConfigRepository.
"""

def get_rule_config():
    try:
        from database.config_repository import ConfigRepository
        return ConfigRepository().get_editorial_rules()
    except Exception:
        return {}


class _RuleConfigProxy(dict):
    def __getitem__(self, key):
        return get_rule_config().get(key)
    
    def get(self, key, default=None):
        return get_rule_config().get(key, default)
    
    def __repr__(self):
        return repr(get_rule_config())

    def items(self):
        return get_rule_config().items()

    def keys(self):
        return get_rule_config().keys()

    def values(self):
        return get_rule_config().values()


RULE_CONFIG = _RuleConfigProxy()

