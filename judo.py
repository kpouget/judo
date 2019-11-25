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

names_renamed = {}

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
            name_to_technique[a] = name_to_technique[b]
            name_to_comments[b].add("ou "+a)
            names_renamed[a] = b
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
    for jp, techniques in sorted(name_to_technique.items()):
        name = [jp]
        if not translate(jp).startswith("!"):
            name += ["<" + translate(jp) + ">"]
        if name_to_comments[jp]:
            name += ["("+";".join(name_to_comments[jp])+")"]
        name += ":"

        if jp in names_renamed:
            print(" ".join(name+["Voir", names_renamed[jp]]))
            print()
            continue

        first = True
        for technique in sorted(techniques):
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

def tech_to_glossary(technique):
    section = '/'.join(group_for_technique[technique])
    tech_name = technique.replace("`", "")

    tech_fr = translate_tech(technique).replace('-', ' | ')
    if tech_fr.startswith("!"): tech_fr = tech_fr[1:]

    return tech_name, section, tech_fr

def jp_to_desc(jp):
    tr = "<" + translate(jp) + ">" if not translate(jp).startswith("!") else ""
    comment = "("+";".join(name_to_comments[jp])+")" if name_to_comments[jp] else ""
    return comment, tr

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
            comment, tr = jp_to_desc(jp)

            def do_first():
                table.add_empty_row()
                table.add_row((pylatex.MultiColumn(3, align='l', data=[pylatex.utils.bold(jp.replace("`", "") +" "+ tr),
                                                                       pylatex.NoEscape("~"), comment]), ""))

            if jp in names_renamed:
                comment = "voir "+ names_renamed[jp]+"."
                do_first()
                continue

            first = True
            for technique in sorted(techniques):
                if len(sys.argv) == 2 and sys.argv[1] != group_for_technique[technique][0]: continue
                if first:
                    do_first()
                    first = False

                tech_name, section, tech_fr = tech_to_glossary(technique)

                if len(sys.argv) == 2:
                    section = section.partition("/")[-1]

                table.add_row(("", tech_name, tech_fr, section))

    doc.generate_pdf(dest, clean_tex=False)

def run_dash():
    import dash
    from dash.dependencies import Output, Input, State
    import dash_core_components as dcc
    import dash_html_components as html

    app = dash.Dash(__name__)

    import dash_table
    cols = ["Nom", "Traduction", "Domaine"]


    name_search = dcc.Dropdown(
        id='name-search', multi=True,
        options=[{'label': name, 'value': name}
                 for name in sorted(jp_fr)]
    )

    domain_search = dcc.Dropdown(
        id='domain-dropdown',
        options=[{'label': " > ".join(d), 'value': "/".join(d)} for d in sorted(techniques_by_group)]
    )

    app.layout = html.Div([
        html.P([name_search, domain_search]),
        dash_table.DataTable(
        id='data-table',
        columns=[{"name": i, "id": i} for i in cols],
        data=[],
        )])

    @app.callback(
        Output('data-table', 'data'),
        [Input('name-search', "value"),
         Input('domain-dropdown', "value")])
    def update_table(names, domain):
        if names is None: names = []

        dicts = []
        for name in names[:]:
            try: names.append(names_renamed[name])
            except KeyError: pass

        for names_in_technique in sorted(techniques_transation):
            if names and not [name for name in names if name in names_in_technique]:
                continue

            tech_name, section, tech_fr = tech_to_glossary("-".join(names_in_technique))
            if domain and not section.startswith(domain): continue
            dicts.append(dict(Nom=tech_name,
                              Traduction=tech_fr,
                              Domaine=section))
        return dicts

    if __name__ == "__main__":
        app.run_server(debug=True)
    else:
        return app.application

if __name__ == "__main__":
    parse_file("judo")

    #print_as_text()
    #print_missing()
    #print_as_latext()
    run_dash()
else:
    application = run_dash()
