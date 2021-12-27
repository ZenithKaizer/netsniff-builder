# service-netsniff-netsniff-hp-builder

Builder d'images pour la HP permettant de tester les performances d'un site.



## Table of Contents

* [Installation](#installation)
* [Uninstallation](#uninstallation)
* [Usage](#usage)
* [Configuration](#configuration)
* [Updating Metadata](#updating-metadata)
* [Updating Manifest](#updating-manifest)

## Installation

```bash
pip install -e .

pip install netsniff -i https://artifactory.si.francetelecom.fr/api/pypi/dom-scp-pypi/simple
```

(You don't need to run `pip install -r requirements.txt`)

## Deployment 
```bash
# build
python3 -m build -n

# check 
twine check dist/*

# Deploy
twine upload --cert /usr/share/ca-certificates/Hebex/root_sha512.pki_orange.crt --repository-url https://artifactory.si.francetelecom.fr/api/pypi/dom-scp-pypi dist/*
```
## Uninstallation

```bash
pip uninstall skills-configs-cli
```

## Usage

```bash
skills-configs-cli --help
```

or

```bash
skills-configs-cli -h
```