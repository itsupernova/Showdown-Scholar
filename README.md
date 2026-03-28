# 🛡️ Showdown Scholar: Pokémon VGC & Singles Analytics Bot

**Showdown Scholar** is a high-performance Discord bot built with `discord.py` that parses Pokémon Showdown replay logs to provide deep tactical insights. Unlike basic win/loss trackers, this bot calculates **Direct vs. Passive damage**, identifies **Synergy Pairs** in Doubles, and generates a **Threat Index** using real type-matchup data.

---

## 🚀 Key Features

### 📊 Advanced Analytics
* **Direct Damage Logic:** Automatically filters out "Passive Damage" (Sandstorm, Stealth Rock, Poison) to measure true offensive pressure.
* **Tankiness Tracking:** Calculates **Average Damage Taken** per match to identify your most reliable sponges and redirectors.
* **Top 6 Anchors:** Tracks "Turn Presence" to show which Pokémon spend the most time on the field, identifying your team's true core.

### 🤝 Doubles Synergy Engine
* Analyzes Pokémon pairs active on the field simultaneously.
* Calculates a **Synergy Score** based on shared damage output and win rate.

### ⚠️ Dynamic Threat Index (Nemesis System)
Uses the `pypokedex` library to cross-reference your most-used Pokémon against opponents that beat you.
* **Weighting:** $T = (D \times 0.25) + (P \times 0.25) + (W \times 0.50)$
* **Type Logic:** Factors in super-effective hits, resistances, and "walls" (where the opponent resists your anchors).

---

## 🛠️ Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/YOUR_USERNAME/showdown-scholar-bot.git](https://github.com/YOUR_USERNAME/showdown-scholar-bot.git)
   cd showdown-scholar-bot
