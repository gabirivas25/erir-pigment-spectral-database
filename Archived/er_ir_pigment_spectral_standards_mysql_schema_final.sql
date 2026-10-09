-- ============================================================
-- Pigment Spectral Standards Database — MySQL-compatible version
-- Converted from the SQLite schema (Revised_Schema_v2_REVIEW.sql)
-- ============================================================

CREATE TABLE MineralClass (
    ClassID INT AUTO_INCREMENT PRIMARY KEY,
    ClassName VARCHAR(100) UNIQUE NOT NULL
);

CREATE TABLE LocationType (
    LocationTypeID INT AUTO_INCREMENT PRIMARY KEY,
    TypeName VARCHAR(100) UNIQUE NOT NULL
);

CREATE TABLE AcquisitionModeType (
    AcquisitionModeID INT AUTO_INCREMENT PRIMARY KEY,
    ModeName VARCHAR(50) UNIQUE NOT NULL
);

CREATE TABLE Institution (
    InstitutionID INT AUTO_INCREMENT PRIMARY KEY,
    InstitutionName TEXT,
    Location TEXT
);

CREATE TABLE Operator (
    OperatorID INT AUTO_INCREMENT PRIMARY KEY,
    Name TEXT,
    Email TEXT,
    InstitutionID INT,
    FOREIGN KEY (InstitutionID) REFERENCES Institution(InstitutionID)
);

CREATE TABLE Collection (
    CollectionID INT AUTO_INCREMENT PRIMARY KEY,
    CollectionName TEXT,
    Location TEXT,
    InstitutionID INT,
    FOREIGN KEY (InstitutionID) REFERENCES Institution(InstitutionID)
);

CREATE TABLE MeasurementLocation (
    LocationID INT AUTO_INCREMENT PRIMARY KEY,
    LocationTypeID INT NOT NULL,
    LocationName TEXT,
    City TEXT,
    Country TEXT,
    Latitude REAL,
    Longitude REAL,
    Notes TEXT,
    FOREIGN KEY (LocationTypeID) REFERENCES LocationType(LocationTypeID)
);

CREATE TABLE Object (
    ObjectID INT AUTO_INCREMENT PRIMARY KEY,
    ObjectName TEXT,
    Description TEXT,
    CollectionID INT,
    SiteLocationID INT,
    FOREIGN KEY (CollectionID) REFERENCES Collection(CollectionID),
    FOREIGN KEY (SiteLocationID) REFERENCES MeasurementLocation(LocationID)
);

CREATE TABLE Material (
    MaterialID INT AUTO_INCREMENT PRIMARY KEY,
    MaterialName VARCHAR(255) UNIQUE NOT NULL,
    ClassID INT,
    ChemicalFormula TEXT,
    Description TEXT,
    FOREIGN KEY (ClassID) REFERENCES MineralClass(ClassID)
);

CREATE TABLE Sample (
    SampleID INT AUTO_INCREMENT PRIMARY KEY,
    SampleType TEXT,
    PreparationNotes TEXT,
    MeasurementPointDescription TEXT,
    MaterialID INT,
    ObjectID INT,
    FOREIGN KEY (MaterialID) REFERENCES Material(MaterialID),
    FOREIGN KEY (ObjectID) REFERENCES Object(ObjectID)
);

CREATE TABLE Instrument (
    InstrumentID INT AUTO_INCREMENT PRIMARY KEY,
    InstrumentName TEXT,
    Model TEXT,
    Manufacturer TEXT
);

CREATE TABLE InstrumentConfiguration (
    InstrumentConfigurationID INT AUTO_INCREMENT PRIMARY KEY,
    Resolution TEXT,
    AngleOfIncidence REAL,
    NumberOfScans INT,
    BeamSplitterType TEXT,
    ApertureSize TEXT
);

CREATE TABLE EnvironmentConditions (
    ConditionID INT AUTO_INCREMENT PRIMARY KEY,
    Temperature REAL,
    Humidity REAL,
    Pressure REAL,
    IlluminationType TEXT
);

CREATE TABLE Measurement (
    MeasurementID INT AUTO_INCREMENT PRIMARY KEY,
    SampleID INT NOT NULL,
    InstrumentID INT NOT NULL,
    OperatorID INT,
    InstrumentConfigurationID INT NOT NULL,
    ConditionID INT,
    LocationID INT,
    DateTime TEXT,
    Notes TEXT,
    FOREIGN KEY (SampleID) REFERENCES Sample(SampleID),
    FOREIGN KEY (InstrumentID) REFERENCES Instrument(InstrumentID),
    FOREIGN KEY (OperatorID) REFERENCES Operator(OperatorID),
    FOREIGN KEY (InstrumentConfigurationID) REFERENCES InstrumentConfiguration(InstrumentConfigurationID),
    FOREIGN KEY (ConditionID) REFERENCES EnvironmentConditions(ConditionID),
    FOREIGN KEY (LocationID) REFERENCES MeasurementLocation(LocationID)
);

CREATE TABLE Spectrum (
    SpectrumID INT AUTO_INCREMENT PRIMARY KEY,
    MeasurementID INT NOT NULL,
    AcquisitionModeID INT NOT NULL,
    ReferenceSpectrumID INT,
    SourceFilename TEXT,
    Notes TEXT,
    FOREIGN KEY (MeasurementID) REFERENCES Measurement(MeasurementID),
    FOREIGN KEY (AcquisitionModeID) REFERENCES AcquisitionModeType(AcquisitionModeID),
    FOREIGN KEY (ReferenceSpectrumID) REFERENCES Spectrum(SpectrumID)
);

CREATE TABLE SpectralDataPoint (
    DataPointID INT AUTO_INCREMENT PRIMARY KEY,
    SpectrumID INT NOT NULL,
    Wavenumber REAL NOT NULL,
    Intensity REAL NOT NULL,
    FOREIGN KEY (SpectrumID) REFERENCES Spectrum(SpectrumID)
);

CREATE TABLE OpticalArtifacts (
    ArtifactID INT AUTO_INCREMENT PRIMARY KEY,
    SpectrumID INT NOT NULL,
    ArtifactType TEXT,
    CorrectionApplied INT DEFAULT 0,
    Notes TEXT,
    FOREIGN KEY (SpectrumID) REFERENCES Spectrum(SpectrumID)
);

CREATE TABLE Preprocessing (
    StepID INT AUTO_INCREMENT PRIMARY KEY,
    SpectrumID INT NOT NULL,
    StepType TEXT,
    Parameters TEXT,
    DateTime TEXT,
    FOREIGN KEY (SpectrumID) REFERENCES Spectrum(SpectrumID)
);

CREATE TABLE SpectralFile (
    FileID INT AUTO_INCREMENT PRIMARY KEY,
    SpectrumID INT NOT NULL,
    FileRole TEXT,
    FilePath TEXT,
    FileType TEXT,
    Description TEXT,
    UploadedAt DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (SpectrumID) REFERENCES Spectrum(SpectrumID)
);

CREATE TABLE Tag (
    TagID INT AUTO_INCREMENT PRIMARY KEY,
    TagLabel VARCHAR(100) UNIQUE NOT NULL
);

CREATE TABLE TaggedEntity (
    TagID INT NOT NULL,
    EntityType VARCHAR(20) CHECK (EntityType IN ('Sample', 'Measurement', 'Spectrum')),
    EntityID INT NOT NULL,
    FOREIGN KEY (TagID) REFERENCES Tag(TagID),
    PRIMARY KEY (TagID, EntityType, EntityID)
);
