"""
COMBINE Archive helper functions and classes based on libcombine.

Here common operations with COMBINE archives are implemented, like
extracting archives, creating archives from entries or directories,
adding metadata, listing content of archives.

When working with COMBINE archives these wrapper functions should be used.

"""
# FIXME: handle the adding of metadata

from __future__ import absolute_import, print_function

import os
import shutil
import warnings
import zipfile
import tempfile
try:
    import libcombine
except ImportError:
    import tecombine as libcombine
import pprint

MANIFEST_PATTERN = "manifest.xml"
METADAT_PATTERN = "metadata.*"



class Entry(object):
    """ Helper class to store content to create an OmexEntry."""

    def __init__(self, location, format=None, formatKey=None, master=False, description=None, creators=None):
        """ Create entry from information.

        If format and formatKey are provided the format is used.

        :param location: location of the entry
        :param format: full format string
        :param formatKey: short formatKey string
        :param master: master attribute
        :param description: description
        :param creators: iterator over Creator objects
        """
        if (formatKey is None) and (format is None):
            raise ValueError("Either 'formatKey' or 'format' must be specified for Entry.")
        if format is None:
            format = libcombine.KnownFormats.lookupFormat(formatKey=formatKey)

        # self.formatKey = formatKey
        self.format = format
        self.location = location
        self.master = master
        self.description = description
        self.creators = creators

    def __str__(self):
        if self.master:
            return '<*master* Entry {} | {}>'.format(self.master, self.location, self.format)
        else:
            return '<Entry {} | {}>'.format(self.master, self.location, self.format)


class Creator(object):
    """ Helper class to store the creator information. """

    def __init__(self, givenName, familyName, organization, email):
        self.givenName = givenName
        self.familyName = familyName
        self.organization = organization
        self.email = email


def combineArchiveFromDirectory(directory, omexPath, creators=None, creators_for_all=False):
    """ Creates a COMBINE archive from a given folder.

    The file types are inferred,
    in case of existing manifest or metadata information this should be reused.

    For all SED-ML files in the directory the master attribute is set to True.

    :param directory:
    :param omexPath:
    :param
    :return:
    """
    manifest_path = os.path.join(directory, MANIFEST_PATTERN)

    if os.path.exists(manifest_path):
        # FIXME: reuse information in existing manifest
        warnings.warn("Manifest file exists in directory, but not used in COMBINE archive creation: {}".format(manifest_path))

    # add the base entry
    entries = [
        Entry(location=".", format="http://identifiers.org/combine.specifications/omex", master=False)
    ]

    # iterate over all locations & guess format
    for root, dirs, files in os.walk(directory):
        for file in files:
            file_path = os.path.join(root, file)
            location = os.path.relpath(file_path, directory)

            # handle existing manifest file
            if location == MANIFEST_PATTERN:
                # don't package the manifest file
                continue

            # handle existing metadata files
            # FIXME: handle existing metadata

            # guess the format
            format = libcombine.KnownFormats.guessFormat(file_path)
            master = False
            if libcombine.KnownFormats.isFormat(formatKey="sed-ml", format=format):
                master = True

            entries.append(
                Entry(location=location, format=format, master=master, creators=creators)
            )

    # create additional metadata if available

    # write all the entries
    combineArchiveFromEntries(omexPath=omexPath, entries=entries, workingDir=directory)


def combineArchiveFromEntries(omexPath, entries, workingDir):
    """ Creates combine archive from given entries.

    Overwrites existing combine archive at omexPath.

    :param entries:
    :param workingDir:
    :return:
    """
    _addEntriesToArchive(omexPath, entries, workingDir=workingDir, add_entries=False)
    print("*" * 80)
    print('Archive created:\n\t', omexPath)
    print("*" * 80)


def addEntriesToCombineArchive(omexPath, entries, workingDir):
    """ Adds entries to

    :param omexPath:
    :param entries: iteratable of Entry
    :param workingDir: locations are relative to working dir
    :return:
    """
    _addEntriesToArchive(omexPath, entries, workingDir=workingDir, add_entries=True)
    print("*" * 80)
    print('Archive updated:\n\t', omexPath)
    print("*" * 80)


def _addEntriesToArchive(omexPath, entries, workingDir, add_entries, strict=True):
    """

    :param archive:
    :param entries:
    :param workingDir:
    :return:
    """
    omexPath = os.path.abspath(omexPath)
    print('omexPath:', omexPath)
    print('workingDir:', workingDir)

    if not os.path.exists(workingDir):
        raise IOError("Working directory does not exist: {}".format(workingDir))

    if add_entries is False:
        if os.path.exists(omexPath):
            # delete the old omex file
            warnings.warn("Combine archive is overwritten: {}".format(omexPath))
            os.remove(omexPath)

    archive = libcombine.CombineArchive()

    if add_entries is True:
        # use existing entries
        if os.path.exists(omexPath):
            # init archive from existing content
            if archive.initializeFromArchive(omexPath) is None:
                raise IOError("Combine Archive is invalid: ", omexPath)

    # timestamp
    time_now = libcombine.OmexDescription.getCurrentDateAndTime()

    # ----------------------------------
    # Create metadata file
    # ----------------------------------
    # create the metadata file
    # <content format = "http://identifiers.org/combine.specifications/omex-metadata" location = "metadata.rdf" / >

    metadata_xml = []
    for entry in entries:
        if entry.format is None or len(entry.format) == 0:
            # only add known files to archive metadata
            continue

        location = entry.location

        # add metadata for location
        description = entry.description
        creators = entry.creators

        # Create an omex description
        omex_d = libcombine.OmexDescription()
        omex_d.setAbout(location)
        omex_d.setCreated(time_now)

        if not description:
            description = "-"
        omex_d.setDescription(description)

        if creators:
            for c in creators:
                creator = libcombine.VCard()
                creator.setFamilyName(c.familyName)
                creator.setGivenName(c.givenName)
                creator.setEmail(c.email)
                creator.setOrganization(c.organization)
                omex_d.addCreator(creator)

        metadata_xml.append(omex_d.toXML())

    # store the metadata file
    # the library creates separate metadata file for every entry, so using this hack for now
    # see https://github.com/sbmlteam/libCombine/issues/23
    # FIXME: bad hack for now, but seems to work
    contents = [(item.split("\n"))[2:-2] for item in metadata_xml]
    start_str = "<?xml version='1.0' encoding='UTF-8'?>\n" \
                "<rdf:RDF xmlns:rdf='http://www.w3.org/1999/02/22-rdf-syntax-ns#' xmlns:dcterms='http://purl.org/dc/terms/' xmlns:vCard='http://www.w3.org/2006/vcard/ns#'>"
    content_str = "\n".join(["\n".join(lines) for lines in contents])
    end_str = "</rdf:RDF>"
    metadata_str = "\n".join([start_str, content_str, end_str])

    f_metadata = os.path.join(workingDir, "metadata.rdf")
    with open(f_metadata, "w") as f:
        f.write(metadata_str)

    # ----------------------------------
    # Add entries to COMBINE archive
    # ----------------------------------
    archive = libcombine.CombineArchive()

    for entry in entries:
        path = os.path.join(workingDir, entry.location)

        if not os.path.exists(path):
            msg = "File does not exist at given location: {}".format(path)
            if strict:
                raise IOError(msg)
            else:
                warnings.warn(msg)

        # add file to archive
        if entry.master:
            print("\t*\t", path)
        else:
            print("\t", path)
        archive.addFile(path, entry.location, entry.format, entry.master)

    # ----------------------------------
    # Write Combine archives
    # ----------------------------------
    archive.writeToFile(omexPath)
    archive.cleanUp()


def extractCombineArchive(omexPath, directory, method="zip"):
    """ Extracts combine archive at given path to directory.

    The zip method extracts all entries in the zip, the omex method
    only extracts the entries listed in the manifest.
    In some archives not all content is listed in the manifest.

    :param omexPath:
    :param directory:
    :param method: method to extract content, either 'zip' or 'omex'
    :return:
    """
    if method not in ["zip", "omex"]:
        raise ValueError("Method is not supported: {}".format(method))

    if method == "zip":
        zip_ref = zipfile.ZipFile(omexPath, 'r')
        zip_ref.extractall(directory)
        zip_ref.close()

    elif method == "omex":
        omex = libcombine.CombineArchive()
        if omex.initializeFromArchive(omexPath) is None:
            raise IOError("Invalid Combine Archive: {}", omexPath)

        for i in range(omex.getNumEntries()):
            entry = omex.getEntry(i)
            location = entry.getLocation()
            filename = os.path.join(directory, location)
            omex.extractEntry(location, filename)

        omex.cleanUp()


def getLocationsByFormat(omexPath, formatKey=None, method="omex"):
    """ Returns locations to files with given format in the archive.

    Uses the libcombine KnownFormats for formatKey, e.g., 'sed-ml' or 'sbml'.
    Files which have a master=True have higher priority and are listed first.

    :param omexPath:
    :param formatKey:
    :param method:
    :return:
    """
    if not formatKey:
        raise ValueError("Format must be specified.")

    if method not in ["zip", "omex"]:
        raise ValueError("Method is not supported: {}".format(method))

    locations_master = []
    locations = []

    if method == "omex":
        omex = libcombine.CombineArchive()
        if omex.initializeFromArchive(omexPath) is None:
            raise IOError("Invalid Combine Archive: {}", omexPath)

        for i in range(omex.getNumEntries()):
            entry = omex.getEntry(i)
            format = entry.getFormat()
            master = entry.getMaster()
            if libcombine.KnownFormats.isFormat(formatKey, format):
                loc = entry.getLocation()
                if (master is None) or (master is False):
                    locations.append(loc)
                else:
                    locations_master.append(loc)
        omex.cleanUp()

    elif method == "zip":
        # extract to tmpfile and guess format
        tmp_dir = tempfile.mkdtemp()

        try:
            extractCombineArchive(omexPath, directory=tmp_dir, method="zip")

            # iterate over all locations & guess format
            for root, dirs, files in os.walk(tmp_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    location = os.path.relpath(file_path, tmp_dir)
                    # guess the format
                    format = libcombine.KnownFormats.guessFormat(file_path)
                    if libcombine.KnownFormats.isFormat(formatKey=formatKey, format=format):
                        locations.append(location)
                    # print(format, "\t", location)

        finally:
            shutil.rmtree(tmp_dir)

    return locations_master + locations


def listContents(omexPath, method="omex"):
    """ Returns list of contents of the combine archive.

    :param omexPath:
    :param method: method to extract content, only 'omex' supported
    :return: list of contents
    """
    if method not in ["omex"]:
        raise ValueError("Method is not supported: {}".format(method))

    contents = []
    omex = libcombine.CombineArchive()
    if omex.initializeFromArchive(omexPath) is None:
        raise IOError("Invalid Combine Archive: {}", omexPath)

    for i in range(omex.getNumEntries()):
        entry = omex.getEntry(i)
        location = entry.getLocation()
        format = entry.getFormat()
        master = entry.getMaster()
        info = None
        try:
            for formatKey in ["sed-ml", "sbml", "sbgn", "cellml"]:
                if libcombine.KnownFormats_isFormat(formatKey, format):
                    info = omex.extractEntryToString(location)
        except:
            pass

        contents.append([i, location, format, master, info])

    omex.cleanUp()

    return contents


def printMetaDataFor(archive, location):
    """ Prints metadata for given location.

    :param archive: CombineArchive instance
    :param location:
    :return:
    """
    desc = archive.getMetadataForLocation(location)
    if desc.isEmpty():
        print("  no metadata for '{0}'".format(location))
        return None

    print("  metadata for '{0}':".format(location))
    print("     Created : {0}".format(desc.getCreated().getDateAsString()))
    for i in range(desc.getNumModified()):
        print("     Modified : {0}".format(desc.getModified(i).getDateAsString()))

    print("     # Creators: {0}".format(desc.getNumCreators()))
    for i in range(desc.getNumCreators()):
        creator = desc.getCreator(i)
        print("       {0} {1}".format(creator.getGivenName(), creator.getFamilyName()))


def printArchive(fileName):
    """ Prints content of combine archive

    :param fileName: path of archive
    :return: None
    """
    archive = libcombine.CombineArchive()
    if archive.initializeFromArchive(fileName) is None:
        print("Invalid Combine Archive")
        return None

    print('*'*80)
    print('Print archive:', fileName)
    print('*' * 80)
    printMetaDataFor(archive, ".")
    print("Num Entries: {0}".format(archive.getNumEntries()))

    for i in range(archive.getNumEntries()):
        entry = archive.getEntry(i)
        print(" {0}: location: {1} format: {2}".format(i, entry.getLocation(), entry.getFormat()))
        printMetaDataFor(archive, entry.getLocation())

    archive.cleanUp()


def printContents(omexPath):
    """ Prints contents of archive.

    :param omexPath:
    :return:
    """
    pprint.pprint(listContents(omexPath))
