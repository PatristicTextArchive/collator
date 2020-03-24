Collator is a simple and early script that assists in collating an arbitrary
number of TEI XML transcriptions of a text. It uses the collation features
provided by [CollateX](https://collatex.net/) and creates a HTML document with a
representation of the witnesses that is inspired by the CollateX HTML output.

It is basically a wrapper for the CollateX CLI. It converts the witnesses into
plain text with a very small xslt-script (and therefore also uses saxon -- maybe
I could cut that dependency). It then reads those witnesses into a JSON
temporary file that it feeds to CollateX which returns a nested list that it
processes into a HTML representation.

This is developed to handle [Patristic Text Archive
Schema](https://github.com/PatristicTextArchive/Schema) compliant material, but it might
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
functional
[Java Runtime Environment](http://www.oracle.com/technetwork/java/javase/downloads/jre8-downloads-2133155.html).

### Run without any installation

The only external dependency right now is the wonderful [docopt
module](http://docopt.org/). I want to shred this dependency, but for now, the
script needs it.

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

### Install development version for testing

If you want to try it out, and maybe fiddle with the script yourself (PR's are
very welcome!), I would recommend creating a virtual environment and install the
script in development mode:

```bash
$ pip3 install -e .
```

Notice the dot! Now you can run `$ collator.py` from anywhere.

By using the `-e` the script is install with a symlink to the file so that
changes are immediately available in the command line script without updating
the install.

Once you leave the virtual environment, the script is no longer available. When
you delete the environment, it's gone.

### Install permanently

If you just want to be able to use the script at any time, from the directory of
the script, run:

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

Arguments:
  <file> <file>...        Two or more files that are to be collated.

Options:
  -o, --output <file>     Location of the output file. [default: ./output.html].
  -i, --interpunction     Do collation with interpunction [default: without interpunction].
  -d, --diacritics        Do collation without diacritics [default: with diacritics].
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
