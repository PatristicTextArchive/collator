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
import pandas as pd
from datetime import datetime
from xml.dom.minidom import Document

__version__ = '0.4.0'

BASE_DIR = os.path.dirname(__file__)

def normalize(inputText):
    ## remove annotations
    normalized = re.sub(r'[(){}=–]+', r'', inputText)
    normalized = re.sub(r'add', r'', normalized)
    normalized = re.sub(r'del', r'', normalized)
    normalized = re.sub(r'margin', r'', normalized)
    normalized = re.sub(r'above', r'', normalized)
    normalized = re.sub(r'inline', r'', normalized)
    normalized = re.sub(r'overline', r'', normalized)
    normalized = re.sub(r'strikethrough', r'', normalized)
    normalized = re.sub(r'erasure', r'', normalized)
    normalized = re.sub(r'initial', r'', normalized)
    normalized = re.sub(r'ekthesis', r'', normalized)
    normalized = re.sub(r'unclear', r'', normalized)
    ## unicode normalization
    normalized = unicodedata.normalize("NFD", normalized).translate({ord(c): None for c in "̓̔́̀͂̈ͅ"}).lower().strip()
    if normalized == "":
        normalized = " "
    return normalized

def processToken(inputText):
    return {"t": inputText.strip(), "n": normalize(inputText)}

def diacritics(inputText):
    return [processToken(token) for token in re.findall(r'[\w\S]+', inputText, flags=re.UNICODE)]

def delete_interpunction(inputText):
    return re.sub(r'[.,:··;›»⁘—\+\-\n]+', r'', inputText)

def clean(text):
    """Remove superfluous spaces and linebreaks from extracted text"""
    cleaned = re.sub(r"\n",r"",text)
    cleaned = re.sub(r"\s{2,}",r" ",cleaned)
    cleaned = re.sub(r"=\s",r"=",cleaned)
    cleaned = re.sub(r"\s([–\}\).,··:;?]+)",r"\1",cleaned)
    return cleaned

def merge_identical_rows(data):
    """Merge identical rows in generated all_variants list of lists"""
    merged = []

    # Signature = sorted list of numeric‐tails of all sublists
    def signature(row):
        return sorted(tuple(sub[2:]) for sub in row)

    for row in data:
        sig = signature(row)

        if merged and signature(merged[-1]) == sig:
            # Same multiset of tails → merge all sublists by their tail‐key
            acc = {}     # tail-tuple → full sublist with merged texts
            order = []   # to remember the order in which tails first appear

            # 1) seed from the already‐merged row
            for sub in merged[-1]:
                tail = tuple(sub[2:])
                if tail not in acc:
                    order.append(tail)
                    acc[tail] = sub[:]  # copy entire original sublist

            # 2) absorb the new row’s sublists
            for sub in row:
                tail = tuple(sub[2:])
                txt0, txt1 = str(sub[0]), str(sub[1])
                if tail in acc:
                    # concatenate the first two fields (as long as the first is not empty)
                    if txt0:
                        acc[tail][0] += " " + txt0
                        acc[tail][1] += " " + txt1
                    else:
                        acc[tail][0] += "" + txt0
                        acc[tail][1] += "" + txt1
                else:
                    # brand-new tail (shouldn’t happen if signatures matched exactly)
                    order.append(tail)
                    acc[tail] = sub[:]

            # 3) rebuild merged[-1] in the original order
            merged[-1] = [acc[tail] for tail in order]

        else:
            # New signature → copy row in full
            new_row = [sub[:] for sub in row]
            merged.append(new_row)

    return merged

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
            text = delete_interpunction(text)
        text = diacritics(clean(text))
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
        pass #raise Exception(err)
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

def write_metadata_file(metadata):
    """Write the `metadata` to a local file for reference.
    """
    if args['--output']:
        output_file = args['--output']
    else:
        output_file = 'output'
    with open(output_file+"_metadata.json", "w", encoding='utf8') as fp:
        fp.write(json.dumps(metadata, indent=4, ensure_ascii=False))
        logging.info(f'Write metadata file to {fp.name}')
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
    write_metadata_file(metadata)
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


def collation_table_graph_file(data, output_file):
    """Process the collation table and return a Graphviz dot representation of it.

    Keyword Arguments:
    table -- Dictionary containing the table contents.
    """    
    with open(output_file, 'w') as outfile:
        outfile.write("digraph {\n")
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
        count_outer = 0
        for wit in cleaned_content:
            # create a temporary copy of the dictionary so we can change it during processing and
            # pop the witness under investigation. We want it popped to avoid match in every case.
            tmp = cleaned_content.copy()
            popped = tmp.pop(wit)
            # If the witness has not already been matched, see if there are matches in other
            # witnesses.    
            count_outer = count_outer+1
            counter_inner = 0
            if wit not in compared:
                counter_inner = counter_inner+1
                id = str(count_outer)+"."+str(counter_inner)
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
    # ab hier
    count_outer = 0
    flatlist = []
    start = {"id":"0.0","word":"°","witnesses":data["witnesses"]}
    flatlist.append(start)
    all_readings_merged = merge_identical_rows(all_readings)
    for list_i in all_readings_merged:
        tokens = [item[0] for item in list_i if item[0]]
        seen = set()
        duplicates = [x for x in tokens if x in seen or seen.add(x)] 
        count_outer = count_outer+1
        counter_inner = 0
        for entry in list_i:
            items = {}
            counter_inner = counter_inner+1
            id = str(count_outer)+"."+str(counter_inner)
            if entry[1] == "":
                counter_inner = counter_inner-1
                pass
            elif entry[0] in duplicates:  
                items["id"] = id 
                items["word"] = "orth: "+entry[1]
            else:   
                items["id"] = id
                items["word"] = entry[1]
            if entry[1]:
                witlist = []
                for i in entry[2:]:
                    wits = numbered_witnesses[i]
                    witlist.append(wits)
                items["witnesses"] = witlist
                flatlist.append(items)
    start = {"id":str(len(all_readings))+".0","word":"°","witnesses":data["witnesses"]}
    flatlist.append(start)
    df = pd.DataFrame(flatlist)
    with open(output_file, 'a') as outfile:
        for entry in flatlist:
            outfile.write(entry['id']+' [label="'+entry['word']+'"]\n')
    edges = {}
    for wit in data['witnesses']:
        witlist = [wit]
        new = df[df.witnesses.apply(lambda x: bool(set(x) & set(witlist)))]['id'].tolist()
        thisedges = []
        for index, item in enumerate(new):
            if index < len(new) - 1:
                edge = item+' -> '+new[index + 1]
            thisedges.append(edge)
        edges[wit] = thisedges
    alledges = set(num for sublist in edges.values() for num in sublist)
    final_edges = []
    for entry in alledges:
        collect = {}
        collect["edge"] = entry
        witnesses = []
        for key, val in edges.items():
            if entry in val:
                witnesses.append(key)
        collect["wit"] = ",".join(witnesses)
        final_edges.append(collect)
    with open(output_file, 'a') as outfile:
        for entry in final_edges:
            outfile.write(entry['edge']+' [label="'+entry['wit']+'"]\n')
        outfile.write("}")
        logging.info(f'{outfile.name} created.')
    return output_file


def collation_table_nexus_file(data,output_file):
    """Process the collation table and return a Nexus representation of it for further processing with
    phylogenetic software. Caution: misalignments may 
    cause serious problems for the interpretation of the
    file!

    Keyword Arguments:
    table -- Dictionary containing the table contents.
    """    
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
        count_outer = 0
        for wit in cleaned_content:
            # create a temporary copy of the dictionary so we can change it during processing and
            # pop the witness under investigation. We want it popped to avoid match in every case.
            tmp = cleaned_content.copy()
            popped = tmp.pop(wit)
            # If the witness has not already been matched, see if there are matches in other
            # witnesses.    
            count_outer = count_outer+1
            counter_inner = 0
            if wit not in compared:
                counter_inner = counter_inner+1
                id = str(count_outer)+"."+str(counter_inner)
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
    flatlist = []
    symbols = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "A", "B", "C", "D", "E", "F", "G", "H", "K", "L", "M", "N", "P", "Q", "R", "S", "T", "U", "V", "W", "X", "Y", "Z", "a", "b", "c", "d", "e", "f", "g", "h", "k", "l", "m", "n", "p", "q", "r", "s", "t", "u", "v", "w", "x", "y", "z",]
    all_readings_merged = merge_identical_rows(all_readings)
    for list_i in all_readings_merged:
        tokens = [item[0] for item in list_i if item[0]]
        seen = set()
        duplicates = [x for x in tokens if x in seen or seen.add(x)]
        duplicate_index =[index for index, token in enumerate(tokens) if token in duplicates]
        counter_inner = 1
        for index, entry in enumerate(list_i):
            items = {}
            if entry[1] == "":
                items["id"] = "?"
                #counter_inner = counter_inner-1
            elif entry[0] in duplicates: 
                distance = index-duplicate_index[0]
                items["id"] = symbols[counter_inner-distance]
            else:   
                items["id"] = symbols[counter_inner]
            witlist = []
            for i in entry[2:]:
                wits = numbered_witnesses[i]
                witlist.append(wits)
            items["witnesses"] = witlist
            flatlist.append(items)
            counter_inner = counter_inner+1
    nexus = []
    for entry in data["witnesses"]:
        collect = {}
        collect["ms"] = entry
        status = []
        for x in flatlist:
            if entry in x["witnesses"]:
                status.append(x["id"])
        collect["status"] = status
        nexus.append(collect)
    with open(output_file, 'w') as outfile:
        outfile.write('#NEXUS\n')
        outfile.write('begin data;\n')
        outfile.write('  dimensions ntax='+str(len(data["witnesses"]))+' nchar='+str(len(nexus[0]["status"]))+';\n')
        outfile.write('  format datatype=standard symbols="0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz" missing=? gap=-;\n')
        outfile.write('matrix\n')
        for n in nexus:
            outfile.write(n['ms']+'\t'+''.join(n['status'])+'\n')
        outfile.write(';\n')
        outfile.write('end;\n')        
    logging.info(f'{outfile.name} created.')
    return output_file

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
        colours = ['lightblue', 'lightcoral', 'lightcyan', 'lightgoldenrodyellow', 'lightgreen', 'lightpink', 'lightsalmon', 'lightseagreen', 'lightskyblue', 'lightslategray', 'lightslategrey', 'lightsteelblue', 'lightyellow', 'aquamarine', 'azure', 'beige', 'bisque', 'blanchedalmond', 'blue', 'blueviolet', 'brown', 'burlywood', 'cadetblue', 'chartreuse', 'chocolate', 'coral', 'cornflowerblue', 'cornsilk', 'crimson', 'cyan', 'deeppink', 'deepskyblue', 'dodgerblue', 'firebrick', 'floralwhite', 'forestgreen', 'fuchsia', 'gainsboro', 'ghostwhite', 'gold', 'goldenrod', 'green', 'greenyellow', 'honeydew', 'hotpink', 'indianred', 'indigo', 'ivory', 'khaki', 'lavender', 'lavenderblush', 'lawngreen', 'lemonchiffon', 'lime', 'limegreen', 'linen', 'magenta', 'maroon', 'mediumaquamarine', 'mediumblue', 'mediumorchid', 'mediumpurple', 'mediumseagreen', 'mediumslateblue', 'mediumspringgreen', 'mediumturquoise', 'mediumvioletred', 'midnightblue', 'mintcream', 'mistyrose', 'moccasin', 'navajowhite', 'navy', 'oldlace', 'olive', 'olivedrab', 'orange', 'orangered', 'orchid', 'palegoldenrod', 'palegreen', 'paleturquoise', 'palevioletred', 'papayawhip', 'peachpuff', 'peru', 'pink', 'plum', 'powderblue', 'purple', 'rebeccapurple', 'red', 'rosybrown', 'royalblue', 'saddlebrown', 'salmon', 'sandybrown', 'seagreen', 'seashell', 'sienna', 'silver', 'skyblue', 'slateblue', 'slategray', 'slategrey', 'snow', 'springgreen', 'steelblue', 'tan', 'teal', 'thistle', 'tomato', 'turquoise', 'violet', 'wheat', 'whitesmoke', 'yellow', 'yellowgreen']
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
        td.aquamarine { background-color: #7FFFD4; }
        td.azure { background-color: #F0FFFF; }
        td.beige { background-color: #F5F5DC; }
        td.bisque { background-color: #FFE4C4; }
        td.blanchedalmond { background-color: #FFEBCD; }
        td.blue { background-color: #0000FF; }
        td.blueviolet { background-color: #8A2BE2; }
        td.brown { background-color: #A52A2A; }
        td.burlywood { background-color: #DEB887; }
        td.cadetblue { background-color: #5F9EA0; }
        td.chartreuse { background-color: #7FFF00; }
        td.chocolate { background-color: #D2691E; }
        td.coral { background-color: #FF7F50; }
        td.cornflowerblue { background-color: #6495ED; }
        td.cornsilk { background-color: #FFF8DC; }
        td.crimson { background-color: #DC143C; }
        td.cyan { background-color: #00FFFF; }
        td.deeppink { background-color: #FF1493; }
        td.deepskyblue { background-color: #00BFFF; }
        td.dodgerblue { background-color: #1E90FF; }
        td.firebrick { background-color: #B22222; }
        td.floralwhite { background-color: #FFFAF0; }
        td.forestgreen { background-color: #228B22; }
        td.fuchsia { background-color: #FF00FF; }
        td.gainsboro { background-color: #DCDCDC; }
        td.ghostwhite { background-color: #F8F8FF; }
        td.gold { background-color: #FFD700; }
        td.goldenrod { background-color: #DAA520; }
        td.green { background-color: #008000; }
        td.greenyellow { background-color: #ADFF2F; }
        td.honeydew { background-color: #F0FFF0; }
        td.hotpink { background-color: #FF69B4; }
        td.indianred { background-color: #CD5C5C; }
        td.indigo { background-color: #4B0082; }
        td.ivory { background-color: #FFFFF0; }
        td.khaki { background-color: #F0E68C; }
        td.lavender { background-color: #E6E6FA; }
        td.lavenderblush { background-color: #FFF0F5; }
        td.lawngreen { background-color: #7CFC00; }
        td.lemonchiffon { background-color: #FFFACD; }
        td.lightblue { background-color: #ADD8E6; }
        td.lightcoral { background-color: #F08080; }
        td.lightcyan { background-color: #E0FFFF; }
        td.lightgoldenrodyellow { background-color: #FAFAD2; }
        td.lightgray { background-color: #D3D3D3; }
        td.lightgreen { background-color: #90EE90; }
        td.lightgrey { background-color: #D3D3D3; }
        td.lightpink { background-color: #FFB6C1; }
        td.lightsalmon { background-color: #FFA07A; }
        td.lightseagreen { background-color: #20B2AA; }
        td.lightskyblue { background-color: #87CEFA; }
        td.lightslategray { background-color: #778899; }
        td.lightslategrey { background-color: #778899; }
        td.lightsteelblue { background-color: #B0C4DE; }
        td.lightyellow { background-color: #FFFFE0; }
        td.lime { background-color: #00FF00; }
        td.limegreen { background-color: #32CD32; }
        td.linen { background-color: #FAF0E6; }
        td.magenta { background-color: #FF00FF; }
        td.maroon { background-color: #800000; }
        td.mediumaquamarine { background-color: #66CDAA; }
        td.mediumblue { background-color: #0000CD; }
        td.mediumorchid { background-color: #BA55D3; }
        td.mediumpurple { background-color: #9370DB; }
        td.mediumseagreen { background-color: #3CB371; }
        td.mediumslateblue { background-color: #7B68EE; }
        td.mediumspringgreen { background-color: #00FA9A; }
        td.mediumturquoise { background-color: #48D1CC; }
        td.mediumvioletred { background-color: #C71585; }
        td.midnightblue { background-color: #191970; }
        td.mintcream { background-color: #F5FFFA; }
        td.mistyrose { background-color: #FFE4E1; }
        td.moccasin { background-color: #FFE4B5; }
        td.navajowhite { background-color: #FFDEAD; }
        td.navy { background-color: #000080; }
        td.oldlace { background-color: #FDF5E6; }
        td.olive { background-color: #808000; }
        td.olivedrab { background-color: #6B8E23; }
        td.orange { background-color: #FFA500; }
        td.orangered { background-color: #FF4500; }
        td.orchid { background-color: #DA70D6; }
        td.palegoldenrod { background-color: #EEE8AA; }
        td.palegreen { background-color: #98FB98; }
        td.paleturquoise { background-color: #AFEEEE; }
        td.palevioletred { background-color: #DB7093; }
        td.papayawhip { background-color: #FFEFD5; }
        td.peachpuff { background-color: #FFDAB9; }
        td.peru { background-color: #CD853F; }
        td.pink { background-color: #FFC0CB; }
        td.plum { background-color: #DDA0DD; }
        td.powderblue { background-color: #B0E0E6; }
        td.purple { background-color: #800080; }
        td.rebeccapurple { background-color: #663399; }
        td.red { background-color: #FF0000; }
        td.rosybrown { background-color: #BC8F8F; }
        td.royalblue { background-color: #4169E1; }
        td.saddlebrown { background-color: #8B4513; }
        td.salmon { background-color: #FA8072; }
        td.sandybrown { background-color: #F4A460; }
        td.seagreen { background-color: #2E8B57; }
        td.seashell { background-color: #FFF5EE; }
        td.sienna { background-color: #A0522D; }
        td.silver { background-color: #C0C0C0; }
        td.skyblue { background-color: #87CEEB; }
        td.slateblue { background-color: #6A5ACD; }
        td.slategray { background-color: #708090; }
        td.slategrey { background-color: #708090; }
        td.snow { background-color: #FFFAFA; }
        td.springgreen { background-color: #00FF7F; }
        td.steelblue { background-color: #4682B4; }
        td.tan { background-color: #D2B48C; }
        td.teal { background-color: #008080; }
        td.thistle { background-color: #D8BFD8; }
        td.tomato { background-color: #FF6347; }
        td.turquoise { background-color: #40E0D0; }
        td.violet { background-color: #EE82EE; }
        td.wheat { background-color: #F5DEB3; }
        td.white { background-color: #FFFFFF; }
        td.whitesmoke { background-color: #F5F5F5; }
        td.yellow { background-color: #FFFF00; }
        td.yellowgreen { background-color: #9ACD32; }
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
    all_readings_merged = merge_identical_rows(all_readings)
    for list_i in all_readings_merged:
        # test whether there are variants. If not:
        if len(list_i) == 1:
            for entry in list_i:
                text_node = d.createTextNode(entry[1])
                p.appendChild(text_node)
        else: 
            app = d.createElementNS("http://www.tei-c.org/ns/1.0", "app")
            app.setAttribute("type","variants")
            p.appendChild(app)
            text_node = d.createTextNode(" ")
            p.appendChild(text_node)
            tokens = [item[0] for item in list_i if item[0]]
            seen = set()
            duplicates = [x for x in tokens if x in seen or seen.add(x)] 
            for entry in list_i:
                rdg = d.createElementNS("http://www.tei-c.org/ns/1.0", "rdg")
                app.appendChild(rdg)
                text_node = d.createTextNode(re.sub("\\s+"," ",entry[1]))
                rdg.appendChild(text_node)
                if entry[1] == "":
                    rdg.setAttribute("type","omission")
                if entry[0] in duplicates:
                    rdg.setAttribute("cause","orthographic")
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
    dot_file = collation_table_graph_file(collation_table, output_file+".dot")
    nexus_file = collation_table_nexus_file(collation_table, output_file+".nex")

    logging.info('Results returned sucessfully.')
