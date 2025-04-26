"""
    Name: 
        AzTierSyncer
        
    Author: 
        Emilien Socchi

    Description:  
        AzTierSyncer synchronizes the following built-in assets with the upstream Azure Administrative Tiering (AAT) project:
            - Azure roles
            - Entra roles
            - MS Graph application permissions

    References:
        https://github.com/emiliensocchi/azure-tiering

    Requirements:
        None

"""
import datetime
import json
import os
import requests
import sys


def get_tiered_builtin_azure_role_definitions_from_aat():
    """
        Retrieves a list of tiered built-in Azure roles from the Azure Administrative Tiering (AAT) project.
       
        Returns:
            list(): list of dict containing the tiered Azure roles

        References:
            https://github.com/emiliensocchi/azure-tiering

    """
    endpoint = 'https://raw.githubusercontent.com/emiliensocchi/azure-tiering/refs/heads/main/Azure%20roles/tiered-azure-roles.json'
    response = requests.get(endpoint)

    if response.status_code != 200:
        print('FATAL ERROR - The tiered Azure roles could not be retrieved from the AAT project.')
        exit()

    tiered_azure_role_definitions = response.json()
    return tiered_azure_role_definitions


def get_tiered_builtin_entra_role_definitions_from_aat():
    """
        Retrieves a list of tiered built-in Entra roles from the Azure Administrative Tiering (AAT) project.
       
        Returns:
            list(): list of dict containing the tiered Entra roles

        References:
            https://github.com/emiliensocchi/azure-tiering

    """
    endpoint = 'https://raw.githubusercontent.com/emiliensocchi/azure-tiering/refs/heads/main/Entra%20roles/tiered-entra-roles.json'
    response = requests.get(endpoint)

    if response.status_code != 200:
        print('FATAL ERROR - The tiered Entra roles could not be retrieved from the AAT project.')
        exit()

    tiered_entra_role_definitions = response.json()
    return tiered_entra_role_definitions


def get_tiered_builtin_msgraph_app_permission_definitions_from_aat():
    """
        Retrieves a list of tiered built-in MS Graph application permissions from the Azure Administrative Tiering (AAT) project.
       
        Returns:
            list(): list of dict containing the tiered application permissions

        References:
            https://github.com/emiliensocchi/azure-tiering

    """
    endpoint = 'https://raw.githubusercontent.com/emiliensocchi/azure-tiering/refs/heads/main/Microsoft%20Graph%20application%20permissions/tiered-msgraph-app-permissions.json'
    response = requests.get(endpoint)

    if response.status_code != 200:
        print('FATAL ERROR - The tiered MS Graph application permissions could not be retrieved from the AAT project.')
        exit()

    tiered_msgraph_app_permission_definitions = response.json()
    return tiered_msgraph_app_permission_definitions


def find_added_assets(extended_assets, base_assets):
    """
        Compares a base list with a list of extended assets, to determine the assets that have been added to the extended list.

        Args:
            extended_assets(list(dict(str:str))): list of extended assets, whose length is equal to or greater than the base list
            base_assets(list(dict(str:str))): list of base assets to compare with

        Returns:
            list(): added assets

    """
    if len(extended_assets) < len(base_assets):
        print ('FATAL ERROR - Improper use of function: the length of the extended list should be equal to or greater than the length of the base list')
        exit() 

    added_assets = []
    extended_asset_ids = [asset['id'] for asset in extended_assets]
    base_asset_ids = [asset['id'] for asset in base_assets]
    added_asset_ids = [asset_id for asset_id in extended_asset_ids if asset_id not in base_asset_ids]

    if added_asset_ids:
        for added_asset_id in added_asset_ids:
            asset = [asset for asset in extended_assets if asset['id'] == added_asset_id][0]
            added_assets.append(asset)

    return added_assets


def find_removed_assets(extended_assets, base_assets):
    """
        Compares a base list with a list of extended assets, to determine the assets that have been removed from the based list.

        Args:
            extended_assets(list(dict(str:str))): list of extended assets, whose length is equal to or greater than the base list
            base_assets(list(dict(str:str))): list of base assets to compare with
        
        Returns:
            list(): removed assets
            
    """
    if len(extended_assets) < len(base_assets):
        print ('FATAL ERROR - Improper use of function: the length of the extended list should be equal to or greater than the length of the base list')
        exit() 

    removed_assets = []
    extended_asset_ids = [asset['id'] for asset in extended_assets]
    base_asset_ids = [asset['id'] for asset in base_assets]
    removed_asset_ids = [asset_id for asset_id in base_asset_ids if asset_id not in extended_asset_ids]

    if removed_asset_ids:
        for removed_asset_id in removed_asset_ids:
            asset = [asset for asset in base_assets if asset['id'] == removed_asset_id][0]
            removed_assets.append(asset)

    return removed_assets


def find_modified_assets(extended_assets, base_assets):
    """
        Compares a base list with a list of extended assets, to determine the assets that have been modified in the extended list.

        Args:
            extended_assets(list(dict(str:str))): list of extended assets, whose length is equal to or greater than the base list
            base_assets(list(dict(str:str))): list of base assets to compare with

        Returns:
            list(): modified assets

    """
    if len(extended_assets) < len(base_assets):
        print ('FATAL ERROR - Improper use of function: the length of the extended list should be equal to or greater than the length of the base list')
        exit() 

    modified_assets = []

    for base_asset in base_assets:
        base_asset_id = base_asset['id']
        extended_asset = next((asset for asset in extended_assets if asset["id"] == base_asset_id), None)

        if extended_assets:
            base_asset_properties = base_asset.keys()
            extended_asset_properties = extended_asset.keys()

            for base_asset_property in base_asset_properties:
                if base_asset_property in extended_asset_properties:
                    is_asset_modified = base_asset[base_asset_property] != extended_asset[base_asset_property]

                    if is_asset_modified:
                        modified_assets.append(base_asset)

    return modified_assets


def read_tiered_json_file(tiered_json_file):
    """
         Retrieves the content of the passed tiered JSON file.

        Args:
            json_file(str): path to the local tiered JSON file from which the content is retrieved

        Returns:
            list(): the content of the tiered JSON file
    """
    try:
        if os.path.exists(tiered_json_file):
            with open(tiered_json_file, 'r', encoding = 'utf-8') as file:
                file_content = file.read()

                if file_content:
                    return json.loads(file_content)

        with open(tiered_json_file, 'w+', encoding = 'utf-8') as file:
            file.write('[]')
            file.seek(0)
            return json.load(file)
    
    except Exception:
        print('FATAL ERROR - The tiered JSON file could not be retrieved.')
        exit()


def update_tiered_assets(tiered_json_file, tiered_assets):
    """
        Updates the passed file providing an overview of tiered roles and permissions with the passed tiered assets.

        Args:
            tiered_file(str): the local JSON file with tiered roles and permissions
            tiered_assets(list(dict)): the assets to be added to the tiered file

    """
    try:
        with open(tiered_json_file, 'w', encoding = 'utf-8') as file:
            file.write(json.dumps(tiered_assets, indent = 4))
    except FileNotFoundError:
        print('FATAL ERROR - The tiered file could not be updated.')
        exit()


def enrich_asset_with_type(asset, asset_type):
    """
        Enriches the passed asset with the passed type, while keeping the structure of the asset.
    
        Args:
            asset(dict(str:str)): asset to enrich
            asset_type(str): the asset type information used to enrich the asset
    
        Returns:
            dict(str:str): the enriched asset
    
    """
    asset_type = asset_type.lower()
    valid_asset_types = [
        'builtin',
        'custom'
    ]

    if asset_type not in valid_asset_types:
        print ('FATAL ERROR - Improper use of function: the value of the asset_type parameter is invalid. Accepted values are: builtin, custom')
        exit()

    readable_asset_type = 'Built-in' if asset_type == valid_asset_types[0] else 'Custom'
    asset_values = list(asset.items())
    asset_values.insert(2, ('assetType', readable_asset_type))
    return dict(asset_values)


def run_sync_workflow(keep_local_changes, role_type, tiered_builtin_roles_from_aat, tiered_all_roles_from_local):
    """
        Synchronizes the passed roles from AAT with local roles. Local changes are either overriden or preserved based on 
        the passed workflow type.

        Args:
            keep_local_changes(bool): the type of workflow to execute, deciding whether local changes should be preserved or overriden from the AAT (accepted values: 'override_local', 'keep_local_changes')
            role_type(str): the type of role to synchronize (accepted values: 'azure' or 'entra')
            tiered_builtin_roles_from_aat(list(dict)): list of built-in roles from the AAT
            tiered_builtin_roles_from_local(list(dict)): list of all currently tiered locally

        Returns:
            list(dict()): list of synchronized roles with the AAT

    """
    tiered_builtin_roles_from_local = [role for role in tiered_all_roles_from_local if role['assetType'] == 'Built-in']
    role_type = role_type.lower()

    if role_type == 'azure':
        # Added Azure roles
        added_tiered_azure_roles = find_added_assets(tiered_builtin_roles_from_aat, tiered_builtin_roles_from_local)

        for added_azure_role in added_tiered_azure_roles:
            enriched_added_azure_role = enrich_asset_with_type(added_azure_role, 'builtin')
            tiered_all_roles_from_local.append(enriched_added_azure_role)

        # Modified Azure roles
        if not keep_local_changes:
            modified_tiered_azure_roles = find_modified_assets(tiered_builtin_roles_from_aat, tiered_builtin_roles_from_local)

            for modified_tiered_azure_role in modified_tiered_azure_roles:
                tiered_azure_roles_from_aat = [role for role in tiered_builtin_roles_from_aat if role['id'] == modified_tiered_azure_role['id']]

                if len(tiered_azure_roles_from_aat) > 0:
                    tiered_azure_role_from_aat = tiered_azure_roles_from_aat[0]
                    enriched_tiered_azure_role_from_aat = enrich_asset_with_type(tiered_azure_role_from_aat, 'builtin')
                    index = next((i for i, role in enumerate(tiered_all_roles_from_local) if role['id'] == modified_tiered_azure_role['id']), None)
                    tiered_all_roles_from_local[index] = enriched_tiered_azure_role_from_aat

        # Removed Azure roles
        removed_tiered_azure_roles = find_removed_assets(tiered_builtin_roles_from_aat, tiered_builtin_roles_from_local)
        removed_tiered_built_in_azure_role = [role for role in removed_tiered_azure_roles if role['assetType'] == 'Built-in']   # Custom roles should always be preserved

        for removed_azure_role in removed_tiered_built_in_azure_role:
            removed_azure_role_id = removed_azure_role['id']
            tiered_all_roles_from_local = [role for role in tiered_all_roles_from_local if role['id'] != removed_azure_role_id]

    elif role_type == 'entra':
        # Added Entra roles
        added_tiered_entra_roles = find_added_assets(tiered_builtin_roles_from_aat, tiered_builtin_roles_from_local)

        for added_entra_role in added_tiered_entra_roles:
            enriched_added_entra_role = enrich_asset_with_type(added_entra_role, 'builtin')
            tiered_all_roles_from_local.append(enriched_added_entra_role)

        # Modified Entra roles
        if not keep_local_changes:
            modified_tiered_entra_roles = find_modified_assets(tiered_builtin_roles_from_aat, tiered_builtin_roles_from_local)

            for modified_tiered_entra_role in modified_tiered_entra_roles:
                tiered_entra_roles_from_aat = [role for role in tiered_builtin_roles_from_aat if role['id'] == modified_tiered_entra_role['id']]

                if len(tiered_entra_roles_from_aat) > 0:
                    tiered_entra_role_from_aat = tiered_entra_roles_from_aat[0]
                    enriched_tiered_entra_role_from_aat = enrich_asset_with_type(tiered_entra_role_from_aat, 'builtin')
                    index = next((i for i, role in enumerate(tiered_all_roles_from_local) if role['id'] == modified_tiered_entra_role['id']), None)
                    tiered_all_roles_from_local[index] = enriched_tiered_entra_role_from_aat

        # Removed Entra roles
        removed_tiered_entra_roles = find_removed_assets(tiered_builtin_roles_from_aat, tiered_builtin_roles_from_local)
        removed_tiered_built_in_entra_role = [role for role in removed_tiered_entra_roles if role['assetType'] == 'Built-in']   # Custom roles should always be preserved

        for removed_role in removed_tiered_built_in_entra_role:
            removed_role_id = removed_role['id']
            tiered_all_entra_roles_from_local = [role for role in tiered_all_entra_roles_from_local if role['id'] != removed_role_id]
    else:
        print ('FATAL ERROR - Improper use of function: the value of the role_type parameter is invalid. Accepted values are: azure, entra')
        exit() 

    return tiered_all_roles_from_local


if __name__ == "__main__":
    # Set local directory    
    github_action_dir_name = '.github'
    absolute_path_to_script = os.path.abspath(sys.argv[0])
    root_dir = absolute_path_to_script.split(github_action_dir_name)[0]

    # Set local config file
    config_file = root_dir + 'config.json'

    # Set local tier files
    azure_dir = root_dir + 'Azure roles'
    entra_dir = root_dir + 'Entra roles'
    app_permissions_dir = root_dir + 'Microsoft Graph application permissions'
    azure_roles_tier_file = f"{azure_dir}/tiered-azure-roles.json"
    entra_roles_tier_file = f"{entra_dir}/tiered-entra-roles.json"
    msgraph_app_permissions_tier_file = f"{app_permissions_dir}/tiered-msgraph-app-permissions.json"

    # Get project configuration from local config file
    project_config = {}
    try:
        with open(config_file, 'r', encoding = 'utf-8') as file:
            project_config = json.load(file)
    except Exception:
        print('FATAL ERROR - The config JSON file could not be retrieved.')
        exit()

    # Get workflow type and set whether to keep local changes
    keep_local_changes_config = project_config['keepLocalChanges'].lower()
    accepted_values = [ 'false', 'true' ]

    if not keep_local_changes_config in accepted_values:
        print("FATAL ERROR - The 'overrideLocal' value set in the project's configuration file is invalid. Accepted values are: 'True', 'False'")
        exit()

    keep_local_changes = True if keep_local_changes_config == 'true' else False

    # Get tiered built-in roles/permissions from local files
    tiered_builtin_azure_roles = read_tiered_json_file(azure_roles_tier_file)
    tiered_builtin_entra_roles = read_tiered_json_file(entra_roles_tier_file)
    tiered_builtin_msgraph_app_permissions = read_tiered_json_file(msgraph_app_permissions_tier_file)
    
    # Update locally-tiered Azure roles with the latest upstream version from AAT
    tiered_all_azure_roles_from_local = read_tiered_json_file(azure_roles_tier_file)
    tiered_builtin_azure_roles_from_aat = get_tiered_builtin_azure_role_definitions_from_aat()

    updated_tiered_all_azure_roles_from_local = run_sync_workflow(keep_local_changes, 'azure', tiered_builtin_azure_roles_from_aat, tiered_all_azure_roles_from_local[:])
    has_aat_been_updated = False if (updated_tiered_all_azure_roles_from_local == tiered_all_azure_roles_from_local) else True

    if has_aat_been_updated:
        has_aat_been_updated = False if (len(updated_tiered_all_azure_roles_from_local) == len(tiered_all_azure_roles_from_local)) else True
        tiered_all_azure_roles_from_local = sorted(updated_tiered_all_azure_roles_from_local, key=lambda x: (x['tier'], x['assetName']))
        update_tiered_assets(azure_roles_tier_file, tiered_all_azure_roles_from_local)

        if has_aat_been_updated:
            print ('Built-in Azure roles: changes have been detected and merged from AAT')
        else:
            print ('Built-in Azure roles: no changes detected in AAT, but local changes have been overridden')
    else:
        print ('Built-in Azure roles: no changes')

    # Update locally-tiered Entra roles with the latest upstream version from AAT
    tiered_all_entra_roles_from_local = read_tiered_json_file(entra_roles_tier_file)
    tiered_builtin_entra_roles_from_aat = get_tiered_builtin_entra_role_definitions_from_aat()

    updated_tiered_all_entra_roles_from_local = run_sync_workflow(keep_local_changes, 'entra', tiered_builtin_entra_roles_from_aat, tiered_all_entra_roles_from_local[:])
    has_aat_been_updated = False if (updated_tiered_all_entra_roles_from_local == tiered_all_entra_roles_from_local) else True

    if has_aat_been_updated:
        has_aat_been_updated = False if (len(updated_tiered_all_entra_roles_from_local) == len(tiered_all_entra_roles_from_local)) else True
        tiered_all_entra_roles_from_local = sorted(updated_tiered_all_entra_roles_from_local, key=lambda x: (x['tier'], x['assetName']))
        update_tiered_assets(entra_roles_tier_file, tiered_all_entra_roles_from_local)

        if has_aat_been_updated:
            print ('Built-in Entra roles: changes have been detected and merged from AAT')
        else:
            print ('Built-in Entra roles: no changes detected in AAT, but local changes have been overridden')
    else:
        print ('Built-in Entra roles: no changes')

    # Update locally-tiered MS Graph application permissions with the latest upstream version from AAT
    tiered_builtin_msgraph_app_permissions_from_aat = get_tiered_builtin_msgraph_app_permission_definitions_from_aat()    
    local_tiered_builtin_msgraph_app_permissions = read_tiered_json_file(msgraph_app_permissions_tier_file)

    # Enrich each permission with its asset type
    enriched_tiered_builtin_msgraph_app_permissions_from_aat = []

    for app_permission in tiered_builtin_msgraph_app_permissions_from_aat:
        enriched_app_permission = enrich_asset_with_type(app_permission, 'builtin')
        enriched_tiered_builtin_msgraph_app_permissions_from_aat.append(enriched_app_permission)

    has_aat_been_updated = True if enriched_tiered_builtin_msgraph_app_permissions_from_aat != local_tiered_builtin_msgraph_app_permissions else False

    if has_aat_been_updated:
        has_aat_been_updated = False if (len(enriched_tiered_builtin_msgraph_app_permissions_from_aat) == len(local_tiered_builtin_msgraph_app_permissions)) else True
        update_tiered_assets(msgraph_app_permissions_tier_file, enriched_tiered_builtin_msgraph_app_permissions_from_aat)

        if has_aat_been_updated:
            print ('Built-in MS Graph app permissions: changes have been detected and merged from AAT')
        else:
            print ('Built-in MS Graph app permissions: no changes detected in AAT, but local changes have been overridden')
    else:
        print ('Built-in MS Graph app permissions: no changes')
