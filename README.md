Collator is a simple and early script that assists in collating an arbitrary
number of TEI XML transcriptions of a text. It uses the collation features
provided by [CollateX](https://collatex.net/) and creates a HTML document with a
representation of the witnesses that is inspired by the CollateX HTML output as well as a TEI document.

It is basically a wrapper for the CollateX CLI. It converts the witnesses into
plain text with a very small xslt-script (and therefore also uses saxon). It then normalizes (Unicode NFC), 
tokenizes, and strips all diacritics from those witnesses and finally reads them into a CollateX compliant 
JSON input file that it feeds to CollateX. The output of CollateX is then converted to a CollateX JSON 
output file, to a HTML file, and to a TEI XML file.

This is developed to handle [Patristic Text Archive
Schema](https://github.com/PatristicTextArchive/Schema) compliant material, mainly in Greek, but it might
handle many other TEI documents well for now, as the encoding conventions of the
document are not central to it.


# Installation

## Requirements

- Python 3.6
- Java Runtime Environment

### Vendored binaries

The script uses [saxon](http://saxon.sourceforge.net/) for XML processing
and [CollateX](https://collatex.net/) for collation. The binaries of those are
included in the `vendor` directory, so no installation is required for that.

But you do need to have a
functional *Java Runtime Environment* installed.

### Run without any installation

The only external dependency right now is the wonderful [docopt
module](http://docopt.org/). 

Before you install anything, you should probably create a [virtual
environment](http://docs.python-guide.org/en/latest/dev/virtualenvs/) for the
project. To do that, run:

```bash
$ virtualenv -p python3 <name>
```
Where `<name>` is the name you want to give the venv.

After activating the venv (`workon` or `source`), install dependencies:
```bash
$ pip install -r requirements.txt
```

Now you can run the script from its directory with `./collator.py`.

### Install 

From the directory of the script, run:

```bash
pip3 install .
```

Now `collator.py` should be globally available.

## Usage


The usage statement:
```
Usage: collator.py [options] <file> <file>...

A script for simplifying collation of several text witnesses encoded according
to the PTA Schema.

Original script by Michael Stenskjær Christensen (https://github.com/stenskjaer/collator)

Arguments:
  <file> <file>...        Two or more files that are to be collated.

Options:
  -t, --title=<title>     Set title
  -e, --editor=<editor>   Set editor name
  -q, --editorID=<ID>     Set editor ID
  -o, --output <file>     Location of the output files (input-json, collation-json and collation-html). [default: ./output].
  -i, --interpunction     Do collation without interpunction [default: with interpunction].
  -V, --verbosity <level> Set verbosity. Possibilities: silent, info, debug [default: info].
  -v, --version           Show version and exit.
  -h, --help              Show this help message and exit.
```

The input files must be XML files. They will be converted to plain text during
processing. The following elements will be preserved in the plain text for later
analysis:
- unclear
- pb
- del
- add
- gap
- hi
- expan (= Nomina sacra in their expanded form)
