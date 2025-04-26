"""
    Name: 
        convert-json-to-markdown
        
    Author: 
        Emilien Socchi

    Description:  
         convert-json-to-markdown converts roles and permissions already categorized in specific tiers from JSON to Markdown.

    Requirements:
        None

"""
import json
import os
import sys


def remove_substring_until_char(original_string, substring, char):
    """
        Removes all occurrences of a substring from the end of a string until a certain character is encountered.

        Parameters:
            original_string(str): the original string
            substring(str): the substring to be removed
            char(str): the character until which the substring should be removed

        Returns:
            str: the modified string with the substring removed until the specified character

    """
    reversed_s = original_string[::-1]
    reversed_substring = substring[::-1]
    reversed_char = char[::-1]
    char_pos = reversed_s.find(reversed_char)
    
    if char_pos != -1:
        modified_s = reversed_s[:char_pos].replace(reversed_substring, '') + reversed_s[char_pos:]
    else:
        modified_s = reversed_s.replace(reversed_substring, '')
    
    return modified_s[::-1]


def convert_azure_json_to_markdown(azure_json_file, azure_markdown_file):
    """
        Converts and outputs the Azure roles tiering information located in the passed JSON file to Markdown.
        The Azure roles tiering data is enriched with documentation URIs to role definitions.

        Args:
            azure_json_file(str): the JSON file containing Azure roles tiering to parse from
            azure_markdown_file(str): the output file to which the converted Markdown is exported to

        Returns:
            None

    """
    try:
        upstream_uri = 'https://github.com/emiliensocchi/azure-tiering/tree/main/Azure%20roles'
        tier_0_assets = []
        tier_1_assets = []
        tier_2_assets = []
        tier_3_assets = []
        
        with open(azure_json_file, 'r', encoding = 'utf-8') as file:
            file_content = json.load(file)
            tier_0_assets = [asset for asset in file_content if asset['tier'] == '0']
            tier_1_assets = [asset for asset in file_content if asset['tier'] == '1']
            tier_2_assets = [asset for asset in file_content if asset['tier'] == '2']
            tier_3_assets = [asset for asset in file_content if asset['tier'] == '3']

        with open(azure_markdown_file, 'r+', encoding = 'utf-8') as file:
            file_content = file.read()
            splitter = '##' 
            splitted_content = file_content.split(splitter)
            page_metadata = splitted_content[0] + splitter + splitted_content[1]

            tier_0_content = splitter + splitted_content[2]
            tier_1_content = splitter + splitted_content[3]
            tier_2_content = splitter + splitted_content[4]
            tier_3_content = splitter + splitted_content[5]

            # Tier 0
            new_tier_0_content = ''
            splitter = '\n| ['
            splitted_tier_0_content = tier_0_content.split(splitter)
            splitter = "<a id='tier-"
            tier_0_footer = ''

            if len(splitted_tier_0_content) == 1:
                # No asset has been tiered yet
                splitted_tier_0_content = tier_0_content.split(splitter)
                tier_0_footer = "\n\n\n" + splitter + splitted_tier_0_content[-1]
            else:
                tier_0_footer = splitted_tier_0_content[-1].split('|')[-1]

            tier_0_header = remove_substring_until_char(splitted_tier_0_content[0], '\n', '|')

            for tier_0_asset in tier_0_assets:
                # Build hyperlinks
                asset_name_anchor = tier_0_asset['assetName'].lower().replace(' ', '-')
                upstream_link = f"{upstream_uri}#{asset_name_anchor}"
                # Build Markdown content
                name = f"[{tier_0_asset['assetName']}]({upstream_link})" if tier_0_asset['assetType'] == 'Built-in' else tier_0_asset['assetName']
                type = tier_0_asset['assetType']
                shortest_path = tier_0_asset['shortestPath']
                example = tier_0_asset['example']
                # Build line
                line = f"\n| {name} | {type} | {shortest_path} | {example} |"
                new_tier_0_content += line

            new_tier_0_content = tier_0_header + new_tier_0_content + tier_0_footer

            # Tier 1
            new_tier_1_content = ''
            splitter = '\n| ['
            splitted_tier_1_content = tier_1_content.split(splitter)
            splitter = "<a id='tier-"
            tier_1_footer = ''

            if len(splitted_tier_1_content) == 1:
                # No asset has been tiered yet
                splitted_tier_1_content = tier_1_content.split(splitter)
                tier_1_footer = "\n\n\n" + splitter + splitted_tier_1_content[-1]
            else:
                tier_1_footer = splitted_tier_1_content[-1].split('|')[-1]

            tier_1_header = remove_substring_until_char(splitted_tier_1_content[0], '\n', '|')

            for tier_1_asset in tier_1_assets:
                # Build hyperlink
                asset_name_anchor = tier_1_asset['assetName'].lower().replace(' ', '-')
                upstream_link = f"{upstream_uri}#{asset_name_anchor}"
                # Build Markdown content
                name = f"[{tier_1_asset['assetName']}]({upstream_link})" if tier_1_asset['assetType'] == 'Built-in' else tier_1_asset['assetName']
                type = tier_1_asset['assetType'] 
                shortest_path = tier_1_asset['shortestPath']
                example = tier_1_asset['example']
                # Build line
                line = f"\n| {name} | {type} | {shortest_path} | {example} |"
                new_tier_1_content += line

            new_tier_1_content = tier_1_header + new_tier_1_content + tier_1_footer

            # Tier 2
            new_tier_2_content = ''
            splitter = '\n| ['
            splitted_tier_2_content = tier_2_content.split(splitter)
            splitter = "<a id='tier-"
            tier_2_footer = ''

            if len(splitted_tier_2_content) == 1:
                # No asset has been tiered yet
                splitted_tier_2_content = tier_2_content.split(splitter)
                tier_2_footer = "\n\n\n" + splitter + splitted_tier_2_content[-1]
            else:
                tier_2_footer = splitted_tier_2_content[-1].split('|')[-1]

            tier_2_header = remove_substring_until_char(splitted_tier_2_content[0], '\n', '|')

            for tier_2_asset in tier_2_assets:
                # Build hyperlink
                asset_name_anchor = tier_2_asset['assetName'].lower().replace(' ', '-')
                upstream_link = f"{upstream_uri}#{asset_name_anchor}"
                # Build Markdown content
                name = f"[{tier_2_asset['assetName']}]({upstream_link})" if tier_2_asset['assetType'] == 'Built-in' else tier_2_asset['assetName']
                type = tier_2_asset['assetType']
                worst_case_scenario = tier_2_asset['worstCaseScenario']
                # Build line
                line = f"\n| {name} | {type} | {worst_case_scenario} |"
                new_tier_2_content += line

            new_tier_2_content = tier_2_header + new_tier_2_content + tier_2_footer

            # Tier 3
            new_tier_3_content = ''
            splitter = '\n| ['
            splitted_tier_3_content = tier_3_content.split(splitter)
            splitter = "<a id='tier-"

            if len(splitted_tier_3_content) == 1:
                # No asset has been tiered yet
                splitted_tier_3_content = tier_3_content.split(splitter)

            tier_3_header = remove_substring_until_char(splitted_tier_3_content[0], '\n', '|')
            tier_3_footer = "\n"

            for tier_3_asset in tier_3_assets:
                # Build hyperlink
                asset_name_anchor = tier_3_asset['assetName'].lower().replace(' ', '-')
                upstream_link = f"{upstream_uri}#{asset_name_anchor}"
                # Build Markdown content
                name = f"[{tier_3_asset['assetName']}]({upstream_link})" if tier_3_asset['assetType'] == 'Built-in' else tier_3_asset['assetName']
                type = tier_3_asset['assetType']
                worst_case_scenario = tier_3_asset['worstCaseScenario']
                # Build line
                line = f"\n| {name} | {type} | {worst_case_scenario} |"
                new_tier_3_content += line

            new_tier_3_content = tier_3_header + new_tier_3_content + tier_3_footer

            new_page_content = page_metadata + new_tier_0_content + new_tier_1_content + new_tier_2_content + new_tier_3_content
            file.seek(0)
            file.write(new_page_content)

    except FileNotFoundError:
        print('FATAL ERROR - Converting Azure JSON to markdown has failed.')
        exit()


def convert_entra_json_to_markdown(entra_json_file, entra_markdown_file):
    """
        Converts and outputs the Entra roles tiering information located in the passed JSON file to Markdown.
        The Entra roles tiering data is enriched with documentation URIs to role definitions.

        Args:
            entra_entra_json_file(str): the JSON file containing Entra roles tiering to parse from
            entra_entra_markdown_file(str): the output file to which the converted Markdown is exported to

        Returns:
            None

    """
    try:
        upstream_uri = 'https://github.com/emiliensocchi/azure-tiering/tree/main/Entra%20roles'
        tier_0_assets = []
        tier_1_assets = []
        tier_2_assets = []
        
        with open(entra_json_file, 'r', encoding = 'utf-8') as file:
            file_content = json.load(file)
            tier_0_assets = [asset for asset in file_content if asset['tier'] == '0']
            tier_1_assets = [asset for asset in file_content if asset['tier'] == '1']
            tier_2_assets = [asset for asset in file_content if asset['tier'] == '2']

        with open(entra_markdown_file, 'r+', encoding = 'utf-8') as file:
            file_content = file.read()
            splitter = '##' 
            splitted_content = file_content.split(splitter)
            page_metadata = splitted_content[0] + splitter + splitted_content[1]

            tier_0_content = splitter + splitted_content[2]
            tier_1_content = splitter + splitted_content[3]
            tier_2_content = splitter + splitted_content[4]

            # Tier 0
            new_tier_0_content = ''
            splitter = '\n| ['
            splitted_tier_0_content = tier_0_content.split(splitter)
            splitter = "<a id='tier-"
            tier_0_footer = ''

            if len(splitted_tier_0_content) == 1:
                # No asset has been tiered yet
                splitted_tier_0_content = tier_0_content.split(splitter)
                tier_0_footer = "\n\n\n" + splitter + splitted_tier_0_content[-1]
            else:
                tier_0_footer = splitted_tier_0_content[-1].split('|')[-1]

            tier_0_header = remove_substring_until_char(splitted_tier_0_content[0], '\n', '|')

            for tier_0_asset in tier_0_assets:
                # Build hyperlink
                asset_name_anchor = tier_0_asset['assetName'].lower().replace(' ', '-')
                upstream_link = f"{upstream_uri}#{asset_name_anchor}"
                # Build Markdown content
                name = f"[{tier_0_asset['assetName']}]({upstream_link})" if tier_0_asset['assetType'] == 'Built-in' else tier_0_asset['assetName']
                type = tier_0_asset['assetType']
                path_type = tier_0_asset['pathType']
                shortest_path = tier_0_asset['shortestPath']
                example = tier_0_asset['example']
                # Build line
                line = f"\n| {name} | {type} | {path_type} | {shortest_path} | {example} |"
                new_tier_0_content += line

            new_tier_0_content = tier_0_header + new_tier_0_content + tier_0_footer

            # Tier 1
            new_tier_1_content = ''
            splitter = '\n| ['
            splitted_tier_1_content = tier_1_content.split(splitter)
            splitter = "<a id='tier-"
            tier_1_footer = ''

            if len(splitted_tier_1_content) == 1:
                # No asset has been tiered yet
                splitted_tier_1_content = tier_1_content.split(splitter)
                tier_1_footer = "\n\n\n" + splitter + splitted_tier_1_content[-1]
            else:
                tier_1_footer = splitted_tier_1_content[-1].split('|')[-1]

            tier_1_header = remove_substring_until_char(splitted_tier_1_content[0], '\n', '|')
            
            for tier_1_asset in tier_1_assets:
                # Build hyperlink
                asset_name_anchor = tier_1_asset['assetName'].lower().replace(' ', '-')
                upstream_link = f"{upstream_uri}#{asset_name_anchor}"
                # Build Markdown content
                name = f"[{tier_1_asset['assetName']}]({upstream_link})" if tier_1_asset['assetType'] == 'Built-in' else tier_1_asset['assetName']
                type = tier_1_asset['assetType']
                provides_full_access_to = tier_1_asset['providesFullAccessTo']
                # Build line
                line = f"\n| {name} | {type} | {provides_full_access_to} |"
                new_tier_1_content += line

            new_tier_1_content = tier_1_header + new_tier_1_content + tier_1_footer

            # Tier 2
            new_tier_2_content = ''
            splitter = '\n| ['
            splitted_tier_2_content = tier_2_content.split(splitter)
            splitter = "<a id='tier-"

            if len(splitted_tier_2_content) == 1:
                # No asset has been tiered yet
                splitted_tier_2_content = tier_2_content.split(splitter)

            tier_2_header = remove_substring_until_char(splitted_tier_2_content[0], '\n', '|')
            tier_2_footer = "\n"

            for tier_2_asset in tier_2_assets:
                # Build hyperlink
                asset_name_anchor = tier_2_asset['assetName'].lower().replace(' ', '-')
                upstream_link = f"{upstream_uri}#{asset_name_anchor}"
                # Build Markdown content
                name = f"[{tier_2_asset['assetName']}]({upstream_link})"if tier_2_asset['assetType'] == 'Built-in' else tier_2_asset['assetName']
                type = tier_2_asset['assetType']
                # Build line
                line = f"\n| {name} | {type} |"
                new_tier_2_content += line

            new_tier_2_content = tier_2_header + new_tier_2_content + tier_2_footer

            new_page_content = page_metadata + new_tier_0_content + new_tier_1_content + new_tier_2_content
            file.seek(0)
            file.write(new_page_content)

    except FileNotFoundError:
        print('FATAL ERROR - Converting Entra json to markdown has failed.')
        exit()


def convert_msgraph_json_to_markdown(msgraph_json_file, msgraph_markdown_file):
    """
        Converts and outputs the MS Graph applications permission tiering information located in the passed JSON file to Markdown.
        The application permissions tiering data is enriched with documentation URIs to role definitions.

        Args:
            msgraph_json_file(str): the JSON file containing application permissions tiering to parse from
            msgraph_markdown_file(str): the output file to which the converted Markdown is exported to

        Returns:
            None

    """
    try:
        upstream_uri = 'https://github.com/emiliensocchi/azure-tiering/tree/main/Microsoft%20Graph%20application%20permissions'
        tier_0_assets = []
        tier_1_assets = []
        tier_2_assets = []
        
        with open(msgraph_json_file, 'r', encoding = 'utf-8') as file:
            file_content = json.load(file)
            tier_0_assets = [asset for asset in file_content if asset['tier'] == '0']
            tier_1_assets = [asset for asset in file_content if asset['tier'] == '1']
            tier_2_assets = [asset for asset in file_content if asset['tier'] == '2']

        with open(msgraph_markdown_file, 'r+', encoding = 'utf-8') as file:
            file_content = file.read()
            splitter = '##' 
            splitted_content = file_content.split(splitter)
            page_metadata = splitted_content[0] + splitter + splitted_content[1]

            tier_0_content = splitter + splitted_content[2]
            tier_1_content = splitter + splitted_content[3]
            tier_2_content = splitter + splitted_content[4]

            # Tier 0
            new_tier_0_content = ''
            splitter = '\n| ['
            splitted_tier_0_content = tier_0_content.split(splitter)
            splitter = "<a id='tier-"
            tier_0_footer = ''

            if len(splitted_tier_0_content) == 1:
                # No asset has been tiered yet
                splitted_tier_0_content = tier_0_content.split(splitter)
                tier_0_footer = "\n\n\n" + splitter + splitted_tier_0_content[-1]
            else:
                tier_0_footer = splitted_tier_0_content[-1].split('|')[-1]

            tier_0_header = remove_substring_until_char(splitted_tier_0_content[0], '\n', '|')

            for tier_0_asset in tier_0_assets:
                # Build hyperlink
                asset_name_anchor = tier_0_asset['assetName'].lower().replace(' ', '-')
                upstream_link = f"{upstream_uri}#{asset_name_anchor}"
                # Build Markdown content
                name = f"[{tier_0_asset['assetName']}]({upstream_link})" if tier_0_asset['assetType'] == 'Built-in' else tier_0_asset['assetName']
                type = tier_0_asset['assetType']
                path_type = tier_0_asset['pathType']
                shortest_path = tier_0_asset['shortestPath']
                example = tier_0_asset['example']
                # Build line
                line = f"\n| {name} | {type} | {path_type} | {shortest_path} | {example} |"
                new_tier_0_content += line

            new_tier_0_content = tier_0_header + new_tier_0_content + tier_0_footer

            # Tier 1
            new_tier_1_content = ''
            splitter = '\n| ['
            splitted_tier_1_content = tier_1_content.split(splitter)
            splitter = "<a id='tier-"
            tier_1_footer = ''

            if len(splitted_tier_1_content) == 1:
                # No asset has been tiered yet
                splitted_tier_1_content = tier_1_content.split(splitter)
                tier_1_footer = "\n\n\n" + splitter + splitted_tier_1_content[-1]
            else:
                tier_1_footer = splitted_tier_1_content[-1].split('|')[-1]

            tier_1_header = remove_substring_until_char(splitted_tier_1_content[0], '\n', '|')

            for tier_1_asset in tier_1_assets:
                # Build hyperlink
                asset_name_anchor = tier_1_asset['assetName'].lower().replace(' ', '-')
                upstream_link = f"{upstream_uri}#{asset_name_anchor}"
                # Build Markdown content
                name = f"[{tier_1_asset['assetName']}]({upstream_link})" if tier_1_asset['assetType'] == 'Built-in' else tier_1_asset['assetName']
                type = tier_1_asset['assetType']
                # Build line
                line = f"\n| {name} | {type} |"
                new_tier_1_content += line

            new_tier_1_content = tier_1_header + new_tier_1_content + tier_1_footer

            # Tier 2
            new_tier_2_content = ''
            splitter = '\n| ['
            splitted_tier_2_content = tier_2_content.split(splitter)
            splitter = "<a id='tier-"

            if len(splitted_tier_2_content) == 1:
                # No asset has been tiered yet
                splitted_tier_2_content = tier_2_content.split(splitter)

            tier_2_header = remove_substring_until_char(splitted_tier_2_content[0], '\n', '|')
            tier_2_footer = "\n"

            for tier_2_asset in tier_2_assets:
                # Build hyperlink
                asset_name_anchor = tier_2_asset['assetName'].lower().replace(' ', '-')
                upstream_link = f"{upstream_uri}#{asset_name_anchor}"
                # Build Markdown content
                name = f"[{tier_2_asset['assetName']}]({upstream_link})" if tier_2_asset['assetType'] == 'Built-in' else tier_2_asset['assetName']
                type = tier_2_asset['assetType']
                # Build line
                line = f"\n| {name} | {type} |"
                new_tier_2_content += line

            new_tier_2_content = tier_2_header + new_tier_2_content + tier_2_footer

            new_page_content = page_metadata + new_tier_0_content + new_tier_1_content + new_tier_2_content
            file.seek(0)
            file.write(new_page_content)

    except FileNotFoundError:
        print('FATAL ERROR - Converting MS Graph json to markdown has failed.')
        exit()


if __name__ == "__main__":
    # Set local directories
    github_action_dir_name = '.github'
    absolute_path_to_script = os.path.abspath(sys.argv[0])
    root_dir = absolute_path_to_script.split(github_action_dir_name)[0]
    azure_dir = root_dir + 'Azure roles'
    entra_dir = root_dir + 'Entra roles'
    app_permissions_dir = root_dir + 'Microsoft Graph application permissions'
    
    # Set local Markdown files
    azure_role_markdown_file = f"{azure_dir}/README.md"
    entra_roles_markdown_file = f"{entra_dir}/README.md"
    app_permissions_markdown_file = f"{app_permissions_dir}/README.md"

    # Set local JSON files
    azure_roles_json_file = f"{azure_dir}/tiered-azure-roles.json"
    entra_roles_json_file = f"{entra_dir}/tiered-entra-roles.json"
    app_permissions_json_file = f"{app_permissions_dir}/tiered-msgraph-app-permissions.json"

    # Convert JSON content for Azure roles to Markdown
    print (f"Converting for: Azure roles")
    convert_azure_json_to_markdown(azure_roles_json_file, azure_role_markdown_file)

    # Convert JSON content for Entra roles to Markdown
    print (f"Converting for: Entra roles")
    convert_entra_json_to_markdown(entra_roles_json_file, entra_roles_markdown_file)

    # Convert JSON content for MS Graph application permissions to Markdown
    print (f"Converting for: MS Graph application permissions")
    convert_msgraph_json_to_markdown(app_permissions_json_file, app_permissions_markdown_file)
