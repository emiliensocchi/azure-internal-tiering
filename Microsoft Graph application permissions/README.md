# 🌩️ Application permissions tiering

Tiering of Microsoft Graph application permissions **based on known attack paths**.

## 📃 Tier definition

**Important**: suspicious permissions that have not been tested are categorized as Tier-0 for safety and marked with "⚠️" until they are researched properly.

| Tag | Tier | Name | Definition | 
|---|---|---|---|
| 🔴 | 0 | [Family of Global Admins](#tier-0) | Permissions with a risk of having a direct or indirect path to Global Admin and full tenant takeover. |
| 🟠 | 1 | [Family of restricted Graph permissions](#tier-1) | Permissions with write access to MS Graph scopes or read access to sensitive scopes (e.g. email content), but <u>without</u> a known path to Global Admin. |
| 🟢 | 2 | [Family of unprivileged Graph permission](#tier-2) | Permissions with read access to MS Graph scopes and little to no security implications. |


<a id='tier-0'></a>
## 🔴 Tier 0: Family of Global Admins

**Description**: permissions with a risk of having a direct or indirect path to Global Admin and full tenant takeover.

| Application permission | Permission type | Path type | Known shortest path | Example |
|---|---|---|---|---|
| 📌 *Name of the MS Graph permission.* | *Can only be built-in.* | *"Direct" means the escalation requires a single step to become Global Admin. "Indirect" means the privilege escalation requires two or more steps.* | *One of the shortest paths possible to Global Admin that is known with the application permission. <br> It does **not** mean this is the most common or only possible path. In most cases, a large number of paths are possible, but the idea is to document one of the shortest to demonstrate the risk.* | *A concrete high-level example with a Threat Actor (TA), illustrating the "Known shortest path".* |


<a id='tier-1'></a>
## 🟠 Tier 1: Family of restricted Graph permissions

**Description**: permissions with write access to MS Graph scopes or read access to sensitive scopes (e.g. email content), but <u>without</u> a known path to Global Admin.

| Application permission | Permission type |
|---|---|


<a id='tier-2'></a>
## 🟢 Tier 2: Family of unprivileged Graph permissions

**Description**: Permissions with read access to MS Graph scopes and little to no security implications.

| Application permission | Permission type |
|---|---|