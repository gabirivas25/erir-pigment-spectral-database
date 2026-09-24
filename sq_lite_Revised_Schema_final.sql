-- ============================================================
-- Pigment Spectral Standards Database — REVISED SCHEMA (v2)
-- Prepared by Maria Gabriela Rivas Carmona, University of Padova
-- ============================================================
-- Table count: 21
--
-- ADDED (relative to the original 16-table schema):
--   - MineralClass         (normalizes Material.Category into a lookup table)
--   - LocationType         (normalizes measurement location into Lab /
--                           In Situ - Interior / In Situ - Exterior)
--   - AcquisitionModeType  (normalizes Spectrum.AcquisitionMode from free
--                           text into a lookup table: 'ER-IR' or 'ATR')
--   - MeasurementLocation  (where a measurement was physically taken,
--                           with optional GPS for future in-situ work)
--   - OpticalArtifacts     (structured record of which optical effects —
--                           reststrahlen, specular reflection, scattering —
--                           were observed in a given spectrum, and whether
--                           any correction was applied)
--   - SpectralFile         (restored, to pair with Preprocessing as a
--                           raw-vs-processed audit trail)
--
-- MODIFIED:
--   - Material     : Category (free text) replaced by ClassID (FK to
--                    MineralClass); added ChemicalFormula
--   - Collection   : added InstitutionID (FK to Institution)
--   - Object       : added SiteLocationID (FK to MeasurementLocation) —
--                    a real object's permanent physical location, distinct
--                    from where any single measurement session took place
--   - Sample       : added MeasurementPointDescription
--   - Measurement  : added LocationID (FK to MeasurementLocation);
--                    SampleID, InstrumentID, and InstrumentConfigurationID
--                    are all now required (NOT NULL)
--   - Spectrum     : AcquisitionMode (free text) replaced by
--                    AcquisitionModeID (FK to AcquisitionModeType);
--                    added ReferenceSpectrumID (self-referencing FK,
--                    explicitly links an ER-IR scan to its ATR standard)
--   - Preprocessing: Timestamp renamed to DateTime for naming consistency
--                    with Measurement.DateTime (not auto-filled — must
--                    reflect when the processing step actually occurred)
--
-- UNCHANGED from the original, working database:
--   Institution, Operator, Instrument, InstrumentConfiguration,
--   EnvironmentConditions, SpectralDataPoint, Tag, TaggedEntity
-- ============================================================


-- ---------- Lookup tables ----------

CREATE TABLE MineralClass (
    ClassID INTEGER PRIMARY KEY AUTOINCREMENT,
    ClassName TEXT UNIQUE NOT NULL   -- 'Carbonate', 'Oxide', 'Silicate', 'Sulfide'
);

CREATE TABLE LocationType (
    LocationTypeID INTEGER PRIMARY KEY AUTOINCREMENT,
    TypeName TEXT UNIQUE NOT NULL    -- 'Laboratory', 'In Situ - Interior', 'In Situ - Exterior'
);

CREATE TABLE AcquisitionModeType (
    AcquisitionModeID INTEGER PRIMARY KEY AUTOINCREMENT,
    ModeName TEXT UNIQUE NOT NULL    -- 'ER-IR', 'ATR'
);


-- ---------- Institutional / provenance context ----------

CREATE TABLE Institution (
    InstitutionID INTEGER PRIMARY KEY AUTOINCREMENT,
    InstitutionName TEXT,
    Location TEXT
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
    Location TEXT,
    InstitutionID INTEGER,             -- NEW: which institution this collection belongs to
    FOREIGN KEY (InstitutionID) REFERENCES Institution(InstitutionID)
);

CREATE TABLE Object (
    ObjectID INTEGER PRIMARY KEY AUTOINCREMENT,
    ObjectName TEXT,
    Description TEXT,
    CollectionID INTEGER,
    SiteLocationID INTEGER,            -- NEW: the real object's permanent physical
                                        -- location (e.g., a specific chapel), distinct
                                        -- from MeasurementLocation, which records where
                                        -- a specific measurement session took place
    FOREIGN KEY (CollectionID) REFERENCES Collection(CollectionID),
    FOREIGN KEY (SiteLocationID) REFERENCES MeasurementLocation(LocationID)
);


-- ---------- Materials and samples ----------

CREATE TABLE Material (
    MaterialID INTEGER PRIMARY KEY AUTOINCREMENT,
    MaterialName TEXT UNIQUE NOT NULL,
    ClassID INTEGER,
    ChemicalFormula TEXT,             -- e.g., 'CaCO3', '2CuCO3.Cu(OH)2'
    Description TEXT,
    FOREIGN KEY (ClassID) REFERENCES MineralClass(ClassID)
);

CREATE TABLE Sample (
    SampleID INTEGER PRIMARY KEY AUTOINCREMENT,
    SampleType TEXT,
    PreparationNotes TEXT,
    MeasurementPointDescription TEXT, -- where on a real Object this measurement was taken,
                                       -- e.g., 'lower register, red drapery, kneeling figure'
                                       -- (kept separate from PreparationNotes, which describes
                                       -- lab sample preparation, not point-of-measurement)
    MaterialID INTEGER,
    ObjectID INTEGER,                 -- optional: link to a real heritage object, if applicable
    FOREIGN KEY (MaterialID) REFERENCES Material(MaterialID),
    FOREIGN KEY (ObjectID) REFERENCES Object(ObjectID)
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
    ApertureSize TEXT
);

CREATE TABLE EnvironmentConditions (
    ConditionID INTEGER PRIMARY KEY AUTOINCREMENT,
    Temperature REAL,
    Humidity REAL,
    Pressure REAL,
    IlluminationType TEXT
);


-- ---------- Where a measurement was taken ----------

CREATE TABLE MeasurementLocation (
    LocationID INTEGER PRIMARY KEY AUTOINCREMENT,
    LocationTypeID INTEGER NOT NULL,
    LocationName TEXT,                -- e.g., 'University of Padova FTIR Lab',
                                       --       'Peruzzi Chapel, Santa Croce, Florence'
    City TEXT,
    Country TEXT,
    Latitude REAL,                    -- optional, NULL for lab measurements
    Longitude REAL,                   -- optional, NULL for lab measurements
    Notes TEXT,
    FOREIGN KEY (LocationTypeID) REFERENCES LocationType(LocationTypeID)
);


-- ---------- The measurement event itself ----------

CREATE TABLE Measurement (
    MeasurementID INTEGER PRIMARY KEY AUTOINCREMENT,
    SampleID INTEGER NOT NULL,
    InstrumentID INTEGER NOT NULL,
    OperatorID INTEGER,
    InstrumentConfigurationID INTEGER NOT NULL,
    ConditionID INTEGER,
    LocationID INTEGER,               -- NEW: where this measurement was taken
    DateTime TEXT,
    Notes TEXT,
    FOREIGN KEY (SampleID) REFERENCES Sample(SampleID),
    FOREIGN KEY (InstrumentID) REFERENCES Instrument(InstrumentID),
    FOREIGN KEY (OperatorID) REFERENCES Operator(OperatorID),
    FOREIGN KEY (InstrumentConfigurationID) REFERENCES InstrumentConfiguration(InstrumentConfigurationID),
    FOREIGN KEY (ConditionID) REFERENCES EnvironmentConditions(ConditionID),
    FOREIGN KEY (LocationID) REFERENCES MeasurementLocation(LocationID)
);


-- ---------- The resulting spectrum and its data ----------

CREATE TABLE Spectrum (
    SpectrumID INTEGER PRIMARY KEY AUTOINCREMENT,
    MeasurementID INTEGER NOT NULL,
    AcquisitionModeID INTEGER NOT NULL, -- FK -> AcquisitionModeType ('ER-IR' or 'ATR')
    ReferenceSpectrumID INTEGER,       -- NEW: links an ER-IR scan to its ATR standard
    SourceFilename TEXT,
    Notes TEXT,
    FOREIGN KEY (MeasurementID) REFERENCES Measurement(MeasurementID),
    FOREIGN KEY (AcquisitionModeID) REFERENCES AcquisitionModeType(AcquisitionModeID),
    FOREIGN KEY (ReferenceSpectrumID) REFERENCES Spectrum(SpectrumID)
);

CREATE TABLE SpectralDataPoint (
    DataPointID INTEGER PRIMARY KEY AUTOINCREMENT,
    SpectrumID INTEGER NOT NULL,
    Wavenumber REAL NOT NULL,
    Intensity REAL NOT NULL,
    FOREIGN KEY (SpectrumID) REFERENCES Spectrum(SpectrumID)
);

CREATE TABLE OpticalArtifacts (
    ArtifactID INTEGER PRIMARY KEY AUTOINCREMENT,
    SpectrumID INTEGER NOT NULL,
    ArtifactType TEXT,                 -- 'ReststrahlenEffect', 'SpecularReflection',
                                        -- 'LightScattering', 'AnomalousDispersion'
    CorrectionApplied INTEGER DEFAULT 0,   -- 0 = false, 1 = true (SQLite has no native BOOLEAN)
    Notes TEXT,
    FOREIGN KEY (SpectrumID) REFERENCES Spectrum(SpectrumID)
);

CREATE TABLE Preprocessing (
    StepID INTEGER PRIMARY KEY AUTOINCREMENT,
    SpectrumID INTEGER NOT NULL,
    StepType TEXT,                     -- e.g., 'SNV normalization', 'baseline correction'
    Parameters TEXT,
    DateTime TEXT,                     -- NOT automated: must reflect when the processing
                                        -- step was actually performed on the data (e.g.,
                                        -- sourced from file metadata or a processing log),
                                        -- entered explicitly during population -- NOT the
                                        -- moment this database row happens to be inserted,
                                        -- which could be much later and would be inaccurate
    FOREIGN KEY (SpectrumID) REFERENCES Spectrum(SpectrumID)
);

CREATE TABLE SpectralFile (
    FileID INTEGER PRIMARY KEY AUTOINCREMENT,
    SpectrumID INTEGER NOT NULL,
    FileRole TEXT,                     -- 'Raw' or 'Processed' — which stage this file represents
    FilePath TEXT,                     -- full path or URL
    FileType TEXT,                     -- e.g., 'DPT', 'CSV', 'JCAMP-DX'
    Description TEXT,
    UploadedAt TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (SpectrumID) REFERENCES Spectrum(SpectrumID)
);


-- ---------- Flexible tagging for data-quality issues, etc. ----------

CREATE TABLE Tag (
    TagID INTEGER PRIMARY KEY AUTOINCREMENT,
    TagLabel TEXT UNIQUE NOT NULL
);

CREATE TABLE TaggedEntity (
    TagID INTEGER NOT NULL,
    EntityType TEXT CHECK(EntityType IN ('Sample', 'Measurement', 'Spectrum')),
    EntityID INTEGER NOT NULL,
    FOREIGN KEY (TagID) REFERENCES Tag(TagID),
    PRIMARY KEY (TagID, EntityType, EntityID)
);
