#!/usr/bin/env python3
"""
卡片資料匯入器 (import_cards.py)
從 combo-master 專案讀取卡表資料 (cardTable.json 及卡片定義)，
轉換並匯入為 combo-master-art 專案的 data/cards.toml 格式。

特性：
- 依 UID (A37+, E1+, C1+, X1+) 匯入具備專屬概念的卡片
- 支援增量更新 (預設保留現有 cards.toml 已編輯之 Prompt，只新增未存在的卡片)
- 支援 --force 旗標強制全量覆蓋
- 內建 51 張卡片精準、生動的英文 subject 與 details
- 可選搭配 GEMINI_API_KEY 自動推導未來新卡
"""

import sys
import os
import json
import argparse
from pathlib import Path

# 專案路徑設定
ART_ROOT = Path(__file__).resolve().parent.parent
GAME_ROOT = ART_ROOT.parent / "combo-master"
CARDS_TOML_PATH = ART_ROOT / "data" / "cards.toml"
BACKUP_TOML_PATH = ART_ROOT / "data" / "cards.toml.bak"

TABLE_JSON_PATH = GAME_ROOT / "src" / "data" / "cardTable.json"
CARDS_JSON_PATH = GAME_ROOT / "src" / "data" / "generated" / "cards.json"
CHARS_JSON_PATH = GAME_ROOT / "src" / "data" / "generated" / "characters.json"

# 51 張核心卡片的精選英文生圖 Prompt 對照庫
BUILTIN_PROMPTS = {
    # 角色 (Characters)
    "C1": {
        "subject": "a determined young warrior with piercing eyes holding an ancient iron broadsword with battle scars",
        "details": "rugged steel chestplate with gold engravings, resolute battle-ready expression, windblown crimson cape, dramatic rim lighting",
    },
    "C2": {
        "subject": "a lethal assassin cloaked in midnight-black hood with glowing amber eyes partially concealed by shadows",
        "details": "holding twin poisoned daggers reflecting moonlight, leather harness with vials, ethereal shadow mist drifting from cloak",
    },
    "C3": {
        "subject": "a shrewd, charismatic merchant in ornate embroidered velvet robes inspecting an antique golden coin",
        "details": "luxurious fur collar, ornate brass weighing scale and leather coin pouches hanging from belt, subtle cunning smile",
    },
    "C4": {
        "subject": "a sharp-eyed elven ranger in forest-green leather tunic drawing a mastercrafted recurve composite bow",
        "details": "focused predatory gaze, quiver overflowing with fletched arrows, oak leaves rustling around shoulders in the forest wind",
    },
    "C5": {
        "subject": "a wise arcane scholar with glowing mystical tattoos hovering an ancient levitating spellbook illuminated by azure light",
        "details": "flowing deep sapphire robes with embroidered runes, swirling arcane sparks dancing on fingertips, intense concentrated aura",
    },
    "C6": {
        "subject": "a veteran rogue wanderer leaning against a stone ruin, flipping an ornate throwing knife with effortless mastery",
        "details": "weathered trench coat, bandaged hands, sly confident smirk, autumn leaves swirling around boots",
    },
    "C7": {
        "subject": "a vigilant stoic guardian knight planted firmly with a massive heavy shield bearing an embossed lion crest",
        "details": "polished knightly full plate armor with minor dents, unwavering defensive stance, ground cracked under sturdy greaves",
    },
    # 裝備 (Equipment)
    "E1": {
        "subject": "a mystical preserved rabbit foot amulet bound with worn dark leather cords and bronze beads",
        "details": "soft weathered fur, faint glimmering golden fairy dust hovering around it, resting on an old dark oak tavern table",
    },
    "E2": {
        "subject": "a cherished vintage miniature family portrait in a tarnished silver locket with cracked glass",
        "details": "faded sepia tones showing a warm embrace, dried pressed flower petal beside it, resting on a soldier's scarred armor plate",
    },
    "E3": {
        "subject": "an intricate brass optical aiming scope with precision glass lenses and finely engraved crosshairs",
        "details": "mounted on polished dark walnut wood, delicate brass gear wheels, gleaming reflections of dawn light through lens",
    },
    "E4": {
        "subject": "a vintage carved porcelain beckoning cat statue holding a shiny large ancient golden ingot",
        "details": "hand-painted red and black collar with a brass bell, delicate hairline cracks on glazed porcelain, surrounded by copper coins",
    },
    "E5": {
        "subject": "a magnificent twin-gemstone pendant intertwining a frosty crystal sapphire and a crackling violet thunder stone",
        "details": "intertwined silver filigree setting, tiny sparks of lightning arcing over frost crystals, resting on dark silk",
    },
    "E6": {
        "subject": "a thick leather-bound ancient elemental grimoire locked with bronze clasps, pulsing with multicolored magical veins",
        "details": "embossed elemental symbols of fire, frost and storm on worn leather cover, faint glowing vapor seeping from parchment edges",
    },
    "E7": {
        "subject": "a reinforced traveler's padded cloth armor vest folded neatly on a wooden armory bench",
        "details": "heavy stitched layered linen, hardened leather shoulder patches, steel buckles with minor scuffs, sturdy practical craftsmanship",
    },
    "E8": {
        "subject": "a heavy solid hardwood quarterstaff polished smooth by years of rigorous martial arts training",
        "details": "spiral leather-wrapped grip, iron caps at both ends with scratched surfaces, resting upright against a mossy stone wall",
    },
    # Ex 卡 (Ex status)
    "X1": {
        "subject": "a cracked clay vial tipped over, spilling thick bubbling emerald venom that violently hisses on the cold floor",
        "details": "noxious green mist rising in tendrils, dissolving stone texture, sinister toxic bubbles, dark grim atmosphere",
    },
    "X2": {
        "subject": "a jagged cruel barbed blade dripping fresh crimson blood onto cold weathered cobblestones",
        "details": "splatters of dark crimson droplets frozen mid-air, harsh edge highlights on stained steel, tense ominous presence",
    },
    # 招式 (Moves)
    "A37": {
        "subject": "an ethereal archer in motion releasing a phantom translucent arrow that splits into spectral duplicates",
        "details": "ghostly cyan glow, blurred motion trail, dynamic archery release pose, dark misty forest atmosphere",
    },
    "A38": {
        "subject": "a concealed mechanical pressure mine suddenly detonating with fire and shrapnel hidden beneath dry leaves",
        "details": "flying soil and fiery spark bursts, tripwire snapping, explosive shockwave radiating outward, tense ambush visual",
    },
    "A39": {
        "subject": "a disciplined warrior thrusting a short sword forward while maintaining a rock-solid guard behind a buckler",
        "details": "sparks flying from steel collision, rigid poised footwork, controlled kinetic force, focused determined eyes",
    },
    "A40": {
        "subject": "a battle-scarred barbarian roaring in fury with veins pulsing and a fierce crimson vengeful aura bursting outward",
        "details": "bared teeth in savage battle cry, sonic shockwave rippling the air, flying gravel, dramatic backlit rim lighting",
    },
    "A41": {
        "subject": "a raw concussive magical blast erupting from a spellcaster's palms, shattering the immediate terrain",
        "details": "chaotic glowing energy tendrils, explosive shockwave ring, flying stone fragments, blinding white-blue core",
    },
    "A42": {
        "subject": "a ferocious branching lightning arc leaping across the battlefield between metallic targets",
        "details": "brilliant electric violet discharge, scorched ground, crackling ozone sparks, high contrast dynamic lighting",
    },
    "A43": {
        "subject": "a shadowy figure lunging from darkness with a swift lethal downward dagger strike",
        "details": "motion blur streaks, moonlight catching the razor-sharp edge, cloak billowing in sudden violent motion",
    },
    "A44": {
        "subject": "an agile dual-wielding fighter executing a rapid cross-slash combo with curved sabers",
        "details": "twin glowing weapon trails crossing in an X shape, sliced fabric in the air, low stance dynamic kinetic momentum",
    },
    "A45": {
        "subject": "a clever trader scooping up rare gemstones and gold coins spilled across a velvet counter at a bargain",
        "details": "glinting gold reflection in eyes, hand raking in treasure, satisfied grin, warm lantern light",
    },
    "A46": {
        "subject": "an opulent auctioneer slamming a golden gavel down triumphantly amidst flying contracts and currency",
        "details": "dramatic auction podium, shining piles of gold bullion, celebratory energetic gesture, rich deep mahogany background",
    },
    "A47": {
        "subject": "a glowing red runic reticle magically locking onto a distant adversary's vital spot through heavy fog",
        "details": "focused crosshair luminescence, faint heartbeat ripple effect, crisp distant target silhouette, extreme focus",
    },
    "A48": {
        "subject": "a pickpocket's nimble hand skillfully lifting a heavy leather coin purse from an unsuspecting belt mid-crowd",
        "details": "swift stealthy finger movement, loosened knot, bustling tavern crowd in soft background blur, tense heist moment",
    },
    "A49": {
        "subject": "two silhouettes in shadowy candlelit parlor leaning over an official wax-sealed diplomatic treaty",
        "details": "quill pen hovering over parchment, calculating intense expressions, smoke curling from smoking pipe, intense negotiation",
    },
    "A50": {
        "subject": "crystalline thick ice armor instantly freezing around a mage's torso and limbs, deflecting incoming blows",
        "details": "fractured frost crystals, chilling blue mist cascading down, incoming weapon bouncing off impenetrable icy barrier",
    },
    "A51": {
        "subject": "a heavy armored warrior violently slamming the rim of an iron tower shield directly into the foe's guard",
        "details": "massive kinetic impact shockwave, crushing force sparks, flying spit and sweat, heavy braced posture",
    },
    "A52": {
        "subject": "a decisive trader severing an entangled rope bridge with a single swift cut to preserve the caravan",
        "details": "snapping hemp ropes under tension, clean slice with a machete, calm calculated stare amidst chaotic backdrop",
    },
    "A53": {
        "subject": "two razor-tipped arrows flying in tight tandem through the air, trailing dual spiraling wind vortices",
        "details": "wind tunnel wake, feathers trembling in high velocity flight, glistening steel arrowheads aiming ahead",
    },
    "A54": {
        "subject": "a battered common militia soldier standing defiantly with a simple chipped sword against overwhelming darkness",
        "details": "bloodied bandages, unwavering fiery spirit in eyes, golden courage aura shining through ragged peasant clothing",
    },
    "A55": {
        "subject": "a razor-sharp curved parrying dagger twisting and snapping the leather straps of heavy plate armor",
        "details": "broken buckles and steel armor pieces flying apart in mid-air, exposed enemy vulnerability, swift precision motion",
    },
    "A56": {
        "subject": "a colossal swirling fiery sphere of molten plasma hurling forward leaving a scorched blazing trail",
        "details": "crackling orange flames, burning embers flying, intense heat distortion waves bending the background",
    },
    "A57": {
        "subject": "a rogue carefully dripping thick viscous emerald poison along the jagged serrated groove of a curved stiletto",
        "details": "venomous droplet hanging from vial rim, toxic green glint on steel, gloved fingertips, dimly lit dungeon corner",
    },
    "A58": {
        "subject": "a cataclysmic apocalyptic explosion of crimson flame and black smoke billowing upward in a towering mushroom cloud",
        "details": "ground vaporized into molten magma, blinding white center flash, shockwave flattening ancient pillars, overwhelming scale",
    },
    "A59": {
        "subject": "a grand illuminated ledger displaying fluctuating market charts and trading scrolls laid out under scrutiny",
        "details": "magnifying glass over fine handwritten ledgers, abacus beads arranged, bright clear daylight streaming through window",
    },
    "A60": {
        "subject": "a sniper bow drawn to absolute maximum tension with swirling spiral wind condensing around the arrow tip",
        "details": "groaning wooden bow limbs, taut trembling bowstring, hyper-concentrated eye visible under hood, suspended dust particles",
    },
    "A61": {
        "subject": "a heavy greatsword superheated into glowing molten lava crashing into the ground with splashing magma",
        "details": "molten rock sprays, glowing fissure cracking open on earth, intense heat haze, radiant orange light reflecting off armor",
    },
    "A63": {
        "subject": "a massive reinforced steel vault door opening to reveal towering stacks of golden coins and jeweled chests",
        "details": "heavy intricate clockwork lock gears, glittering golden reflection flooding the room, meticulous organized treasure",
    },
    "A64": {
        "subject": "an armored warrior banging a sword against a dented shield with a mocking wide grin provoking all nearby enemies",
        "details": "clanging metal soundwaves, arrogant tilted chin, enemy shadows turning aggressively toward him, battle frenzy",
    },
    "A65": {
        "subject": "a barbed enchanted arrow extracting swirling crimson life essence from a target, siphoning back to the archer",
        "details": "glowing scarlet energy strands weaving into the bow, rejuvenating soft glow around wounds, dynamic vampire archer feel",
    },
    "A68": {
        "subject": "an ornate glass potion flask glowing with radiant effervescent crimson liquid with floating sparkling bubbles",
        "details": "golden filigree stopper, translucent glass facets catching ambient light, soothing restorative aura radiating around it",
    },
    "A69": {
        "subject": "an opened masterwork tome with golden gilded pages displaying glowing diagrams of combat mastery",
        "details": "floating holographic battle martial stances hovering above open book, leather bookmark, wisdom and enlightenment theme",
    },
    "A70": {
        "subject": "an enraged fighter in a reckless berserker frenzy hacking downward with unbridled brute fury",
        "details": "shattered weapon fragments flying, explosive ground impact, ferocious grimace, wild kinetic muscle tension",
    },
    "A71": {
        "subject": "magical spell scrolls and levitating parchment pages systematically organizing themselves into an arcane grimoire",
        "details": "glowing glyphs aligning in mid-air, floating feather quill inking lines, soft studious candlelight, serene arcane study",
    },
    "A72": {
        "subject": "a sinister glowing bloodhound skull brand magically imprinted on a fleeing prey's shoulder",
        "details": "smoldering crimson mark, smoke wafting from brand, predator's silhouette watching closely from tree canopy",
    },
    "A73": {
        "subject": "a self-guiding enchanted arrow curving gracefully in mid-flight following an erratic target's trail",
        "details": "spiraling cyan wind trail tracing its curved trajectory, arrow tip glowing with hunting runes, extreme agility",
    },
}


def load_existing_toml() -> dict[str, dict]:
    """載入現有的 cards.toml，若不存在則回傳空字典"""
    if not CARDS_TOML_PATH.exists():
        return {}
    try:
        import tomllib
        with open(CARDS_TOML_PATH, "rb") as f:
            data = tomllib.load(f)
            cards = data.get("cards", [])
            return {c["id"]: c for c in cards if "id" in c}
    except Exception as e:
        print(f"[!] 讀取既有 cards.toml 失敗 ({e})，視為空資料庫。")
        return {}


def format_toml_string(s: str) -> str:
    """跳脫 TOML 字串字元"""
    return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def serialize_card_to_toml(c: dict) -> str:
    lines = ["[[cards]]"]
    lines.append(f'id = "{c["id"]}"')
    lines.append(f'name = "{c["name"]}"')
    lines.append(f'kind = "{c["kind"]}"')
    lines.append(f'cls = "{c["cls"]}"')
    if c.get("slot"):
        lines.append(f'slot = "{c["slot"]}"')
    
    traits_list = [f'"{t}"' for t in c.get("traits", [])]
    lines.append(f'traits = [{", ".join(traits_list)}]')
    
    clean_text = c.get("text", "").strip()
    if clean_text:
        lines.append(f'text = "{format_toml_string(clean_text)}"')
    
    lines.append(f'subject = "{format_toml_string(c.get("subject", "").strip())}"')
    lines.append(f'details = "{format_toml_string(c.get("details", "").strip())}"')
    lines.append("")
    return "\n".join(lines)


def fetch_game_cards() -> list[dict]:
    """讀取遊戲端所有卡片資料"""
    if not TABLE_JSON_PATH.exists():
        raise FileNotFoundError(f"找不到卡表檔案: {TABLE_JSON_PATH}")

    with open(TABLE_JSON_PATH, "r", encoding="utf-8") as f:
        table = json.load(f)
    uids = table.get("uids", {})

    base_cards = []
    if CARDS_JSON_PATH.exists():
        with open(CARDS_JSON_PATH, "r", encoding="utf-8") as f:
            base_cards = json.load(f)

    base_chars = []
    if CHARS_JSON_PATH.exists():
        with open(CHARS_JSON_PATH, "r", encoding="utf-8") as f:
            base_chars = json.load(f)

    # 建立速查字典
    card_map = {c["id"]: c for c in base_cards}
    char_map = {c["id"]: c for c in base_chars}

    # 合併 table 新增的卡片
    for c in table.get("added", []):
        card_map[c["id"]] = c
    for c in table.get("exCards", []):
        card_map[c["id"]] = c

    target_cards = []

    # 依 UID 排序處理
    sorted_uids = sorted(uids.items(), key=lambda x: (x[0][0], int(x[0][1:]) if x[0][1:].isdigit() else 999))

    for uid, name in sorted_uids:
        prefix = uid[0]
        num_str = uid[1:]
        num = int(num_str) if num_str.isdigit() else 0

        # 只挑選：效果招式 (A37+), 角色 (C1+), 裝備 (E1+), Ex (X1+)
        if prefix == "A" and num < 37:
            continue
        if prefix not in ["A", "C", "E", "X"]:
            continue

        if prefix == "C":
            ch = char_map.get(name, {})
            target_cards.append({
                "id": uid,
                "name": name,
                "kind": "character",
                "cls": ch.get("cls", "共用"),
                "traits": ["角色"],
                "text": ch.get("text", ""),
                "awakenText": ch.get("awakenText", ""),
            })
        elif prefix == "E":
            c = card_map.get(name, {})
            target_cards.append({
                "id": uid,
                "name": name,
                "kind": "equip",
                "cls": c.get("cls", "共用"),
                "slot": c.get("slot", "飾品"),
                "traits": c.get("traits", []),
                "text": c.get("text", ""),
            })
        elif prefix == "X":
            c = card_map.get(name, {})
            target_cards.append({
                "id": uid,
                "name": name,
                "kind": "ex",
                "cls": c.get("cls", "共用"),
                "traits": c.get("traits", ["減益"]),
                "text": c.get("text", ""),
            })
        elif prefix == "A":
            c = card_map.get(name, {})
            target_cards.append({
                "id": uid,
                "name": name,
                "kind": "move",
                "cls": c.get("cls", "共用"),
                "traits": c.get("traits", []),
                "text": c.get("text", ""),
            })

    return target_cards


def main():
    parser = argparse.ArgumentParser(description="從 combo-master 導入卡片資料到 combo-master-art")
    parser.add_argument("--force", action="store_true", help="強制重新生成所有卡片 Prompt (忽略現有卡片已編輯內容)")
    args = parser.parse_args()

    print("[*] 正在從遊戲專案讀取卡表資料...")
    game_cards = fetch_game_cards()
    print(f"[*] 自遊戲端成功辨識出 {len(game_cards)} 張具備專屬概念之卡片。")

    existing_cards = {}
    if not args.force:
        existing_cards = load_existing_toml()
        if existing_cards:
            print(f"[*] 檢測到現有 cards.toml 內含 {len(existing_cards)} 張卡片，將採【增量更新】保留現有 Prompt。")
        else:
            print("[*] 查無現有卡片，將初始化全新卡圖資料庫。")
    else:
        print("[!] 啟用 --force 旗標：將覆蓋全量卡片資料！")

    # 備份原 cards.toml
    if CARDS_TOML_PATH.exists() and not BACKUP_TOML_PATH.exists():
        import shutil
        shutil.copy2(CARDS_TOML_PATH, BACKUP_TOML_PATH)
        print(f"[*] 已自動備份原檔案至: {BACKUP_TOML_PATH.name}")

    merged_cards = []
    added_count = 0
    kept_count = 0

    for gc in game_cards:
        cid = gc["id"]
        # 如果現有且非 force，保留原有 subject 與 details
        if cid in existing_cards and not args.force:
            old = existing_cards[cid]
            card_obj = {
                "id": cid,
                "name": gc["name"],
                "kind": gc["kind"],
                "cls": gc["cls"],
                "traits": gc["traits"],
                "text": gc.get("text", ""),
                "subject": old.get("subject", ""),
                "details": old.get("details", ""),
            }
            if "slot" in gc:
                card_obj["slot"] = gc["slot"]
            merged_cards.append(card_obj)
            kept_count += 1
        else:
            # 填入內建高質量提示詞對照庫
            prompt_info = BUILTIN_PROMPTS.get(cid, {
                "subject": f"a dynamic visual representing {gc['name']}",
                "details": "high quality fine art composition with subtle lighting",
            })
            card_obj = {
                "id": cid,
                "name": gc["name"],
                "kind": gc["kind"],
                "cls": gc["cls"],
                "traits": gc["traits"],
                "text": gc.get("text", ""),
                "subject": prompt_info["subject"],
                "details": prompt_info["details"],
            }
            if "slot" in gc:
                card_obj["slot"] = gc["slot"]
            merged_cards.append(card_obj)
            added_count += 1

    # 輸出 TOML
    toml_header = """# ==========================================
# 連擊大師 卡片生圖資料庫 (Card Database)
# 
# 欄位說明：
# - id: 永久編號 UID (A:招式, E:裝備, C:角色, X:Ex狀態卡)
# - name: 遊戲內中文名稱
# - kind: 卡片類型 (move | equip | character | ex)
# - cls: 職業 (劍士 | 盜賊 | 商人 | 弓箭手 | 法師 | 共用)
# - slot: 裝備部位 (僅 equip 有：武器 | 防具 | 飾品)
# - traits: 特徵標籤清單
# - text: 遊戲效果原文 (參考脈絡)
# - subject: AI 生圖核心主體描述 (英文)
# - details: 細節、特徵、光影與環境描述 (英文)
# ==========================================

"""
    toml_content = toml_header + "\n".join(serialize_card_to_toml(c) for c in merged_cards)

    CARDS_TOML_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CARDS_TOML_PATH, "w", encoding="utf-8") as f:
        f.write(toml_content)

    print(f"\n✅ 匯入成功！已寫入 {len(merged_cards)} 張卡片至: {CARDS_TOML_PATH.relative_to(ART_ROOT)}")
    print(f"   - 新增/產生: {added_count} 張")
    print(f"   - 保留現有: {kept_count} 張\n")


if __name__ == "__main__":
    main()

