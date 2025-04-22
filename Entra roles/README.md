# 🌩️ Entra roles tiering

Tiering of Microsoft Entra roles **based on known attack paths**.

## 📃 Tier definition

| Color | Tier | Name | Definition |
|---|---|---|---|
| 🔴 | 0 | [Family of Global Admins](#tier-0) | Roles with a risk of having a direct or indirect path to Global Admin and full tenant takeover. |
| 🟠 | 1 | [Family of M365 and restricted Entra Admins](#tier-1) | Roles with full access to individual Microsoft 365 services, limited administrative access to Entra ID, or global read access across services, but <u>without</u> a known path to Global Admin. |
| 🟢 | 2 | [Family of unprivileged administrators](#tier-2) | Roles with little to no security implications. |


<a id='tier-0'></a>
## 🔴 Tier 0: Family of Global Admins

**Description**: roles with a risk of having a direct or indirect path to Global Admin and full tenant takeover.

| Entra role | Role type | Path type | Shortest path | Example |
|---|---|---|---|---|
| 📌 *Name of the Entra role.* | *Whether the role is built-in or custom.* |  *"Direct" means the escalation requires a single step to become Global Admin. "Indirect" means the privilege escalation requires two or more steps.* | *One of the shortest paths possible to Global Admin that is known with the Entra role. <br> It does **not** mean this is the most common or only possible path. In most cases, a large number of paths are possible, but the idea is to document one of the shortest to demonstrate the risk.* | *A concrete high-level example with a Threat Actor (TA), illustrating the "Known shortest path".* |


<a id='tier-1'></a>
## 🟠 Tier 1: Family of M365 and restricted Entra Admins

**Description**: roles with full access to individual Microsoft 365 services, limited administrative access to Entra ID, or global read access across services, but <u>without</u> a known path to Global Admin.

| Entra role | Role type | Provides <u>full</u> access to |
|---|---|---|


<a id='tier-2'></a>
## 🟢 Tier 2: Family of unprivileged administrators

**Description**: roles with little to no security implications.

| Entra role | Role type |
|---|---|
