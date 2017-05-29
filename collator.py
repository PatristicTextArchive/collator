#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Usage: collator.py [options] <file> <file>...

A script for simplifying collation of several text witnesses encoded according
to the Lombard Press Schema.

Arguments:
  <file> <file>...        Two or more files that are to be collated.

Options:
  -o, --output <file>     Location of the output file. [default: ./output.html].
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

__version__ = '0.1.0'

BASE_DIR = os.path.dirname(__file__)


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
        logging.debug(f'Start conversion of {file}')
        buffer = subprocess.run(['saxon', f'-s:{file}', f'-xsl:{stylesheet}'],
                                stdout=subprocess.PIPE).stdout
        witness_dictionary = dict(id=re.search(r'\{witness:([^}]+)\}', str(buffer)).group(1),
                                  content=re.search('\{content:(.*)}', str(buffer)).group(1))
        output_dict['witnesses'].append(witness_dictionary)
    return output_dict


def write_collation_file(input_dict):
    """Write the `input_dict` to a local file for collatex processing.

    Keyword Arguments:
    input_dict -- Dump the witness dictionary to a JSON file.
    """
    fp = tempfile.NamedTemporaryFile(mode='w')
    fp.write(json.dumps(input_dict))
    return fp


def run_collatex(input_file):
    """Run the collatex script on the temporary file.

    Keyword arguments:
    input_file -- File object of the json file that should be collated by collatex.

    Return:
    Collatex output as dictionary.
    """
    collatex_binary = os.path.join(BASE_DIR, 'collatex-tools-1.7.1.jar')
    cmd = subprocess.Popen(['java', '-jar', collatex_binary,
                            input_file.name], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = cmd.communicate()
    if err:
        raise Exception(err)
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
        colours = ['green', 'blue', 'red', 'yellow', 'pink']
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
        if width_sum > 100:
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
        <title>HTML collation</title>
        <style>
        td { border: 1px solid #d3d3d3; white-space: nowrap; padding: 0.25em; }
        table.alignment {
            border-collapse: separate; border-spacing: 0.25em; margin: 0.25em; border-top: 1px solid #d3d3d3;
        }
        td.green { background-color: #eaffea; }
        td.blue { background-color: #ECEFFF; }
        td.red { background-color: #ffecec; }
        td.yellow { background-color: #FFFFEE; }
        td.pink { background-color: #FEEEFF; }
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
        output_file = 'output.html'
    html_file = write_html_to_file(output_html, output_file)

    logging.info('Results returned sucessfully.')
