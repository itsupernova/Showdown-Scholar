import discord
from discord.ext import commands
import aiohttp
import os
from dotenv import load_dotenv
from collections import Counter
import pypokedex  

#SETUP & CONFIGURATION
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)
bot.remove_command('help')

TYPE_INTERACTIONS = {
    "Normal":   {"weak": ["Rock", "Steel"], "resist": ["Ghost"]},
    "Fire":     {"weak": ["Fire", "Water", "Rock", "Dragon"], "resist": ["Grass", "Ice", "Bug", "Steel"]},
    "Water":    {"weak": ["Water", "Grass", "Dragon"], "resist": ["Fire", "Ground", "Rock"]},
    "Electric": {"weak": ["Electric", "Grass", "Dragon"], "resist": ["Water", "Flying"]},
    "Grass":    {"weak": ["Fire", "Grass", "Poison", "Flying", "Bug", "Dragon", "Steel"], "resist": ["Water", "Ground", "Rock"]},
    "Ice":      {"weak": ["Fire", "Water", "Ice", "Steel"], "resist": ["Grass", "Ground", "Flying", "Dragon"]},
    "Fighting": {"weak": ["Poison", "Flying", "Psychic", "Bug", "Fairy"], "resist": ["Normal", "Ice", "Rock", "Dark", "Steel"]},
    "Poison":   {"weak": ["Poison", "Ground", "Rock", "Ghost"], "resist": ["Grass", "Fairy"]},
    "Ground":   {"weak": ["Grass", "Bug"], "resist": ["Fire", "Electric", "Poison", "Rock", "Steel"]},
    "Flying":   {"weak": ["Electric", "Rock", "Steel"], "resist": ["Grass", "Fighting", "Bug"]},
    "Psychic":  {"weak": ["Psychic", "Steel"], "resist": ["Fighting", "Poison"]},
    "Bug":      {"weak": ["Fire", "Fighting", "Poison", "Flying", "Ghost", "Steel", "Fairy"], "resist": ["Grass", "Psychic", "Dark"]},
    "Rock":     {"weak": ["Fighting", "Ground", "Steel"], "resist": ["Fire", "Ice", "Flying", "Bug"]},
    "Ghost":    {"weak": ["Dark"], "resist": ["Psychic", "Ghost"]},
    "Dragon":   {"weak": ["Steel"], "resist": ["Dragon"]},
    "Dark":     {"weak": ["Fighting", "Dark", "Fairy"], "resist": ["Psychic", "Ghost"]},
    "Steel":    {"weak": ["Fire", "Water", "Electric", "Steel"], "resist": ["Ice", "Rock", "Fairy"]},
    "Fairy":    {"weak": ["Fire", "Poison", "Steel"], "resist": ["Fighting", "Dragon", "Dark"]}
}

POKE_CACHE = {}

def get_pokemon_types(name):
    """Fetches types from pypokedex or cache."""
    clean_name = name.split('-')[0].lower().replace(" ", "-")
    
    if clean_name in POKE_CACHE:
        return POKE_CACHE[clean_name]
    
    try:
        p = pypokedex.get(name=clean_name)
        types = [t.capitalize() for t in p.types]
        POKE_CACHE[clean_name] = types
        return types
    except:
        return [] 

def calculate_weakness_score(opponent_types, anchor_types):
    """
    Calculates the W factor based on type interaction.
    """
    score = 0
    for o_type in opponent_types:
        if o_type not in TYPE_INTERACTIONS: continue
        
        pass

    for a_type in anchor_types:
        for o_type in opponent_types:
            if is_super_effective(o_type, a_type): score += 10
            if is_resisted(o_type, a_type): score -= 5
            if is_resisted(a_type, o_type): score += 5
            
    return score

def is_super_effective(atk_type, def_type):
    SE_MAP = {
        "Fire": ["Grass", "Ice", "Bug", "Steel"],
        "Water": ["Fire", "Ground", "Rock"],
        "Grass": ["Water", "Ground", "Rock"],
        "Electric": ["Water", "Flying"],
        "Ice": ["Grass", "Ground", "Flying", "Dragon"],
        "Fighting": ["Normal", "Ice", "Rock", "Dark", "Steel"],
        "Poison": ["Grass", "Fairy"],
        "Ground": ["Fire", "Electric", "Poison", "Rock", "Steel"],
        "Flying": ["Grass", "Fighting", "Bug"],
        "Psychic": ["Fighting", "Poison"],
        "Bug": ["Grass", "Psychic", "Dark"],
        "Rock": ["Fire", "Ice", "Flying", "Bug"],
        "Ghost": ["Psychic", "Ghost"],
        "Dragon": ["Dragon"],
        "Dark": ["Psychic", "Ghost"],
        "Steel": ["Ice", "Rock", "Fairy"],
        "Fairy": ["Fighting", "Dragon", "Dark"]
    }
    return def_type in SE_MAP.get(atk_type, [])

def is_resisted(atk_type, def_type):
    if atk_type in TYPE_INTERACTIONS:
        return def_type in TYPE_INTERACTIONS[atk_type]["resist"]
    return False

def parse_hp(hp_str):
    if not hp_str or '/' not in hp_str: return 0.0
    try:
        parts = hp_str.split('/')
        current = float(parts[0].split(' ')[0])
        total = float(parts[1].split(' ')[0])
        return (current / total) * 100
    except: return 0.0

async def fetch_log(session, url):
    if not url.endswith('.log'):
        url = url.split('?')[0] + '.log'
    async with session.get(url) as response:
        if response.status != 200: return None
        return await response.text()

#CORE ANALYTICS ENGINE

def parse_replay_logic(log_text):
    stats = {
        "p1": {"name": "P1", "direct": 0.0, "passive": 0.0, "mons": set(), "dmg_map": Counter(), "presence": Counter(), "pairs": {}},
        "p2": {"name": "P2", "direct": 0.0, "passive": 0.0, "mons": set(), "dmg_map": Counter(), "presence": Counter(), "pairs": {}},
        "turns": 0, "winner": None
    }
    slots = {}
    prev_hp = Counter()
    last_atk_mon = None
    last_atk_side = None

    for line in log_text.split('\n'):
        p = line.split('|')
        if len(p) < 2: continue
        cmd = p[1]

        if cmd == 'player':
            stats[p[2]]["name"] = p[3]
        elif cmd == 'poke':
            mon = p[3].split(',')[0]
            stats[p[2]]["mons"].add(mon)
        elif cmd == 'turn':
            stats["turns"] = int(p[2])
            for side in ["p1", "p2"]:
                active_mons = [slots[s] for s in slots if s.startswith(side)]
                for m in active_mons: stats[side]["presence"][m] += 1
                if len(active_mons) == 2:
                    pair = tuple(sorted(active_mons))
                    if pair not in stats[side]["pairs"]: stats[side]["pairs"][pair] = {'dmg': 0, 'turns': 0}
                    stats[side]["pairs"][pair]['turns'] += 1
        elif cmd in ['switch', 'drag']:
            slot, mon_name = p[2][:3], p[2].split(': ')[1]
            slots[slot] = mon_name
            prev_hp[slot] = parse_hp(p[3])
        elif cmd == 'move':
            last_atk_side, last_atk_mon = p[2][:2], slots.get(p[2][:3])
        elif cmd == '-damage':
            target_slot = p[2][:3]
            attacker_side = "p1" if "p2" in target_slot else "p2"
            new_hp = parse_hp(p[3])
            dmg = max(0, prev_hp[target_slot] - new_hp)
            prev_hp[target_slot] = new_hp
            if any("[from]" in x for x in p):
                stats[attacker_side]["passive"] += dmg
            elif last_atk_side == attacker_side:
                stats[attacker_side]["direct"] += dmg
                if last_atk_mon:
                    stats[attacker_side]["dmg_map"][last_atk_mon] += dmg
                    active_mons = [slots[s] for s in slots if s.startswith(attacker_side)]
                    if len(active_mons) == 2:
                        pair = tuple(sorted(active_mons))
                        if pair in stats[attacker_side]["pairs"]: stats[attacker_side]["pairs"][pair]['dmg'] += dmg
        elif cmd == 'win': stats["winner"] = p[2]
    return stats

#EVENTS & COMMANDS

@bot.event
async def on_ready():
    print(f'✅ {bot.user.name} is online!')
    await bot.change_presence(activity=discord.Game(name="!help | Analyzing Replays"))

@bot.event
async def on_guild_join(guild):
    for channel in guild.text_channels:
        if channel.permissions_for(guild.me).send_messages:
            embed = discord.Embed(title="👋 Hello Trainers!", description="I am **Showdown Scholar**. Type `!help` to see my tactics!", color=0x3498db)
            await channel.send(embed=embed)
            break

@bot.event
async def on_message(message):
    if message.author == bot.user: return
    if bot.user.mentioned_in(message) and not message.mention_everyone:
        await message.channel.send(f"👋 Hello {message.author.mention}! Type `!help` to scan your battles.")
    await bot.process_commands(message)

@bot.command(name="help")
async def help_command(ctx):
    embed = discord.Embed(title="📖 Showdown Scholar Guide", color=0xf1c40f)
    embed.add_field(name="🛠 Commands", value="**`!analyze <URL>`**: Single match stats.\n**`!profile <User> <4-16 URLs>`**: Career analysis.", inline=False)
    embed.add_field(name="📊 Advanced Metrics", value="**Direct Dmg:** Attacks only.\n**Synergy:** Double battle pair efficiency.\n**Threat Index:** Calculates nemesis based on Damage + Type Matchups.", inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def analyze(ctx, url: str):
    async with aiohttp.ClientSession() as session:
        log = await fetch_log(session, url)
        if not log: return await ctx.send("❌ Replay not found.")
    res = parse_replay_logic(log)
    embed = discord.Embed(title="Battle Breakdown", color=0x3498db)
    for p in ["p1", "p2"]:
        d = res[p]
        val = f"⚔️ **Direct:** {round(d['direct'],1)}%\n☁️ **Passive:** {round(d['passive'],1)}%"
        embed.add_field(name=f"Player: {d['name']}", value=val, inline=True)
    await ctx.send(embed=embed)

@bot.command()
async def profile(ctx, username: str, *links):
    if not (4 <= len(links) <= 16): return await ctx.send("⚠️ Provide 4 to 16 links.")
    await ctx.send(f"📊 Analyzing {len(links)} matches for **{username}**...")

    wins, total_turns = 0, 0
    presence_all, total_dmg_all, match_apps = Counter(), Counter(), Counter()
    synergy_all = {}
    nemesis_data = {} 

    async with aiohttp.ClientSession() as session:
        for url in links:
            log = await fetch_log(session, url)
            if not log: continue
            res = parse_replay_logic(log)
            side = next((s for s in ["p1", "p2"] if res[s]["name"].lower() == username.lower()), None)
            if not side: continue

            total_turns += res["turns"]
            is_win = res["winner"].lower() == username.lower()
            
            if is_win: 
                wins += 1
            else:
                opp_side = "p2" if side == "p1" else "p1"
                for mon in res[opp_side]["mons"]:
                    if mon not in nemesis_data: nemesis_data[mon] = {'dmg': 0, 'turns': 0}
                    nemesis_data[mon]['turns'] += res[opp_side]["presence"][mon]
                    nemesis_data[mon]['dmg'] += res[opp_side]["dmg_map"][mon]

            presence_all.update(res[side]["presence"])
            total_dmg_all.update(res[side]["dmg_map"])
            match_apps.update(res[side]["mons"])
            
            for pair, data in res[side]["pairs"].items():
                if pair not in synergy_all: synergy_all[pair] = {'dmg': 0, 'turns': 0, 'wins': 0}
                synergy_all[pair]['dmg'] += data['dmg']
                synergy_all[pair]['turns'] += data['turns']
                if is_win: synergy_all[pair]['wins'] += 1

    # RESULTS
    embed = discord.Embed(title=f"Career Profile: {username}", color=0x9b59b6)
    embed.add_field(name="Performance", value=f"📈 **Win Rate:** {round((wins/len(links))*100,1)}%\n🏆 **Record:** {wins}W - {len(links)-wins}L", inline=True)
    embed.add_field(name="Pace", value=f"⏳ **Avg Match:** {round(total_turns/len(links), 1)} turns", inline=True)

    # 1. Top 6
    top_6_anchors = [m[0] for m in presence_all.most_common(6)] # Get names only
    used_str = "\n".join([f"**{m}**: {presence_all[m]} turns" for m in top_6_anchors])
    embed.add_field(name="Top 6 Anchors", value=used_str or "N/A", inline=False)

    # 2. Lethality
    candidates = [m for m in total_dmg_all.keys() if match_apps[m] >= 1]
    sorted_lethal = sorted(candidates, key=lambda m: total_dmg_all[m]/match_apps[m], reverse=True)[:5]
    lethal_str = "\n".join([f"**{m}**: {round(total_dmg_all[m]/match_apps[m], 1)}% avg" for m in sorted_lethal])
    embed.add_field(name="Most Lethal (Direct Dmg)", value=lethal_str or "N/A", inline=False)

    # 3. Synergy
    if synergy_all:
        valid = [p for p in synergy_all.items() if p[1]['turns'] > 5]
        def syn_score(x): return (x[1]['dmg']/x[1]['turns']) + ((x[1]['wins']/len(links))*20)
        sorted_pairs = sorted(valid, key=syn_score, reverse=True)[:3]
        pair_str = "\n".join([f"**{p[0][0]} + {p[0][1]}** (Score: {round(syn_score(p),1)})" for p in sorted_pairs])
        if pair_str: embed.add_field(name="Top Synergy Pairs", value=pair_str, inline=False)

    threat_list = []
    
    anchor_types_map = {anc: get_pokemon_types(anc) for anc in top_6_anchors}
    
    for mon, stats in nemesis_data.items():
        D = stats['dmg']
        P = stats['turns']
        
        opp_types = get_pokemon_types(mon)
        W = 0
        if opp_types:
            for anc_name, anc_types in anchor_types_map.items():
                if anc_types:
                    W += calculate_weakness_score(opp_types, anc_types)
        
        T = (D * 0.25) + (P * 0.25) + (W * 0.50)
        threat_list.append((mon, T, W))

    top_threats = sorted(threat_list, key=lambda x: x[1], reverse=True)[:3]
    
    nemesis_display = []
    for t in top_threats:
        reason = "High Damage"
        if t[2] > 20: reason = "Type Advantage (Core Breaker)"
        elif t[2] > 10: reason = "Offensive Pressure"
        elif t[2] < 0: reason = "Hard to Kill (Wall)"
        
        nemesis_display.append(f"**{t[0]}** (Index: {round(t[1])})\n└ {reason}")

    embed.add_field(name="Difficult Matchups (Threat Index)", value="\n".join(nemesis_display) or "None detected", inline=False)

    await ctx.send(embed=embed)

bot.run(TOKEN)
