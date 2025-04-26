"""
    Name: 
        convert-markdown-to-json
        
    Author: 
        Emilien Socchi

    Description:  
         convert-markdown-to-json converts roles and permissions already categorized in specific tiers from Markdown to JSON.

    Requirements:
        - A service principal with the following access:
            1. Granted application permissions in MS Graph:
                a. 'RoleManagement.Read.Directory' (to read Entra role definitions)
                b. 'Application.Read.All' (to read the definitions of application permissions)
            2. Granted Azure role actions on the Tenant Root Management Group:
                a. Microsoft.Authorization/roleAssignments/read
                b. Microsoft.Authorization/roleDefinitions/read
                c. Microsoft.Management/managementGroups/read
                d. Microsoft.Resources/subscriptions/read
                e. Microsoft.Resources/subscriptions/resourceGroups/read
                f. Microsoft.Resources/subscriptions/resourceGroups/resources/read
        - Valid access tokens for ARM and MS Graph are expected to be available to AzTierWatcher via the following environment variables:
            - 'ARM_ACCESS_TOKEN'
            - 'MSGRAPH_ACCESS_TOKEN'

    Note:
        During the conversion to JSON, tiered roles and permissions are enriched with their definition Ids, which need to be retrieved
        from the MS Graph and ARM APIs.

"""
import json
import os
import re
import requests
import sys
import time
import uuid


def send_batch_request_to_arm(token, batch_requests):
    """
        Sends the passed batch requests to ARM, while handling pagination and throttling to return a complete response.

        Note:
            The batch requests are limited to 500 requests per batch, as per the ARM API documentation.
        
        Args:
            token(str): a valid access token for ARM
            batch_requests(list(dict)): list of batch requests to send to ARM

        Returns:
            list(dict): list of responses from ARM
    
    """
    batch_request_limit = 500
    limited_batch_requests = [batch_requests[i:i + batch_request_limit] for i in range(0, len(batch_requests), batch_request_limit)]
    complete_response = []

    for limited_batch_request in limited_batch_requests:
        endpoint = 'https://management.azure.com/batch?api-version=2021-04-01'
        headers = {'Authorization': f"Bearer {token}"}
        body = { 
            'requests': limited_batch_request
        }

        http_response = requests.post(endpoint, headers = headers, json = body)

        if http_response.status_code != 200 and http_response.status_code != 202:
            return None

        redirect_header = 'Location'
        retry_header = 'Retry-After'

        if redirect_header not in http_response.headers:
            # The response is not paginated
            responses = http_response.json()['responses']
            return responses

        # The response is paginated
        retry_after_x_seconds = int(http_response.headers.get(retry_header))
        time.sleep(retry_after_x_seconds)
        endpoint = http_response.headers.get(redirect_header)
        headers = {'Authorization': f"Bearer {token}"}
        http_response = requests.get(endpoint, headers = headers)
        
        if http_response.status_code != 200 and http_response.status_code != 202:
            return None

        paginated_response = http_response.json()['value']
        complete_response = paginated_response
        test = http_response.json()
        next_page = http_response.json()['nextLink'] if 'nextLink' in http_response.json() else ''

        while next_page:
            http_response = requests.get(next_page, headers = headers)

            if http_response.status_code != 200 and http_response.status_code != 202:
                return None

            paginated_response = http_response.json()['value']
            next_page = http_response.json()['nextLink'] if 'nextLink' in http_response.json() else ''
            complete_response += paginated_response

    return complete_response


def get_resource_id_of_higher_scopes_from_arm(token):
    """
        Retrieves the resource Id of the following "higher" scopes that the passed token has access to:
            - Management Groups
            - Subscriptions
            - Resource groups

        Args:
            str: a valid access token for ARM

        Returns:
            list(str): list of resource Ids for all scopes that the token has access to

    """
    all_scopes = []

    # Get Management groups and Subscriptions
    batch_requests = [
        {
            "httpMethod": "GET",
            "url": "https://management.azure.com/providers/Microsoft.Management/managementGroups?api-version=2021-04-01"
        },
        {
            "httpMethod": "GET",
            "url": "https://management.azure.com/subscriptions?api-version=2021-04-01"
        }
    ]

    http_responses = send_batch_request_to_arm(token, batch_requests)

    if http_responses is None:
        print('FATAL ERROR - The Azure scopes could not be retrieved from ARM.')
        exit()

    mg_responses = http_responses[0]['content']['value']
    mg_resource_ids = [response['id'] for response in mg_responses]
    subscription_responses = http_responses[1]['content']['value']
    subscription_resource_ids = [response['id'] for response in subscription_responses]

    # Get Resource groups
    batch_requests = []

    for subscription_resource_id in subscription_resource_ids:
        batch_requests.append({
            "name": str(uuid.uuid4()),
            "httpMethod": "GET",
            "url": f"https://management.azure.com{subscription_resource_id}/resourceGroups?api-version=2021-04-01"
        })

    http_responses = send_batch_request_to_arm(token, batch_requests)
    
    if http_responses is None:
        print('FATAL ERROR - The Azure scopes could not be retrieved from ARM.')
        exit()

    rg_responses = sum([response['content']['value'] for response in http_responses], [])
    rg_resource_ids = [response['id'] for response in rg_responses]

    # Merge all scopes
    all_scopes = mg_resource_ids + subscription_resource_ids + rg_resource_ids
    return subscription_resource_ids


def get_custom_azure_role_definitions_from_arm(token):
    """
        Retrieves custom Azure role definitions from ARM.

        Args:
            token(str): a valid access token for ARM

        Returns:
            list(str): list of custom role definitions
    """
    batch_requests = []
    scope = get_resource_id_of_higher_scopes_from_arm(token)

    for resource_id in scope:
        batch_requests.append({
            "httpMethod": "GET",
            "name": str(uuid.uuid4()),
            "url": f"https://management.azure.com{resource_id}/providers/Microsoft.Authorization/roleDefinitions?$filter=type eq 'CustomRole'&api-version=2022-04-01"
        })

    http_responses = send_batch_request_to_arm(token, batch_requests)

    if http_responses is None:
        print('FATAL ERROR - The assigned Azure role definition could not be retrieved from ARM.')
        exit()
 
    role_definitions = sum([response['content']['value'] for response in http_responses if response['httpStatusCode'] == 200], [])
    unique_role_definition_ids = set()
    unique_role_definitions = [role_definition for role_definition in role_definitions if role_definition['name'] not in unique_role_definition_ids and not unique_role_definition_ids.add(role_definition['name'])]

    return unique_role_definitions


def get_built_in_azure_role_definitions_from_arm(token):
    """
        Retrieves built-in Azure role definitions from ARM.

        Args:
            token(str): a valid access token for ARM

        Returns:
            list(str): list of built-in role definitions

    """
    endpoint = "https://management.azure.com/providers/Microsoft.Authorization/roleDefinitions?$filter=type eq 'BuiltInRole'&api-version=2022-04-01"
    headers = {'Authorization': f"Bearer {token}"}
    response = requests.get(endpoint, headers = headers)

    if response.status_code != 200:
        print('FATAL ERROR - The Azure roles could not be retrieved from ARM.')
        exit()

    paginated_response = response.json()['value']
    complete_response = paginated_response
    next_page = response.json()['nextLink'] if 'nextLink' in response.json() else ''

    while next_page:
        response = requests.get(next_page, headers = headers)

        if response.status_code != 200:
            print('FATAL ERROR - The Azure roles could not be retrieved from ARM.')
            exit()
        
        paginated_response = response.json()['value']
        next_page = response.json()['nextLink'] if 'nextLink' in response.json() else ''
        complete_response += paginated_response

    return complete_response


def get_entra_role_definitions_from_graph(token):
    """
        Retrieves all Entra role definitions from MS Graph.

        Args:
            str: a valid access token for MS Graph

        Returns:
            list(str): list of role definitions

    """
    endpoint = 'https://graph.microsoft.com/v1.0/roleManagement/directory/roleDefinitions'
    headers = {'Authorization': f"Bearer {token}"}
    response = requests.get(endpoint, headers = headers)

    if response.status_code != 200:
        print('FATAL ERROR - The Entra roles could not be retrieved from Graph.')
        exit()

    response_content = response.json()['value']
    return response_content


def get_application_permission_definitions_from_graph(token):
    """
        Retrieves all application permission definitions from MS Graph.

        Args:
            str: a valid access token for MS Graph

        Returns:
            list(str): list of application permission definitions

    """
    endpoint = "https://graph.microsoft.com/v1.0/servicePrincipals(appId='00000003-0000-0000-c000-000000000000')"
    headers = {'Authorization': f"Bearer {token}"}
    response = requests.get(endpoint, headers = headers)

    if response.status_code != 200:
        print('FATAL ERROR - The MS Graph application permissions could not be retrieved from Graph.')
        exit()

    response_content = response.json()['appRoles']
    return response_content


def standardize_markdown_asset_names(markdown_file):
    """
        Standardizes the asset names in the passed Markdown file by replacing them with hyperlinks.

        Args:
            markdown_file(str): the Markdown file containing asset names to standardize

        Returns:
            str: the updated Markdown content with standardized asset names
    """
    try:
        with open(markdown_file, 'r+', encoding='utf-8') as file:
            updated_content = []
            content = file.readlines()
            regex = r"^\| (?!Color|Azure role|Entra role|Application permission)([a-zA-Z- ]+) [^a-zA-Z]"
            asset_pattern = re.compile(regex)

            for line in content:
                if asset_pattern.match(line):
                    asset_name = asset_pattern.match(line).group(1).strip()
                    hyperlinked_asset = f"[{asset_name}](#)"
                    line = line.replace(asset_name, hyperlinked_asset, 1)
                                        
                updated_content.append(line)

            file.seek(0)
            file.write(''.join(updated_content))

    except FileNotFoundError:
        print('FATAL ERROR - Standardizing the Markdown file has failed.')
        exit()


def convert_azure_markdown_to_json(azure_markdown_file, azure_json_file, azure_role_ids):
    """
        Converts and outputs the Azure roles tiering information located in the passed Markdown file to JSON.
        The Azure roles tiering data is enriched with the role IDs in the process.

        Args:
            azure_markdown_file(str): the Markdown file containing Azure roles tiering to parse from
            azure_json_file(str): the output file to which the converted JSON is exported to
            azure_role_ids(dict(str:str)): dictionary mapping Azure role names to their respective IDs

        Returns:
            None

    """
    try:
        json_roles = []
        regex = r"(\[|\]|\(https?:\/\/[^\s)]+\)|\(#[a-z0-9\-]*\)|\\u26a0\\ufe0f |\*|<br>|`|\\ud83d\\udd70\\ufe0f )"    # strips unwanted content
        
        with open(azure_markdown_file, 'r', encoding = 'utf-8') as file:
            file_content = file.read()
            tiered_content = file_content.split('##')[2:]
            tier_0_content = tiered_content[0]
            tier_1_content = tiered_content[1]
            tier_2_content = tiered_content[2]
            tier_3_content = tiered_content[3]

            # Parsing Tier-0 content
            splitted_tier_0_content = tier_0_content.split('\n| [')[1:]

            for line in splitted_tier_0_content:
                elements = line.split('|')
                asset_name = re.sub(regex, '', elements[0].split(']', 1)[0])
                asset_name_key = asset_name.lower().replace(' ', '')
                asset_id = azure_role_ids[asset_name_key] if asset_name_key in azure_role_ids.keys() else ''
                asset_type = re.sub(regex, '', elements[1].split(']', 1)[0]).strip()
                shortest_path = re.sub(regex, '', elements[2]).encode('ascii', 'ignore').decode().strip()
                example = re.sub(regex, '', elements[3].strip())
                json_role = {
                    'tier': "0", 
                    'id': asset_id,
                    'assetType': asset_type,
                    'assetName': asset_name, 
                    'shortestPath': shortest_path,
                    'example': example
                }
                json_roles.append(json_role)

            # Parsing Tier-1 content
            splitted_tier_1_content = tier_1_content.split('\n| [')[1:]

            for line in splitted_tier_1_content:
                elements = line.split('|')
                asset_name = re.sub(regex, '', elements[0].split(']', 1)[0])
                asset_name_key = asset_name.lower().replace(' ', '')
                asset_id = azure_role_ids[asset_name_key] if asset_name_key in azure_role_ids.keys() else ''
                asset_type = re.sub(regex, '', elements[1].split(']', 1)[0]).strip()
                shortest_path = re.sub(regex, '', elements[2]).encode('ascii', 'ignore').decode().strip()
                example = re.sub(regex, '', elements[3].strip())
                json_role = {
                    'tier': "1", 
                    'id': asset_id,
                    'assetType': asset_type,
                    'assetName': asset_name, 
                    'shortestPath': shortest_path,
                    'example': example
                }
                json_roles.append(json_role)

            # Parsing Tier-2 content
            splitted_tier_2_content = tier_2_content.split('\n| [')[1:]

            for line in splitted_tier_2_content:
                elements = line.split('|')
                asset_name = re.sub(regex, '', elements[0].split(']', 1)[0])
                asset_name_key = asset_name.lower().replace(' ', '')
                asset_id = azure_role_ids[asset_name_key] if asset_name_key in azure_role_ids else ''
                asset_type = re.sub(regex, '', elements[1].split(']', 1)[0]).strip()
                worst_case_scenario = re.sub(regex, '', elements[2].strip())
                json_role = {
                    'tier': '2',
                    'id': asset_id,
                    'assetType': asset_type,
                    'assetName': asset_name,
                    'worstCaseScenario': worst_case_scenario
                }
                json_roles.append(json_role)

            # Parsing Tier-3 content
            splitted_tier_3_content = tier_3_content.split('\n| [')[1:]

            for line in splitted_tier_3_content:
                elements = line.split('|')
                asset_name = re.sub(regex, '', elements[0].split(']', 1)[0])
                asset_name_key = asset_name.lower().replace(' ', '')
                asset_id = azure_role_ids[asset_name_key] if asset_name_key in azure_role_ids else ''
                asset_type = re.sub(regex, '', elements[1].split(']', 1)[0]).strip()
                worst_case_scenario = re.sub(regex, '', elements[2].strip())
                json_role = {
                    'tier': '3',
                    'id': asset_id,
                    'assetType': asset_type,
                    'assetName': asset_name,
                    'worstCaseScenario': worst_case_scenario
                }
                json_roles.append(json_role)

        with open(azure_json_file, "w", encoding = 'utf-8') as file:
            file.write(json.dumps(json_roles, indent = 4))

    except FileNotFoundError:
        print('FATAL ERROR - Converting Azure markdown to json has failed.')
        exit()


def convert_entra_markdown_to_json(entra_markdown_file, entra_json_file, entra_role_ids):
    """
        Converts and outputs the Entra roles tiering information located in the passed Markdown file to JSON.
        The Entra roles tiering data is enriched with the role IDs in the process.

        Args:
            entra_markdown_file(str): the Markdown file containing Entra roles tiering to parse from
            entra_json_file(str): the output file to which the converted JSON is exported to
            entra_role_ids(dict(str:str)): dictionary mapping Entra role names to their respective IDs

        Returns:
            None

    """
    try:
        json_roles = []
        regex = r"(\[|\]|\(https?:\/\/[^\s)]+\)|\(#[a-z0-9\-]*\)|\\u26a0\\ufe0f |\*|<br>|`|\\ud83d\\udd70\\ufe0f )"    # strips unwanted content
        
        with open(entra_markdown_file, 'r', encoding = 'utf-8') as file:
            file_content = file.read()
            tiered_content = file_content.split('##')[2:]
            tier_0_content = tiered_content[0]
            tier_1_content = tiered_content[1]
            tier_2_content = tiered_content[2]

            # Parsing Tier-0 content
            splitted_tier_0_content = tier_0_content.split('\n| [')[1:]

            for line in splitted_tier_0_content:
                elements = line.split('|')
                asset_name = re.sub(regex, '', elements[0].split(']', 1)[0])
                asset_name_key = asset_name.lower().replace(' ', '')
                asset_id = entra_role_ids[asset_name_key] if asset_name_key in entra_role_ids.keys() else ''
                asset_type = re.sub(regex, '', elements[1].split(']', 1)[0]).strip()
                path_type = elements[2].strip()
                shortest_path = re.sub(regex, '', elements[3]).encode('ascii', 'ignore').decode().strip()
                example = re.sub(regex, '', elements[4].strip())
                json_role = {
                    'tier': "0", 
                    'id': asset_id,
                    'assetType': asset_type,
                    'assetName': asset_name, 
                    'pathType': path_type,
                    'shortestPath': shortest_path,
                    'example': example
                }
                json_roles.append(json_role)

            # Parsing Tier-1 content
            splitted_tier_1_content = tier_1_content.split('\n| [')[1:]

            for line in splitted_tier_1_content:
                elements = line.split('|')
                asset_name = re.sub(regex, '', elements[0].split(']', 1)[0])
                asset_name_key = asset_name.lower().replace(' ', '')
                asset_id = entra_role_ids[asset_name_key] if asset_name_key in entra_role_ids else ''
                asset_type = re.sub(regex, '', elements[1].split(']', 1)[0]).strip()
                provides_full_access_to = re.sub(regex, '', elements[2].strip())
                json_role = {
                    'tier': '1', 
                    'id': asset_id,
                    'assetType': asset_type,
                    'assetName': asset_name,
                    'providesFullAccessTo': provides_full_access_to
                }
                json_roles.append(json_role)

            # Parsing Tier-2 content
            splitted_tier_2_content = tier_2_content.split('\n| [')[1:]

            for line in splitted_tier_2_content:
                elements = line.split('|')
                asset_name = re.sub(regex, '', elements[0].split(']', 1)[0])
                asset_name_key = asset_name.lower().replace(' ', '')
                asset_id = entra_role_ids[asset_name_key] if asset_name_key in entra_role_ids else ''
                asset_type = re.sub(regex, '', elements[1].split(']', 1)[0]).strip()
                json_role = {
                    'tier': '2',
                    'id': asset_id,
                    'assetType': asset_type,
                    'assetName': asset_name
                }
                json_roles.append(json_role)

        with open(entra_json_file, "w", encoding = 'utf-8') as file:
            file.write(json.dumps(json_roles, indent = 4))

    except FileNotFoundError:
        print('FATAL ERROR - Converting Entra markdown to json has failed.')
        exit()


def convert_msgraph_markdown_to_json(msgraph_markdown_file, msgraph_json_file, msgraph_permission_ids):
    """
        Converts and outputs the MS Graph permissions tiering information located in the passed Markdown file to JSON.
        The MS Graph permissions tiering data is enriched with the permission IDs in the process.

        Args:
            msgraph_markdown_file(str): the Markdown file containing msgraph permissions tiering to parse from
            msgraph_json_file(str): the output file to which the converted JSON is exported to
            msgraph_permission_ids(dict(str:str)): dictionary mapping MS Graph permission names to their respective IDs

        Returns:
            None

    """
    try:
        json_permissions = []
        regex = r"(\[|\]|\(https?:\/\/[^\s)]+\)|\(#[a-z0-9\-]*\)|\\u26a0\\ufe0f |\*|<br>|`|\\ud83d\\udd70\\ufe0f )"    # strips unwanted content
        
        with open(msgraph_markdown_file, 'r', encoding = 'utf-8') as file:
            file_content = file.read()

            tiered_content = file_content.split('##')[2:]
            tier_0_content = tiered_content[0]
            tier_1_content = tiered_content[1]
            tier_2_content = tiered_content[2]

            # Parsing Tier-0 content
            splitted_tier_0_content = tier_0_content.split('\n| [')[1:]

            for line in splitted_tier_0_content:
                elements = line.split('|')
                asset_name = re.sub(regex, '', elements[0].split(']', 1)[0])
                asset_name_key = asset_name.lower().replace(' ', '')
                asset_id = msgraph_permission_ids[asset_name_key] if asset_name_key in msgraph_permission_ids.keys() else ''
                asset_type = re.sub(regex, '', elements[1].split(']', 1)[0]).strip()
                path_type = elements[2].strip()
                shortest_path = re.sub(regex, '', elements[3]).encode('ascii', 'ignore').decode().strip()
                example = re.sub(regex, '', elements[4].strip())
                json_permission = {
                    'tier': "0", 
                    'id': asset_id,
                    'assetType': asset_type,
                    'assetName': asset_name, 
                    'pathType': path_type,
                    'shortestPath': shortest_path,
                    'example': example
                }
                json_permissions.append(json_permission)

            # Parsing Tier-1 content
            splitted_tier_1_content = tier_1_content.split('\n| [')[1:]

            for line in splitted_tier_1_content:
                elements = line.split('|')
                asset_name = re.sub(regex, '', elements[0].split(']', 1)[0])
                asset_name_key = asset_name.lower().replace(' ', '')
                asset_id = msgraph_permission_ids[asset_name_key] if asset_name_key in msgraph_permission_ids else ''
                asset_type = re.sub(regex, '', elements[1].split(']', 1)[0]).strip()
                json_permission = {
                    'tier': '1', 
                    'id': asset_id,
                    'assetType': asset_type,
                    'assetName': asset_name
                }
                json_permissions.append(json_permission)

            # Parsing Tier-2 content
            splitted_tier_2_content = tier_2_content.split('\n| [')[1:]

            for line in splitted_tier_2_content:
                elements = line.split('|')
                asset_name = re.sub(regex, '', elements[0].split(']', 1)[0])
                asset_name_key = asset_name.lower().replace(' ', '')
                asset_id = msgraph_permission_ids[asset_name_key] if asset_name_key in msgraph_permission_ids else ''
                asset_type = re.sub(regex, '', elements[1].split(']', 1)[0]).strip()
                json_permission = {
                    'tier': '2',
                    'id': asset_id,
                    'assetType': asset_type,
                    'assetName': asset_name
                }
                json_permissions.append(json_permission)

        with open(msgraph_json_file, "w", encoding = 'utf-8') as file:
            file.write(json.dumps(json_permissions, indent = 4))

    except FileNotFoundError:
        print('FATAL ERROR - Converting MS Graph markdown to json has failed.')
        exit()


if __name__ == "__main__":
    # Get ARM and MS Graph access tokens from environment variables
    arm_access_token = os.environ['ARM_ACCESS_TOKEN']
    graph_access_token = os.environ['MSGRAPH_ACCESS_TOKEN']

    if not arm_access_token:
        print('FATAL ERROR - A valid access token for ARM is required.')
        exit()

    if not graph_access_token:
        print('FATAL ERROR - A valid access token for MS Graph is required.')
        exit()

    # Set local directories
    github_action_dir_name = '.github'
    absolute_path_to_script = os.path.abspath(sys.argv[0])
    root_dir = absolute_path_to_script.split(github_action_dir_name)[0]
    azure_dir = root_dir + 'Azure roles'
    entra_dir = root_dir + 'Entra roles'
    app_permissions_dir = root_dir + 'Microsoft Graph application permissions'
    
    # Set local Markdown files
    azure_roles_markdown_file = f"{azure_dir}/README.md"
    entra_roles_markdown_file = f"{entra_dir}/README.md"
    app_permissions_markdown_file = f"{app_permissions_dir}/README.md"

    # Set local JSON files
    azure_roles_json_file = f"{azure_dir}/tiered-azure-roles.json"
    entra_roles_json_file = f"{entra_dir}/tiered-entra-roles.json"
    app_permissions_json_file = f"{app_permissions_dir}/tiered-msgraph-app-permissions.json"

    # Get all Azure roles from ARM
    azure_roles = {}
    built_in_azure_role_definitions = get_built_in_azure_role_definitions_from_arm(arm_access_token)
    custom_azure_role_definitions = get_custom_azure_role_definitions_from_arm(arm_access_token)   
    all_azure_role_definitions = built_in_azure_role_definitions + custom_azure_role_definitions

    for azure_role_definition in all_azure_role_definitions:
        id = azure_role_definition['name']
        name = azure_role_definition['properties']['roleName'].lower().replace(' ', '')
        azure_roles[name] = id

    # Get all Entra roles from MS Graph
    entra_roles = {}
    entra_role_definitions = get_entra_role_definitions_from_graph(graph_access_token)

    for entra_role_definition in entra_role_definitions:
        id = entra_role_definition['id']
        name = entra_role_definition['displayName'].lower().replace(' ', '')
        entra_roles[name] = id

    # Get all MS Graph application permissions from MS Graph
    msgraph_app_permissions = {}
    msgraph_app_permission_definitions = get_application_permission_definitions_from_graph(graph_access_token)

    for msgraph_app_permission_definition in msgraph_app_permission_definitions:
        id = msgraph_app_permission_definition['id']
        name = msgraph_app_permission_definition['value'].lower().replace(' ', '')
        msgraph_app_permissions[name] = id

    # Convert Markdown content for Azure roles to JSON
    print (f"Converting: Azure roles")
    standardize_markdown_asset_names(azure_roles_markdown_file)
    convert_azure_markdown_to_json(azure_roles_markdown_file, azure_roles_json_file, azure_roles)

    # Convert Markdown content for Entra roles to JSON
    print (f"Converting: Entra roles")
    standardize_markdown_asset_names(entra_roles_markdown_file)
    convert_entra_markdown_to_json(entra_roles_markdown_file, entra_roles_json_file, entra_roles)

    # Convert Markdown content for MS Graph application permissions to JSON
    print (f"Converting: MS Graph application permissions")
    standardize_markdown_asset_names(app_permissions_markdown_file)
    convert_msgraph_markdown_to_json(app_permissions_markdown_file, app_permissions_json_file, msgraph_app_permissions)
