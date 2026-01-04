# VPN Tools API Roadmap 🚀

This document outlines the development plan to evolve the API into a comprehensive VPN utility platform.

## 🏆 Masterplan (4 Phases)

### Phase 1: Security & Stability 🛡️
Focus: Hardening the system for production use.
- [x] **Rate Limiting:** Protect against DDoS/Spam (100 req/3s).
- [x] **SSL/HTTPS Integration:** Auto-renew certificates using Certbot.
- [ ] **Log Monitoring:** Admin endpoint to view system logs.

### Phase 2: Converter Refinement 🔧
Focus: Making the `/sub` endpoint smarter.
- [x] **UDP Toggle:** Allow enabling/disabling UDP in config.
- [x] **Advanced Filters:** Regex include/exclude for account names.
- [x] **Force SNI:** Overwrite SNI/Host for all accounts.
- [x] **Expired Cleaner:** Remove accounts with expired dates.
- [ ] **Filter by Country/ISP:** e.g., `/sub?country=ID`.
- [ ] **Auto-Rename:** Standardize server names (e.g., `Server-01`, `Server-02`).

### Phase 3: Growth & Content 📈
Focus: Attracting users.
- [x] **Network Utilities:** Added Ping, Port Scan, CIDR, and MyIP tools.
- [x] **Free Account Scraper:** Bot to aggregate free VPNs from public sources (`/free`).
- [ ] **Warp+ Key Generator:** Generate Cloudflare Warp+ license keys.
- [ ] **Telegram Bot V1:** Interactive bot for converting links via chat.

### Phase 4: Pro Ecosystem 👑
Focus: Advanced features.
- [ ] **User Database:** Simple auth system for persistent configs.
- [ ] **Speedtest Lite:** Real-time proxy speed measurement.

---

## 🛠️ Feature Backlog Status

### Converter & Subscription
1. [x] **Regex Filtering:** Filter accounts by name pattern.
2. [ ] **Emoji Flags:** Add country flags (🇮🇩) to proxy names based on GeoIP.
3. [x] **Expired Cleaner:** Remove accounts with expired dates in names.
4. [x] **Protocol Selector:** `/sub?filter_protocol=vmess`.
5. [ ] **Custom Proxy Groups:** Allow user-defined group names.
6. [x] **Force SNI/Host:** Overwrite SNI for all accounts (Bug fixing).
7. [x] **UDP Relay Toggle:** Option to enable/disable UDP in config.
8. [ ] **Sort by Ping:** Order proxies by latency (cached).

### Checker Tools
9. [x] **Port Scan:** Check common ports (80, 443, 22) in one go.
10. [x] **ICMP Ping:** Real ping (ms) measurement.
11. [ ] **Website Check:** Test accessibility of Google/Netflix.
12. [ ] **SSL Info:** Show certificate issuer and expiration date.

### Network Utilities
13. [x] **CIDR Calculator:** Subnet masking tool.
14. [x] **MyIP Info:** Show requester's IP and User-Agent.
15. [ ] **DNS Checker:** Debug DNS poisoning.
16. [ ] **MAC Vendor Lookup:** Identify device manufacturer.
17. [x] **User-Agent Parser:** Analyze browser strings (integrated in `/myip`).

### System & Ops
18. [ ] **Auto-Update Blocklist:** Daily update for adblock rules.
19. [x] **Cache Warmer:** Script to keep GeoIP cache fresh (Implemented as passive cache).
20. [ ] **Backup Config:** Auto-backup system settings to Telegram.
