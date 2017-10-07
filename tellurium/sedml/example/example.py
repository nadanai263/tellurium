"""
Testing of tesedml
"""

from __future__ import print_function, absolute_import
import os
import tellurium as te
from tellurium.tests.testdata import SEDML_TEST_DIR, OMEX_TEST_DIR



if __name__ == "__main__":
    outputDir = "./__tmp__"
    if not os.path.exists(outputDir):
        os.makedirs(outputDir)


    test_omex = os.path.join(OMEX_TEST_DIR, 'specification', 'L1V3', 'L1V3_parameter-scan-2d.omex')
    # test_omex = os.path.join(OMEX_TEST_DIR, 'specification', 'L1V3', 'L1V3_repressilator.omex')
    dgs = te.executeCombineArchive(test_omex, printPython=True, outputDir=outputDir, saveOutputs=True,
                                   workingDir=outputDir)
