
from src.url import URL

class CloudAppURLMapping:
    def __init__(self, cloud_app_mapping_file_content_file_path = None):
        """Builds a database of URLs and their corresponding Cloud Applications based on a CSV file. Generate this file using pstools/urlcat.

        Args:
            cloud_app_mapping_file_content_file_path (str): Path to the file containing the URL to Cloud app mapping.
        """
        print(f'Building Cloud App to URL mapping database')
        if cloud_app_mapping_file_content_file_path == None:
            raise ValueError('Cloud App mapping requested but file not provided')
        else:
            self.cloud_app_map = []
            with open(cloud_app_mapping_file_content_file_path, 'r') as cloud_app_mapping_file_content_f:
                cloud_app_mapping_file_content = cloud_app_mapping_file_content_f.readlines()        
            for url_to_cloud_app_map in cloud_app_mapping_file_content:
                map_as_list = url_to_cloud_app_map.split(',')
                if len(map_as_list) > 3:
                    url = map_as_list[0].strip('"').strip("'")
                    cloud_app = map_as_list[3].strip('"').strip("'")
                    if len(cloud_app) > 0:
                        self.cloud_app_map.append(
                            {
                                'url': url,
                                'cloud app': cloud_app,
                                }
                        )
            print(f'Completed')
            # print(cloud_app_map)
        
    def add_cloud_app_for_url(self, url :URL):
        # print(url.url_details['Url'])
        for mapping in self.cloud_app_map:
            # print(f'Checking for match between mapping data URL "{mapping['url']}" and URL object URL "{url.url_details['Url']}"')
            if mapping['url'] == url.url_details['Url']:
                # print('Expanding URL object data with cloud app')
                url.url_details['Cloud App'] = mapping['cloud app']
                # print(url)