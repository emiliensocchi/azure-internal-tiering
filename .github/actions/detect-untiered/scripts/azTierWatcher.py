"""
    Name: 
        AzTierWatcher
        
    Author: 
        Emilien Socchi

    Description:
         AzTierWatcher verifies if following assets have changed due to new additions/removals:
            - Built-in and Custom Azure roles
            - Custom Entra roles
            
        Note that the creation of custom MS Graph application permissions is not possible at the moment.
            
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

"""
import datetime
import json
import os
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
        #retry_after_x_seconds = http_response.headers.get(retry_header)
        #time.sleep(retry_after_x_seconds)
        time.sleep(5)
        endpoint = http_response.headers.get(redirect_header)
        headers = {'Authorization': f"Bearer {token}"}
        http_response = requests.get(endpoint, headers = headers)
        
        if http_response.status_code != 200 and http_response.status_code != 202:
            return None

        paginated_response = http_response.json()['value']
        complete_response = paginated_response
        next_page = http_response.json()['nextLink'] if 'nextLink' in http_response.json() else ''

        while next_page:
            http_response = requests.get(next_page, headers = headers)

            if http_response.status_code != 200 and http_response.status_code != 202:
                return None

            paginated_response = http_response.json()['value']
            next_page = http_response.json()['nextLink'] if 'nextLink' in http_response.json() else ''
            complete_response += paginated_response

    return complete_response


def get_resource_id_of_all_scopes_from_arm(token):
    """
        Retrieves the resource Id of all scopes that the passed token has access to:
            - Management Groups
            - Subscriptions
            - Resource groups
            - Individual resources

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

    # Get individual resources
    batch_requests = []

    for rg_resource_id in rg_resource_ids:
        batch_requests.append({
            "name": str(uuid.uuid4()),
            "httpMethod": "GET",
            "url": f"https://management.azure.com{rg_resource_id}/resources?api-version=2021-04-01"
        })

    http_responses = send_batch_request_to_arm(token, batch_requests)

    if http_responses is None:
        print('FATAL ERROR - The Azure scopes could not be retrieved from ARM.')
        exit()

    resource_responses = sum([response['content']['value'] for response in http_responses], [])
    resource_resource_ids = [response['id'] for response in resource_responses]

    # Merge all scopes
    all_scopes = mg_resource_ids + subscription_resource_ids + rg_resource_ids + resource_resource_ids
    return all_scopes


def is_pim_enabled_for_arm(token):
    """
        Checks if the passed token has access to the PIM endpoints.

        Args:
            str: a valid access token for ARM

        Returns:
            bool: True if PIM is enabled, False otherwise

    """
    endpoint = 'https://management.azure.com/providers/Microsoft.Authorization/roleEligibilityScheduleInstances?$filter=asTarget()&api-version=2020-10-01'
    headers = {'Authorization': f"Bearer {token}"}
    response = requests.get(endpoint, headers = headers)

    if response.status_code == 200:
        return True

    return False


def get_role_definition_id_of_assigned_azure_roles_within_scope_from_arm(token, scope):
    """
        Retrieves the definition Id of all assigned Azure roles within the passed scope.
        
        Note:
            Uses the traditional role-assignment endpoint for tenants without PIM 
         
        Args:
            token(str): a valid access token for ARM
            scope(list(str)): list of resource Ids to check for existing role assignments

        Returns:
            list(str): list of role definition Ids

    """
    batch_requests = []

    for resource_id in scope:
        batch_requests.append({
            "httpMethod": "GET",
            "name": str(uuid.uuid4()),
            "url": f"https://management.azure.com{resource_id}/providers/Microsoft.Authorization/roleAssignments?api-version=2022-04-01&$filter=atScope()"
        })

    http_responses = send_batch_request_to_arm(token, batch_requests)

    if http_responses is None:
        print('FATAL ERROR - The assigned Azure role definition Ids could not be retrieved from ARM.')
        exit()
 
    assignment_responses = sum([response['content']['value'] for response in http_responses], [])
    role_definition_ids = [response['properties']['roleDefinitionId'] for response in assignment_responses]    
    unique_role_ids = set()
    unique_role_definition_ids = [role_definition_id for role_definition_id in role_definition_ids if role_definition_id.split("/")[-1] not in unique_role_ids and not unique_role_ids.add(role_definition_id.split("/")[-1])]

    return unique_role_definition_ids


def get_role_definition_id_of_active_azure_roles_within_scope_from_arm(token, scope):
    """
        Retrieves the definition Id of all active Azure roles within the passed scope.
        
        Note:
            Uses PIM endpoints, which requires an Entra Premium 2 license 
         
        Args:
            token(str): a valid access token for ARM
            scope(list(str)): list of resource Ids to check for existing role assignments

        Returns:
            list(str): list of role definition Ids

    """
    batch_requests = []

    for resource_id in scope:
        batch_requests.append({
            "httpMethod": "GET",
            "name": str(uuid.uuid4()),
            "url": f"https://management.azure.com{resource_id}/providers/Microsoft.Authorization/roleAssignmentScheduleInstances?api-version=2020-10-01&$filter=atScope()"
        })

    http_responses = send_batch_request_to_arm(token, batch_requests)

    if http_responses is None:
        print('FATAL ERROR - The active Azure role definition Ids could not be retrieved from ARM.')
        exit()
 
    assignment_responses = sum([response['content']['value'] for response in http_responses], [])
    role_definition_ids = [response['properties']['roleDefinitionId'] for response in assignment_responses]    
    unique_role_ids = set()
    unique_role_definition_ids = [role_definition_id for role_definition_id in role_definition_ids if role_definition_id.split("/")[-1] not in unique_role_ids and not unique_role_ids.add(role_definition_id.split("/")[-1])]

    return unique_role_definition_ids


def get_role_definition_id_of_eligible_azure_roles_within_scope_from_arm(token, scope):
    """
        Retrieves the definition Id of all eligible Azure roles within the passed scope.

        Note:
            Uses PIM endpoints, which requires an Entra Premium 2 license 

        Args:
            token(str): a valid access token for ARM
            scope(list(str)): list of resource Ids to check for existing role assignments

        Returns:
            list(str): list of role definition Ids

    """
    batch_requests = []

    for resource_id in scope:
        batch_requests.append({
            "httpMethod": "GET",
            "name": str(uuid.uuid4()),
            "url": f"https://management.azure.com{resource_id}/providers/Microsoft.Authorization/roleEligibilityScheduleInstances?api-version=2020-10-01&$filter=atScope()"
        })

    http_responses = send_batch_request_to_arm(token, batch_requests)

    if http_responses is None:
        print('FATAL ERROR - The eligible Azure role definition Ids could not be retrieved from ARM.')
        exit()
 
    assignment_responses = sum([response['content']['value'] for response in http_responses], [])
    role_definition_ids = [response['properties']['roleDefinitionId'] for response in assignment_responses]
    unique_role_ids = set()
    unique_role_definition_ids = [role_definition_id for role_definition_id in role_definition_ids if role_definition_id.split("/")[-1] not in unique_role_ids and not unique_role_ids.add(role_definition_id.split("/")[-1])]

    return unique_role_definition_ids


def get_all_azure_role_definitions_from_arm(token, role_definition_ids):
    """
        Retrieves the definition of all built-in and custom Azure roles with the passed definition Ids.
        Note: 
        
        Args:
            str: a valid access token for ARM
            role_definition_ids(list): list of role definition Ids to check for existing role assignments

        Returns:
            list(str): list of resource Ids for all scopes that the token has access to

    """
    all_role_definitions = []
    batch_requests = []

    for role_definition_id in role_definition_ids:
        batch_requests.append({
            "httpMethod": "GET",
            "name": str(uuid.uuid4()),
            "url": f"https://management.azure.com{role_definition_id}?api-version=2022-04-01"
        })

    http_responses = send_batch_request_to_arm(token, batch_requests)

    if http_responses is None:
        print('FATAL ERROR - The Azure role definitions could not be retrieved from ARM.')
        exit()
 
    role_definition_responses = [response['content'] for response in http_responses if response['httpStatusCode'] == 200]

    for role_definition_response in role_definition_responses:
        all_role_definitions.append({
            'roleDefinitionId': role_definition_response['id'],
            'roleId': role_definition_response['name'],
            'roleName': role_definition_response['properties']['roleName'],
            'roleType': role_definition_response['properties']['type'],
            'roleDescription': role_definition_response['properties']['description']
        })

    return all_role_definitions


def get_built_in_azure_role_definitions_from_arm(token, role_definition_ids):
    """
        Retrieves the definition of all built-in Azure roles with the passed definition Ids.
        Note: 
        
        Args:
            str: a valid access token for ARM
            role_definition_ids(list): list of role definition Ids to check for existing role assignments

        Returns:
            list(str): list of resource Ids for all scopes that the token has access to

        Returns:
            list(str): list of custom role definitions

    """
    all_role_definitions = get_all_azure_role_definitions_from_arm(token, role_definition_ids)
    built_in_role_definitions = [definition for definition in all_role_definitions if definition['roleType'] == 'BuiltInRole']

    return built_in_role_definitions


def deprecated_get_assigned_azure_role_definitions_from_arm(token):
    """
        Retrieves all Azure role definitions from ARM that are currently in use in the tenant, with the following properties:
            - roleDefinitionId
            - roleId
            - roleName
            - roleType
            - roleDescription

        Args:
            token(str): a valid access token for ARM

        Returns:
            list(str): list of role definitions

    """
    endpoint = 'https://management.azure.com/providers/Microsoft.ResourceGraph/resources?api-version=2024-04-01'
    headers = {'Authorization': f"Bearer {token}"}
    body = { 
        'query': """authorizationresources 
        | where type == 'microsoft.authorization/roledefinitions' 
        | extend roleDefinitionId = tostring(id)
        | extend roleId = tostring(name)
        | extend roleName = tostring(properties['roleName'])
        | extend roleType = tostring(properties['type'])
        | extend roleDescription = tostring(properties['description'])
        | project roleDefinitionId, roleId, roleName, roleType, roleDescription
        | join kind=inner (
            authorizationresources 
            | where type == 'microsoft.authorization/roleassignments' 
            | extend roleDefinitionId = tostring(properties['roleDefinitionId']) 
            | project roleDefinitionId
        ) on roleDefinitionId
        | summarize by roleDefinitionId, roleId, roleName, roleType, roleDescription
        | order by ['roleName'] asc"""
    }
    response = requests.post(endpoint, headers = headers, json = body)

    if response.status_code != 200:
        print('FATAL ERROR - The Azure role definitions could not be retrieved from ARM.')
        exit()

    role_definitions = response.json()['data']
    return role_definitions


def get_custom_azure_role_definitions_from_arm(token):
    """
        Retrieves all custom Azure role definitions from ARM.

        Args:
            str: a valid access token for ARM

        Returns:
            list(str): list of custom role definitions

    """
    endpoint = "https://management.azure.com/providers/Microsoft.Authorization/roleDefinitions?$filter=type+eq+'CustomRole'&api-version=2022-04-01"
    headers = {'Authorization': f"Bearer {token}"}
    response = requests.get(endpoint, headers = headers)

    if response.status_code != 200:
        print('FATAL ERROR - The custom Azure roles could not be retrieved from ARM.')
        exit()

    response_content = response.json()['value']
    return response_content


def get_custom_entra_role_definitions_from_graph(token):
    """
        Retrieves all custom Entra role definitions from MS Graph.

        Args:
            str: a valid access token for MS Graph

        Returns:
            list(str): list of custom role definitions

    """
    endpoint = 'https://graph.microsoft.com/v1.0/roleManagement/directory/roleDefinitions?$filter=isBuiltIn eq false'
    headers = {'Authorization': f"Bearer {token}"}
    response = requests.get(endpoint, headers = headers)

    if response.status_code != 200:
        print('FATAL ERROR - The custom Entra roles could not be retrieved from Graph.')
        exit()

    response_content = response.json()['value']
    return response_content


def find_added_assets(extended_assets, base_assets):
    """
        Compares a base list with a list of extended assets, to determine the assets that have been added to the extended list.

        Args:
            extended_assets(list): list of extended assets, whose length is equal or greater than the base list
            base_assets(list): list of base assets to compare with

        Returns:
            list(): list of added assets

    """
    added_assets = []
    extended_asset_ids = [asset['id'] for asset in extended_assets]
    base_asset_ids = [asset['id'] for asset in base_assets]
    added_asset_ids = [asset_id for asset_id in extended_asset_ids if asset_id not in base_asset_ids]

    if added_asset_ids:
        now = datetime.datetime.now()
        date = now.strftime("%Y-%m-%d")

        for added_asset_id in added_asset_ids:
            asset = [asset for asset in extended_assets if asset['id'] == added_asset_id][0]
            enriched_asset = { 'date': date }
            enriched_asset.update(asset)
            added_assets.append(enriched_asset)

    return added_assets


def find_removed_assets(extended_assets, base_assets):
    """
        Compares a base list with a list of extended assets, to determine the assets that have been removed from the based list.

        Args:
            extended_assets(list): list of extended assets, whose length is equal or greater than the base list
            base_assets(list): list of base assets to compare with
        
        Returns:
            list(): list of removed assets
            
    """
    removed_assets = []
    extended_asset_ids = [asset['id'] for asset in extended_assets]
    base_asset_ids = [asset['id'] for asset in base_assets]
    removed_asset_ids = [asset_id for asset_id in base_asset_ids if asset_id not in extended_asset_ids]

    if removed_asset_ids:
        now = datetime.datetime.now()
        date = now.strftime("%Y-%m-%d")

        for removed_asset_id in removed_asset_ids:
            asset = [asset for asset in base_assets if asset['id'] == removed_asset_id][0]
            removed_assets.append(asset)

    return removed_assets


def read_json_file(json_file):
    """
         Retrieves the content of the passed JSON file as a dictionary.

        Args:
            json_file(str): path to the local JSON file from which the content is to be retrieved

        Returns:
            list(): the content of the passed JSON file
    """
    try:
        if os.path.exists(json_file):
            with open(json_file, 'r+') as file:
                file_content = file.read()
                
                if file_content:
                    return json.loads(file_content)
    
        with open(json_file, 'w+') as file:
            file.write('[]')
            file.seek(0)
            return json.load(file)
    
    except json.JSONDecodeError:
        print('FATAL ERROR - The JSON file does not contain valid JSON.')
        exit()
    except Exception:
        print('FATAL ERROR - The JSON file could not be retrieved.')
        exit()


def update_tiered_assets(tiered_json_file, tiered_assets):
    """
        Updates the passed file providing an overview of tiered roles and permissions with the passed tiered assets.

        Args:
            tiered_file(str): the local JSON file with tiered roles and permissions
            tiered_assets(list(dict)): the assets to be added to the tiered file

    """
    try:
        with open(tiered_json_file, 'w') as file:
            file.write(json.dumps(tiered_assets, indent = 4))
    except FileNotFoundError:
        print('FATAL ERROR - The tiered file could not be updated.')
        exit()


def update_untiered_assets(untiered_md_file, added_assets):
    """
        Updates the passed file providing an overview of untiered roles with the passed administrative assets.

        Args:
            untiered_file_md(str): the local Markdown file with untiered roles
            added_assets(list(dict)): the assets to be added to the untiered file

        Returns:
            bool: True if at least one of the passed assets has not been detected as untiered before, False otherwise
    """
    try:
        page_metadata_content = ''
        additions_content = ''

        with open(untiered_md_file, 'r', encoding = 'utf-8') as file:
            file_content = file.read()
            splitter = '##' 
            splitted_content = file_content.split(splitter)
            page_metadata_content = splitted_content[0]
            additions_content = splitter + splitted_content[1]

        # Add to untiered additions
        are_new_assets_untiered = False
        updated_additions_content = ''
        new_additions_content = ''
        splitter = '---|'
        splitted_additions_content = additions_content.rsplit(splitter, 1)
        additions_metadata_content = splitted_additions_content[0] + splitter
        current_additions_content = splitted_additions_content[1]
        current_additions_assets = set(current_additions_content.split('\n|')[1:])
        assets_to_add = [asset for asset in added_assets if (str(current_additions_assets).find(asset['name']) == -1)]

        for asset in assets_to_add:
            date = asset['date']
            name = f"[{asset['name']}]({asset['link']})"
            type = asset['type']
            description = asset['description']
            line = f"\n| {date} | {name} | {type} | {description} |"
            new_additions_content += line

        if new_additions_content:
            # Update the untiered file with the new content
            are_new_assets_untiered = True
            updated_additions_content = additions_metadata_content + new_additions_content + current_additions_content
            updated_content = page_metadata_content + updated_additions_content
            with open(untiered_md_file, 'w', encoding = 'utf-8') as file:
                file.write(updated_content)

        return are_new_assets_untiered
    except FileNotFoundError:
        print('FATAL ERROR - The untiered file could not be updated.')
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

    # Set Microsoft APIs info
    arm_role_template_base_uri = 'https://management.azure.com/providers/Microsoft.Authorization/roleDefinitions/'
    graph_role_template_base_uri = 'https://graph.microsoft.com/v1.0/roleManagement/directory/roleDefinitions/'
    arm_role_template_api_version = '2022-04-01'

    # Set local tier files
    github_action_dir_name = '.github'
    absolute_path_to_script = os.path.abspath(sys.argv[0])
    root_dir = absolute_path_to_script.split(github_action_dir_name)[0]
    azure_dir = root_dir + 'Azure roles'
    entra_dir = root_dir + 'Entra roles'
    azure_roles_tier_file = f"{azure_dir}/tiered-azure-roles.json"
    entra_roles_tier_file = f"{entra_dir}/tiered-entra-roles.json"

    # Set local untiered files
    azure_roles_untiered_file = f"{azure_dir}/Untiered Azure roles.md"
    entra_roles_untiered_file = f"{entra_dir}/Untiered custom Entra roles.md"

    # Get tiered built-in roles from local files
    tiered_azure_roles = read_json_file(azure_roles_tier_file)
    tiered_entra_roles = read_json_file(entra_roles_tier_file)

    # Get built-in Azure roles in use
    built_in_azure_roles_in_use = []
    is_pim_enabled = is_pim_enabled_for_arm(arm_access_token)

    if is_pim_enabled:
        # Get active + eligible roles
        azure_scope_resource_ids = get_resource_id_of_all_scopes_from_arm(arm_access_token)
        active_azure_role_ids = get_role_definition_id_of_active_azure_roles_within_scope_from_arm(arm_access_token, azure_scope_resource_ids)
        eligible_azure_role_ids = get_role_definition_id_of_eligible_azure_roles_within_scope_from_arm(arm_access_token, azure_scope_resource_ids)
        all_azure_role_ids_in_use = active_azure_role_ids + eligible_azure_role_ids
        built_in_azure_role_definitions_in_use = get_built_in_azure_role_definitions_from_arm(arm_access_token, all_azure_role_ids_in_use)

        for built_in_azure_role_definition in built_in_azure_role_definitions_in_use:
            azure_role_type = 'Built-in' if built_in_azure_role_definition['roleType'] == 'BuiltInRole' else 'Custom'
            built_in_azure_roles_in_use.append({
                'id': built_in_azure_role_definition['roleId'],
                'type': azure_role_type,
                'name': built_in_azure_role_definition['roleName'],
                'description': built_in_azure_role_definition['roleDescription'],
                'link': f"{arm_role_template_base_uri}{built_in_azure_role_definition['roleId']}?api-version={arm_role_template_api_version}"   
            })
    else:
        # Get permanently assigned roles
        azure_scope_resource_ids = get_resource_id_of_all_scopes_from_arm(arm_access_token)
        assigned_azure_role_ids = get_role_definition_id_of_assigned_azure_roles_within_scope_from_arm(arm_access_token, azure_scope_resource_ids)
        all_azure_role_definitions_in_use = get_all_azure_role_definitions_from_arm(arm_access_token, assigned_azure_role_ids)

        for azure_role_definition in all_azure_role_definitions_in_use:
            azure_role_type = 'Built-in' if azure_role_definition['roleType'] == 'BuiltInRole' else 'Custom'
            built_in_azure_roles_in_use.append({
                'id': azure_role_definition['roleId'],
                'type': azure_role_type,
                'name': azure_role_definition['roleName'],
                'description': azure_role_definition['roleDescription'],
                'link': f"{arm_role_template_base_uri}{azure_role_definition['roleId']}?api-version={arm_role_template_api_version}"   
            })

    # Get custom Azure roles
    custom_azure_roles = []
    custom_azure_role_definitions = get_custom_azure_role_definitions_from_arm(arm_access_token)

    for custom_azure_role_definition in custom_azure_role_definitions:
        custom_azure_roles.append({
            'id': custom_azure_role_definition['name'],
            'type': 'Custom',
            'name': custom_azure_role_definition['properties']['roleName'],
            'description': custom_azure_role_definition['properties']['description'],
            'link': f"{arm_role_template_base_uri}{custom_azure_role_definition['name']}?api-version={arm_role_template_api_version}"   
        })

    # Merge all custom + built-in Azure roles in use
    azure_roles = built_in_azure_roles_in_use + custom_azure_roles

    # Find untiered Azure roles
    added_azure_roles = sorted(find_added_assets(azure_roles, tiered_azure_roles), key=lambda x: x['name'])
    removed_azure_roles = find_removed_assets(azure_roles, tiered_azure_roles)
    removed_custom_azure_roles = [role for role in removed_azure_roles if role['assetType'] == 'Custom']
    have_custom_roles_been_removed = True if removed_custom_azure_roles else False

    if have_custom_roles_been_removed:
        for removed_custom_role in removed_custom_azure_roles:
            removed_role_id = removed_custom_role['id']
            tiered_azure_roles = [role for role in tiered_azure_roles if role['id'] != removed_role_id]

        update_tiered_assets(azure_roles_tier_file, tiered_azure_roles)

    have_roles_been_added = update_untiered_assets(azure_roles_untiered_file, added_azure_roles)

    if have_roles_been_added:
        print ('➕ Azure roles: additions have been detected')
    if have_custom_roles_been_removed:
        print ('❌ Custom Azure roles: removals have been detected and applied')
    if not have_roles_been_added and not have_custom_roles_been_removed:
        print ('➖ Azure roles: no changes')

    # Get all custom Entra roles
    custom_entra_roles = []
    custom_entra_role_definitions = get_custom_entra_role_definitions_from_graph(graph_access_token)

    for custom_entra_role_definition in custom_entra_role_definitions:
        custom_entra_roles.append({
            'id': custom_entra_role_definition['id'],
            'type': 'Custom',
            'name': custom_entra_role_definition['displayName'],
            'description': custom_entra_role_definition['description'],
            'link': f"{graph_role_template_base_uri}{custom_entra_role_definition['id']}"
        })

    # Find untiered custom Entra roles
    tiered_custom_entra_roles = [role for role in tiered_entra_roles if role['assetType'] == 'Custom']
    added_custom_entra_roles = sorted(find_added_assets(custom_entra_roles, tiered_custom_entra_roles), key=lambda x: x['name'])
    removed_custom_entra_roles = find_removed_assets(custom_entra_roles, tiered_custom_entra_roles)
    have_custom_roles_been_removed = True if removed_custom_entra_roles else False

    if have_custom_roles_been_removed:
        for removed_role in removed_custom_entra_roles:
            removed_role_id = removed_role['id']
            tiered_entra_roles = [role for role in tiered_entra_roles if role['id'] != removed_role_id]

        update_tiered_assets(entra_roles_tier_file, tiered_entra_roles)

    have_custom_roles_been_added = update_untiered_assets(entra_roles_untiered_file, added_custom_entra_roles)

    if have_custom_roles_been_added:
        print ('➕ Custom Entra roles: additions have been detected')
    if have_custom_roles_been_removed:
        print ('❌ Custom Entra roles: removals have been detected and applied')
    if not have_custom_roles_been_added and not have_custom_roles_been_removed:
        print ('➖ Custom Entra roles: no changes')
