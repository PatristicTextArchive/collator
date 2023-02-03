#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Usage: collator.py [options] <file> <file>...

A script for simplifying collation of several text witnesses encoded according
to the PTA Schema. 
Outputs CollateX-Input-JSON, CollateX-Collation-JSON, collation as html, xml (TEI), csv.

Original script by Michael Stenskjær Christensen (https://github.com/stenskjaer/collator). This was modified to a large extent.

Arguments:
  <file> <file>...        Two or more TEI encoded transcription files that are to be collated.

Options:
  -t, --title=<title>     Set title
  -e, --editor=<editor>   Set editor name
  -q, --editorID=<ID>     Set editor ID
  -a, --algorithm <algo>  Set algorithm: dekker (standard), needleman-wunsch
  -c, --comparator <comp> Set tokenComparator: 'equality','levenshtein','levenshteinNormalized','jaccard' (standard)
  -d, --distance <value>  Set distance value between 0 and 1
  -o, --output <file>     Location of the output files (input-json, collation-json and collation-html, collation-xml, collation-csv). [default: ./output].
  -i, --interpunction     Do collation without interpunction [default: with interpunction].
  -V, --verbosity <level> Set verbosity. Possibilities: silent, info, debug [default: info].
  -v, --version           Show version and exit.
  -h, --help              Show this help message and exit.
"""

from docopt import docopt
import json
import csv
import logging
import re
import os
import subprocess
import unicodedata
from datetime import datetime
from xml.dom.minidom import Document

__version__ = '0.2.0'

BASE_DIR = os.path.dirname(__file__)

def processToken(inputText):
    return {"t": inputText.strip(), "n": unicodedata.normalize("NFD", inputText).translate({ord(c): None for c in "̓̔́̀͂̈ͅ"}).lower().strip()}

def diacritics(inputText):
    return [processToken(token) for token in re.findall(r'\S+\s*', inputText)]

def interpunction(inputText):
    return re.sub(r'[.,:··;›»⁘—\+\-\n]+', r'', inputText)

def convert_xml_to_plaintext(xml_files):
    """Convert the list of encoded files to plain text, using the auxilary XSLT script. This requires
    saxon installed.

    Keyword Arguments: xml_files -- list of files to be converted
    """
    output_dict = {}
    if args['--algorithm']:
        output_dict['algorithm'] = args['--algorithm']
    else:
        output_dict['algorithm'] = 'dekker'
    tc = {}
    if args['--comparator']:
        tc['type'] = args['--comparator']
    else:
        tc['type'] = 'jaccard'
    if args['--distance']:
        tc['distance'] = args['--distance']
    else:
        if args['--comparator'] == 'equality':
            pass
        else:
            tc['distance'] = 0.7
    output_dict['tokenComparator'] = tc
    output_dict['witnesses'] = []
    for file in xml_files:
        stylesheet = os.path.join(BASE_DIR, 'conversion-script.xslt')
        saxon = os.path.join(BASE_DIR, 'vendor/saxon9he.jar')
        logging.debug(f'Start conversion of {file}')
        buffer = subprocess.run(['java', '-jar', saxon, f'-s:{file}', f'-xsl:{stylesheet}'],
                                stdout=subprocess.PIPE).stdout
        siglum = re.search(r'\{witness:([^}]+)\}', str(buffer)).group(1)
        text = re.search(r'\{content:([\W\w\s]*)}', str(buffer.decode('utf-8'))).group(1)
        text = unicodedata.normalize("NFC", text)
        if args['--interpunction']:
            text = interpunction(text)
        text = diacritics(text)
        # convert text to tokens
        witness_dictionary = dict(id=siglum,tokens=text)
        output_dict['witnesses'].append(witness_dictionary)
    return output_dict

def write_collation_file(input_dict):
    """Write the `input_dict` to a local file for collatex processing.

    Keyword Arguments:
    input_dict -- Dump the witness dictionary to a JSON file.
    """
    if args['--output']:
        output_file = args['--output']
    else:
        output_file = 'output'
    with open(output_file+".json", "w", encoding='utf8') as fp:
        fp.write(json.dumps(input_dict, indent=4, ensure_ascii=False))
        logging.info(f'Write JSON-Input file to {fp.name}')
    return fp


def run_collatex(input_file):
    """Run the collatex script on the temporary file.

    Keyword arguments:
    input_file -- File object of the json file that should be collated by collatex.
    options for -a: needleman-wunsch, dekker, medite (slow), gst (slow)
    Return:
    Collatex output as dictionary.
    """
    logging.info(f'Running collatex. This may take some time...')
    collatex_binary = os.path.join(BASE_DIR, 'vendor/collatex-tools-1.8-SNAPSHOT-TSAligner.jar')
    cmd = subprocess.Popen(['java', '-jar', collatex_binary, '-t', 
                            input_file.name], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = cmd.communicate()
    if err:
        pass#raise Exception(err)
    return json.loads(out)

def collation_json(table):
    """Write the collation file to json."""
    if args['--output']:
        output_file = args['--output']
    else:
        output_file = 'output'
    with open(output_file+"-collation.json", "w", encoding='utf8') as fp:
        fp.write(json.dumps(table, ensure_ascii=False))
        logging.info(f'Write JSON-Collation-file file to {fp.name}')
    return fp   

def get_collation_metadata(data):
    """Process the collation table and extract metadata.

    Keyword Arguments:
    table -- Dictionary containing the table contents.
    """
    logging.info(f'Extract metadata as dict from collation table.') 
    metadata = {}
    metadata['manuscripts'] = ", ".join(data['witnesses']) # list of witnesses
    metadata['algorithm'] = data['used_options']['algo']
    metadata['comparator'] = data['used_options']['tokenComparator']['type']
    try:
        metadata['threshold'] = data['used_options']['tokenComparator']['c3']
    except(KeyError):
        metadata['threshold'] = ""
    metadata['time_start'] = data['align_start']
    metadata['time_end'] = data['align_end']
    return metadata

def collation_table_csv_file(data, output_file):
    """Process the collation table and return a CSV representation of it.

    Keyword Arguments:
    table -- Dictionary containing the table contents.
    """
    logging.info(f'Process collation table to csv.')
    manuscripts = data['witnesses'] # list of witnesses
    collation = data['table'] # collation
    towrite = []
    for line in collation:
        row = []
        for i in range(len(line)):
            w = "".join([d['t'] for d in line[i] if 't' in d])
            row.append(w)
        towrite.append(row)

    with open(output_file, 'w', encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(manuscripts)
        writer.writerows(towrite)
        logging.info(f'{f.name} created.')
    return f


def collation_table_html(table):
    """Process the collation table and return a HTML representation of it.

    Keyword Arguments:
    table -- Dictionary containing the table contents.
    """
    logging.info(f'Process collation table to html.')
    numbered_witnesses = {k: wit for k, wit in enumerate(table['witnesses'])}

    table_array = [[] for wit in numbered_witnesses]  # Create rows for all the witnesses.
    col_widths = []

    for cell in table['table']:
# rewrite empty token set
        newline = []
        for content in cell:
            if not content:
                content = {'t': '', 'n': ''}
                newline.append(content)
            else:
                newline.append(content[0])
    #
        cleaned_content = {wit: content for wit, content in enumerate(newline)}

        # Sort into sets of matching witnesses.
        #
        # Basic idea: For each witness, find any other witnesses that have
        # identical content and register those into the list `wit_eqs`.
        #
        # `sorted_witnesses` is final results list; `compared` registers witnesses that have already
        # been compared
        sorted_witnesses = []
        compared = []
        for wit in cleaned_content:
            # create a temporary copy of the dictionary so we can change it during processing and
            # pop the witness under investigation. We want it popped to avoid match in every case.
            tmp = cleaned_content.copy()
            popped = tmp.pop(wit)
            # If the witness has not already been matched, see if there are matches in other
            # witnesses.
            if wit not in compared:
                # Add the witness to list of equals, as unique witnesses go to the result list too.
                wit_eqs = list()
                wit_eqs.append(popped['n'])
                wit_eqs.append(popped['t'])
                wit_eqs.append(wit)
                # If there are other witnesses with the same content, check which
                if popped in tmp.values():
                    # Iterate all other witnesses
                    for sub_wit, value in tmp.items():
                        # Register which match and add those to the `wit_eqs` and `compared` lists.
                        if popped['n'] == value['n']:
                            if popped['t'] == value['t']:
                                wit_eqs.append(sub_wit)
                                compared.append(sub_wit)
                # Add the wit_eqs list to the result list
                sorted_witnesses.append(wit_eqs)

        # Assign colour classes
        colours = ['Melon', 'Pastel_Yellow', 'Very_Pale_Orange', 'Dirty_White', 'Magic_Mint', 'Light_Salmon_Pink', 'Crayola',  'Vodka', 'Pale_Blue', 'Granny_Smith_Apple', 'Calamansi', 'Persian_Pink', 'Ceil', 'Orchid', 'Tea_Green', 'Pearl_Aqua', 'Aero', 'Pastel_Purple', 'Light_Silver', 'Pastel_Blue', 'Black_Shadows', 'Shadow_Blue', 'Laurel_Green']
        colour_classes = {}
        for i, item in enumerate(sorted_witnesses):
            # If we have differences, mark with colours
            if len(sorted_witnesses) > 1:
                for wit in item:
                    colour_classes[wit] = colours[i]
            else:
                for wit in item:
                    colour_classes[wit] = 'none'

        for i, wit in enumerate(cleaned_content):
            if not cleaned_content[wit]['t'] == '':
                content_string = f'<td class="{colour_classes[wit]}">{cleaned_content[wit]["t"]}</td>'
            else:
                content_string = f'<td class="empty"></td>'
            table_array[i].append(content_string)

        col_widths.append(
            len(sorted(cleaned_content.values(), key=lambda x: len(x), reverse=True)[0])
        )

    shift_row = []
    width_sum = 0

    for i, width in enumerate(col_widths):
        width_sum += width
        if width_sum > 20:
            shift_row.append(i)
            width_sum = 0
    shift_row.append(len(col_widths))  # Let the shifted array include the final material too.

    shifted_array = []
    prev_cutoff = 0
    for i, cutoff in enumerate(shift_row):
        for j, row in enumerate(table_array):
            if cutoff == prev_cutoff:
                row_list = [f'<td>{numbered_witnesses[j]}</td>']
                row_list.extend(table_array[j][prev_cutoff:])
            else:
                row_list = [f'<td>{numbered_witnesses[j]}</td>']
                row_list.extend(table_array[j][prev_cutoff:cutoff])
            try:
                shifted_array[i].append(row_list)
            except IndexError:
                shifted_array.append([])
                shifted_array[i].append(row_list)
        prev_cutoff = cutoff

    return shifted_array


def wrap_table_html(table_array, metadata):
    """Wrap the html table in a html document. Return html document as string.

    Keyword Arguments:
    table_array -- html as string.
    """
    html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="utf-8" />
        <title>Collation of witnesses """
    html += metadata['manuscripts']
    html += """
        </title>
        <style>
        td { border: 1px solid #d3d3d3; white-space: nowrap; padding: 0.25em; }
        table.alignment {
            border-collapse: separate; border-spacing: 0.25em; margin: 0.25em; border-top: 1px solid #d3d3d3;
        }
        td.Melon { background-color: #FFB7B2; }
        td.Pastel_Yellow {background-color: #FDFD95}
        td.Very_Pale_Orange { background-color: #FFDAC1; }
        td.Dirty_White { background-color: #E2F0CB; }
        td.Magic { background-color: #B5EAD7; }
        td.Crayola { background-color: #C7CEEA; }
        td.Light_Salmon_Pink { background-color: #FF9AA2; }
        td.Vodka { background-color: #B2B7F6; }
        td.Pale_Blue { background-color: #B2F6F0; }
        td.Granny_Smith_Apple { background-color: #B3EE9A; }
        td.Calamansi { background-color: #F6F39F; }
        td.Ceil { background-color: #998AD3; }
        td.Orchid { background-color: #E494D3; }
        td.Tea_Green { background-color: #CDF1AF; }
        td.Pearl_Aqua { background-color: #87DCC0; }
        td.Aero { background-color: #88BBE4; }
        td.Pastel_Purple { background-color: #B29DB6; }
        td.Light_Silver { background-color: #D6D6D6; }
        td.Pastel_Blue { background-color: #ABC3CE; }
        td.Black_Shadows { background-color: #C5AEB4; }
        td.Shadow_Blue { background-color: #7B8FA5; }
        td.Laurel_Green { background-color: #99B49F; }
        td.empty { border: 1px dotted; }
        </style>
    </head>
    <body>
    """
    html += '<h1>'
    if args['--title']:
        html += args['--title'] + ' (' + args['--output'] + ')'
    else:
        html += args['--output']
    html += '</h1>'
    html += '<h2>Collation of witnesses '
    html += metadata['manuscripts']
    html += '</h2>'
    html += '<p>Algorithm: '
    html += metadata['algorithm']
    html += ', token comparator: '
    html += metadata['comparator']
    if metadata['threshold']:
        html += ' (threshold: '
        html += metadata['threshold']
        html += ')'
    html += '</p>'
    html += '<p>Collation started '
    start = datetime.strptime(metadata['time_start'], "%Y-%m-%dT%H:%M:%S.%fZ").replace(microsecond=0)
    end = datetime.strptime(metadata['time_end'], "%Y-%m-%dT%H:%M:%S.%fZ").replace(microsecond=0)
    duration = end - start
    html += str(start)
    html += ' and ended '
    html += str(end)
    html += ' (duration: '
    html += str(duration)
    html += ').</p>'
    html += '<div id="alignment-table">'
    for row in table_array:
        html += '<table class="alignment">'
        for sub_row in row:
            html += '<tr>'
            for cell in sub_row:
                html += f'{cell}'
            html += '</tr>'
        html += '</table>'

    html += """
    </div>
    </body>
    </html>
    """
    return html


def write_html_to_file(html_input, output_file):
    """Write the html document to a file. Return file object.

    Keyword Arguments:
    html_input -- html document as string.
    """
    with open(output_file, 'w') as f:
        f.write(html_input)
        logging.info(f'{f.name} created.')
    return f

def collation_table_tei(data):
    logging.info(f'Process collation table to tei xml.')
    numbered_witnesses = {k: wit for k, wit in enumerate(data['witnesses'])}
    all_readings = []
    for line in data['table']:
        # rewrite empty token set
        newline = []
        for content in line:
            if not content:
                content = {'t': '', 'n': ''}
                newline.append(content)
            else:
                newline.append(content[0])
        #
        cleaned_content = {wit: content for wit, content in enumerate(newline)}
        sorted_witnesses = []
        compared = []
        for wit in cleaned_content:
            # create a temporary copy of the dictionary so we can change it during processing and
            # pop the witness under investigation. We want it popped to avoid match in every case.
            tmp = cleaned_content.copy()
            popped = tmp.pop(wit)
            # If the witness has not already been matched, see if there are matches in other
            # witnesses.
            if wit not in compared:
                # Add the witness to list of equals, as unique witnesses go to the result list too.
                wit_eqs = list()
                wit_eqs.append(popped['n'])
                wit_eqs.append(popped['t'])
                wit_eqs.append(wit)
                # If there are other witnesses with the same content, check which
                if popped in tmp.values():
                    # Iterate all other witnesses
                    for sub_wit, value in tmp.items():
                        # Register which match and add those to the `wit_eqs` and `compared` lists.
                        if popped['n'] == value['n']:
                            if popped['t'] == value['t']:
                                wit_eqs.append(sub_wit)
                                compared.append(sub_wit)
                # Add the wit_eqs list to the result list
                sorted_witnesses.append(wit_eqs)
        all_readings.append(sorted_witnesses)
    if args['--title']:
        set_title = args['--title']
    else:
        set_title = 'Title'
    if args['--editor']:
        set_editor = args['--editor']
    else:
        set_editor = 'Editor'
    if args['--editorID']:
        set_editorID = args['--editorID']
    else:
        set_editorID = 'ID'
    d = Document()
    root = d.createElementNS("http://www.tei-c.org/ns/1.0", "TEI")
    root.setAttribute("xmlns", "http://www.tei-c.org/ns/1.0")
    d.appendChild(root)
    ## write header
    header = d.createElementNS("http://www.tei-c.org/ns/1.0", "teiHeader")
    root.appendChild(header)
    filedesc = d.createElementNS("http://www.tei-c.org/ns/1.0", "fileDesc")
    header.appendChild(filedesc)
    titlestmt = d.createElementNS("http://www.tei-c.org/ns/1.0", "titleStmt")
    filedesc.appendChild(titlestmt)
    title = d.createElementNS("http://www.tei-c.org/ns/1.0", "title")
    text_node = d.createTextNode(set_title)
    title.appendChild(text_node)
    titlestmt.appendChild(title)
    editor = d.createElementNS("http://www.tei-c.org/ns/1.0", "editor")
    persname = d.createElementNS("http://www.tei-c.org/ns/1.0", "persName")
    persname.setAttribute("xml:id", set_editorID)
    text_node = d.createTextNode(set_editor)
    persname.appendChild(text_node)
    rolename = d.createElementNS("http://www.tei-c.org/ns/1.0", "roleName")
    text_node = d.createTextNode("Editor")
    rolename.appendChild(text_node)
    editor.appendChild(persname)
    editor.appendChild(rolename)
    titlestmt.appendChild(editor)
    editionstmt = d.createElementNS("http://www.tei-c.org/ns/1.0", "editionStmt")
    filedesc.appendChild(editionstmt)
    estmt_text = d.createElementNS("http://www.tei-c.org/ns/1.0", "p")
    text_node = d.createTextNode("New digital critical edition.")
    estmt_text.appendChild(text_node)
    editionstmt.appendChild(estmt_text)
    publicationstmt = d.createElementNS("http://www.tei-c.org/ns/1.0", "publicationStmt")
    filedesc.appendChild(publicationstmt)
    authority = d.createElementNS("http://www.tei-c.org/ns/1.0", "authority")
    text_node = d.createTextNode("Berlin-Brandenburgische Akademie der Wissenschaften (BBAW)")
    authority.appendChild(text_node)
    distributor = d.createElementNS("http://www.tei-c.org/ns/1.0", "distributor")
    text_node = d.createTextNode("Patristic Text Archive")
    distributor.appendChild(text_node)
    publicationstmt.appendChild(authority)
    publicationstmt.appendChild(distributor)
    sourcedesc = d.createElementNS("http://www.tei-c.org/ns/1.0", "sourceDesc")
    filedesc.appendChild(sourcedesc)
    listwit = d.createElementNS("http://www.tei-c.org/ns/1.0", "listWit")
    sourcedesc.appendChild(listwit)
    for entry in numbered_witnesses.values():
        witness = d.createElementNS("http://www.tei-c.org/ns/1.0", "witness")
        witness.setAttribute("xml:id", entry)
        listwit.appendChild(witness)
        sigle = d.createElementNS("http://www.tei-c.org/ns/1.0", "abbr")
        sigle.setAttribute("type","siglum")
        text_node = d.createTextNode(entry)
        sigle.appendChild(text_node)
        witness.appendChild(sigle)
        name = d.createElementNS("http://www.tei-c.org/ns/1.0", "name")
        witness.appendChild(name)
        origdate = d.createElementNS("http://www.tei-c.org/ns/1.0", "origDate")
        witness.appendChild(origdate)
        locus = d.createElementNS("http://www.tei-c.org/ns/1.0", "locus")
        witness.appendChild(locus)
    ## write text
    text = d.createElementNS("http://www.tei-c.org/ns/1.0", "text")
    root.appendChild(text)
    body = d.createElementNS("http://www.tei-c.org/ns/1.0", "body")
    text.appendChild(body)
    p = d.createElementNS("http://www.tei-c.org/ns/1.0", "p")
    body.appendChild(p)
    for list_i in all_readings:
        # test whether there are variants. If not:
        if len(list_i) == 1:
            for entry in list_i:
                text_node = d.createTextNode(entry[1])
                p.appendChild(text_node)
        else: 
            app = d.createElementNS("http://www.tei-c.org/ns/1.0", "app")
            app.setAttribute("type","textcritical")
            p.appendChild(app)
            text_node = d.createTextNode(" ")
            p.appendChild(text_node)
            tokens = [item[0] for item in list_i if item[0]]
            seen = set()
            duplicates = [x for x in tokens if x in seen or seen.add(x)] 
            for entry in list_i:
                rdg = d.createElementNS("http://www.tei-c.org/ns/1.0", "rdg")
                app.appendChild(rdg)
                text_node = d.createTextNode(re.sub(" ","",entry[1]))
                rdg.appendChild(text_node)
                if entry[1] == "":
                    rdg.setAttribute("cause","omission")
                if entry[0] in duplicates:
                    rdg.setAttribute("type","orthographic")
                witlist = []
                for i in entry[2:]:
                    wits = numbered_witnesses[i]
                    witlist.append("#"+wits)
                rdg.setAttribute("wit"," ".join(witlist))
    tei = d.toprettyxml()
    return tei

def write_tei_to_file(tei_input, output_file):
    """Write the tei document to a file. Return file object.

    Keyword Arguments:
    tei_input -- tei document as string.
    """
    with open(output_file, 'w', encoding="utf-8") as f:
        f.write(tei_input)
        logging.info(f'{f.name} created.')
    return f

if __name__ == "__main__":

    # Read command line arguments
    args = docopt(__doc__, version="0.0.1")

    # Setup logging
    log_formatter = logging.Formatter()
    verbosity = args['--verbosity']
    if not verbosity:
        verbosity = 'DEBUG'
        logging.basicConfig(level=verbosity.upper(), format="%(levelname)s: %(message)s")
        logging.debug(args)

    logging.info('App and logging initiated.')

    witnesses = convert_xml_to_plaintext(args["<file>"])
    json_tmp_file = write_collation_file(witnesses)
    collation_table = run_collatex(json_tmp_file)
    collation_json_file = collation_json(collation_table)
    tei_table = collation_table_tei(collation_table)
    html_table = collation_table_html(collation_table)
    collation_metadata = get_collation_metadata(collation_table)
    output_html = wrap_table_html(html_table, collation_metadata)

    if args['--output']:
        output_file = args['--output']
    else:
        output_file = 'output'
    html_file = write_html_to_file(output_html, output_file+".html")
    tei_file = write_tei_to_file(tei_table, output_file+".xml")
    csv_file = collation_table_csv_file(collation_table, output_file+".csv")

    logging.info('Results returned sucessfully.')
