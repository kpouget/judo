#! /usr/bin/python3

from collections import defaultdict
import sys

current_section = []

jp_fr = defaultdict(set)

techniques_transation = {}

name_to_technique = defaultdict(set)

techniques_by_group = defaultdict(set)
group_for_technique = {}

name_to_comments = defaultdict(set)

def translate(word):
    if not jp_fr[word]: return "?"

    return "|".join(list(jp_fr[word]))

def translate_tech(name):
    key = tuple(name.split("-"))

    return techniques_transation[key]

def parse_file(fname):
    for no, line in enumerate(open(fname).readlines()):
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
        techniques_transation[tuple(name.split("-"))] = []

        groups = []
        for group in current_section:
            groups.append(group)
            techniques_by_group[tuple(groups)].add(name)

        group_for_technique[name] = current_section[:]

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

    global longest_tech_name, longest_fr_tech_name
    
    longest_tech_name = max(map(len, map("-".join, techniques_transation.keys())))

    for tech in techniques_transation:
        name_jp = "-".join(tech)
        name_fr = "-".join([translate(w) for w in tech])

        techniques_transation[tech] = name_fr

    longest_fr_tech_name = max(map(len, techniques_transation.values()))

def print_as_text():
    for jp, techniques in name_to_technique.items():
        name = [jp]
        if not translate(jp).startswith("!"):
            name += ["<" + translate(jp) + ">"]
        if name_to_comments[jp]:
            name += ["("+";".join(name_to_comments[jp])+")"]
        name += ":"

        first = True
        for technique in techniques:
            if len(sys.argv) == 2 and sys.argv[1] != group_for_technique[technique][0]: continue
            if first:
                print(" ".join(name))
                first = False

            print(f"\t - {technique:<{longest_tech_name}s}",
                  f"{translate_tech(technique).replace('-', '|'):<{longest_fr_tech_name}s}",
                  f"# {'/'.join(group_for_technique[technique])}")
        if not first:
            print()

    print(f"{len(techniques_transation)} noms de techniques")
    print(f"{len(jp_fr)} mots japonais")

def print_missing():
    missing = [jp for jp, fr in jp_fr.items() if not fr or "?" in fr]
    if not missing: return
    
    print(f"{len(missing)} traductions manquantes:")
    for jp in missing:
        print(f"\t - {jp} ({','.join(name_to_technique[jp])})")
          
def print_as_latext():
    import pylatex
    dest = sys.argv[1] if len(sys.argv) == 2 else 'judo'
    geometry_options = {"tmargin": "0.5cm", "lmargin": "1cm", "bmargin": "1.5cm"}
    doc = pylatex.Document(geometry_options=geometry_options)
    doc.preamble.append(pylatex.Command('title', ))
    doc.preamble.append(pylatex.Command('date', pylatex.NoEscape(r'')))

    with doc.create(pylatex.Center()) as centered:
        centered.append(pylatex.utils.bold(f'Glossaire de {dest.capitalize()}'))
    
    with doc.create(pylatex.LongTable('rlll')) as table:
        for jp, techniques in sorted(name_to_technique.items()):
            name = [jp]
            
            tr = "<" + translate(jp) + ">" if not translate(jp).startswith("!") else ""
            comment = "("+";".join(name_to_comments[jp])+")" if name_to_comments[jp] else ""

            def do_first():
                table.add_empty_row()
                table.add_row((pylatex.MultiColumn(3, align='l', data=[pylatex.utils.bold(jp.replace("`", "") +" "+ tr), pylatex.NoEscape("~"), comment]), ""))
                
            first = True
            for technique in techniques:
                if len(sys.argv) == 2 and sys.argv[1] != group_for_technique[technique][0]: continue
                if first:
                    do_first()
                    first = False

                section = '/'.join(group_for_technique[technique])
                if len(sys.argv) == 2:
                    section = section.partition("/")[-1]

                tech_fr = translate_tech(technique).replace('-', ' | ')
                if tech_fr.startswith("!"): tech_fr = tech_fr[1:]

                table.add_row(("", technique.replace("`", ""), tech_fr, section))
        
    doc.generate_pdf(dest, clean_tex=False)
    
if __name__ == "__main__":
    parse_file("judo")

    print_as_text()
    print_missing()
    print_as_latext()
    
