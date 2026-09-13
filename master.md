# Domain Expansion: Infinite Void v2.0

<img width="1376" height="768" alt="image" src="https://github.com/user-attachments/assets/cb0a22cb-8609-471f-8e89-d57761ef33b0" />

An ultra-fast Active Directory object dumper forged with the absolute perception of Gojo Satoru. Freezes a Domain Controller via LDAP and strips it of every high-value target in seconds — privileged groups, Kerberoastable accounts, delegation misconfigs, LAPS passwords, GMSA accounts, leaked credentials, password policy, trust relationships, and more.

Built for the AD segments of **OSCP** and **CPTS**. One command, total domain visibility.

**Husky Hacker × Infinite Void**

*"Throughout Heaven and Earth, I alone am the honored one."*

---

## What's New in v2.0

| v1 (4 queries) | v2 (13 techniques) |
|---|---|
| Domain Admins only | All 10 privileged groups enumerated |
| Basic Kerberoast | Kerberoast with AdminCount flagging |
| AS-REP Roast | AS-REP Roast (unchanged) |
| Password in descriptions | Broader keyword search (pass, pwd, cred, temp, default, secret, key) |
| — | Unconstrained / Constrained / RBCD delegation |
| — | LAPS password extraction |
| — | GMSA account enumeration |
| — | AdminCount=1 user dump |
| — | Domain password policy (lockout check for spraying) |
| — | Password never expires accounts |
| — | All domain computers with OS versions |
| — | Domain trust relationships |
| — | Full user dump (spray list auto-saved) |
| — | LDAPS support |
| — | Pass-the-Hash support |
| — | JSON report + user list file output |

---

## Prerequisites

```bash
pip install ldap3
```

---

## Usage

```bash
python3 infinite_void.py -d <DOMAIN> -u <USER> [-p <PASSWORD> | -H <HASH>] -dc <DC_IP>
```

### Examples

```bash
# Standard — plaintext password
python3 infinite_void.py -d corp.local -u megumi -p 'Shadows123!' -dc 10.10.11.200

# Pass-the-Hash — NT hash only (LM auto-padded)
python3 infinite_void.py -d corp.local -u satoru -H 31d6cfe0d16ae931b73c59d7e0c089c0 -dc 10.10.11.200

# LDAPS (port 636, encrypted)
python3 infinite_void.py -d corp.local -u user -p 'pass' -dc 10.10.11.200 --ldaps

# Save output to a directory
python3 infinite_void.py -d corp.local -u user -p 'pass' -dc 10.10.11.200 -o ./loot/

# Just dump users (for spray lists)
python3 infinite_void.py -d corp.local -u user -p 'pass' -dc 10.10.11.200 --users-only

# With scope.sh variables
python3 infinite_void.py -d $AD_DOMAIN -u $AD_USER -p $AD_PASS -dc $AD_DC -o ./loot/
```

### Options

| Flag | Description | Default |
|---|---|---|
| `-d, --domain` | Fully qualified domain name | required |
| `-u, --user` | Compromised domain username | required |
| `-p, --password` | Plaintext password | (or -H) |
| `-H, --hash` | NTLM hash (LM:NT or just NT) | (or -p) |
| `-dc, --dc-ip` | Domain Controller IP | required |
| `--ldaps` | Use LDAPS (port 636) | off |
| `-o, --output` | Output directory for JSON + user list | current dir |
| `--users-only` | Only dump domain users and exit | off |

---

## Sorcery Techniques

### THE SIX EYES — Privileged Group Isolation
Enumerates members of all 10 high-value groups:

| Group | Why It Matters |
|---|---|
| Domain Admins | Full domain control |
| Enterprise Admins | Forest-wide admin |
| Administrators | Local admin on DC |
| Backup Operators | Backup SAM/SYSTEM → offline hash extraction |
| Server Operators | Modify services on DC → binpath hijack |
| Account Operators | Modify non-admin accounts → password reset chain |
| DnsAdmins | Load malicious DLL via DNS service |
| Remote Desktop Users | RDP access |
| Remote Management Users | WinRM / Evil-WinRM access |
| Group Policy Creator Owners | Create/modify GPOs |

### LAPSE BLUE — Kerberoastable Accounts
Finds accounts with `servicePrincipalName` set. Flags accounts with `AdminCount=1` as high-value targets — cracking their TGS hash gives you a privileged account.

```
→ Crack with: hashcat -m 13100 kerberoast.hash rockyou.txt
```

### REVERSAL RED — AS-REP Roastable Accounts
Finds accounts with `DONT_REQ_PREAUTH` — request a TGT without authentication, crack it offline.

```
→ Crack with: hashcat -m 18200 asrep.hash rockyou.txt
```

### HOLLOW PURPLE — Password Leaks
Searches user description fields for keywords: pass, pwd, cred, temp, default, initial, secret, key. These are surprisingly common — admins love putting temporary passwords in descriptions and forgetting about them.

### AMPLIFICATION — Delegation Misconfigurations
Detects three types of delegation abuse:

| Type | Risk | Attack |
|---|---|---|
| **Unconstrained** | Critical | Any user authenticating to this machine can be impersonated |
| **Constrained** | High | Can impersonate users to specific SPNs via S4U2Proxy |
| **RBCD** | High | Resource-based constrained delegation configured |

### DOMAIN AMPLIFICATION — LAPS Passwords
Attempts to read Local Administrator Password Solution (LAPS) attributes. If your user has `ReadLAPSPassword` rights, you get the local admin password in cleartext.

### LIMITLESS — GMSA Accounts
Enumerates Group Managed Service Accounts. If your user can read the `msDS-ManagedPassword` attribute, extract the NT hash.

```
→ Read with: bloodyAD get object <gmsa> --attr msDS-ManagedPassword
```

### PERCEPTION — AdminCount=1 Users
Lists all users with `AdminCount=1` — these have been (or currently are) members of a privileged group. Even if removed, their ACLs may still be elevated.

### BARRIER — Password Policy
Dumps the domain password policy. The critical check: **lockout threshold**. If it's 0, password spraying is safe with no risk of lockout.

### INFINITY — Password Never Expires
Accounts with `DONT_EXPIRE_PASSWORD` set. These often have weak, old passwords that were never rotated.

### SCANNING — Domain Computers
Lists all domain-joined computers with operating system versions. Useful for identifying legacy systems (Server 2008, Windows 7) that may have unpatched vulnerabilities.

### DIMENSIONAL RIFT — Domain Trusts
Maps trust relationships between domains. Bidirectional trusts can enable cross-domain attacks.

### MAP — Domain User Dump
Dumps all domain usernames and saves to a file for Kerberoasting, AS-REP Roasting, and password spraying.

---

## Output Files

The tool saves three files to the output directory:

| File | Contents |
|---|---|
| `<domain>_void_<timestamp>.json` | Full JSON report with all findings |
| `<domain>_users.txt` | One username per line — ready for spraying |
| `<domain>_kerberoastable.txt` | Kerberoastable accounts and their SPNs |

### Pipe into Other Tools

```bash
# Kerberoast every SPN found
impacket-GetUserSPNs "$AD_DOMAIN/$AD_USER:$AD_PASS" -dc-ip $AD_DC -request

# AS-REP Roast using the user list
impacket-GetNPUsers "$AD_DOMAIN/" -usersfile corp_users.txt -no-pass -dc-ip $AD_DC

# Password spray the user list
crackmapexec smb $AD_DC -u corp_users.txt -p 'Welcome1!' -d $AD_DOMAIN --continue-on-success
kerbrute passwordspray -d $AD_DOMAIN --dc $AD_DC corp_users.txt 'Welcome1!'

# Feed findings into adchain
adchain chain "user>GenericAll>svc>DCSync>domain" -d $AD_DOMAIN --dc-ip $AD_DC -p 'pass'
```

---

## OSCP Exam Workflow

```bash
# 1. Get starting creds from exam panel
# 2. Run Infinite Void immediately
python3 infinite_void.py -d $AD_DOMAIN -u $AD_USER -p $AD_PASS -dc $AD_DC -o ./loot/

# 3. Check findings:
#    - Kerberoastable admin? → hashcat -m 13100
#    - Password in description? → try it everywhere
#    - No lockout policy? → spray with user list
#    - Delegation? → S4U2Proxy / RBCD attack
#    - LAPS readable? → local admin password

# 4. Run BloodHound for ACL paths
bloodhound-python -u $AD_USER -p $AD_PASS -d $AD_DOMAIN -ns $AD_DC -c All

# 5. Map the chain with adchain
adchain chain "user>WriteDACL>svc>DCSync>domain" -d $AD_DOMAIN --dc-ip $AD_DC -p 'pass'
```

---

## Legal

Created exclusively for authorized penetration testing, Active Directory security audits, and educational CTF structures.

*"Don't worry, I'm the strongest."* — Gojo Satoru

---

## License

MIT
