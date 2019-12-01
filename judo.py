#! /usr/bin/python3

from collections import defaultdict
import sys, os

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

def print_as_latext(dest=None, section_filter=None):
    import pylatex
    if dest is None:
        dest = sys.argv[1] if len(sys.argv) == 2 else 'judo'
    if dest.endswith(".pdf"):
        dest = dest[:-4]

    if section_filter is None:
        section_filter = sys.argv[1].replace('.', "/") if len(sys.argv) == 2 else 'judo'

    geometry_options = {"tmargin": "0.5cm", "lmargin": "1cm", "bmargin": "1.5cm"}
    doc = pylatex.Document(geometry_options=geometry_options, document_options=['a4paper'])
    doc.preamble.append(pylatex.Command('title', ))
    doc.preamble.append(pylatex.Command('date', pylatex.NoEscape(r'')))

    with doc.create(pylatex.Center()) as centered:
        centered.append(pylatex.utils.bold(f'Glossaire de {section_filter if section_filter else "judo/jujutsu"}'))

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
                if section_filter and not "/".join(group_for_technique[technique]).startswith(section_filter): continue

                if first:
                    do_first()
                    first = False

                tech_name, section, tech_fr = tech_to_glossary(technique)

                if section_filter and section.startswith(section_filter):
                    section = section[len(section_filter)+1:]

                table.add_row(("", tech_name, tech_fr, section))

    r1 = doc.generate_pdf(dest, clean_tex=True)
    r2 = doc.generate_pdf(dest, clean_tex=False, clean=False)
    r3 = doc.generate_pdf(dest, clean_tex=False, clean=False)

def run_dash():
    import dash
    from dash.dependencies import Output, Input, State
    import dash_core_components as dcc
    import dash_html_components as html

    app = dash.Dash(__name__, requests_pathname_prefix='/judo/')

    import dash_table
    cols = ["Nom", "Traduction", "Domaine"]

    name_search = dcc.Dropdown(
        placeholder="Mot japonais ...",
        id='name-search', multi=True,
        options=[{'label': f"{jp} {jp_to_desc(jp)[1]}", 'value': jp}
                 for jp, fr in sorted(jp_fr.items())]
    )

    depth_2_domains = {d[:2] for d in techniques_by_group}
    domain_search = dcc.Dropdown(
        placeholder="Discipline ...",
        id='domain-dropdown',
        options=[{'label': "judo & jujutsu ", 'value': 'all'}] +
                [{'label': " > ".join(d), 'value': "/".join(d)}
                 for d in sorted(depth_2_domains)],
        value='all'
    )

    download_links = ["Télécharger: "]
    for what in ("tout", "judo-jujutsu"), "judo", "jujutsu", "current":
        if isinstance(what, tuple):
            label = what[0]
            link = what[1]
        else: label = link = what
        download_links += [" ", html.A(label, href=f"download/glossaire-{link}.pdf",
                                       id=f"dl_{link}", target="_blank")]

    app.layout = html.Div([
        html.P([name_search, domain_search]),
        html.P(download_links),
        dash_table.DataTable(
            sort_action="native",
            style_cell_conditional=[
                {'if': {'column_id': 'Domaine'}, 'textAlign': 'left'},
                {'if': {'column_id': 'Traduction'}, 'textAlign': 'center'}
            ],
            style_header={
                 'backgroundColor': 'white',
                 'fontWeight': 'bold'
             },
            style_as_list_view=True,
            id='data-table',
            columns=[{"name": i, "id": i} for i in cols],
            data=[],
        )])

    @app.server.route('/download/glossaire-<what>.pdf')
    def download_pipeline(what):
        if ".." in what: return f"Invalid name: {what}"

        module_dir = os.path.dirname(os.path.realpath(__file__))
        dest = f"{module_dir}/pdf/glossaire-{what}.pdf"

        if not os.path.exists(dest):
            if what == "judo-jujutsu": section_filter = ''
            else: section_filter = what.replace(".", "/")

            print_as_latext(dest, section_filter)

            if not os.path.exists(dest): return f"{dest} generation failed ..."

        import flask
        return flask.send_file(dest,
                               mimetype='application/pdf',
                               attachment_filename=f'glossaire-{what}.pdf',
                               as_attachment=True )

    @app.callback(
        [Output('data-table', 'data'),
         Output('dl_current', 'children'), Output('dl_current', 'href')],
        [Input('name-search', "value"),
         Input('domain-dropdown', "value")])
    def update_table(names, domain):
        if names is None: names = []

        dicts = []
        for name in names[:]:
            try: names.append(names_renamed[name])
            except KeyError: pass

        if domain == 'all': domain = ""
        for names_in_technique in sorted(techniques_transation):
            if names and not [name for name in names if name in names_in_technique]:
                continue

            tech_name, section, tech_fr = tech_to_glossary("-".join(names_in_technique))

            if domain and not section.startswith(domain): continue
            dicts.append(dict(Nom=tech_name,
                              Traduction=tech_fr,
                              Domaine=section))

        dl = ['', ''] if domain in [None, "judo", "jujutsu", 'all'] \
            else [domain, f"download/glossaire-{domain.replace('/', '.')}.pdf"]

        return [dicts] + dl

    if __name__ == "__main__":
        app.run_server(debug=True)
    else:
        return app.server

if __name__ == "__main__":
    parse_file("judo")

    #print_as_text()
    #print_missing()
    #print_as_latext()
    run_dash()
else:
    module_dir = os.path.dirname(os.path.realpath(__file__))
    parse_file(module_dir + "/judo")
    application = run_dash()
