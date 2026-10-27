-- ============================================================
-- Pigment Spectral Standards Database: SCHEMA v5 (SQLite)
-- Prepared by Maria Gabriela Rivas Carmona, University of Padova
-- ============================================================
-- Table count: 6
--   Material, Specimen, Measurement, Instrument, InstrumentConfiguration, Operator
--
-- Scope: a library of ER-IR reference scans of materials. Researchers match
-- unknown scans against it. Matching is read-only and unknown scans are
-- not stored.
--
-- CHANGES FROM v4:
--   REMOVED   Object, Collection, MeasurementSiteType (out of scope: the
--             database holds reference scans, not scans of objects).
--             Specimen.ObjectID, Specimen.SourceID, Specimen.SourceNotes,
--             Measurement.ObjectSpotDescription, PointX_cm, PointY_cm and
--             MeasurementSiteTypeID are removed with them.
--   REMOVED   Source and SpecimenType tables. Specimen.SpecimenSource and
--             Specimen.SpecimenType are now free text.
--   REMOVED   Tag and TaggedEntity tables. Specimen.Tags is now a text
--             column (labels separated by a semicolon).
--   REMOVED   SpectralFile. Measurement now holds FilePath (required),
--             Checksum and UploadedAt.
--   REMOVED   Identification (matching results are not stored; a junction
--             table between Measurement and Material could be added later).
--   REMOVED   Institution table. Operator.Institution is now text.
--   REMOVED   AcquisitionModeType table and Measurement.AcquisitionModeID.
--             InstrumentConfiguration.AcquisitionMode is text, limited to
--             'ER-IR' or 'ATR' by a CHECK rule.
--   REMOVED   InstrumentConfiguration.AngleOfIncidence.
--   ADDED     InstrumentConfiguration.Detector (default 'LN-MCT').
--   ADDED     CHECK rules: Measurement.IntensityMode = 'Absorbance';
--             Measurement.ScanDate in the format YYYY-MM-DD.
--
-- A field is required (NOT NULL) only where the data dictionary marks it
-- NOT NULL. Every other field is optional.
--
-- NOTE: SQLite enforces foreign keys only when PRAGMA foreign_keys = ON
-- for the connection. No ON DELETE action is set, so the default
-- (NO ACTION) applies: a row cannot be deleted while another row points to it.
-- ============================================================

PRAGMA foreign_keys = ON;


-- ---------- Materials and specimens ----------

CREATE TABLE Material (
    MaterialID INTEGER PRIMARY KEY AUTOINCREMENT,
    MaterialName TEXT UNIQUE NOT NULL,
    ChemicalFormula TEXT,              -- plain text, e.g. 'CaCO3'
    IsSynthetic TEXT                   -- Y = synthetic, N = natural, empty = not stated
        CHECK (IsSynthetic IN ('Y', 'N')),
    Description TEXT,
    ChemicalClass TEXT                 -- optional, e.g. 'Carbonate', 'Oxide'; several separated by a semicolon
);

CREATE TABLE Specimen (
    SpecimenID INTEGER PRIMARY KEY AUTOINCREMENT,
    SpecimenType TEXT,                 -- free text, e.g. 'mineral fragment', 'ground mineral', 'powder pigment'
    PreparationNotes TEXT,
    MaterialID INTEGER,                -- the material of the specimen; known for standards
    SpecimenSource TEXT,               -- who supplied the piece, free text
    Tags TEXT,                         -- labels separated by a semicolon, e.g. 'needs-atr-recollection'
    ImageReference TEXT,
    FOREIGN KEY (MaterialID) REFERENCES Material(MaterialID)
);


-- ---------- People and instrumentation ----------

CREATE TABLE Operator (
    OperatorID INTEGER PRIMARY KEY AUTOINCREMENT,
    Name TEXT,
    Email TEXT,
    Institution TEXT                   -- free text
);

CREATE TABLE Instrument (
    InstrumentID INTEGER PRIMARY KEY AUTOINCREMENT,
    InstrumentName TEXT,
    Model TEXT,
    Manufacturer TEXT,
    SerialNumber TEXT UNIQUE,             -- from the maker's label; optional
    LabAssetID TEXT UNIQUE                -- the lab's own inventory number; optional
);

CREATE TABLE InstrumentConfiguration (
    InstrumentConfigurationID INTEGER PRIMARY KEY AUTOINCREMENT,
    InstrumentID INTEGER NOT NULL,        -- the instrument these settings belong to
    Resolution TEXT,
    NumberOfScans INTEGER,
    BeamSplitterType TEXT,
    Detector TEXT DEFAULT 'LN-MCT',
    AcquisitionMode TEXT NOT NULL         -- ER-IR or ATR
        CHECK (AcquisitionMode IN ('ER-IR', 'ATR')),
    ApertureSize TEXT,
    Notes TEXT,
    FOREIGN KEY (InstrumentID) REFERENCES Instrument(InstrumentID)
);


-- ---------- The measurement and its spectrum ----------

CREATE TABLE Measurement (
    MeasurementID INTEGER PRIMARY KEY AUTOINCREMENT,
    SpecimenID INTEGER NOT NULL,
    InstrumentConfigurationID INTEGER NOT NULL,   -- the configuration names the instrument and the mode
    IntensityMode TEXT NOT NULL DEFAULT 'Absorbance'
        CHECK (IntensityMode = 'Absorbance'),
    SpectrumData TEXT NOT NULL            -- JSON array of [wavenumber, intensity] pairs
        CHECK (json_valid(SpectrumData)),
    OperatorID INTEGER,
    ReferenceMeasurementID INTEGER,       -- links an ER-IR scan to its ATR standard
    ScanDate TEXT                         -- date of the scan, YYYY-MM-DD
        CHECK (ScanDate IS NULL OR ScanDate GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
    SpecimenSpotDescription TEXT,         -- where on the specimen the spot is
    ImageReference TEXT,
    FilePath TEXT NOT NULL,               -- the .dpt file (required)
    Checksum TEXT,                        -- SHA-256 of the file
    UploadedAt TEXT DEFAULT CURRENT_TIMESTAMP,
    Notes TEXT,
    FOREIGN KEY (SpecimenID) REFERENCES Specimen(SpecimenID),
    FOREIGN KEY (InstrumentConfigurationID) REFERENCES InstrumentConfiguration(InstrumentConfigurationID),
    FOREIGN KEY (OperatorID) REFERENCES Operator(OperatorID),
    FOREIGN KEY (ReferenceMeasurementID) REFERENCES Measurement(MeasurementID)
);


-- ---------- Indexes on the columns most often joined ----------

CREATE INDEX idx_measurement_specimen  ON Measurement(SpecimenID);
CREATE INDEX idx_measurement_reference ON Measurement(ReferenceMeasurementID);
CREATE INDEX idx_specimen_material     ON Specimen(MaterialID);
