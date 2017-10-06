# Transformer/Framework/FiltersBase.py by J. M. Skelton


# -------
# Imports
# -------

import warnings;

from Transformer import Structure;

# Try to import the tqdm module to display progress bars in the _GenerateChildStructutes*() routines.

_TQDM = False;

try:
    import tqdm;

    _TQDM = True;
except ImportError:
    pass;


# ----------------
# FilterBase Class
# ----------------

class FilterBase(object):
    # -----------
    # Constructor
    # -----------

    def __init__(self):
        # Initialise fields.

        self._substitutions = None;

        self._tolerance = None;

        self._useMP = False;
        self._mpNumProcesses = None;

        self._substitutionIndex = None;

    # -------
    # Methods
    # -------

    def IsMPSafe(self):
        # The safe default is to return False; however, since this really _should_ be set in a derived class, we issue a warning if this method is called.

        warnings.warn("IsMPSafe() should be overridden in derived classes.", RuntimeWarning);

        return False

    def RequiresFilteredStructures(self):
        # The safe default is to return True; again, this should be set in a derived class, so we issue a warning if this method gets called.

        warnings.warn("RequiresFilteredStructures() should be overridden in derived classes.", RuntimeWarning);

        return True;

    def Initialise(self, substitutions, tolerance, printProgressUpdate, useMP, mpNumProcesses):
        # Update fields.

        self._substitutions = substitutions;

        self._tolerance = tolerance;

        self._printProgressUpdate = printProgressUpdate;

        self._useMP = useMP;
        self._mpNumProcesses = mpNumProcesses;

    def OnStartSubstitution(self, index):
        # Update the _substitutionIndex field.

        self._substitutionIndex = index;

    def TestSubstitutedStructure(self, structure, degeneracy):
        # Accept all structures (i.e. do nothing).

        return True;

    def SetFilteredStructures(self, structures, degeneracies):
        # Do nothing.

        pass;

    def FinaliseMergedStructureSet(self, structureSet):
        # Do nothing.

        pass;


# ------------------------
# CoverageFilterBase Class
# ------------------------

class CoverageFilterBase(FilterBase):
    # -----------
    # Constructor
    # -----------

    def __init__(self, coverage = 'full'):
        # Call the base class constructor.

        super(CoverageFilterBase, self).__init__();

        # Parameter validation.

        if coverage not in CoverageFilterBase.CoverageLevels:
            raise Exception(
                "Error: coverage must be one of {0}.".format(", ".join(CoverageFilterBase.CoverageLevels))
                );

        # Store the coverage level.

        self._coverage = coverage;

        # Initialise empty fields for storing the current and last sets of filtered structures and degeneracies passed to SetFilteredStructures().

        self._lastFilteredStructures, self._lastFilteredDegeneracies = None, None;
        self._currentFilteredStructures, self._currentFilteredDegeneracies = None, None;

    # -------
    # Methods
    # -------

    def RequiresFilteredStructures(self):
        # If the coverage level is set to 'low', the filtered structures are not required.

        return self._coverage != 'low';

    def OnStartSubstitution(self, index):
        # If the coverage level is not set to 'low', update the last set of filtered structures and degeneracies and call the base class method.

        if self._coverage != 'low':
            self._lastFilteredStructures = self._currentFilteredStructures;
            self._lastFilteredDegeneracies = self._currentFilteredDegeneracies;

            self._currentFilteredStructures, self._currentFilteredDegeneracies = None, None;

            self._substitutionIndex = index;

    def SetFilteredStructures(self, structures, degeneracies):
        # If the coverage level is not set to 'low', store the filtered structures and degeneracies.

        if self._coverage != 'low':
            self._currentFilteredStructures = structures;
            self._currentFilteredDegeneracies = degeneracies;

    def FinaliseMergedStructureSet(self, structureSet):
        # For all bar the 'low' coverage level, we need to apply the current substitution to the last set of filtered structures (if available).

        if self._coverage != 'low':
            structures, degeneracies = self._lastFilteredStructures, self._lastFilteredDegeneracies;

            if structures != None and len(structures) > 0:
                printProgressUpdate = self._printProgressUpdate;

                if printProgressUpdate:
                    # Since the user will lilely be using a derived class, we get the class name for the message (rather than printing "CoverageFilterBase").

                    print("{0}: Finalising merged structure set for {1} coverage.".format(self.__class__.__name__, self._coverage));

                # Decide whether to display a tqdm progress bar while generating new child structures.

                progressBar = printProgressUpdate and _TQDM;

                # Load the current substitution and convert atom types to atom-type numbers.

                atomType1, atomType2 = self._substitutions[self._substitutionIndex];

                atomTypeNumber1 = Structure.AtomTypeToAtomTypeNumber(atomType1);
                atomTypeNumber2 = Structure.AtomTypeToAtomTypeNumber(atomType2);

                # Load the symmetry tolerance.

                tolerance = self._tolerance;

                # Count the number of structures added to the merged structure set.

                addCount = 0;

                # Lists to store child structures removed by the TestSubstitutedStructure().

                filteredStructures, filteredDegeneracies = [], [];

                if progressBar:
                    print("");

                # Set up a primary iterator; if progressBar is set, wrap the iterator in a tqdm progress bar.

                iValues = range(0, len(structures));

                if _TQDM:
                    iValues = tqdm.tqdm(iValues);

                for i in iValues:
                    structure, degeneracy = structures[i], degeneracies[i];

                    # Generate substituted child structures.

                    newStructures, newDegeneracies = structure.GetUniqueAtomicSubstitutions(atomTypeNumber1, atomTypeNumber2, tolerance = tolerance);

                    # The degeneracies obtained from the Structure.GetUniqueAtomicSubstitutions() function need to be multiplied by that of the parent structure.

                    newDegeneracies = [
                        newDegeneracy * degeneracy for newDegeneracy in newDegeneracies
                        ];

                    # Test each structure with the TestSubstitutedStructure() method.

                    for newStructure, newDegeneracy in zip(newStructures, newDegeneracies):
                        if self.TestSubstitutedStructure(newStructure, newDegeneracy):
                            if structureSet.Add(newStructure, newDegeneracy):
                                addCount += 1;
                        else:
                            filteredStructures.append(newStructures);
                            filteredDegeneracies.append(newDegeneracy);

                if progressBar:
                    print("");

                # For formatting the terminal output.

                printedMessage = False;

                if printProgressUpdate and addCount > 0:
                    print("{0}: Added {1} structure(s) to merged structure set.".format(self.__class__.__name__, addCount));

                    printedMessage = True;

                # If the coverage level is set to 'full', add any filtered structures to the current set passed to SetFilteredStructures().

                if self._coverage == 'full' and len(filteredStructures) > 0:
                    self._currentFilteredStructures = self._currentFilteredStructures + filteredStructures;
                    self._currentFilteredDegeneracies = self._currentFilteredDegeneracies + filteredDegeneracies;

                    if printProgressUpdate:
                        print("{0}: Added {1} structure(s) to the filtered list.".format(self.__class__.__name__, len(filteredStructures)));

                        printedMessage = True;

                if printedMessage:
                    print("");

    # -------------
    # Static Fields
    # -------------

    CoverageLevels = ['low', 'medium', 'full'];