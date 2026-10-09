-- ============================================================
-- Pigment Spectral Standards Database: SCHEMA v4 (MySQL 8)
-- Prepared by Maria Gabriela Rivas Carmona, University of Padova
-- ============================================================
-- Same design as Revised_Schema_v4.sql (SQLite): 18 tables
-- (15 data tables + 3 pick lists).
--
-- Differences from the SQLite file, forced by MySQL:
--   * AUTO_INCREMENT and ENGINE=InnoDB instead of AUTOINCREMENT.
--   * Columns that must be UNIQUE are VARCHAR(255) (MySQL cannot index
--     an unlimited TEXT column without a length).
--   * Measurement.SpectrumData uses the native JSON type, which rejects
--     invalid JSON by itself.
--   * IsSynthetic is TINYINT(1): 1 = synthetic, 0 = natural, NULL = not stated.
--   * CHECK constraints need MySQL 8.0.16 or later.
--
-- A field is required (NOT NULL) only where the field list in the
-- revision document marks it with *. Every other field is optional.
-- ============================================================

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;


-- ---------- Pick lists (3) ----------

CREATE TABLE AcquisitionModeType (
    AcquisitionModeID INT AUTO_INCREMENT PRIMARY KEY,
    ModeName VARCHAR(255) NOT NULL UNIQUE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE MeasurementSiteType (
    MeasurementSiteTypeID INT AUTO_INCREMENT PRIMARY KEY,
    TypeName VARCHAR(255) NOT NULL UNIQUE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE SpecimenType (
    SpecimenTypeID INT AUTO_INCREMENT PRIMARY KEY,
    TypeName VARCHAR(255) NOT NULL UNIQUE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT INTO AcquisitionModeType (ModeName) VALUES ('ER-IR'), ('ATR');
INSERT INTO MeasurementSiteType (TypeName) VALUES
    ('Laboratory'), ('In Situ - Interior'), ('In Situ - Exterior');
INSERT INTO SpecimenType (TypeName) VALUES
    ('powder pigment'), ('ground mineral'), ('mineral fragment');


-- ---------- Institutions, operators, collections, objects ----------

CREATE TABLE Institution (
    InstitutionID INT AUTO_INCREMENT PRIMARY KEY,
    InstitutionName VARCHAR(255)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE Operator (
    OperatorID INT AUTO_INCREMENT PRIMARY KEY,
    Name VARCHAR(255),
    Email VARCHAR(255),
    InstitutionID INT,
    FOREIGN KEY (InstitutionID) REFERENCES Institution(InstitutionID)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE Collection (
    CollectionID INT AUTO_INCREMENT PRIMARY KEY,
    CollectionName VARCHAR(255),
    InstitutionID INT,                 -- optional: excavation finds, for example,
                                        -- are a collection with no institution
    Notes TEXT,
    FOREIGN KEY (InstitutionID) REFERENCES Institution(InstitutionID)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE Object (
    ObjectID INT AUTO_INCREMENT PRIMARY KEY,
    ObjectName VARCHAR(255),
    Description TEXT,
    CollectionID INT,
    Origin TEXT,                       -- where the object came from originally
    ObjectDate VARCHAR(255),           -- date or period, as text (often approximate)
    ProvenanceNotes TEXT,
    CurrentAddress TEXT,               -- where the object is now
    CoordinateReference TEXT,          -- reference point for Measurement.PointX_cm / PointY_cm
    Notes TEXT,
    ImageReference VARCHAR(1024),      -- file name, ID or URL; image is held outside the database
    FOREIGN KEY (CollectionID) REFERENCES Collection(CollectionID)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- ---------- Materials, sources, specimens ----------

CREATE TABLE Material (
    MaterialID INT AUTO_INCREMENT PRIMARY KEY,
    MaterialName VARCHAR(255) NOT NULL UNIQUE,
    ChemicalFormula VARCHAR(255),      -- plain text, e.g. 'CaCO3'
    IsSynthetic TINYINT(1),            -- 1 = synthetic, 0 = natural, NULL = not stated
    Description TEXT,
    CHECK (IsSynthetic IN (0, 1))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE Source (
    SourceID INT AUTO_INCREMENT PRIMARY KEY,
    SourceName VARCHAR(255) NOT NULL UNIQUE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE Specimen (
    SpecimenID INT AUTO_INCREMENT PRIMARY KEY,
    SpecimenTypeID INT,
    PreparationNotes TEXT,
    SourceNotes TEXT,                  -- e.g. product number, or a group of similar pieces
    MaterialID INT,                    -- known for standards, empty for unknowns
    ObjectID INT,                      -- for pieces of a real object
    SourceID INT,
    ImageReference VARCHAR(1024),
    FOREIGN KEY (SpecimenTypeID) REFERENCES SpecimenType(SpecimenTypeID),
    FOREIGN KEY (MaterialID) REFERENCES Material(MaterialID),
    FOREIGN KEY (ObjectID) REFERENCES Object(ObjectID),
    FOREIGN KEY (SourceID) REFERENCES Source(SourceID)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- ---------- Instrumentation ----------

CREATE TABLE Instrument (
    InstrumentID INT AUTO_INCREMENT PRIMARY KEY,
    InstrumentName VARCHAR(255),
    Model VARCHAR(255),
    Manufacturer VARCHAR(255)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE InstrumentConfiguration (
    InstrumentConfigurationID INT AUTO_INCREMENT PRIMARY KEY,
    Resolution VARCHAR(255),
    AngleOfIncidence DOUBLE,
    NumberOfScans INT,
    BeamSplitterType VARCHAR(255),
    ApertureSize VARCHAR(255),
    Notes TEXT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE EnvironmentConditions (
    ConditionID INT AUTO_INCREMENT PRIMARY KEY,
    Temperature DOUBLE,
    Humidity DOUBLE,
    Pressure DOUBLE,
    IlluminationType VARCHAR(255)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- ---------- The measurement and its spectrum ----------

CREATE TABLE Measurement (
    MeasurementID INT AUTO_INCREMENT PRIMARY KEY,
    SpecimenID INT NOT NULL,
    InstrumentID INT NOT NULL,
    InstrumentConfigurationID INT NOT NULL,
    AcquisitionModeID INT NOT NULL,       -- ER-IR or ATR
    IntensityMode VARCHAR(50) NOT NULL DEFAULT 'Absorbance',
    SpectrumData JSON NOT NULL,           -- array of [wavenumber, intensity] pairs
    OperatorID INT,
    ConditionID INT,
    MeasurementSiteTypeID INT,
    ReferenceMeasurementID INT,           -- links an ER-IR scan to its ATR standard
    `DateTime` VARCHAR(64),
    ObjectSpotDescription TEXT,           -- where on a real object the spot is
    SpecimenSpotDescription TEXT,         -- where on the specimen the spot is
    PointX_cm DOUBLE,                     -- cm from Object.CoordinateReference
    PointY_cm DOUBLE,
    ImageReference VARCHAR(1024),
    Notes TEXT,
    FOREIGN KEY (SpecimenID) REFERENCES Specimen(SpecimenID),
    FOREIGN KEY (InstrumentID) REFERENCES Instrument(InstrumentID),
    FOREIGN KEY (InstrumentConfigurationID) REFERENCES InstrumentConfiguration(InstrumentConfigurationID),
    FOREIGN KEY (AcquisitionModeID) REFERENCES AcquisitionModeType(AcquisitionModeID),
    FOREIGN KEY (OperatorID) REFERENCES Operator(OperatorID),
    FOREIGN KEY (ConditionID) REFERENCES EnvironmentConditions(ConditionID),
    FOREIGN KEY (MeasurementSiteTypeID) REFERENCES MeasurementSiteType(MeasurementSiteTypeID),
    FOREIGN KEY (ReferenceMeasurementID) REFERENCES Measurement(MeasurementID)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE SpectralFile (
    FileID INT AUTO_INCREMENT PRIMARY KEY,
    MeasurementID INT NOT NULL,
    FilePath VARCHAR(1024) NOT NULL,      -- the .dpt file (required)
    FileType VARCHAR(50),                 -- filled in at upload, from the extension
    FileSize BIGINT,                      -- bytes, filled in at upload
    Checksum VARCHAR(128),                -- fingerprint, filled in at upload
    UploadedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    Description TEXT,
    FOREIGN KEY (MeasurementID) REFERENCES Measurement(MeasurementID)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- ---------- Matching results (written by the matching software) ----------

CREATE TABLE Identification (
    SpecimenID INT NOT NULL,
    MaterialID INT NOT NULL,
    MeasurementID INT NOT NULL,
    PRIMARY KEY (SpecimenID, MaterialID, MeasurementID),
    FOREIGN KEY (SpecimenID) REFERENCES Specimen(SpecimenID),
    FOREIGN KEY (MaterialID) REFERENCES Material(MaterialID),
    FOREIGN KEY (MeasurementID) REFERENCES Measurement(MeasurementID)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- ---------- Tags for data-quality notes ----------

CREATE TABLE Tag (
    TagID INT AUTO_INCREMENT PRIMARY KEY,
    TagLabel VARCHAR(255) NOT NULL UNIQUE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE TaggedEntity (
    TagID INT NOT NULL,
    EntityType VARCHAR(20) NOT NULL,
    EntityID INT NOT NULL,
    PRIMARY KEY (TagID, EntityType, EntityID),
    FOREIGN KEY (TagID) REFERENCES Tag(TagID),
    CHECK (EntityType IN ('Specimen', 'Measurement'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

SET FOREIGN_KEY_CHECKS = 1;
