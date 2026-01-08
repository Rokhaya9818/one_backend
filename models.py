from sqlalchemy import Column, Integer, String, Text, DateTime, Date, Enum as SQLEnum, Float
from sqlalchemy.sql import func
from database import Base
import enum

class UserRole(str, enum.Enum):
    user = "user"
    admin = "admin"

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    open_id = Column(String(64), unique=True, nullable=False)
    name = Column(Text, nullable=True)
    email = Column(String(320), nullable=True)
    login_method = Column(String(64), nullable=True)
    role = Column(SQLEnum(UserRole), default=UserRole.user, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    last_signed_in = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class Malaria(Base):
    __tablename__ = "malaria"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    indicator_code = Column(String(100), nullable=False)
    indicator_name = Column(Text, nullable=False)
    year = Column(Integer, nullable=False)
    value = Column(String(100), nullable=True)
    numeric_value = Column(String(50), nullable=True)
    low_value = Column(String(50), nullable=True)
    high_value = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class Tuberculose(Base):
    __tablename__ = "tuberculose"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    indicator_code = Column(String(100), nullable=False)
    indicator_name = Column(Text, nullable=False)
    year = Column(Integer, nullable=False)
    value = Column(String(100), nullable=True)
    numeric_value = Column(String(50), nullable=True)
    low_value = Column(String(50), nullable=True)
    high_value = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class FvrHumain(Base):
    __tablename__ = "fvr_humain"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    date_bilan = Column(Date, nullable=False)
    cas_confirmes = Column(Integer, nullable=False, default=0)
    deces = Column(Integer, nullable=False, default=0)
    gueris = Column(Integer, nullable=False, default=0)
    region = Column(String(100), nullable=True)
    district = Column(String(100), nullable=True)
    taux_letalite = Column(String(20), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class FvrAnimal(Base):
    __tablename__ = "fvr_animal"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    annee = Column(Integer, nullable=False)
    cas = Column(Integer, nullable=False, default=0)
    espece = Column(String(100), nullable=True)
    region = Column(String(100), nullable=True)
    localisation = Column(String(100), nullable=True)
    source = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class GrippeAviaire(Base):
    __tablename__ = "grippe_aviaire"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    report_id = Column(String(100), unique=True, nullable=False)
    date_rapport = Column(Date, nullable=False)
    region = Column(String(100), nullable=True)
    espece = Column(String(100), nullable=True)
    maladie = Column(Text, nullable=True)
    cas_confirmes = Column(Integer, nullable=False, default=0)
    deces = Column(Integer, nullable=False, default=0)
    statut_epidemie = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class Pluviometrie(Base):
    __tablename__ = "pluviometrie"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    date_observation = Column(Date, nullable=False)
    region = Column(String(100), nullable=True)
    pluie_moyenne = Column(String(20), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class PollutionAir(Base):
    __tablename__ = "pollution_air"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    annee = Column(Integer, nullable=False)
    zone = Column(String(50), nullable=False)
    concentration_pm25 = Column(String(20), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class AnimalMortalite(Base):
    __tablename__ = "animal_mortalite"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    date_observation = Column(Date, nullable=False)
    departement = Column(String(100), nullable=True)
    nombre_morts = Column(Integer, nullable=False, default=0)
    espece = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class Region(Base):
    __tablename__ = "regions"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    nom = Column(String(100), unique=True, nullable=False)
    code = Column(String(10), unique=True, nullable=False)
    latitude = Column(String(20), nullable=True)
    longitude = Column(String(20), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class MalariaRegional(Base):
    __tablename__ = "malaria_regional"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    region = Column(String(100), nullable=False)
    annee = Column(Integer, nullable=False)
    cas_confirmes = Column(Integer, nullable=False, default=0)
    deces = Column(Integer, nullable=False, default=0)
    prevalence_rdt = Column(Float, nullable=True)
    prevalence_microscopie = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
