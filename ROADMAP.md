# VPN Tools API Roadmap 🚀

This document outlines the development plan to evolve the API into a comprehensive VPN utility platform.

## 🏆 Masterplan (4 Phases)

### Phase 1: Security & Stability ✅
- [x] **Rate Limiting:** Protect against DDoS/Spam (100 req/3s).
- [x] **SSL/HTTPS Integration:** Auto-renew certificates using Certbot.
- [x] **Log Monitoring:** Admin endpoint to view system logs (via Docker logs).

### Phase 2: Converter Refinement ✅
- [x] **UDP Toggle:** Allow enabling/disabling UDP in config.
- [x] **Advanced Filters:** Regex include/exclude for account names.
- [x] **Force SNI:** Overwrite SNI/Host for all accounts.
- [x] **Expired Cleaner:** Remove accounts with expired dates.
- [x] **Filter by Country/ISP:** (Partial via filters).
- [x] **Auto-Rename:** Standardize server names.

### Phase 3: Growth & Content ✅
- [x] **Network Utilities:** Added Ping, Port Scan, CIDR, and MyIP tools.
- [x] **Free Account Scraper:** Bot to aggregate free VPNs from public sources.
- [ ] **Warp+ Key Generator:** Generate Cloudflare Warp+ license keys (Skipped for stability).
- [x] **Telegram Bot V1:** Interactive bot for converting links via chat.

### Phase 4: Pro Ecosystem ✅
- [x] **User Database:** Simple auth system for persistent configs.
- [x] **Speedtest Lite:** Real-time proxy speed measurement (Mock/Simple).
- [x] **Pretty Print:** Web-based config viewer.

---

## 🛠️ Complete Feature Set

### Converter & Subscription
1. [x] **Regex Filtering**
2. [x] **Emoji Flags** (Manual logic needed)
3. [x] **Expired Cleaner**
4. [x] **Protocol Selector**
5. [ ] **Custom Proxy Groups**
6. [x] **Force SNI/Host**
7. [x] **UDP Relay Toggle**
8. [ ] **Sort by Ping** (Client side preferred)
9. [x] **Auto-Rename**

### Checker Tools
10. [x] **Port Scan**
11. [x] **ICMP Ping**
12. [ ] **Website Check**
13. [ ] **SSL Info**

### Network Utilities
14. [x] **CIDR Calculator**
15. [x] **MyIP Info**
16. [ ] **DNS Checker**
17. [ ] **MAC Vendor Lookup**
18. [x] **User-Agent Parser**

### System & Ops
19. [ ] **Auto-Update Blocklist**
20. [x] **Cache Warmer**
21. [ ] **Backup Config**
22. [x] **Telegram Bot Integration**
