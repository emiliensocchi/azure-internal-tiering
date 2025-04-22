# 🌩️ Azure roles tiering

Tiering of common Microsoft Azure roles **based on known attack paths**.

## 📃 Tier definition

> [!IMPORTANT]
> This model attempts to tier **common** Azure roles

| Color | Tier | Name | Definition |
|---|---|---|---|
| 🔴 | 0 | [Family of privilege ascenders](#tier-0) | Roles with a risk of privilege escalation via one or multiple resource types in scope. |
| 🟠 | 1 | [Family of lateral navigators](#tier-1) | Roles with a risk of lateral movement via data-plane access to a specific resource type in scope, but with a limited risk for privilege escalation. |
| 🟡 | 2 | [Family of data explorers](#tier-2) | Roles with data-plane access to a specific resource type in scope, but with a limited risk for lateral movement and without a risk for privilege escalation. |
| 🟢 | 3 | [Family of unprivileged Azure users](#tier-3) | Roles with little to no security implications. | 


<a id='tier-0'></a>
## 🔴 Tier 0: Family of privilege ascenders

**Description**: roles with a risk of privilege escalation via one or multiple resource types in scope.

| Azure role | Role type | Shortest path | Example |
|---|---|---|---|
| 📌 *Name of the Azure role.* | *Whether the role is built-in or custom.* | *The typical shortest path to escalate privileges with the Azure role. <br> It does **not** mean this is the only possible path. In most cases, a large number of paths are possible, but the idea is to document the "typical" shortest path to demonstrate the risk.* | *A concrete high-level example with a Threat Actor (TA), illustrating the "Shortest path".* |


<a id='tier-1'></a>
## 🟠 Tier 1: Family of lateral navigators

**Description**: roles with a risk of lateral movement via data-plane access to a specific resource type in scope, but with a limited risk for privilege escalation.

| Azure role | Role type | Shortest path | Example |
|---|---|---|---|
| 📌 *Name of the Azure role.* | *Whether the role is built-in or custom.* | *The typical shortest path to move laterally with the Azure role. <br> It does **not** mean this is the only possible path. In most cases, a large number of paths are possible, but the idea is to document the "typical" shortest path to demonstrate the risk.* | *A concrete high-level example with a Threat Actor (TA), illustrating the "Shortest path".* |


<a id='tier-2'></a>
## 🟡 Tier 2: Family of data explorers

**Description**: roles with data-plane access to a specific resource type in scope, but with a limited risk for lateral movement and without a risk for privilege escalation.

| Azure role | Role type | Worst-case scenario |
|---|---|---|
| 📌 *Name of the Azure role.* | *Whether the role is built-in or custom.* | *The worst-case scenario in case a principal with the Azure role is compromised.* |


<a id='tier-3'></a>
## 🟢 Tier 3: Family of unprivileged Azure users

**Description**: roles with little to no security implications.

| Azure role | Role type | Worst-case scenario | 
|---|---|---|
| 📌 *Name of the Azure role.* | *Whether the role is built-in or custom.* | *If any, the worst-case scenario in case a principal with the Azure role is compromised.* |
| [Role assignment reader](#) | Custom | Can read Azure scopes, role assignments and definitions. Provides no access to the control or data plane of Azure resources. |
