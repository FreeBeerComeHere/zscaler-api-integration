from url import URL
from cloud_app_url_mapping import CloudAppURLMapping
import mimetypes
import pandas as pd
import re
import json
import time
import requests
import os

DEBUG = True

cloud_app_types = [
  "SOCIAL_NETWORKING",
  "STREAMING_MEDIA",
  "WEBMAIL",
  "INSTANT_MESSAGING",
  "BUSINESS_PRODUCTIVITY",
  "ENTERPRISE_COLLABORATION",
  "SALES_AND_MARKETING",
  "SYSTEM_AND_DEVELOPMENT",
  "CONSUMER",
  "HOSTING_PROVIDER",
  "IT_SERVICES",
  "FILE_SHARE",
  "DNS_OVER_HTTPS",
  "HUMAN_RESOURCES",
  "LEGAL",
  "HEALTH_CARE",
  "FINANCE",
  "CUSTOM_CAPP",
  "AI_ML"
]


    
class URLCat:
    def __init__(self, name, urlcontents, keywords):
        self.name = name
        self.urlcontents = urlcontents
        self.keywords = keywords
        
    def __str__(self) -> str:
        return f'This is a URL category: Name: {self.name}, URLcontents: {self.urlcontents}, Keywords: {self.keywords}'

class URLCategories:
    def __init__(self) -> None:
        self.urlcategories = []
    def add(self, urlcat :URLCat):
        self.urlcategories.append(urlcat)
    def in_url_categories(self, url :URL):
        part_of_these_urlcats = []
        for urlcat in self.urlcategories:
            # print(f'comparing {url.url_details["Url"]} and {urlcat.urlcontents}')
            if url.url_details["Url"] in urlcat.urlcontents or f'.{url.url_details["Url"]}' in urlcat.urlcontents:
                part_of_these_urlcats.append(urlcat.name)
        return part_of_these_urlcats
    def show_url_cat_contents(self):
        for urlcat in self.urlcategories:
            print(urlcat)
    def get_len(self):
        return len(self.urlcategories)

class API():
    def __init__(self,configFileLocation):
        if os.path.exists('sessionid.txt') and os.path.getsize('sessionid.txt') > 0:
            with open('sessionid.txt','r') as file:
                content = file.read()
            self.sessionId = content
        else:
            self.sessionId = None
        try:
            with open(configFileLocation, 'r') as f:
                data = json.load(f)
        except Exception as e:
            print(f"An error occured while reading the configuration file:\n{e}")
        else:
            self.base_url = data.get('base_url')
            self.admin = data.get('admin')
            self.password = data.get('password')
            self.key = data.get('api_key')
            
            # Get additional data from config file - these might not exist!
            self.csb_url = data.get('csb_url')
            self.csb_api_key = data.get('csb_api_key')
            self.headers = {'Content-Type': 'application/json','Cache-Control': 'no-cache'}
            
        self.urlcategories = URLCategories()
        
        if not self.logon_to_api():
            raise RuntimeError('Unable to logon to API. Quitting.')
    def _obfuscate_api_key(self,seed):
        now = int(time.time() * 1000)
        n = str(now)[-6:]
        r = str(int(n) >> 1).zfill(6)
        key = ""
        for i in range(0, len(str(n)), 1):
            key += seed[int(str(n)[i])]
        for j in range(0, len(str(r)), 1):
            key += seed[int(str(r)[j])+2]
        return now,key
    def logon_to_api(self):
        if self.is_api_successfully_connected():
            print(f"Session already established!")
        else:
            url = '/authenticatedSession'
            timestamp,key = self._obfuscate_api_key(self.key)
            print("Logging on to API...")
            payload= {
                "apiKey": key,
                "username": self.admin,
                "password": self.password,
                "timestamp": timestamp
                }
            try:
                response = requests.request("POST", headers=self.headers, url=self.base_url + url, data=json.dumps(payload))
            except Exception as e:
                print(f"An error occured while connecting to the API:\n{e}")
                return False
            else:
                if 'authType' in response.text:
                    self.sessionId = response.cookies['JSESSIONID']
                    # print(response.cookies)
                    print(f"Logged on!")
                    self._write_session_id()
                    # self.show_session_id()
                else:
                    print(f"Authentication failed: {response.status_code} {response.text}")
                    return False
        return True
    def logout_of_api(self):
        # user_input = input("Do you want to activate before logging out? (Y/N): ").upper()
        # if user_input == "Y":
        #     self.activate()
        # else:
        #     print("Skipping activation")

        print('Will now log out of API. ', end='')
        url = '/authenticatedSession'
        
        cookies={'JSESSIONID': self.sessionId }
        payload={}

        try:
            response = requests.request("DELETE", self.base_url + url, cookies=cookies, data=payload)
        except Exception as e:
            print(f"An error occurred while logging out of the API:\n{e}")
        else:
            print(f"Logged out of the API. Response code {response.status_code}")
    def show_session_id(self):
        print(f"JSESSIONID is {self.sessionId}")
    def _write_session_id(self):
        with open('sessionid.txt','w') as file:
            file.write(self.sessionId)
    def is_api_successfully_connected(self) -> bool:
        url = '/authenticatedSession'        
        response = self._call_api(method='GET', url=url)
        if 'authType' in json.loads(response.text).keys() and json.loads(response.text).get('authType') == 'ADMIN_LOGIN':
            if json.loads(response.text).get('loginName') == self.admin:
                # The logged in session is for the proper administrator
                return True
            else:
                self.logout_of_api()
                self.logon_to_api()
                return False
        return False
    def _call_api(self, method, url, **kwargs):
        # print(data)
        url = self.base_url + url
        if 'data' not in kwargs and method in ['post','POST']:
            print('ERROR: POSTing without data!')
            raise RuntimeError('POSTing without data!')
        else:
            data = kwargs['data'] if 'data' in kwargs else ''
            params = kwargs['params'] if 'params' in kwargs else ''
            cookies={'JSESSIONID': self.sessionId }
            retry_required = True
            while retry_required:
                response = requests.request(method=method, url=url, cookies=cookies, headers=self.headers, data=data, params=params)
                
                if response.status_code == 429:
                    # Rate limit exceeded
                    retry_required = True
                    print(f'Response: HTTP {response.status_code} - {response.text} - will retry')
                    time.sleep(2)
                    
                elif response.status_code == 400:
                    # Request error
                    retry_required = False
                    print(f'Response: HTTP {response.status_code} - {response.text} - will NOT retry')
                    
                elif response.status_code == 204:
                    # Successful. No content returned.
                    retry_required = False
                    # print(f'Response: HTTP {response.status_code} - {response.text} - will NOT retry')
                    
                elif response.status_code == 200:
                    retry_required = False
                
                else:
                    print(f'Unknown response: {response.status_code} - {response.text}. Will not retry.')
                    retry_required = False
            return response
    def activate(self):
        url = '/status/activate'
        data={}        
        # response = requests.request("POST", self.base_url + url, cookies=cookies, data=payload)
        response = self._call_api('post', url=url, data=data)
        activateStatusCode = str(response.status_code)
        print(f"Activation attempted, return code is: {activateStatusCode}")
    def get_location_overview(self, location_id=0):
        url = '/locations' if location_id == 0 else f'/locations/{location_id}'
        data={}
        
        response = self._call_api(method="get", url=url, data=data)
        # print(response.text)
        print(json.dumps(json.loads(response.text),indent=5))
    def get_sublocation_overview(self, parent_location_id):
        url = f'/locations/{parent_location_id}/sublocations'
        response = self._call_api(method='get', url=url)
        sublocations = json.loads(response.text)
        list_of_sublocation_ids = [sublocation['id'] for sublocation in sublocations]
        return list_of_sublocation_ids
    def add_sublocation(self, parent_location_id, name, ipaddresses:list):
        url = '/locations'
        payload = {
            "name": name,
            "parentId": parent_location_id,
            # "country": "",
            # "tz": "NOT_SPECIFIED",
            # "city": "TBD",
            "ipAddresses": ipaddresses
        }
        response = self._call_api(method="post", url=url, data=json.dumps(payload))
        print(response.text)
    def delete_location(self, location_id):
        url = f'/locations/{location_id}'
        
        response = self._call_api(method="delete", url=url)
        print(response.text)   
    def getFWPol(self):
        url = '/firewallFilteringRules'
        data={}
        # response = requests.request("GET", self.base_url + url, cookies=cookies, data=payload)
        response = self._call_api(method='get', url=url, data=data)
        responseJSON = json.loads(response.text)
        for i in responseJSON:
            print(i['name'])
    def add_user(self, name, email, groups, department):
        url = '/users'
        cookies={'JSESSIONID': self.sessionId }
        payload = {'name': name,
                   'email': email,
                   'groups': [{
                       'id': 90097456,
                       'name': 'asdf'
                       }],
                   'department':
                       {
                           'id': 20521909,
                           'name': 'Default'
                           },
                   'comments': '',
                   'password': 'Usertemp@123',
                    'adminUser': False
                   }
                
        payload = json.dumps(payload)
        response = requests.request("POST", self.base_url + url, cookies=cookies, data=payload)
        print(response.status_code)
        print(response.text)
    def get_users(self):
        url = '/users?page=1&pageSize=1000'
        cookies={'JSESSIONID': self.sessionId }
                        
        response = requests.request("GET", self.base_url + url, cookies=cookies)
        return json.loads(response.text)
    def delete_user(self, userid):
        url = f'/users/{userid}'
        cookies={'JSESSIONID': self.sessionId }
        
                        
        response = requests.delete(self.base_url + url, cookies=cookies)
        while re.search('^429', str(response.status_code)):
            print(f'API rate limit, sleeping. Response: {response.status_code} {response.text}')
            time.sleep(2)
            response = requests.delete(self.base_url + url, cookies=cookies)
        print(f'{response.status_code}: {response.text}')
    def add_ip_address(self, ip_address):
        url = f'/staticIP'
        cookies={'JSESSIONID': self.sessionId }
        
        
        # payload = {'ipAddress:': ip_address,
        #            'geoOverride': False,
        #            'latitude': 0,
        #            'longitude': 0,
        #            'routableIP': True,
        #            'comment': 'added through api'
        #            }
        payload = {"ipAddress": ip_address}
        
        response = requests.post(self.base_url + url, cookies=cookies, data=json.dumps(payload))
        print(response.status_code)
        print(response.text)
    def _split_list(self, urllist :list, chunk_size :int =100):
        for i in range(0,len(urllist), chunk_size):
            yield urllist[i:i + chunk_size]
    def url_lookup(self, urls_to_check :list):
        url = f'/urlLookup'
        """Takes a list of URLs and checks it against the ZS default URL
        categories and security classificiation database

        Args:
            urls_to_check (list): URL(s) to verify

        Returns:
            list: All URL data as a list of dicts
        """
        # print(f'printing what urllookup received: {urls_to_check} - {len(urls_to_check)} - {type(urls_to_check)}')
        if type(urls_to_check) == list:
            if len(urls_to_check) > 100:
                # List has more than 100 items and we need to split it up
                urls_to_check = list(self._split_list(urls_to_check))
            else:
                # List has less than 100 items
                new_list = []
                new_list.append(urls_to_check)
                urls_to_check = new_list

        # urls_to_check is a list inside a list!
        
        elif type(urls_to_check) == str:
            new_list = []
            new_list.append(urls_to_check)
            urls_to_check = new_list
        
        else:
            raise TypeError(f'urls_to_check should be <list> or <str>, received {type(urls_to_check)}')
        
        # Look up all URLs in chunks of 100 (this is what the API supports)
        all_responses = []
        for url_chunk_100 in urls_to_check:
            # print(f'This is what were sending to lookup: {url_chunk_100}')
            response = self._call_api(method='post', url=url, data=json.dumps(url_chunk_100))
            # print(response.status_code)
            all_responses += json.loads(response.text)
            print(f'Looked up {len(all_responses)} URLs.') if DEBUG else 0
            # print(all_responses)
        print('## FINISHED URL LOOKUP ##')
        return all_responses
    def get_all_url_category_names(self, only_custom :bool = True, get_id :bool = True, get_name :bool = True):
        url = f'/urlCategories?customOnly={str(only_custom).lower()}'
        
        response = self._call_api(method='get', url=url)
        resp_json = json.loads(response.text)
        categories = []
        for urlcat in resp_json:
            url_dict = {}
            if get_id:
                url_dict['id'] = urlcat['id']
            if get_name:
                if 'configuredName' in urlcat:
                    url_dict['name'] = urlcat['configuredName']
                else:
                    url_dict['name'] = urlcat['id']
            categories.append(url_dict)
        return categories
    def delete_urlcategory(self, catid):
        url = f'/urlCategories/{catid}'
        response = self._call_api(method='delete', url=url)
        # requests.delete(self.base_url + url, cookies=cookies)
        print(f'{response.status_code}')
    def build_custom_url_classifications(self):
        url = f'/urlCategories?customOnly=true'
        if self.urlcategories.get_len() == 0:
            response = self._call_api(method='get', url=url)
            print(response.status_code)
            custom_urls = json.loads(response.text)
            for urlcat in custom_urls:
                allurls = []
                allkeywords = []
                if 'urls' in urlcat.keys():
                    allurls += urlcat['urls']
                if 'dbCategorizedUrls' in urlcat.keys():
                    allurls += urlcat['dbCategorizedUrls']
                
                if 'keywords' in urlcat.keys():
                    allkeywords += urlcat['keywords']
                if 'keywordsRetainingParentCategory' in urlcat.keys():
                    allkeywords += urlcat['keywordsRetainingParentCategory']

                # Build Custom category list:
                self.urlcategories.add(URLCat(name=urlcat['configuredName'], urlcontents=allurls, keywords=allkeywords))
        return self.urlcategories
    def check_if_url_is_in_urlcategory(self, url_to_check :URL):
        url_cats_for_this_url = self.urlcategories.in_url_categories(url_to_check)
        return url_cats_for_this_url
    def bulk_url_lookup(
            self,
            filename :str,
            custom_lookup :bool =False,
            export :bool = False,
            include_cloud_apps :bool = False,
            cloud_app_mapping_file :str = None
            ) -> list:
        """Does a bulk lookup of URLs based on a file

        Args:
            filename (str): Path to a file containing the URLs we need to lookup
            custom_lookup (bool, optional): Do you want to lookup the custom URL configuration as well? Defaults to True.
            export (bool, optional): Exports the data to XLS. Defaults to False.

        Returns:
            list: A list of dicts that hold the URL database classification
        """
        # Read file
        with open(filename, 'r') as file:
            contents = file.readlines()
            stripped_urls = [url.rstrip('\n') for url in contents]
        # print(stripped)
        looked_up_urls = self.url_lookup(stripped_urls)
        url_objects = []
        for url in looked_up_urls:
            if type(url) == dict:
                u = URL(url['url'])
                u.url_details['Zscaler default URL category'] = ', '.join(url['urlClassifications'])
                u.url_details['Zscaler security classification'] = ', '.join(url['urlClassificationsWithSecurityAlert'])
                url_objects.append(u)
            else:
                print(f'"{url}" is {type(url)}, not dict. Skipping.')
         
        if custom_lookup == True:
            # If we want to check for the URL in the custom URL categories, we need to pull them from the API:
            self.build_custom_url_classifications()
            for url in url_objects:
                # print(f'{type(url)} - {url}')
                url.url_details['Custom URL categories'] = self.check_if_url_is_in_urlcategory(url)
        
        # Translate the list of URL objects into a list of dicts
        url_list_of_dicts = [url.url_details for url in url_objects]
        
        if include_cloud_apps:
            ca_url_mapping = CloudAppURLMapping(cloud_app_mapping_file)
            for url in url_objects:
                ca_url_mapping.add_cloud_app_for_url(url)
        
        if export:
            # Rework the filename
            path, filename = os.path.split(filename)
            if len(path) == 0:
                path = '.'
            new_file = f'{path}/{filename}.xlsx'
            # Create a pandas.Dataframe from the list of dicts and export to Excel
            print(f'Exporting file to {new_file}...')
            try:
                pd.DataFrame.from_records(url_list_of_dicts).to_excel(new_file)
            except OSError as ose:
                print(f'An error occurred while exporting the file. Does the path exist and is it writeable? Error details:\n{ose}')
                # print(f'Dumping URL data:\n{url_list_of_dicts}')
            except Exception as e:
                print(f'An error occurred while exporting the file:\n{e}')
                # print(f'Dumping URL data:\n{url_list_of_dicts}')
            else:
                print(f'File exported successfully: {new_file}')
                                
        return url_list_of_dicts
    def get_cloud_applications(self, sort :bool =False) -> list:
        """Downloads all Zscaler defined cloud applications and returns them as a (sorted) list of dicts
        
        Args:
            sorted (bool, optional): should we sort the list before returning?

        Returns:
            list: A list containing all cloud applications as dicts with id & name keys
        """
        # Get API call ready:        
        url = f'/cloudApplications/lite'
        cookies={'JSESSIONID': self.sessionId }
        
        # Create a new list that will store all Cloud Apps
        all_cloud_apps = []
        
        # We need to keep track of pages as we might need to download for more than one page
        page_number = 0
        
        # Loop through all of the API responses:
        prev_list_is_full = True
        while prev_list_is_full == True:
            response = requests.get(self.base_url + url + f'?pageNumber={page_number}&limit=50000', cookies=cookies)
            # print(f'Page {page_number}: {response.status_code}')
            
            while re.search('^429', str(response.status_code)):
                print(f'API rate limit, sleeping. Response: {response.status_code} {response.text}')
                time.sleep(2)
                response = requests.get(self.base_url + url + f'?pageNumber={page_number}&limit=50000', cookies=cookies)
            
            # Store the response (this should be a list of dicts)
            response = json.loads(response.text)
            
            # Add the response list to the existing list
            all_cloud_apps += response
            
            # Increment the page number so we can download the next page if required
            page_number += 1
            
            # We don't need another API call in case the previous list did not contain 1000 entries
            # (that would mean we've reached the end of the list)
            if len(response) > 1000:
                prev_list_is_full = False
                
        # We will sort the list and return that if request in the method call
        if sort == True:
            return sorted(all_cloud_apps, key=lambda name: name['name']) 
        return all_cloud_apps
    def upload_to_csb(self, file_location=''):
        # Get API call ready:
        # url = f'{self.csb_url}/zscsb/submit'
        url = f'{self.csb_url}/zscsb/submit'
        cookies={'JSESSIONID': self.sessionId }
        params = {'force': 0,
                  'api_token': self.csb_api_key}
            
        files = { 'file': (os.path.basename(file_location), open(file_location, 'rb'), mimetypes.guess_type(file_location)[0]) }
        # print(files)
        response = requests.post(url=url, cookies=cookies, params=params, files=files)
        # response = requests.post(url=url, cookies=cookies, params=params, files={ 'file':open(file_location,'rb')})
        # while re.search('^429', str(response.status_code)):
        #     print(f'API rate limit, sleeping. Response: {response.status_code} {response.text}')
        #     time.sleep(2)
        #     response = requests.get(self.base_url + url + f'?pageNumber={page_number}&limit=50000', cookies=cookies)
        
        # response = json.loads(response.text)
        print(response)
        print(response.text)
    def get_csb_report(self, md5):
        """Download the Cloud Sandbox report for a specific MD5

        Args:
            md5 (string): The MD5 checksum of the file you want to download a report for
        """
        url = f'{self.base_url}/sandbox/report/{md5}'       
        params = {'details': 'full'}
        response = self._call_api('get', url=url, params=params)
        print(response)
        print(response.text)
    def get_csb_quota(self):
        url = f'{self.base_url}/sandbox/report/quota'
        cookies={'JSESSIONID': self.sessionId }
        
        response = requests.get(url=url, cookies=cookies)
        print(response)
        print(response.text)
    def create_url_category(self, url_category_name:str, urls:list, ip_ranges:list=[], description:str=''):
        """Creates a URL category in the Zscaler admin portal. By default, it adds content to the respective "retaining parent category" configuration.

        Args:
            url_category_name (string): URL category name
            urls (list): URLs to include in this URL category.
            ip_ranges (list, optional): IP ranges to include in this URL category.
            description (str, optional): URL category description.

        Returns:
            Response: _description_
        """
        url = '/urlCategories'
        data = {
            'configuredName': url_category_name,
            'superCategory': 'USER_DEFINED',
            'dbCategorizedUrls': urls,
        }
        
        if len(ip_ranges) > 0:
            data['ipRangesRetainingParentCategory'] = ip_ranges
        if len(description) > 0:
            data['description'] = description
        resp = self._call_api(method='post', url=url, data=json.dumps(data))
        print(resp.status_code)
        return resp
    def get_custom_url_category_id_by_name(self, url_category_name:str):
        all_cats = self.get_all_url_category_names(only_custom=True)
        for cat in all_cats:
            if cat['name'] == url_category_name:
                return cat['id']
    def get_location_id_by_name(self, location_name :str, is_sublocation :bool =False):
        location_list = []
        if is_sublocation:
            all_locations = self.get_all_sublocations()
        else:
            # all_locations = self.get_all_locations()
            all_locations = self.get_all_locations()
        # print(type(all_locations))
        for location in all_locations:
            if location['name'] == location_name:
                location_list.append(location['id'])
        if len(location_list) > 1:
            raise ValueError('Multiple sublocations found!')
        else:
            return location_list[0]
    def get_all_sublocations(self) -> list:
        all_sublocations = []
        parent_location_ids = [location['id'] for location in json.loads(self.get_all_locations())]
        for parent_location in parent_location_ids:
            url = f'/locations/{parent_location}/sublocations'
            resp = self._call_api(method='get', url=url)
            all_sublocations.append(json.loads(resp.text))
        # Remove nested list structure
        cleaned_up_location_list = []
        for sublocation in all_sublocations:
            if type(sublocation) == list:
                for sl in sublocation:
                    cleaned_up_location_list.append(sl)
            else:
                cleaned_up_location_list.append(sublocation)
        return cleaned_up_location_list
    def get_all_locations(self) -> str:
        url = f'/locations'
        response = self._call_api(method='get', url=url)
        return response.text
    def _get_locationgroup_id_by_name(self, location_group_name:str):
        all_location_groups = self.get_all_location_groups()
        for location_group in all_location_groups:
            if location_group['name'] == location_group_name:
                return location_group['id']
    def get_all_location_groups(self):
        url = f'/locations/groups'
        response = self._call_api(method='get', url=url)
        return response.text
    def create_url_filtering_policy(self, url_filtering_policy_name:str, location_ids:list, url_category_ids:list, description:str='', state='disabled'):
        url = f'/urlFilteringRules'
        data = {
            'name': url_filtering_policy_name,
            'urlCategories': url_category_ids,
            'rank': 7,
            'order': self._get_last_url_filtering_policy_order()+1,
            'description': description,
            'action': 'ALLOW',
            'protocols': ['ANY_RULE'],
            'state': state.upper(),
        }
        if len(location_ids) > 0:
            list_of_location_ids = location_ids
            data['locations'] = location_ids
        print(data)
        response = self._call_api(method='post', url=url, data=json.dumps(data))
        print(response.text)
    def _get_last_url_filtering_policy_order(self) -> int:
        url = f'/urlFilteringRules'          
        highest_rule_order = 0
        url_filtering_policies = self.get_all_url_filtering_rules()
        if len(url_filtering_policies) == 0:
            return 0
        else:
            for url_filtering_policy in url_filtering_policies:
                if url_filtering_policy['order'] > highest_rule_order:
                    highest_rule_order = url_filtering_policy['order']
        return int(highest_rule_order)
    def get_all_url_filtering_rules(self, only_ids:bool=False) -> list:
        url = f'/urlFilteringRules'
        
        response = self._call_api(method='get', url=url)
        if only_ids:
            list_of_ids = [url_filtering_rule["id"] for url_filtering_rule in json.loads(response.text)]
            return list_of_ids
        return json.loads(response.text)
    def delete_url_filtering_rule(self, rule_id:str='0'):
        url = f'/urlFilteringRules/{rule_id}'
        
        response = self._call_api(method='delete', url=url)
        print(response.status_code)       
    def create_cloud_app_policy(self, rule_type, cloud_app_name):
        if rule_type in cloud_app_types:
            url = f'/webApplicationRules/{rule_type}'
            cloud_app_info = self._find_cloud_app_id_and_name(cloud_app_name)
            data = {
                'name': 'name',
                'rank': 7,
                'order': self._get_last_cloud_app_control_policy_order(rule_type)+1,
                'actions': [
                    "ALLOW_SOCIAL_NETWORKING_VIEW",
                    # "ALLOW_SOCIAL_NETWORKING_POST",
                    # "ALLOW_SOCIAL_NETWORKING_CREATE",
                    # "ALLOW_SOCIAL_NETWORKING_EDIT",
                    # "ALLOW_SOCIAL_NETWORKING_SHARE",
                    # "ALLOW_SOCIAL_NETWORKING_COMMENT",
                    # "ALLOW_SOCIAL_NETWORKING_UPLOAD",
                    # "ALLOW_SOCIAL_NETWORKING_CHAT",
                    ],
                'applications': [
                    {
                        'val': cloud_app_info['id'],
                        # 'backendName' : 'FACEBOOK',
                        # 'originalName': 'Facebook',
                    }
                ]
            }
            print(data)
            
            response = self._call_api(method='post', url=url, data=json.dumps(data))
            print(response.text)
        return False
    def _get_last_cloud_app_control_policy_order(self, rule_type):
        url = f'/webApplicationRules/{rule_type}'
        
        cloud_app_control_policies = json.loads(self._call_api(method='get', url=url).text)
        # print(cloud_app_control_policies)
        highest_rule_order = 0
        if len(cloud_app_control_policies) == 0:
            return 0
        else:
            for cloud_app_control_policy in cloud_app_control_policies:
                if cloud_app_control_policy['order'] > highest_rule_order:
                    highest_rule_order = cloud_app_control_policy['order']
        return int(highest_rule_order)
    def _find_cloud_app_id_and_name(self, querystring):
        page_number = 0
        list_of_cloud_apps = []
        reached_end_of_list = False
        while not reached_end_of_list:
            url = f'/cloudApplications/lite?pageNumber={page_number}&limit=10000'
            response = json.loads(self._call_api(method='get', url=url).text)
            if len(response) == 0:
                reached_end_of_list = True
            else:
                for cloud_app in response:
                    list_of_cloud_apps.append(cloud_app)
                page_number+=1
        
        for cloud_app in list_of_cloud_apps:
            if cloud_app['name'] == querystring:
                return cloud_app
        return False
    def get_all_webdlp_rules(self):
        url = '/webDlpRules'
        response = self._call_api(method='get', url=url)
        return json.loads(response.text)
    def delete_webdlp_rule(self, rule_id:str):
        url = f'/webDlpRules/{rule_id}'
        response = self._call_api(method='delete', url=url)
        return response.status_code
    def create_webdlp_rule(self, data:dict):
        url = f'/webDlpRules'
        response = self._call_api(method='post', url=url, data=json.dumps(data))
        return response.text
