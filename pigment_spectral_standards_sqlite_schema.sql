-- ============================================================
-- Pigment Spectral Standards Database: SCHEMA v4 (SQLite)
-- Prepared by Maria Gabriela Rivas Carmona, University of Padova
-- ============================================================
-- Table count: 18 (15 data tables + 3 pick lists)
--
-- CHANGES FROM v3 (after feedback from Prof. Orio):
--   MERGED    Spectrum and SpectralDataPoint into Measurement. A measurement
--             has exactly one spectrum, stored as a JSON array of
--             [wavenumber, intensity] pairs in Measurement.SpectrumData.
--   RENAMED   Sample -> Specimen.
--   RENAMED   LocationType -> MeasurementSiteType.
--   ADDED     Source (who supplied a specimen), SpecimenType (pick list),
--             Identification (links a specimen to a material it matched).
--   ADDED     Material.IsSynthetic; Object.Origin, ObjectDate,
--             ProvenanceNotes, CurrentAddress, Notes; Collection.Notes;
--             InstrumentConfiguration.Notes; ImageReference columns;
--             Measurement spot description fields.
--   REMOVED   Spectrum, SpectralDataPoint, PostProcessing,
--             MeasurementLocation, MineralClass.
--   REMOVED   Institution.Location, Collection.Location.
--   CHANGED   SpectralFile: now one required .dpt file per measurement;
--             FileSize and Checksum added. FileRole is removed.
--
-- A field is required (NOT NULL) only where the field list in the
-- revision document marks it with *. Every other field is optional.
--
-- NOTE: SQLite enforces foreign keys only when PRAGMA foreign_keys = ON
-- for the connection. DB Browser for SQLite turns it on by default.
-- ============================================================

PRAGMA foreign_keys = ON;


-- ---------- Pick lists (3) ----------

CREATE TABLE AcquisitionModeType (
    AcquisitionModeID INTEGER PRIMARY KEY AUTOINCREMENT,
    ModeName TEXT UNIQUE NOT NULL
);

CREATE TABLE MeasurementSiteType (
    MeasurementSiteTypeID INTEGER PRIMARY KEY AUTOINCREMENT,
    TypeName TEXT UNIQUE NOT NULL
);

CREATE TABLE SpecimenType (
    SpecimenTypeID INTEGER PRIMARY KEY AUTOINCREMENT,
    TypeName TEXT UNIQUE NOT NULL
);

INSERT INTO AcquisitionModeType (ModeName) VALUES ('ER-IR'), ('ATR');
INSERT INTO MeasurementSiteType (TypeName) VALUES
    ('Laboratory'), ('In Situ - Interior'), ('In Situ - Exterior');
INSERT INTO SpecimenType (TypeName) VALUES
    ('powder pigment'), ('ground mineral'), ('mineral fragment');


-- ---------- Institutions, operators, collections, objects ----------

CREATE TABLE Institution (
    InstitutionID INTEGER PRIMARY KEY AUTOINCREMENT,
    InstitutionName TEXT
);

CREATE TABLE Operator (
    OperatorID INTEGER PRIMARY KEY AUTOINCREMENT,
    Name TEXT,
    Email TEXT,
    InstitutionID INTEGER,
    FOREIGN KEY (InstitutionID) REFERENCES Institution(InstitutionID)
);

CREATE TABLE Collection (
    CollectionID INTEGER PRIMARY KEY AUTOINCREMENT,
    CollectionName TEXT,
    InstitutionID INTEGER,             -- optional: excavation finds, for example,
                                        -- are a collection with no institution
    Notes TEXT,
    FOREIGN KEY (InstitutionID) REFERENCES Institution(InstitutionID)
);

CREATE TABLE Object (
    ObjectID INTEGER PRIMARY KEY AUTOINCREMENT,
    ObjectName TEXT,
    Description TEXT,
    CollectionID INTEGER,
    Origin TEXT,                       -- where the object came from originally
    ObjectDate TEXT,                   -- date or period, as text (often approximate)
    ProvenanceNotes TEXT,
    CurrentAddress TEXT,               -- where the object is now
    CoordinateReference TEXT,          -- reference point for Measurement.PointX_cm / PointY_cm
    Notes TEXT,
    ImageReference TEXT,               -- file name, ID or URL; image is held outside the database
    FOREIGN KEY (CollectionID) REFERENCES Collection(CollectionID)
);


-- ---------- Materials, sources, specimens ----------

CREATE TABLE Material (
    MaterialID INTEGER PRIMARY KEY AUTOINCREMENT,
    MaterialName TEXT UNIQUE NOT NULL,
    ChemicalFormula TEXT,              -- plain text, e.g. 'CaCO3'
    IsSynthetic INTEGER                -- 1 = synthetic, 0 = natural, NULL = not stated
        CHECK (IsSynthetic IN (0, 1)),
    Description TEXT
);

CREATE TABLE Source (
    SourceID INTEGER PRIMARY KEY AUTOINCREMENT,
    SourceName TEXT UNIQUE NOT NULL
);

CREATE TABLE Specimen (
    SpecimenID INTEGER PRIMARY KEY AUTOINCREMENT,
    SpecimenTypeID INTEGER,
    PreparationNotes TEXT,
    SourceNotes TEXT,                  -- e.g. product number, or a group of similar pieces
    MaterialID INTEGER,                -- known for standards, empty for unknowns
    ObjectID INTEGER,                  -- for pieces of a real object
    SourceID INTEGER,
    ImageReference TEXT,
    FOREIGN KEY (SpecimenTypeID) REFERENCES SpecimenType(SpecimenTypeID),
    FOREIGN KEY (MaterialID) REFERENCES Material(MaterialID),
    FOREIGN KEY (ObjectID) REFERENCES Object(ObjectID),
    FOREIGN KEY (SourceID) REFERENCES Source(SourceID)
);


-- ---------- Instrumentation ----------

CREATE TABLE Instrument (
    InstrumentID INTEGER PRIMARY KEY AUTOINCREMENT,
    InstrumentName TEXT,
    Model TEXT,
    Manufacturer TEXT
);

CREATE TABLE InstrumentConfiguration (
    InstrumentConfigurationID INTEGER PRIMARY KEY AUTOINCREMENT,
    Resolution TEXT,
    AngleOfIncidence REAL,
    NumberOfScans INTEGER,
    BeamSplitterType TEXT,
    ApertureSize TEXT,
    Notes TEXT
);

CREATE TABLE EnvironmentConditions (
    ConditionID INTEGER PRIMARY KEY AUTOINCREMENT,
    Temperature REAL,
    Humidity REAL,
    Pressure REAL,
    IlluminationType TEXT
);


-- ---------- The measurement and its spectrum ----------

CREATE TABLE Measurement (
    MeasurementID INTEGER PRIMARY KEY AUTOINCREMENT,
    SpecimenID INTEGER NOT NULL,
    InstrumentID INTEGER NOT NULL,
    InstrumentConfigurationID INTEGER NOT NULL,
    AcquisitionModeID INTEGER NOT NULL,   -- ER-IR or ATR
    IntensityMode TEXT NOT NULL DEFAULT 'Absorbance',
    SpectrumData TEXT NOT NULL            -- JSON array of [wavenumber, intensity] pairs
        CHECK (json_valid(SpectrumData)),
    OperatorID INTEGER,
    ConditionID INTEGER,
    MeasurementSiteTypeID INTEGER,
    ReferenceMeasurementID INTEGER,       -- links an ER-IR scan to its ATR standard
    DateTime TEXT,
    ObjectSpotDescription TEXT,           -- where on a real object the spot is
    SpecimenSpotDescription TEXT,         -- where on the specimen the spot is
    PointX_cm REAL,                       -- cm from Object.CoordinateReference
    PointY_cm REAL,
    ImageReference TEXT,
    Notes TEXT,
    FOREIGN KEY (SpecimenID) REFERENCES Specimen(SpecimenID),
    FOREIGN KEY (InstrumentID) REFERENCES Instrument(InstrumentID),
    FOREIGN KEY (InstrumentConfigurationID) REFERENCES InstrumentConfiguration(InstrumentConfigurationID),
    FOREIGN KEY (AcquisitionModeID) REFERENCES AcquisitionModeType(AcquisitionModeID),
    FOREIGN KEY (OperatorID) REFERENCES Operator(OperatorID),
    FOREIGN KEY (ConditionID) REFERENCES EnvironmentConditions(ConditionID),
    FOREIGN KEY (MeasurementSiteTypeID) REFERENCES MeasurementSiteType(MeasurementSiteTypeID),
    FOREIGN KEY (ReferenceMeasurementID) REFERENCES Measurement(MeasurementID)
);

CREATE TABLE SpectralFile (
    FileID INTEGER PRIMARY KEY AUTOINCREMENT,
    MeasurementID INTEGER NOT NULL,
    FilePath TEXT NOT NULL,               -- the .dpt file (required)
    FileType TEXT,                        -- filled in at upload, from the extension
    FileSize INTEGER,                     -- bytes, filled in at upload
    Checksum TEXT,                        -- fingerprint, filled in at upload
    UploadedAt TEXT DEFAULT CURRENT_TIMESTAMP,
    Description TEXT,
    FOREIGN KEY (MeasurementID) REFERENCES Measurement(MeasurementID)
);


-- ---------- Matching results (written by the matching software) ----------

CREATE TABLE Identification (
    SpecimenID INTEGER NOT NULL,
    MaterialID INTEGER NOT NULL,
    MeasurementID INTEGER NOT NULL,
    PRIMARY KEY (SpecimenID, MaterialID, MeasurementID),
    FOREIGN KEY (SpecimenID) REFERENCES Specimen(SpecimenID),
    FOREIGN KEY (MaterialID) REFERENCES Material(MaterialID),
    FOREIGN KEY (MeasurementID) REFERENCES Measurement(MeasurementID)
);


-- ---------- Tags for data-quality notes ----------

CREATE TABLE Tag (
    TagID INTEGER PRIMARY KEY AUTOINCREMENT,
    TagLabel TEXT UNIQUE NOT NULL
);

CREATE TABLE TaggedEntity (
    TagID INTEGER NOT NULL,
    EntityType TEXT NOT NULL CHECK (EntityType IN ('Specimen', 'Measurement')),
    EntityID INTEGER NOT NULL,
    PRIMARY KEY (TagID, EntityType, EntityID),
    FOREIGN KEY (TagID) REFERENCES Tag(TagID)
);


-- ---------- Indexes on the columns most often joined ----------

CREATE INDEX idx_measurement_specimen  ON Measurement(SpecimenID);
CREATE INDEX idx_measurement_reference ON Measurement(ReferenceMeasurementID);
CREATE INDEX idx_specimen_material     ON Specimen(MaterialID);
CREATE INDEX idx_spectralfile_meas     ON SpectralFile(MeasurementID);
