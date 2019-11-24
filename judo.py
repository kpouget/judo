#! /usr/bin/python3

from collections import defaultdict

current_section = []

jp_fr = defaultdict(set)

techniques_transation = {}

name_to_technique = defaultdict(set)

techniques_by_group = defaultdict(set)
group_for_technique = {}

name_to_comments = defaultdict(set)

for no, line in enumerate(open("judo").readlines()):
    line = line[:-1]
    if not line: continue

    if line.startswith("@"):
        name, _, comment = line[1:].partition(": ")
        name_to_comments[name].add(comment)
        continue
    
    if line.startswith("#"):
        # eg: # jujustu
        _depth, _, name = line.partition(" ")
        depth = _depth.count("#") - 1

        while len(current_section) > depth:
            current_section.pop()
        
        current_section.append(name)

        #print(" > ".join(current_section))
        continue

    if " = " in line:
        # eg: katame = gatame
        a, b = line.split(" = ")
        if jp_fr[a] or jp_fr[b]:
            print(f"ERROR: '{a}' ou '{b}' utilisé avant ligne {no}")
        jp_fr[a] = jp_fr[b]
        continue
    
    # eg:
    # ashi-gatame: jambe-control
    # ude-gatame: bras-^
    # ude-garami: ^-plié
    # ashi-garami: ^^

    name, _, trans = line.partition(": ")
    print(no, "--->", name)
    techniques_transation[tuple(name.split("-"))] = []

    groups = []
    for group in current_section:
        groups.append(group)
        techniques_by_group[tuple(groups)].add(name)

    group_for_technique[name] = current_section
    
    for jp in name.split("-"):
        name_to_technique[jp].add(name)
    
    if trans == "^^":
        continue

    for jp, fr in zip(name.split("-"), trans.split("-")):
        if not fr:
            continue
        else:
            jp_fr[jp].add(fr)
            
for jp, fr in jp_fr.items():
    if not "^" in fr: continue
    if len(fr) == 1:
        print(f"ERREUR: pas de définition pour '{jp}'")
    else:
        fr.remove("^")

def translate(word):
    if not jp_fr[word]: return "?"
    
    return "|".join(list(jp_fr[word]))

def translate_tech(name):
    key = tuple(name.split("-"))

    return techniques_transation[key]

longest_tech_name = max(map(len, map("-".join, techniques_transation.keys())))

for tech in techniques_transation:
    name_jp = "-".join(tech)
    name_fr = "-".join([translate(w) for w in tech])

    print(f"{name_jp: <{longest_tech_name}s} -->  ", name_fr)
    techniques_transation[tech] = name_fr
    
longest_fr_tech_name = max(map(len, techniques_transation.values()))

for jp, techniques in name_to_technique.items():
    name = [jp]
    if not translate(jp).startswith("!"):
        name += ["<" + translate(jp) + ">"]
    if name_to_comments[jp]:
        name += ["("+";".join(name_to_comments[jp])+")"]
    name += ":"
    print(" ".join(name))
    for technique in techniques:
        print(f"\t - {technique:<{longest_tech_name}s}",
              f"{translate_tech(technique).replace('-', '|'):<{longest_fr_tech_name}s}",
              f"# {' > '.join(group_for_technique[technique])}")
    print()

print(f"{len(techniques_transation)} noms de techniques")
print(f"{len(jp_fr)} mots japonais")

missing = [jp for jp, fr in jp_fr.items() if not fr or "?" in fr]
if missing:
    print(f"{len(missing)} traductions manquantes:")
    for jp in missing:
        print(f"\t - {jp} ({','.join(name_to_technique[jp])})")
          

