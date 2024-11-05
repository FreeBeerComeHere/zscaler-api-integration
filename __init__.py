import json
from zia_api import API

CONFIG_FILE = 'config.example.json'

if __name__ == '__main__':
    config_file_path = '_config_files/'
    zs_api = API(f'{config_file_path}{CONFIG_FILE}')

    # Dump web dlp rules to file:
    webdlp_rules = zs_api.get_all_webdlp_rules()
    with open('webdlprules_dump.txt', 'w') as f:
        f.write(json.dumps(webdlp_rules,indent=4))
        
    # Create web dlp rules from file:
    with open('webdlprules_dump.txt', 'r') as f:
        webdlp_rules_to_create = f.read()
    webdlp_rules_to_create = json.loads(webdlp_rules_to_create)
    for webdlp_rule in webdlp_rules_to_create:
        print(type(webdlp_rule))
        resp = zs_api.create_webdlp_rule(webdlp_rule)
        print(resp)