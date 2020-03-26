#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Usage: collator.py [options] <file> <file>...

A script for simplifying collation of several text witnesses encoded according
to the PTA Schema.

Original script by Michael Stenskjær Christensen (https://github.com/stenskjaer/collator)

Arguments:
  <file> <file>...        Two or more files that are to be collated.

Options:
  -o, --output <file>     Location of the output files (json and html). [default: ./output].
  -i, --interpunction     Do collation with interpunction [default: without interpunction].
  -d, --diacritics        Do collation without diacritics [default: with diacritics].
  -V, --verbosity <level> Set verbosity. Possibilities: silent, info, debug [default: info].
  -v, --version           Show version and exit.
  -h, --help              Show this help message and exit.
"""

from docopt import docopt
import json
import logging
import re
import os
import subprocess
import tempfile
import unicodedata

__version__ = '0.1.0'

BASE_DIR = os.path.dirname(__file__)

def diacritics(inputText):
    if args['--diacritics']:
        text = unicodedata.normalize("NFKD", inputText).translate({ord(c): None for c in "̓̔́̀͂̈ͅ"})
    else:
        text = inputText
    return text

def interpunction(inputText):
    if args['--interpunction']:
        text = inputText
    else:
        text = re.sub(r'[.,:·;›»]+', r'', inputText)
    return text

def convert_xml_to_plaintext(xml_files):
    """Convert the list of encoded files to plain text, using the auxilary XSLT script. This requires
    saxon installed.

    Keyword Arguments: xml_files -- list of files to be converted

    Return:
    Dictionary for inputting to collatex in this format:
        {
         "witnesses" : [
           {
             "id" : "A",
             "content" : "A black cat in a black basket"
           },
           {
             "id" : "B",
             "content" : "A black cat in a black basket"
           },
           {
             "id" : "C",
             "content" : "A striped cat in a black basket"
           },
           {
             "id" : "D",
             "content" : "A striped cat in a white basket"
            }
         ]
       }
    """
    output_dict = {'witnesses': []}
    for file in xml_files:
        stylesheet = os.path.join(BASE_DIR, 'conversion-script.xslt')
        saxon = os.path.join(BASE_DIR, 'vendor/saxon9he.jar')
        logging.debug(f'Start conversion of {file}')
        buffer = subprocess.run(['java', '-jar', saxon, f'-s:{file}', f'-xsl:{stylesheet}'],
                                stdout=subprocess.PIPE).stdout
        siglum = re.search(r'\{witness:([^}]+)\}', str(buffer)).group(1)
        text = re.search(r'\{content:([\W\w\s]*)}', str(buffer.decode('utf-8'))).group(1)
        text = interpunction(text)
        text = diacritics(text)
        witness_dictionary = dict(id=siglum,content=text)
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
        fp.write(json.dumps(input_dict, ensure_ascii=False))
        logging.info(f'Write JSON-Input file to {fp.name}')
    return fp


def run_collatex(input_file):
    """Run the collatex script on the temporary file.

    Keyword arguments:
    input_file -- File object of the json file that should be collated by collatex.

    Return:
    Collatex output as dictionary.
    """
    collatex_binary = os.path.join(BASE_DIR, 'vendor/collatex-tools-1.7.1.jar')
    cmd = subprocess.Popen(['java', '-jar', collatex_binary, '-t',
                            input_file.name], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = cmd.communicate()
    if err:
        pass#raise Exception(err)
    return json.loads(out)


def collation_table_html(table):
    """Process the collation table and return a HTML representation of it.

    Keyword Arguments:
    table -- Dictionary containing the table contents.
    """
    numbered_witnesses = {k: wit for k, wit in enumerate(table['witnesses'])}

    table_array = [[] for wit in numbered_witnesses]  # Create rows for all the witnesses.
    col_widths = []

    for cell in table['table']:

        cleaned_content = {wit: re.sub('\s+', ' ', ''.join(content).lower())
                           for wit, content in enumerate(cell)}

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
                wit_eqs.append(wit)
                # If there are other witnesses with the same content, check which
                if popped in tmp.values():
                    # Iterate all other witnesses
                    for sub_wit, value in tmp.items():
                        # Register which match and add those to the `wit_eqs` and `compared` lists.
                        if popped == value:
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
            if not cleaned_content[wit] == '':
                content_string = f'<td class="{colour_classes[wit]}">{cleaned_content[wit]}</td>'
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
        if width_sum > 80:
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


def wrap_table_html(table_array):
    """Wrap the html table in a html document. Return html document as string.

    Keyword Arguments:
    table_array -- html as string.
    """
    html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="utf-8" />
        <title>Collation of witnesses</title>
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
    <div id="alignment-table">
    """
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
    html_table = collation_table_html(collation_table)
    output_html = wrap_table_html(html_table)

    if args['--output']:
        output_file = args['--output']
    else:
        output_file = 'output'
    html_file = write_html_to_file(output_html, output_file+".html")

    logging.info('Results returned sucessfully.')
