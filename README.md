PTA-Collator provides a script (adapted from https://github.com/stenskjaer/collator, but with a number of modifications) and a Jupyter Notebook that assist in collating an arbitrary number of TEI XML transcriptions of a text. It uses the collation features provided by [CollateX](https://collatex.net/) (1.8-SNAPSHOT with added features from https://gitlab.informatik.uni-halle.de/alignment_public/tsaligner).

It is basically a wrapper for the CollateX CLI. It converts the witnesses (in TEI) into plain text with a very small XSLT script (and therefore also uses [Saxon HE](https://github.com/Saxonica/Saxon-HE/), available under the Mozilla Public License version 2.0.). It then normalizes (Unicode NFC), tokenizes, and strips all diacritics from the witnesses and finally converts them into CollateX input format (and writes this to a JSON file for later other use) that it then feeds to CollateX. The output of CollateX is finally converted to a CollateX JSON output file (for further use for example in https://enury.github.io/collation-viz/), to a CSV file, to a HTML file, to a Graphviz-Dot file (to be processed by [Graphviz](https://graphviz.org/)), to a Nexus file (to be processed by phylogenetic software like [SplitsTree](https://uni-tuebingen.de/fakultaeten/mathematisch-naturwissenschaftliche-fakultaet/fachbereiche/informatik/lehrstuehle/algorithms-in-bioinformatics/software/splitstree/)) and to a TEI XML file (when using the script; by using the Jupyter Notebook you can select which output you like to have).

This is developed to handle [Patristic Text Archive Schema](https://github.com/PatristicTextArchive/Schema) compliant material, mainly in Greek, but it might handle many other TEI documents, if the XSLT script is adapted.


# Installation

## Requirements

- Python 3
- Java Runtime Environment (< 15)
- Graphviz (optional for converting DOT to PNG, SVG,..., while using the Jupyter Notebook)

### Vendored binaries

The script uses [saxon](http://saxon.sourceforge.net/) for XML processing
and [CollateX](https://collatex.net/) (1.8-SNAPSHOT with added features from https://gitlab.informatik.uni-halle.de/alignment_public/tsaligner) for collation. The binaries of those are
included in the `vendor` directory, so no installation is required for that.

But you do need to have a functional *Java Runtime Environment* installed. CollateX only works with Java versions smaller than v. 15.
 
### Prepare for use

Install `uv`, if you have not yet, with `pip install uv`.

Then create a virtual environment with `uv venv` and activate it (with `source .venv/bin/activate` on MacOS/Linux or `.venv\Scripts\activate` on Windows).

Install dependencies with `uv sync`.


## Usage

The input files must be TEI-XML files (following the [PTA TEI-Schema](https://github.com/PatristicTextArchive/Schema)). They will be converted to plain text during
processing. The following elements will be preserved in the plain text for later
analysis:
- unclear
- pb
- del
- add
- gap (-> `{word}` or `{c}`)
- hi
- expan (= Nomina sacra in their expanded form)

### Usage of the Jupyter Notebook `collate.ipynb`

Open the folder with [VSCode](https://code.visualstudio.com/) (or [VSCodium](https://vscodium.com/)), install the Jupyter extension and load the Jupyter Notebook. (That's what I am using.)

If you don't use VSCode (VSCodium), install [Jupyter Notebook](https://jupyter.org/) with `uv add notebook` and then start with `jupyter notebook`.


### Usage of the script `collator.py` (in a terminal)


The usage statement:
```
Usage: collator.py [options] <file> <file>...

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
```


### Errors

Using the `dekker` algorithm may cause an error (most probably the same problem as in [CollateX refuses Json input](https://github.com/interedition/collatex/issues/76)):

```
Traceback (most recent call last):
  File "pta_collator/collator.py", line 700, in <module>
    collation_table = run_collatex(json_tmp_file)
                      ^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "pta_collator/collator.py", line 134, in run_collatex
    return json.loads(out)
           ^^^^^^^^^^^^^^^
  File "python3.11/json/__init__.py", line 346, in loads
    return _default_decoder.decode(s)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "python3.11/json/decoder.py", line 337, in decode
    obj, end = self.raw_decode(s, idx=_w(s, 0).end())
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "python3.11/json/decoder.py", line 355, in raw_decode
    raise JSONDecodeError("Expecting value", s, err.value) from None
json.decoder.JSONDecodeError: Expecting value: line 1 column 1 (char 0)
```
In that case, as a workaround, use `needleman-wunsch` algorithm instead.
